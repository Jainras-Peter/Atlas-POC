from datetime import datetime

from app.db import users_repo
from app.models.user import UserCreate, UserOut


async def create_user_record(
    name: str,
    email: str,
    age: int | None,
    contact_number: str | None,
    is_active: bool,
) -> UserOut:
    payload = UserCreate(
        name=name,
        email=email,
        age=age,
        contact_number=contact_number,
        is_active=is_active,
    )
    return await users_repo.create_user(payload)


async def delete_user_by_id(user_id: str) -> bool:
    return await users_repo.delete_user(user_id)


async def find_users_by_name(name: str) -> list[UserOut]:
    return await users_repo.find_by_name(name)


async def find_users_created_since(
    start: datetime, end: datetime
) -> list[UserOut]:
    return await users_repo.find_created_between(start, end)
