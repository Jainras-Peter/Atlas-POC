"""SDR agent tools — Mongo-backed company / customer discovery.

These are LangChain tools the ReAct loop can call. They wrap
`app.services.company_search` (ported from Atlas-poc-backend).
No TradeMO or ZoomInfo — data comes from the local seed DB.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import tool

from app.db import companies_repo
from app.models.company import CompanySearchCriteria
from app.models.customer import CustomerSearchCriteria
from app.services import company_search


def _dump(payload: Any) -> str:
    """Serialize tool results as JSON strings for the LLM."""
    if hasattr(payload, "model_dump"):
        return json.dumps(payload.model_dump(mode="json"), default=str)
    return json.dumps(payload, default=str)


@tool
async def search_companies(
    country: str | None = None,
    role: str | None = None,
    products: list[str] | None = None,
    keywords: list[str] | None = None,
    hs_codes: list[str] | None = None,
    trade_countries: list[str] | None = None,
    min_teu_per_month: int | None = None,
    industry: str | None = None,
    bike_transport: bool | None = None,
    states: list[str] | None = None,
    limit: int = 10,
) -> str:
    """Search local Atlas companies by region, HS codes, products, role, etc.

    Use this when the user wants to find buyers, suppliers, or similar companies.
    If multiple companies match, present them and ask the user which companyId
    to lock before fetching full details or customers.

    Args:
        country: Country / region filter, e.g. "India".
        role: BUYER, SUPPLIER, SELLER, or BOTH.
        products: Product names to match, e.g. ["motorcycles"].
        keywords: Free-text keywords matched against name/industry/products.
        hs_codes: HS code list, e.g. ["8711"].
        trade_countries: Countries they trade with.
        min_teu_per_month: Minimum monthly TEU volume.
        industry: Industry substring filter.
        bike_transport: Require bike/motorcycle transport capability.
        states: Optional state filters.
        limit: Max results (default 10).
    """
    criteria = CompanySearchCriteria(
        country=country,
        role=role,
        products=products or [],
        keywords=keywords or [],
        hsCodes=hs_codes or [],
        tradeCountries=trade_countries or [],
        minTeuPerMonth=min_teu_per_month,
        industry=industry,
        bikeTransport=bike_transport,
        states=states or [],
        limit=limit,
    )
    # Auto-boost bike transport when keywords imply it (Atlas POC behaviour)
    if criteria.bikeTransport is None:
        for kw in criteria.keywords + criteria.products:
            lower = kw.lower()
            if any(t in lower for t in ("bike", "motorcycle", "scooter", "motor")):
                criteria.bikeTransport = True
                break

    result = await company_search.search_companies(criteria)
    return _dump(result)


@tool
async def get_company_details(company_id: str) -> str:
    """Fetch the full company profile for a locked companyId.

    Call this after the user picks a company from search results, or when
    search returned exactly one clear match and you are locking it.

    Args:
        company_id: Atlas companyId, e.g. "CMP001".
    """
    company = await companies_repo.get_by_company_id(company_id.strip())
    if company is None:
        return _dump({"error": f"No company found for companyId={company_id}"})
    return _dump(company)


@tool
async def search_customers(
    company_id: str,
    name: str | None = None,
    country: str | None = None,
    products: list[str] | None = None,
    limit: int = 10,
) -> str:
    """Fetch customers / contacts for a locked company.

    Only call after a company is locked (user chose companyId or single match).
    Pass the locked company_id so results stay scoped to that company.

    Args:
        company_id: Locked Atlas companyId (required).
        name: Optional contact name filter.
        country: Optional contact country.
        products: Optional products filter.
        limit: Max results (default 10).
    """
    if not company_id or not company_id.strip():
        return _dump(
            {
                "error": "company_id is required. Lock a company first "
                "(search then ask the user to pick a companyId)."
            }
        )
    criteria = CustomerSearchCriteria(
        companyId=company_id.strip(),
        name=name,
        country=country,
        products=products or [],
        limit=limit,
    )
    result = await company_search.search_customers(criteria)
    return _dump(result)


# Registry used by the LangGraph ToolNode
SDR_TOOLS = [search_companies, get_company_details, search_customers]
