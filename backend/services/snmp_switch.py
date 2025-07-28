import gc
import time
from typing import Dict, List, Optional
from .snmp_base import SNMPBase, logger

class SNMPSwitch(SNMPBase):
    def get_connected_devices_alternative(self, ip: str, community: str) -> List[Dict]:
        """Alternative method to retrieve MAC addresses - Different OIDs"""
        try:
            #local import to avoid memory issues
            from easysnmp import Session
            session = Session(hostname=ip, community=community, version=2, timeout=1, retries=0)
            
            #alternative OIDs for MAC addresses
            alternative_oids = [
                '1.3.6.1.2.1.17.4.3.1.1',  # dot1dTpFdbAddress (BRIDGE-MIB)
                '1.3.6.1.2.1.17.7.1.2.2.1.2',  # dot1qTpFdbAddress (Q-BRIDGE-MIB)
                '1.3.6.1.4.1.9.9.46.1.2.1.1.2',  # cdpCacheDeviceAddress (Cisco)
                '1.3.6.1.4.1.9.9.23.1.2.1.1.6',  # cdpCacheDevicePortId (Cisco)
            ]
            
            connected_devices = []
            
            for oid in alternative_oids:
                try:
                    #logger.info(f"Attempt with alternative OID: {oid}")
                    mac_addresses = session.walk(oid)
                    
                    if mac_addresses:
                        #logger.info(f"OID {oid} returned {len(mac_addresses)} results")
                        
                        for mac_result in mac_addresses[:5]:  #limit to 5 per OID
                            try:
                                #try to convert to MAC address
                                mac_bytes = bytes(mac_result.value)
                                if len(mac_bytes) == 6:  #standard MAC address
                                    mac_address = ':'.join(f'{b:02X}' for b in mac_bytes)
                                    
                                    device_info = {
                                        'mac_address': mac_address,
                                        'port_number': 0,
                                        'interface_name': f"Interface OID {oid}",
                                        'status': "Detected",
                                        'status_code': 1
                                    }
                                    
                                    connected_devices.append(device_info)
                                    #logger.info(f"Device found with OID {oid}: {mac_address}")
                            except Exception as e:
                                logger.debug(f"MAC conversion error with OID {oid}: {e}")
                                continue
                    else:
                        #logger.info(f"OID {oid} returned no results")
                        
                except Exception as e:
                    logger.debug(f"Error with OID {oid}: {e}")
                    continue
                
            #logger.info(f"Total devices found with alternative OIDs: {len(connected_devices)}")
            return connected_devices
                
        except Exception as e:
            logger.error(f"Error in get_connected_devices_alternative for {ip}: {e}")
            return []
        finally:
            gc.collect()

    def get_connected_devices(self, ip: str, community: str) -> List[Dict]:
        """Retrieves MAC addresses connected to switch with complete port/ifIndex/interface mapping"""
        try:
            from easysnmp import Session
            session = Session(hostname=ip, community=community, version=2, timeout=1, retries=0)
            mac_oids = {
                'dot1d_tp_fdb_address': '1.3.6.1.2.1.17.4.3.1.1',
                'dot1d_tp_fdb_port': '1.3.6.1.2.1.17.4.3.1.2',
                'dot1d_tp_fdb_status': '1.3.6.1.2.1.17.4.3.1.3'
            }
            #1. get all MAC addresses
            mac_addresses = session.walk(mac_oids['dot1d_tp_fdb_address'])
            #2. get all associated ports
            mac_ports = session.walk(mac_oids['dot1d_tp_fdb_port'])
            #3. get bridge port -> ifIndex mapping
            bridge_ports = session.walk('1.3.6.1.2.1.17.1.4.1.2')
            port_to_ifindex = {int(str(bp.oid).split('.')[-1]): int(bp.value) for bp in bridge_ports}
            #4. get ifIndex -> interface name mapping
            if_descrs = session.walk('1.3.6.1.2.1.2.2.1.2')
            ifindex_to_name = {int(str(desc.oid).split('.')[-1]): str(desc.value) for desc in if_descrs}
            #5. build connected devices list
            connected_devices = []
            for mac_result in mac_addresses:
                #extract MAC index from OID
                oid_str = str(mac_result.oid)
                oid_parts = oid_str.split('.')
                mac_index = '.'.join(oid_parts[-6:])
                #MAC conversion correction: supports bytes and integer list, and readable format
                if isinstance(mac_result.value, bytes):
                    mac_bytes = mac_result.value
                elif isinstance(mac_result.value, str):
                    #if it's a string, try to parse as hex-string (ex: '0C 9C C7 7F 00 01')
                    try:
                        mac_bytes = bytes(int(x, 16) for x in mac_result.value.split())
                    except Exception:
                        # If it's a byte string, convert each char to int
                        mac_bytes = bytes([ord(c) for c in mac_result.value])
                else:
                    mac_bytes = b''
                mac_address = ':'.join(f'{b:02X}' for b in mac_bytes[:6]) if mac_bytes else str(mac_result.value)
                # Find associated port
                port_result = next((p for p in mac_ports if p.oid.endswith(mac_index)), None)
                port_number = int(port_result.value) if port_result and port_result.value else 0
                # Find ifIndex
                if_index = port_to_ifindex.get(port_number, None)
                # Find interface name
                interface_name = ifindex_to_name.get(if_index, f'Port {port_number}') if if_index else f'Port {port_number}'
                device_info = {
                    'mac_address': mac_address,
                    'port_number': port_number,
                    'interface_name': interface_name,
                    'status': 'Detected',
                    'status_code': 1
                }
                connected_devices.append(device_info)
            if not connected_devices:
                return [{
                    'mac_address': 'None',
                    'port_number': 0,
                    'interface_name': 'None',
                    'status': 'No connected device',
                    'status_code': 0
                }]
            return connected_devices
        except Exception as e:
            logger.error(f"Error in get_connected_devices for {ip}: {e}")
            return [{
                'mac_address': 'None',
                'port_number': 0,
                'interface_name': 'None',
                'status': 'SNMP Error',
                'status_code': 0
            }]
        finally:
            gc.collect()

    def get_switch_interfaces_realtime(self, ip: str, community: str) -> Dict:
        """Gets real-time switch interfaces with traffic - OPTIMIZED"""
        cache_key = f"switch_interfaces_{ip}_{community}"
        cached = self._get_cached_data(cache_key)
        if cached:
            return cached

        try:
            # Local import to avoid memory issues
            from easysnmp import Session
            session = Session(hostname=ip, community=community, version=2, timeout=1, retries=0)
            
            # OIDs for switch interfaces
            interface_oids = {
                'if_index': '1.3.6.1.2.1.2.2.1.1',
                'if_descr': '1.3.6.1.2.1.2.2.1.2',
                'if_admin_status': '1.3.6.1.2.1.2.2.1.7',
                'if_oper_status': '1.3.6.1.2.1.2.2.1.8',
                'if_speed': '1.3.6.1.2.1.2.2.1.5',
                'if_in_octets': '1.3.6.1.2.1.2.2.1.10',
                'if_out_octets': '1.3.6.1.2.1.2.2.1.16',
                'if_in_errors': '1.3.6.1.2.1.2.2.1.14',
                'if_out_errors': '1.3.6.1.2.1.2.2.1.20'
            }
            
            # System OIDs
            system_oids = {
                'system_name': '1.3.6.1.2.1.1.5.0',
                'system_uptime': '1.3.6.1.2.1.1.3.0'
            }
            
            interfaces = []
            errors = {}
            
            # Get system information
            system_info = {}
            for key, oid in system_oids.items():
                try:
                    result = session.get(oid)
                    if result and result.value:
                        system_info[key] = str(result.value)
                    else:
                        system_info[key] = None
                        errors[f'system_{key}'] = f"No value for OID {oid}"
                except Exception as e:
                    system_info[key] = None
                    errors[f'system_{key}'] = str(e)
            
            # Get interfaces
            try:
                # Get interface indices
                if_indices = session.walk(interface_oids['if_index'])
                
                for if_index_result in if_indices:
                    try:
                        if_index = int(if_index_result.value)
                        
                        # Get interface information
                        interface_data = {}
                        
                        for key, oid in interface_oids.items():
                            if key == 'if_index':
                                continue
                            
                            try:
                                full_oid = f"{oid}.{if_index}"
                                result = session.get(full_oid)
                                if result and result.value:
                                    interface_data[key] = str(result.value)
                                else:
                                    interface_data[key] = None
                            except Exception as e:
                                interface_data[key] = None
                                errors[f'interface_{if_index}_{key}'] = str(e)
                        
                        # Determine statuses
                        admin_status = int(interface_data.get('if_admin_status', 0))
                        oper_status = int(interface_data.get('if_oper_status', 0))
                        
                        admin_status_text = "up" if admin_status == 1 else "down"
                        oper_status_text = "up" if oper_status == 1 else "down"
                        
                        # Get speed
                        speed = int(interface_data.get('if_speed', 0))
                        
                        # Get traffic
                        in_octets = int(interface_data.get('if_in_octets', 0))
                        out_octets = int(interface_data.get('if_out_octets', 0))
                        in_errors = int(interface_data.get('if_in_errors', 0))
                        out_errors = int(interface_data.get('if_out_errors', 0))
                        
                        interface_info = {
                            'index': if_index,
                            'name': interface_data.get('if_descr', f'Interface {if_index}'),
                            'admin_status': admin_status,
                            'oper_status': oper_status,
                            'speed': speed,
                            'admin_status_text': admin_status_text,
                            'oper_status_text': oper_status_text,
                            'traffic': {
                                'in_octets': in_octets,
                                'out_octets': out_octets,
                                'in_errors': in_errors,
                                'out_errors': out_errors
                            }
                        }
                        
                        interfaces.append(interface_info)
                        
                    except Exception as e:
                        logger.error(f"Interface processing error {if_index_result.value}: {e}")
                        continue
                        
            except Exception as e:
                errors['interfaces_walk'] = str(e)
            
            # Get connected devices
            connected_devices = self.get_connected_devices(ip, community)
            
            result = {
                'system': {
                    'system_name': system_info.get('system_name', 'Unknown Switch'),
                    'system_uptime': int(system_info.get('system_uptime', 0))
                },
                'interfaces': interfaces,
                'connected_devices': connected_devices,
                'errors': errors,
                'timestamp': time.time()
            }
            
            # Cache
            self._cache_data(cache_key, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Switch interfaces retrieval error for {ip}: {e}")
            return {
                'system': {
                    'system_name': 'Connection Error',
                    'system_uptime': 0
                },
                'interfaces': [],
                'connected_devices': [],
                'errors': {'connection': str(e)},
                'timestamp': time.time()
            }
        finally:
            gc.collect()

    def get_interface_traffic_realtime(self, ip: str, community: str, interface_index: int) -> Optional[Dict]:
        """Gets real-time traffic for a specific interface"""
        try:
            # Local import to avoid memory issues
            from easysnmp import Session
            session = Session(hostname=ip, community=community, version=2, timeout=1, retries=0)
            
            # OIDs for traffic
            traffic_oids = {
                'if_in_octets': f'1.3.6.1.2.1.2.2.1.10.{interface_index}',
                'if_out_octets': f'1.3.6.1.2.1.2.2.1.16.{interface_index}',
                'if_in_errors': f'1.3.6.1.2.1.2.2.1.14.{interface_index}',
                'if_out_errors': f'1.3.6.1.2.1.2.2.1.20.{interface_index}',
                'if_speed': f'1.3.6.1.2.1.2.2.1.5.{interface_index}'
            }
            
            traffic_data = {}
            
            for key, oid in traffic_oids.items():
                try:
                    result = session.get(oid)
                    if result and result.value:
                        traffic_data[key] = int(result.value)
                    else:
                        traffic_data[key] = 0
                except Exception as e:
                    traffic_data[key] = 0
                    logger.warning(f"Traffic retrieval error {key} for interface {interface_index}: {e}")
            
            return {
                'in_octets': traffic_data.get('if_in_octets', 0),
                'out_octets': traffic_data.get('if_out_octets', 0),
                'in_errors': traffic_data.get('if_in_errors', 0),
                'out_errors': traffic_data.get('if_out_errors', 0),
                'speed': traffic_data.get('if_speed', 0),
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"Interface traffic retrieval error {interface_index} for {ip}: {e}")
            return None
        finally:
            gc.collect() 