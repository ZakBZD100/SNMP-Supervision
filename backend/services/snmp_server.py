import gc
import time
from typing import Dict
from .snmp_base import SNMPBase, logger

class SNMPServer(SNMPBase):
    def _get_main_disk(self, ip: str, community: str) -> tuple:
        """Gets main disk metrics"""
        try:
            #local import to avoid memory issues
            from easysnmp import Session
            session = Session(hostname=ip, community=community, version=2, timeout=1, retries=0)
            
            #oids for disks (HOST-RESOURCES-MIB)
            disk_oids = {
                'disk_path_base': '1.3.6.1.2.1.25.2.3.1.3',
                'disk_total_base': '1.3.6.1.2.1.25.2.3.1.5',
                'disk_used_base': '1.3.6.1.2.1.25.2.3.1.6',
                'disk_alloc_unit': '1.3.6.1.2.1.25.2.3.1.4'
            }
            
            #try to find root disk (index 36 is often the main disk)
            for index in ["36", "1", "2", "3"]:
                try:
                    path_oid = f"{disk_oids['disk_path_base']}.{index}"
                    path_result = session.get(path_oid)
                    path = self._safe_str(path_result.value if path_result else None)
                    
                    #logger.info(f"Disk path for index {index}: '{path}'")
                    
                    #check if it's the root disk
                    if path.strip() == "/":
                        total_oid = f"{disk_oids['disk_total_base']}.{index}"
                        used_oid = f"{disk_oids['disk_used_base']}.{index}"
                        alloc_oid = f"{disk_oids['disk_alloc_unit']}.{index}"
                        
                        total_result = session.get(total_oid)
                        used_result = session.get(used_oid)
                        alloc_result = session.get(alloc_oid)
                        
                        total_units = self._safe_int(total_result.value if total_result else None)
                        used_units = self._safe_int(used_result.value if used_result else None)
                        allocation_unit = self._safe_int(alloc_result.value if alloc_result else None)
                        
                        #logger.info(f"Root disk values: total={total_units}, used={used_units}, alloc_unit={allocation_unit}")
                        
                        if total_units > 0 and allocation_unit > 0:
                            total_bytes = total_units * allocation_unit
                            used_bytes = used_units * allocation_unit
                            #logger.info(f"Root disk bytes: total={total_bytes}, used={used_bytes}")
                            return total_bytes, used_bytes, path
                except Exception as e:
                    logger.debug(f"Error for index {index}: {e}")
                    continue
            
            return 0, 0, None
            
        except Exception as e:
            logger.error(f"Disk retrieval error for {ip}: {e}")
            return 0, 0, None
        finally:
            gc.collect()

    def _get_cpu_percent(self, ip: str, community: str) -> float:
        """Calculates CPU percentage correctly with delta"""
        try:
            #local import to avoid memory issues
            from easysnmp import Session
            session = Session(hostname=ip, community=community, version=2, timeout=1, retries=0)
            
            #oids for CPU
            cpu_user_oid = '1.3.6.1.4.1.2021.11.50.0'
            cpu_system_oid = '1.3.6.1.4.1.2021.11.52.0'
            cpu_idle_oid = '1.3.6.1.4.1.2021.11.53.0'
            
            #get raw values
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
            
            #if no previous measurement, wait 1s and retry
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

    def get_server_metrics_realtime(self, ip: str, community: str) -> Dict:
        """Gets real-time server metrics - OPTIMIZED with disk"""
        cache_key = f"server_metrics_{ip}_{community}"
        cached = self._get_cached_data(cache_key)
        if cached:
            return cached

        try:
            #local import to avoid memory issues
            from easysnmp import Session
            session = Session(hostname=ip, community=community, version=2, timeout=1, retries=0)
            
            #oids for servers - corrected and verified
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
            
            #get basic metrics
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
            
            #calculate CPU with correct delta
            try:
                cpu_percent = self._get_cpu_percent(ip, community)
            except Exception as e:
                errors['cpu_calc'] = str(e)
                cpu_percent = 0
            
            #calculate memory correctly (in KB) with detailed values
            try:
                mem_total_kb = int(results['mem_total'] or 0)
                mem_free_kb = int(results['mem_free'] or 0)
                mem_used_kb = mem_total_kb - mem_free_kb
                memory_percent = (mem_used_kb / mem_total_kb * 100) if mem_total_kb > 0 else 0
                
                #convert to MB and GB for display
                mem_total_mb = mem_total_kb / 1024
                mem_used_mb = mem_used_kb / 1024
                mem_free_mb = mem_free_kb / 1024
                
                mem_total_gb = mem_total_mb / 1024
                mem_used_gb = mem_used_mb / 1024
                mem_free_gb = mem_free_mb / 1024
                
            except Exception as e:
                errors['mem_calc'] = str(e)
                memory_percent = 0
                mem_total_kb = 0
                mem_used_kb = 0
                mem_free_kb = 0
                mem_total_mb = 0
                mem_used_mb = 0
                mem_free_mb = 0
                mem_total_gb = 0
                mem_used_gb = 0
                mem_free_gb = 0
            
            #get disk metrics
            try:
                disk_total_bytes, disk_used_bytes, disk_path = self._get_main_disk(ip, community)
                disk_percent = (disk_used_bytes / disk_total_bytes * 100) if disk_total_bytes > 0 else 0
                
                #convert to KB, MB, GB for display
                disk_total_kb = disk_total_bytes / 1024
                disk_used_kb = disk_used_bytes / 1024
                disk_free_kb = disk_total_kb - disk_used_kb
                
                disk_total_mb = disk_total_kb / 1024
                disk_used_mb = disk_used_kb / 1024
                disk_free_mb = disk_free_kb / 1024
                
                disk_total_gb = disk_total_mb / 1024
                disk_used_gb = disk_used_mb / 1024
                disk_free_gb = disk_free_mb / 1024
                
            except Exception as e:
                errors['disk_calc'] = str(e)
                disk_percent = 0
                disk_total_bytes = 0
                disk_used_bytes = 0
                disk_free_bytes = 0
                disk_total_kb = 0
                disk_used_kb = 0
                disk_free_kb = 0
                disk_total_mb = 0
                disk_used_mb = 0
                disk_free_mb = 0
                disk_total_gb = 0
                disk_used_gb = 0
                disk_free_gb = 0
                disk_path = ""
            
            #get real equipment name
            try:
                equipment_name = self.get_equipment_name(ip, community)
            except Exception as e:
                errors['name'] = str(e)
                equipment_name = f'Server-{ip}'
            
            result = {
                'ip': ip,
                'community': community,
                'metrics': {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory_percent,
                    'disk_percent': disk_percent,
                    'system_name': equipment_name,
                    #detailed values for memory
                    'memory_total_kb': mem_total_kb,
                    'memory_used_kb': mem_used_kb,
                    'memory_free_kb': mem_free_kb,
                    'memory_total_mb': round(mem_total_mb, 2),
                    'memory_used_mb': round(mem_used_mb, 2),
                    'memory_free_mb': round(mem_free_mb, 2),
                    'memory_total_gb': round(mem_total_gb, 2),
                    'memory_used_gb': round(mem_used_gb, 2),
                    'memory_free_gb': round(mem_free_gb, 2),
                    #detailed values for disk
                    'disk_total_bytes': disk_total_bytes,
                    'disk_used_bytes': disk_used_bytes,
                    'disk_free_bytes': disk_total_bytes - disk_used_bytes,
                    'disk_total_kb': round(disk_total_kb, 2),
                    'disk_used_kb': round(disk_used_kb, 2),
                    'disk_free_kb': round(disk_free_kb, 2),
                    'disk_total_mb': round(disk_total_mb, 2),
                    'disk_used_mb': round(disk_used_mb, 2),
                    'disk_free_mb': round(disk_free_mb, 2),
                    'disk_total_gb': round(disk_total_gb, 2),
                    'disk_used_gb': round(disk_used_gb, 2),
                    'disk_free_gb': round(disk_free_gb, 2),
                    'disk_path': disk_path
                },
                'errors': errors,
                'timestamp': time.time()
            }
            self._cache_data(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"Server metrics error for {ip}: {e}")
            return {
                'ip': ip,
                'community': community,
                'metrics': {
                    'cpu_percent': 0, 
                    'memory_percent': 0, 
                    'disk_percent': 0,
                    'system_name': f'Server-{ip}',
                    'memory_total_kb': 0,
                    'memory_used_kb': 0,
                    'memory_free_kb': 0,
                    'memory_total_mb': 0,
                    'memory_used_mb': 0,
                    'memory_free_mb': 0,
                    'memory_total_gb': 0,
                    'memory_used_gb': 0,
                    'memory_free_gb': 0,
                    'disk_total_bytes': 0,
                    'disk_used_bytes': 0,
                    'disk_free_bytes': 0,
                    'disk_total_kb': 0,
                    'disk_used_kb': 0,
                    'disk_free_kb': 0,
                    'disk_total_mb': 0,
                    'disk_used_mb': 0,
                    'disk_free_mb': 0,
                    'disk_total_gb': 0,
                    'disk_used_gb': 0,
                    'disk_free_gb': 0,
                    'disk_path': ""
                },
                'errors': {'exception': str(e)},
                'timestamp': time.time()
            }
        finally:
            gc.collect() 