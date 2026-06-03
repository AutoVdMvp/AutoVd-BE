from fastapi import APIRouter, Depends

from app.models.models import User
from app.schemas.user import UserResponse
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/me", response_model=UserResponse)
async def get_my_info(current_user: User = Depends(get_current_user)):
    return current_user