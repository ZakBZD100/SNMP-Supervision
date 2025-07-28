import gc
import time
from typing import Optional, Dict, List
from easysnmp import Session
import logging
from logging.handlers import RotatingFileHandler
from .snmp_server import SNMPServer
from .snmp_switch import SNMPSwitch

#logging
log_file = 'snmp_debug.log'
file_handler = RotatingFileHandler(log_file, maxBytes=1024 * 1024 * 5, backupCount=5)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logging.basicConfig(level=logging.INFO)

class SNMPService:
    def __init__(self):
        self.server = SNMPServer()
        self.switch = SNMPSwitch()
        self.cache = {}
        self.cache_timeout = 2
        self.cpu_cache = {}

    def _get_cached_data(self, key: str):
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < self.cache_timeout:
                return data
            else:
                del self.cache[key]
        return None

    def _set_cached_data(self, key: str, data):
        self.cache[key] = (data, time.time())

    def _safe_int(self, val):
        if val is None or val == '' or val == b'':
            return 0
        try:
            return int(str(val))
        except (ValueError, TypeError):
            return 0

    def _safe_str(self, val):
        if val is None:
            return ''
        return str(val)

    def get_equipment_name(self, ip: str, community: str) -> str:
        try:
            session = Session(hostname=ip, community=community, version=2, timeout=1, retries=0)
            name = self._safe_str(session.get('1.3.6.1.2.1.1.5.0').value)
            if not name or name.strip().lower() in ["switch", "cisco", "default", "", "unknown"]:
                desc = self._safe_str(session.get('1.3.6.1.2.1.1.1.0').value)
                if "Cisco IOS" in desc:
                    return f"Switch Cisco IOS ({ip})"
                return f"Switch Cisco GNS3 ({ip})"
            return name
        except Exception as e:
            logger.warning(f"Unable to retrieve equipment name {ip}: {e}")
            return f"Switch Cisco GNS3 ({ip})"
        finally:
            gc.collect()

    def _get_main_disk(self, ip: str, community: str):
        try:
            session = Session(hostname=ip, community=community, version=2, timeout=1, retries=0)
            for index in ["36", "1", "2", "3"]:
                try:
                    path_oid = f"1.3.6.1.2.1.25.2.3.1.3.{index}"
                    path = self._safe_str(session.get(path_oid).value)
                    if path.strip() == "/":
                        total_oid = f"1.3.6.1.2.1.25.2.3.1.5.{index}"
                        used_oid = f"1.3.6.1.2.1.25.2.3.1.6.{index}"
                        alloc_oid = f"1.3.6.1.2.1.25.2.3.1.4.{index}"
                        total_units = self._safe_int(session.get(total_oid).value)
                        used_units = self._safe_int(session.get(used_oid).value)
                        allocation_unit = self._safe_int(session.get(alloc_oid).value)
                        if total_units > 0 and allocation_unit > 0:
                            total_bytes = total_units * allocation_unit
                            used_bytes = used_units * allocation_unit
                            return total_bytes, used_bytes, path
                except Exception:
                    continue
            return 0, 0, None
        except Exception as e:
            logger.error(f"Disk retrieval error for {ip}: {e}")
            return 0, 0, None
        finally:
            gc.collect()

    def _get_cpu_percent(self, ip: str, community: str) -> float:
        try:
            session = Session(hostname=ip, community=community, version=2, timeout=1, retries=0)
            cpu_user_oid = '1.3.6.1.4.1.2021.11.50.0'
            cpu_system_oid = '1.3.6.1.4.1.2021.11.52.0'
            cpu_idle_oid = '1.3.6.1.4.1.2021.11.53.0'
            user = self._safe_int(session.get(cpu_user_oid).value)
            system = self._safe_int(session.get(cpu_system_oid).value)
            idle = self._safe_int(session.get(cpu_idle_oid).value)
            now = time.time()
            prev = self.cpu_cache.get(ip)
            self.cpu_cache[ip] = {'user': user, 'system': system, 'idle': idle, 'time': now}
            if prev:
                delta_total = (user + system + idle) - (prev['user'] + prev['system'] + prev['idle'])
                delta_idle = idle - prev['idle']
                if delta_total > 0:
                    cpu_percent = 100 * (1 - (delta_idle / delta_total))
                    return max(0, min(cpu_percent, 100))
            time.sleep(1)
            user2 = self._safe_int(session.get(cpu_user_oid).value)
            system2 = self._safe_int(session.get(cpu_system_oid).value)
            idle2 = self._safe_int(session.get(cpu_idle_oid).value)
            delta_total = (user2 + system2 + idle2) - (user + system + idle)
            delta_idle = idle2 - idle
            if delta_total > 0:
                cpu_percent = 100 * (1 - (delta_idle / delta_total))
                return max(0, min(cpu_percent, 100))
            return 0.0
        except Exception as e:
            logger.error(f"CPU calculation error for {ip}: {e}")
            return 0.0
        finally:
            gc.collect()

    def get_server_metrics(self, ip: str, community: str) -> Optional[Dict]:
        cache_key = f"server_metrics_{ip}_{community}"
        cached = self._get_cached_data(cache_key)
        if cached:
            return cached
        try:
            session = Session(hostname=ip, community=community, version=2, timeout=1, retries=0)
            oids = {
                'system_name': '1.3.6.1.2.1.1.5.0',
                'cpu_user': '1.3.6.1.4.1.2021.11.50.0',
                'cpu_system': '1.3.6.1.4.1.2021.11.52.0',
                'cpu_idle': '1.3.6.1.4.1.2021.11.53.0',
                'mem_total': '1.3.6.1.4.1.2021.4.5.0',
                'mem_free': '1.3.6.1.4.1.2021.4.6.0'
            }
            results = {}
            errors = {}
            for key, oid in oids.items():
                try:
                    result = session.get(oid)
                    if result and result.value:
                        results[key] = str(result.value)
                    else:
                        results[key] = None
                        errors[key] = f"No value for OID {oid}"
                except Exception as e:
                    results[key] = None
                    errors[key] = str(e)
            try:
                cpu_percent = self._get_cpu_percent(ip, community)
            except Exception as e:
                errors['cpu_calc'] = str(e)
                cpu_percent = 0
            try:
                mem_total_kb = int(results['mem_total'] or 0)
                mem_free_kb = int(results['mem_free'] or 0)
                mem_used_kb = mem_total_kb - mem_free_kb
                memory_percent = (mem_used_kb / mem_total_kb * 100) if mem_total_kb > 0 else 0
            except Exception as e:
                errors['mem_calc'] = str(e)
                memory_percent = 0
                mem_total_kb = 0
                mem_used_kb = 0
                mem_free_kb = 0
            try:
                disk_total_bytes, disk_used_bytes, disk_path = self._get_main_disk(ip, community)
                disk_percent = (disk_used_bytes / disk_total_bytes * 100) if disk_total_bytes > 0 else 0
            except Exception as e:
                errors['disk_calc'] = str(e)
                disk_percent = 0
                disk_total_bytes = 0
                disk_used_bytes = 0
                disk_path = ""
            try:
                equipment_name = self.get_equipment_name(ip, community)
            except Exception as e:
                errors['name'] = str(e)
                equipment_name = f'Server-{ip}'
            result = {
                'ip': ip,
                'community': community,
                'cpu_usage': max(0, min(cpu_percent, 100)),
                'memory_usage': max(0, min(memory_percent, 100)),
                'disk_usage': max(0, min(disk_percent, 100)),
                'uptime': 0,  #can be added if needed
                'total_memory_bytes': mem_total_kb * 1024,
                'used_memory_bytes': (mem_total_kb - mem_free_kb) * 1024,
                'total_disk_bytes': disk_total_bytes,
                'used_disk_bytes': disk_used_bytes,
                'disk_path': disk_path,
                'equipment_name': equipment_name,
                'errors': errors,
                'timestamp': time.time()
            }
            self._set_cached_data(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"Server metrics error for {ip}: {e}")
            return None
        finally:
            gc.collect()

    def get_switch_metrics(self, ip: str, community: str) -> Optional[Dict]:
                    #logger.info(f"SNMP DEBUG: Start switch collection {ip} {community}")
        cache_key = f"switch_metrics_{ip}_{community}"
        cached = self._get_cached_data(cache_key)
        if cached:
            return cached
        try:
            session = Session(hostname=ip, community=community, version=2, timeout=1, retries=0)
            oids = {
                'system_name': '1.3.6.1.2.1.1.5.0',
                'if_descr': '1.3.6.1.2.1.2.2.1.2',
                'if_admin_status': '1.3.6.1.2.1.2.2.1.7',
                'if_oper_status': '1.3.6.1.2.1.2.2.1.8',
                'if_speed': '1.3.6.1.2.1.2.2.1.5',
                'if_in_octets': '1.3.6.1.2.1.2.2.1.10',
                'if_out_octets': '1.3.6.1.2.1.2.2.1.16',
                'if_in_errors': '1.3.6.1.2.1.2.2.1.14',
                'if_out_errors': '1.3.6.1.2.1.2.2.1.20'
            }
            interfaces = []
            try:
                equipment_name = self.get_equipment_name(ip, community)
                if_descr_results = session.walk(oids['if_descr'])
                if_admin_results = session.walk(oids['if_admin_status'])
                if_oper_results = session.walk(oids['if_oper_status'])
                if_speed_results = session.walk(oids['if_speed'])
                for i, descr_result in enumerate(if_descr_results):
                    interface_index = i + 1
                    try:
                        in_octets = session.get(f"{oids['if_in_octets']}.{interface_index}")
                        out_octets = session.get(f"{oids['if_out_octets']}.{interface_index}")
                        in_errors = session.get(f"{oids['if_in_errors']}.{interface_index}")
                        out_errors = session.get(f"{oids['if_out_errors']}.{interface_index}")
                        admin_status = int(if_admin_results[i].value) if i < len(if_admin_results) else 0
                        oper_status = int(if_oper_results[i].value) if i < len(if_oper_results) else 0
                        speed = int(if_speed_results[i].value) if i < len(if_speed_results) else 0
                        in_octets_val = int(in_octets.value) if in_octets else 0
                        out_octets_val = int(out_octets.value) if out_octets else 0
                        #logger.info(f"SNMP DEBUG: {ip} interface {interface_index} {descr_result.value} in_octets={in_octets_val} out_octets={out_octets_val}")
                        interface = {
                            'index': interface_index,
                            'name': str(descr_result.value),
                            'admin_status': admin_status,
                            'oper_status': oper_status,
                            'speed': speed,
                            'admin_status_text': 'up' if admin_status == 1 else 'down',
                            'oper_status_text': 'up' if oper_status == 1 else 'down',
                            'traffic': {
                                'in_octets': in_octets_val,
                                'out_octets': out_octets_val,
                                'in_errors': int(in_errors.value) if in_errors else 0,
                                'out_errors': int(out_errors.value) if out_errors else 0,
                                'error': None
                            },
                            #legacy fields for history/graphs
                            'traffic_in': in_octets_val,
                            'traffic_out': out_octets_val,
                        }
                        interfaces.append(interface)
                    except Exception as e:
                        interface = {
                            'index': interface_index,
                            'name': str(descr_result.value),
                            'error': str(e)
                        }
                        interfaces.append(interface)
            except Exception as e:
                logger.error(f"Switch interfaces error for {ip}: {e}")
            result = {
                'ip': ip,
                'community': community,
                'system': {'system_name': equipment_name},
                'interfaces': interfaces,
                'connected_devices': self.get_connected_devices(ip, community),
                'timestamp': time.time()
            }
            self._set_cached_data(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"Switch metrics error for {ip}: {e}")
            return None
        finally:
            gc.collect()

    def get_equipment_metrics(self, equipment) -> Optional[Dict]:
        try:
            community = equipment.community or 'public'
            ip = equipment.ip
            if equipment.type == 'server':
                return self.get_server_metrics(ip, community)
            elif equipment.type == 'switch':
                return self.get_switch_metrics(ip, community)
            else:
                logger.warning(f"Unsupported equipment type: {equipment.type}")
                return None
        except Exception as e:
            logger.error(f"Error retrieving metrics for {getattr(equipment, 'ip', 'unknown')}: {e}")
            return None

    def test_connection(self, ip: str, community: str, timeout: int = 1, retries: int = 0) -> bool:
        try:
            session = Session(hostname=ip, community=community, version=2, timeout=timeout, retries=retries)
            result = session.get('1.3.6.1.2.1.1.1.0')
            return result is not None and result.value is not None
        except Exception as e:
            logger.warning(f"SNMP test_connection error: {e}")
            return False
        finally:
            gc.collect()

    def get_server_metrics_realtime(self, ip: str, community: str):
        return self.server.get_server_metrics_realtime(ip, community)

    def get_switch_interfaces_realtime(self, ip: str, community: str):
        return self.switch.get_switch_interfaces_realtime(ip, community)

    def get_connected_devices(self, ip: str, community: str):
        return self.switch.get_connected_devices(ip, community)

    def get_connected_devices_alternative(self, ip: str, community: str):
        return self.switch.get_connected_devices_alternative(ip, community)

    def get_interface_traffic_realtime(self, ip: str, community: str, interface_index: int):
        return self.switch.get_interface_traffic_realtime(ip, community, interface_index)

#global SNMP service instance
snmp_service = SNMPService()
