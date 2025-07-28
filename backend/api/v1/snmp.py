from fastapi import APIRouter, Query, HTTPException
from backend.services.snmp_service import SNMPService
from backend.database.db import SessionLocal
from backend.models.equipment import Equipment
from typing import List, Dict, Any
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

router = APIRouter(prefix="/snmp", tags=["snmp"])
snmp_service = SNMPService()

#utility function to collect equipment metrics
def collect_device_metrics(equipment):
    try:
        ip = str(equipment.ip)
        community = str(equipment.community)
        #retry SNMP 2 times before going offline
        for attempt in range(2):
            try:
                if equipment.type == "server":
                    metrics = snmp_service.get_server_metrics_realtime(ip, community)
                    #if we have a real network/SNMP error (ex: timeout, unreachable), go offline
                    if metrics is None or (isinstance(metrics, dict) and metrics.get('errors', {}).get('cpu_calc', '').lower().find('timeout') != -1):
                        raise Exception('SNMP timeout')
                    status = "online"
                    return {
                        "id": equipment.id,
                        "name": equipment.name,
                        "ip": ip,
                        "community": community,
                        "type": equipment.type,
                        "status": status,
                        "last_seen": time.time(),
                        "cpu_percent": metrics['metrics']['cpu_percent'] if 'metrics' in metrics else None,
                        "memory_percent": metrics['metrics']['memory_percent'] if 'metrics' in metrics else None,
                        "disk_percent": metrics['metrics']['disk_percent'] if 'metrics' in metrics else None,
                        "error": metrics['errors'],
                    }
                elif equipment.type == "switch":
                    switch_data = snmp_service.get_switch_interfaces_realtime(ip, community)
                    if switch_data is None or (isinstance(switch_data, dict) and switch_data.get('errors', {}).get('interfaces_walk', '').lower().find('timeout') != -1):
                        raise Exception('SNMP timeout')
                    status = "online"
                    connected_devices = snmp_service.get_connected_devices(ip, community)
                    return {
                        "id": equipment.id,
                        "name": equipment.name,
                        "ip": ip,
                        "community": community,
                        "type": equipment.type,
                        "status": status,
                        "last_seen": time.time(),
                        "interfaces_count": len(switch_data.get("interfaces", [])),
                        "active_interfaces": len([i for i in switch_data.get("interfaces", []) if i.get("oper_status") == 1]),
                        "connected_devices": connected_devices,
                        "connected_devices_count": len(connected_devices),
                        "error": switch_data['errors'],
                    }
                else:
                    return {"id": equipment.id, "name": equipment.name, "ip": ip, "type": equipment.type, "status": "unknown", "error": "Unsupported type"}
            except Exception as e:
                if attempt == 1:
                    import traceback
                    print(traceback.format_exc())
                    return {"id": equipment.id, "name": equipment.name, "ip": str(equipment.ip), "type": equipment.type, "status": "offline", "error": str(e)}
                time.sleep(1) #small delay before retry
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return {"id": equipment.id, "name": equipment.name, "ip": str(equipment.ip), "type": equipment.type, "status": "offline", "error": str(e)}

@router.get("/devices")
def get_devices():
    db = SessionLocal()
    try:
        equipments = db.query(Equipment).all()
        devices = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(collect_device_metrics, eq) for eq in equipments]
            for future in as_completed(futures):
                devices.append(future.result())
        return devices
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return {"error": str(e), "trace": traceback.format_exc()}
    finally:
        db.close()

@router.get("/server/{equipment_id}/metrics")
def get_server_metrics(equipment_id: int):
    """Gets detailed real-time server metrics"""
    db = SessionLocal()
    try:
        equipment = db.query(Equipment).filter(Equipment.id == equipment_id, Equipment.type == "server").first()
        if not equipment:
            raise HTTPException(status_code=404, detail="Server not found")
        metrics = snmp_service.get_server_metrics_realtime(equipment.ip, equipment.community)
        return {
            "equipment": {
                "id": equipment.id,
                "name": equipment.name,
                "ip": equipment.ip,
                "community": equipment.community,
                "type": equipment.type
            },
            "metrics": metrics.get("metrics", {}),
            "errors": metrics.get("errors", {}),
            "timestamp": time.time()
        }
    finally:
        db.close()

@router.get("/switch/{equipment_id}/interfaces")
def get_switch_interfaces(equipment_id: int):
    """Gets detailed switch interfaces with real-time traffic"""
    db = SessionLocal()
    try:
        equipment = db.query(Equipment).filter(Equipment.id == equipment_id, Equipment.type == "switch").first()
        if not equipment:
            raise HTTPException(status_code=404, detail="Switch not found")
        switch_data = snmp_service.get_switch_interfaces_realtime(equipment.ip, equipment.community)
        return {
            "equipment": {
                "id": equipment.id,
                "name": equipment.name,
                "ip": equipment.ip,
                "community": equipment.community,
                "type": equipment.type
            },
            "system": switch_data.get("system", {}),
            "interfaces": switch_data.get("interfaces", []),
            "errors": switch_data.get("errors", {}),
            "timestamp": time.time()
        }
    finally:
        db.close()

@router.get("/switch/{equipment_id}/interface/{interface_index}/traffic")
def get_interface_traffic(equipment_id: int, interface_index: int):
    """Gets real-time traffic for a specific interface"""
    db = SessionLocal()
    try:
        equipment = db.query(Equipment).filter(Equipment.id == equipment_id, Equipment.type == "switch").first()
        if not equipment:
            raise HTTPException(status_code=404, detail="Switch not found")
        
        #get traffic metrics for specific interface
        traffic_data = snmp_service.get_interface_traffic_realtime(equipment.ip, equipment.community, interface_index)
        if not traffic_data:
            raise HTTPException(status_code=503, detail="Unable to retrieve traffic data")
        
        return {
            "equipment": {
                "id": equipment.id,
                "name": equipment.name,
                "ip": equipment.ip
            },
            "interface_index": interface_index,
            "traffic": traffic_data,
            "timestamp": time.time()
        }
    finally:
        db.close()

@router.get("/equipment/{equipment_id}/status")
def get_equipment_status(equipment_id: int):
    """Gets equipment status with ultra-fast connectivity test"""
    db = SessionLocal()
    try:
        equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
        if not equipment:
            raise HTTPException(status_code=404, detail="Equipment not found")
        
        #ultra-fast SNMP connectivity test
        is_online = snmp_service.test_connectivity(equipment.ip, equipment.community)
        
        return {
            "equipment": {
                "id": equipment.id,
                "name": equipment.name,
                "ip": equipment.ip,
                "type": equipment.type
            },
            "status": "online" if is_online else "offline",
            "last_check": time.time()
        }
    finally:
        db.close()

@router.get("/realtime/{equipment_id}")
def get_realtime_data(equipment_id: int):
    """Gets optimized real-time data for an equipment"""
    db = SessionLocal()
    try:
        equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
        if not equipment:
            raise HTTPException(status_code=404, detail="Equipment not found")
        
        if equipment.type == "server":
            data = snmp_service.get_server_metrics_realtime(equipment.ip, equipment.community)
        elif equipment.type == "switch":
            data = snmp_service.get_switch_interfaces_realtime(equipment.ip, equipment.community)
        else:
            raise HTTPException(status_code=400, detail="Unsupported equipment type")
        
        if not data:
            raise HTTPException(status_code=503, detail="Unable to retrieve data")
        
        return {
            "equipment": {
                "id": equipment.id,
                "name": equipment.name,
                "ip": equipment.ip,
                "type": equipment.type
            },
            "data": data,
            "timestamp": time.time()
        }
    finally:
        db.close() 

@router.get("/test")
def test_snmp_connectivity():
    db = SessionLocal()
    try:
        equipments = db.query(Equipment).all()
        results = []
        for eq in equipments:
            test = snmp_service.test_connectivity(eq.ip, eq.community)
            snmpget_cmd = f"snmpget -v2c -c {eq.community} {eq.ip} 1.3.6.1.2.1.1.1.0"
            snmpwalk_cmd = f"snmpwalk -v2c -c {eq.community} {eq.ip}"
            results.append({
                "id": eq.id,
                "name": eq.name,
                "ip": eq.ip,
                "community": eq.community,
                "type": eq.type,
                "online": test['online'],
                "error": test['error'],
                "snmpget_cmd": snmpget_cmd,
                "snmpwalk_cmd": snmpwalk_cmd
            })
        return results
    finally:
        db.close() 

@router.get("/switch/{equipment_id}/data")
def get_switch_data(equipment_id: int):
    """Gets complete switch data in the format expected by the frontend"""
    db = SessionLocal()
    try:
        equipment = db.query(Equipment).filter(Equipment.id == equipment_id, Equipment.type == "switch").first()
        if not equipment:
            raise HTTPException(status_code=404, detail="Switch not found")
        
        #get switch data
        switch_data = snmp_service.get_switch_interfaces_realtime(equipment.ip, equipment.community)
        connected_devices = snmp_service.get_connected_devices(equipment.ip, equipment.community)
        
        return {
            "system": switch_data.get("system", {
                "system_name": equipment.name,
                "system_uptime": 0
            }),
            "interfaces": switch_data.get("interfaces", []),
            "connected_devices": connected_devices,
            "timestamp": time.time()
        }
    finally:
        db.close() 