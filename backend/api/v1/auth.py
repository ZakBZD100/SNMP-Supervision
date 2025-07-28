from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from backend.database.db import SessionLocal
from backend.services.auth_service import auth_service
from backend.schemas import UserCreate, UserLogin, UserResponse, Token
from backend.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])

#dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/register", response_model=UserResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    try:
        user = auth_service.create_user(db, user_data)
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            is_active=user.is_active
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration error: {str(e)}"
        )

@router.post("/login", response_model=Token)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """User login"""
    user = auth_service.authenticate_user(db, user_data.username, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account disabled"
        )
    
    access_token = auth_service.create_access_token(
        data={"sub": user.username, "role": user.role}
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(auth_service.get_current_user)):
    """Gets current user information"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active
    )

@router.post("/logout")
def logout():
    """Logout (client side)"""
    return {"message": "Logout successful"}

@router.get("/users", response_model=list[UserResponse])
def list_users(current_user: User = Depends(auth_service.require_admin), db: Session = Depends(get_db)):
    """List all users (admin only)"""
    users = db.query(User).all()
    return [
        UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            is_active=user.is_active
        )
        for user in users
    ] 