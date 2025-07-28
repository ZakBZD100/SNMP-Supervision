from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from backend.database.db import Base

class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    equipment_id = Column(Integer)
    equipment_name = Column(String)
    alert_type = Column(String)  # "cpu", "memory", "disk", "interface"
    severity = Column(String)    # "low", "medium", "high", "critical"
    message = Column(Text)
    threshold = Column(String)
    current_value = Column(String)
    is_active = Column(Integer, default=1)  # 1 = active, 0 = resolved
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True) 