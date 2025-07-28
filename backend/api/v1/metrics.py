from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from backend.database.db import SessionLocal
from backend.models.equipment import Equipment
from backend.services.snmp_service import SNMPService

router = APIRouter(prefix="/metrics", tags=["metrics"])

snmp_service = SNMPService()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/{equipment_id}")
def get_metrics(equipment_id: int, db: Session = Depends(get_db)):
    eq = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not eq:
        raise HTTPException(status_code=404, detail="Équipement non trouvé")
    if eq.type == "server":
        metrics = snmp_service.get_server_metrics(eq.ip, eq.community)
    else:
        metrics = snmp_service.get_comprehensive_switch_data(eq.ip, eq.community)
    if not metrics:
        raise HTTPException(status_code=503, detail="Impossible de récupérer les métriques SNMP")
    return metrics 