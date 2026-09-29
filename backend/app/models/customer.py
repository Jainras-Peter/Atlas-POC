from pydantic import BaseModel, Field


class Customer(BaseModel):
    """Atlas POC customer/contact document linked to a company."""

    id: str | None = Field(default=None, alias="_id")
    customerId: str
    companyId: str
    name: str
    email: str = ""
    phone: str = ""
    companyName: str = ""
    role: str = ""
    department: str = ""
    tag: str = ""
    products: list[str] = Field(default_factory=list)
    totalShipments: int = 0
    teu: int = 0
    cargoType: str = ""
    commodity: str = ""
    hsCodes: list[str] = Field(default_factory=list)
    region: str = ""
    country: str = ""
    preferredCarrier: str = ""
    tradelane: str = ""
    business: list[str] = Field(default_factory=list)
    status: str = ""

    model_config = {"populate_by_name": True}


class CustomerSummaryRow(BaseModel):
    customerId: str
    name: str
    companyId: str
    companyName: str = ""
    role: str = ""
    email: str = ""
    phone: str = ""
    country: str = ""
    products: list[str] = Field(default_factory=list)
    teu: int = 0


class CustomerSearchCriteria(BaseModel):
    name: str | None = None
    companyId: str | None = None
    country: str | None = None
    products: list[str] = Field(default_factory=list)
    limit: int = 10


class CustomerSearchResult(BaseModel):
    totalMatches: int
    customers: list[CustomerSummaryRow]
