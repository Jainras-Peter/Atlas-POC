from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    name: str = Field(..., min_length=1)
    email: EmailStr
    age: int | None = Field(default=None, ge=0, le=150)
    contact_number: str | None = None
    is_active: bool = True


class UserOut(BaseModel):
    id: str
    name: str
    email: EmailStr
    age: int | None = None
    contact_number: str | None = None
    is_active: bool = True
    created_at: datetime
