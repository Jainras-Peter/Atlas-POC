"""Optional structured helpers for SDR (kept for symmetry with other agents)."""

from pydantic import BaseModel, Field


class CompanyPick(BaseModel):
    """User selection of a company from ambiguous search results."""

    company_id: str | None = Field(
        default=None,
        description="Atlas companyId the user chose, e.g. CMP001",
    )
    wants_customers: bool = Field(
        default=False,
        description="True if the user is asking for contacts/customers",
    )
