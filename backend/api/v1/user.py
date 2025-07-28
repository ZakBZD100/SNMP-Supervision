from fastapi import APIRouter, Depends
from backend.services.auth_service import auth_service
from backend.models.user import User
from backend.schemas import UserResponse

router = APIRouter(prefix="/user", tags=["user"])

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(auth_service.get_current_user)):
    """Récupère les informations de l'utilisateur connecté"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        role=current_user.role,
        is_active=current_user.is_active
    )

#removed because now in auth.py 