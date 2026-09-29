from typing import Literal

from pydantic import BaseModel, Field


class SalesExtract(BaseModel):
    intent: Literal["import", "delete"] | None = Field(
        default=None,
        description="import = save to CRM Users; delete = remove CRM users",
    )
    name: str | None = Field(default=None, description="Person name for import")
    email: str | None = Field(default=None, description="Email for import")
    age: int | None = Field(default=None, description="Age if provided")
    contact_number: str | None = Field(default=None, description="Phone if provided")
    is_active: bool | None = Field(default=None)
    target_name: str | None = Field(
        default=None, description="Name of user(s) to delete"
    )
    target_user_id: str | None = Field(
        default=None, description="Mongo user id to delete when disambiguating"
    )
    time_filter: Literal["today", "yesterday"] | None = Field(
        default=None,
        description="Delete everyone imported today or yesterday",
    )
    follow_up_question: str | None = Field(
        default=None,
        description="Ask only if import fields are incomplete",
    )
