from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from backend.database.db import SessionLocal
from backend.models.user import User
from backend.schemas import UserCreate, UserLogin, TokenData
import os

#JWT configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()

class AuthService:
    def __init__(self):
        self.secret_key = SECRET_KEY
        self.algorithm = ALGORITHM
        self.access_token_expire_minutes = ACCESS_TOKEN_EXPIRE_MINUTES
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        """Crée un token JWT"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> TokenData:
        """Vérifie un token JWT"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            username: str = payload.get("sub")
            role: str = payload.get("role")
            if username is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token invalide",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return TokenData(username=username, role=role)
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalide",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    def authenticate_user(self, db: Session, username: str, password: str) -> Optional[User]:
        """Authentifie un utilisateur"""
        user = db.query(User).filter(User.username == username).first()
        if not user or not user.check_password(password):
            return None
        return user
    
    def create_user(self, db: Session, user_data: UserCreate) -> User:
        """Crée un nouvel utilisateur"""
        #check if username already exists
        existing_user = db.query(User).filter(User.username == user_data.username).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ce nom d'utilisateur existe déjà"
            )
        
        #check if email already exists
        if hasattr(user_data, 'email') and user_data.email:
            existing_email = db.query(User).filter(User.email == user_data.email).first()
            if existing_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cet email existe déjà"
                )
        
        #create new user
        user = User(
            username=user_data.username,
            email=getattr(user_data, 'email', f"{user_data.username}@example.com"),
            role="user"
        )
        user.set_password(user_data.password)
        
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    def get_current_user(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
        """Récupère l'utilisateur actuel depuis le token"""
        token = credentials.credentials
        token_data = self.verify_token(token)
        
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == token_data.username).first()
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Utilisateur non trouvé"
                )
            return user
        finally:
            db.close()
    
    def require_admin(self, current_user: User = Depends(get_current_user)) -> User:
        """Décorateur pour exiger les droits admin"""
        if not current_user.is_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Droits insuffisants"
            )
        return current_user
    
    def create_admin_user(self, db: Session):
        """Crée l'utilisateur admin par défaut s'il n'existe pas"""
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            admin_user = User(
                username="admin", 
                email="admin@snmp-supervision.com",
                role="admin"
            )
            admin_user.set_password("admin123")
            db.add(admin_user)
            db.commit()
            print("✅ Utilisateur admin créé: admin/admin123")

auth_service = AuthService() 