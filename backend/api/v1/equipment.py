from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from backend.database.db import SessionLocal
from backend.models.equipment import Equipment
from backend.services.snmp_service import snmp_service
from backend.services.metrics_storage import metrics_storage
from pydantic import BaseModel
from typing import List, Dict, Optional
import time

router = APIRouter(prefix="/equipments", tags=["equipments"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class EquipmentCreate(BaseModel):
    name: str
    ip: str
    community: str = "public"
    type: str = "server"
    snmp_version: str = "v2c"

class EquipmentOut(BaseModel):
    id: int
    name: str
    ip: str
    community: str
    type: str
    snmp_version: str
    class Config:
        orm_mode = True

class MetricsResponse(BaseModel):
    equipment_id: int
    current_metrics: Optional[Dict]
    historical_data: Dict
    last_update: float

@router.get("", response_model=List[EquipmentOut])
def list_equipments(db: Session = Depends(get_db)):
    return db.query(Equipment).all()

@router.post("", response_model=EquipmentOut)
def add_equipment(equipment: EquipmentCreate, db: Session = Depends(get_db)):
    db_equipment = Equipment(**equipment.dict())
    db.add(db_equipment)
    db.commit()
    db.refresh(db_equipment)
    return db_equipment

@router.delete("/{equipment_id}")
def delete_equipment(equipment_id: int, db: Session = Depends(get_db)):
    eq = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not eq:
        raise HTTPException(status_code=404, detail="Equipment not found")
    db.delete(eq)
    db.commit()
    return {"ok": True}

@router.get("/{equipment_id}/metrics", response_model=MetricsResponse)
def get_equipment_metrics(equipment_id: int, db: Session = Depends(get_db)):
    """Gets current and historical metrics for an equipment and triggers critical alert generation if needed."""
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")
    try:
        #get current metrics
        if equipment.type == "switch":
            current_metrics = snmp_service.get_switch_metrics(equipment.ip, equipment.community)
            if 'timestamp' in current_metrics:
                del current_metrics['timestamp']
        else:
            current_metrics = snmp_service.get_equipment_metrics(equipment)
        #save current metrics
        if current_metrics:
            if equipment.type == "switch":
                if 'interfaces' in current_metrics and isinstance(current_metrics['interfaces'], list) and len(current_metrics['interfaces']) > 0:
                    metrics_storage.save_metrics(equipment_id, current_metrics)
            else:
                metrics_storage.save_metrics(equipment_id, current_metrics)
        #call critical alert generation (RAM > 90%, etc.)
        from backend.api.v1.alert import check_metrics_and_alert
        check_metrics_and_alert()
        #get historical data for charts
        historical_data = metrics_storage.get_metrics_for_chart(equipment_id, hours=24)
        return MetricsResponse(
            equipment_id=equipment_id,
            current_metrics=current_metrics,
            historical_data=historical_data,
            last_update=time.time()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving metrics: {str(e)}")

@router.get("/{equipment_id}/test")
def test_equipment_connection(equipment_id: int, db: Session = Depends(get_db)):
    """Tests SNMP connection for an equipment"""
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")
    
    try:
        is_connected = snmp_service.test_connection(equipment.ip, equipment.community)
        return {
            "equipment_id": equipment_id,
            "ip": equipment.ip,
            "connected": is_connected,
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "equipment_id": equipment_id,
            "ip": equipment.ip,
            "connected": False,
            "error": str(e),
            "timestamp": time.time()
        } 