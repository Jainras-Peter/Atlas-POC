from datetime import datetime

from pydantic import BaseModel, Field


class QuoteCreate(BaseModel):
    customer_id: str
    customer_name: str
    contact_email: str
    origin: str = Field(..., min_length=1)
    destination: str = Field(..., min_length=1)
    mode: str = Field(..., min_length=1)
    cargo: str = Field(..., min_length=1)
    cut_off_date: str = Field(..., min_length=1)


class QuoteOut(BaseModel):
    id: str
    quote_number: str
    type: str = "QUOTE"
    customer_id: str
    customer_name: str
    contact_email: str
    mode: str
    origin: str
    destination: str
    cargo: str
    cut_off_date: str
    status: str = "PENDING"
    created_at: datetime
