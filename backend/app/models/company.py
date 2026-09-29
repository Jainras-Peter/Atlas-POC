from pydantic import BaseModel, Field


class ShippingRequirements(BaseModel):
    bikeTransport: bool = False
    preferredEquipment: list[str] = Field(default_factory=list)
    requiresDoorToDoor: bool = False
    requiresTracking: bool = False
    hazardousCargo: bool = False
    temperatureControlled: bool = False


class MatchSignals(BaseModel):
    bikeTransport: bool = False
    productKeywords: list[str] = Field(default_factory=list)
    hsCodes: list[str] = Field(default_factory=list)
    targetCountries: list[str] = Field(default_factory=list)
    tradeCountries: list[str] = Field(default_factory=list)
    volumeBand: str = ""


class Company(BaseModel):
    """Atlas POC company document stored in MongoDB."""

    id: str | None = Field(default=None, alias="_id")
    companyId: str
    name: str
    email: str = ""
    phone: str = ""
    website: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    country: str = ""
    employees: int = 0
    companySize: str = ""
    industry: str = ""
    teuPerMonth: int = 0
    annualTeu: int = 0
    annualShipments: int = 0
    preferredCarriers: list[str] = Field(default_factory=list)
    tradeLanes: list[str] = Field(default_factory=list)
    business: list[str] = Field(default_factory=list)
    buyerSupplierRole: str = ""
    products: list[str] = Field(default_factory=list)
    commodities: list[str] = Field(default_factory=list)
    hsCodes: list[str] = Field(default_factory=list)
    cargoTypes: list[str] = Field(default_factory=list)
    preferredModes: list[str] = Field(default_factory=list)
    shippingRequirements: ShippingRequirements = Field(
        default_factory=ShippingRequirements
    )
    matchSignals: MatchSignals = Field(default_factory=MatchSignals)

    model_config = {"populate_by_name": True}


class CompanySearchCriteria(BaseModel):
    country: str | None = None
    states: list[str] = Field(default_factory=list)
    role: str | None = None
    products: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    hsCodes: list[str] = Field(default_factory=list)
    tradeCountries: list[str] = Field(default_factory=list)
    minTeuPerMonth: int | None = None
    industry: str | None = None
    bikeTransport: bool | None = None
    limit: int = 10


class CompanySearchHit(BaseModel):
    companyId: str
    name: str
    city: str = ""
    country: str = ""
    role: str = ""
    teuPerMonth: int = 0
    products: list[str] = Field(default_factory=list)
    hsCodes: list[str] = Field(default_factory=list)
    tradeLanes: list[str] = Field(default_factory=list)
    matchedFields: list[str] = Field(default_factory=list)
    matchScore: int = 0
    matchReasons: list[str] = Field(default_factory=list)


class CompanySearchResult(BaseModel):
    totalMatches: int
    companies: list[CompanySearchHit]
