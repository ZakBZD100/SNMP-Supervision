from fastapi import APIRouter
from .snmp import router as snmp_router
from .alert import router as alert_router
from .auth import router as auth_router
from .user import router as user_router
from .equipment import router as equipment_router
from .metrics import router as metrics_router
from .report import router as report_router
from .config import router as config_router

router = APIRouter()

@router.get("/health", tags=["health"])
def health():
    return {"status": "ok"}

router.include_router(snmp_router)
router.include_router(alert_router)
router.include_router(auth_router)
router.include_router(user_router)
router.include_router(equipment_router)
router.include_router(metrics_router)
router.include_router(report_router)
router.include_router(config_router) 