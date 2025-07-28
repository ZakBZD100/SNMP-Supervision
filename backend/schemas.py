from pydantic import BaseModel, validator, EmailStr
from typing import Optional

class UserCreate(BaseModel):
    username: str
    email: Optional[str] = None
    password: str
    password_confirm: str
    
    @validator('username')
    def username_valid(cls, v):
        if len(v) < 3:
            raise ValueError('Le nom d\'utilisateur doit contenir au moins 3 caractères')
        if len(v) > 20:
            raise ValueError('Le nom d\'utilisateur ne peut pas dépasser 20 caractères')
        return v
    
    @validator('email')
    def email_valid(cls, v):
        if v and '@' not in v:
            raise ValueError('Email invalide')
        return v
    
    @validator('password')
    def password_valid(cls, v):
        if len(v) < 6:
            raise ValueError('Le mot de passe doit contenir au moins 6 caractères')
        return v
    
    @validator('password_confirm')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('Les mots de passe ne correspondent pas')
        return v

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    role: str
    is_active: bool
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None 