from typing import Literal

from pydantic import BaseModel, Field


class RouteDecision(BaseModel):
    route: Literal["sales", "quote", "chat", "sdr"]
    reason: str = Field(description="Short reason for the routing choice")
