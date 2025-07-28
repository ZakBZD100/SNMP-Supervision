from sqlalchemy import Column, Integer, String, Boolean
from backend.database.db import Base
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True) 
    role = Column(String, default="user")
    
    def set_password(self, password: str):
        """Hash le mot de passe"""
        self.hashed_password = pwd_context.hash(password)
    
    def check_password(self, password: str) -> bool:
        """Vérifie le mot de passe"""
        return pwd_context.verify(password, self.hashed_password)
    
    def is_admin(self) -> bool:
        """Vérifie si l'utilisateur est admin"""
        return self.role == "admin" 