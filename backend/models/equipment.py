from sqlalchemy import Column, Integer, String
from backend.database.db import Base

class Equipment(Base):
    __tablename__ = "equipments"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    ip = Column(String, nullable=False, unique=True)
    community = Column(String)
    type = Column(String)
    snmp_version = Column(String, default="v2c") 