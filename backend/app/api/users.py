from fastapi import APIRouter, HTTPException

from app.db import users_repo
from app.models.user import UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
async def list_users() -> list[UserOut]:
    return await users_repo.list_users()


@router.get("/{user_id}", response_model=UserOut)
async def get_user(user_id: str) -> UserOut:
    user = await users_repo.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user
