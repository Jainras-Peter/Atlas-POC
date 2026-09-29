from pydantic import BaseModel, Field


class QuoteExtract(BaseModel):
    intent: str = Field(
        description="create or list — whether the user wants to create a quote or list quotes",
    )
    customer_name: str | None = Field(
        default=None,
        description="Customer display name if the user referred to them by name",
    )
    customer_email: str | None = Field(default=None, description="Customer email if provided")
    customer_id: str | None = Field(
        default=None,
        description="Mongo customer/user id (24 hex chars) if provided",
    )
    origin: str | None = Field(default=None, description="Origin port or city")
    destination: str | None = Field(default=None, description="Destination port or city")
    mode: str | None = Field(default=None, description="Shipping mode e.g. FCL, LCL")
    cargo: str | None = Field(default=None, description="Cargo type e.g. FAK")
    cut_off_date: str | None = Field(
        default=None,
        description="Cut-off date as given by the user",
    )
    follow_up_question: str | None = Field(
        default=None,
        description="Question to ask if required create fields are missing",
    )
