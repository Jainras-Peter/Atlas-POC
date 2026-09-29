"""Company / customer search — ported from Atlas-poc-backend Go services.

Filters Mongo documents then scores and ranks hits the same way the Atlas POC
does (country, role, products, HS codes, trade lanes, volume, bike transport).
"""

from __future__ import annotations

import re
from typing import Any

from app.db import companies_repo, customers_repo
from app.models.company import (
    Company,
    CompanySearchCriteria,
    CompanySearchHit,
    CompanySearchResult,
)
from app.models.customer import (
    CustomerSearchCriteria,
    CustomerSearchResult,
    CustomerSummaryRow,
)


def _escape_regex(value: str) -> str:
    return re.escape(value)


def _intersects_fold(a: list[str], b: list[str]) -> bool:
    left = {x.lower() for x in a}
    return any(y.lower() in left for y in b)


def build_company_filter(criteria: CompanySearchCriteria) -> dict[str, Any]:
    """Build a Mongo filter dict from search criteria (Atlas BuildCompanyFilter)."""
    filter_q: dict[str, Any] = {}
    and_clauses: list[dict[str, Any]] = []

    if criteria.country:
        filter_q["country"] = {
            "$regex": f"^{_escape_regex(criteria.country)}$",
            "$options": "i",
        }
    if criteria.states:
        filter_q["state"] = {"$in": criteria.states}
    if criteria.role:
        role = criteria.role.upper()
        if role == "BUYER":
            filter_q["buyerSupplierRole"] = {"$in": ["BUYER", "BOTH"]}
        elif role in ("SUPPLIER", "SELLER"):
            filter_q["buyerSupplierRole"] = {"$in": ["SUPPLIER", "BOTH"]}
        elif role == "BOTH":
            filter_q["buyerSupplierRole"] = "BOTH"
        else:
            filter_q["buyerSupplierRole"] = role
    if criteria.products:
        and_clauses.append({"products": {"$in": criteria.products}})
    if criteria.hsCodes:
        and_clauses.append({"hsCodes": {"$in": criteria.hsCodes}})
    if criteria.minTeuPerMonth is not None:
        filter_q["teuPerMonth"] = {"$gte": criteria.minTeuPerMonth}
    if criteria.industry:
        filter_q["industry"] = {
            "$regex": _escape_regex(criteria.industry),
            "$options": "i",
        }
    if criteria.bikeTransport:
        filter_q["$or"] = [
            {"shippingRequirements.bikeTransport": True},
            {"matchSignals.bikeTransport": True},
        ]
    if criteria.tradeCountries:
        or_trade: list[dict[str, Any]] = []
        for tc in criteria.tradeCountries:
            pat = {"$regex": _escape_regex(tc), "$options": "i"}
            or_trade.append({"matchSignals.tradeCountries": pat})
            or_trade.append({"tradeLanes": pat})
        and_clauses.append({"$or": or_trade})
    if criteria.keywords:
        or_kw: list[dict[str, Any]] = []
        for kw in criteria.keywords:
            pat = {"$regex": _escape_regex(kw), "$options": "i"}
            or_kw.extend(
                [
                    {"name": pat},
                    {"industry": pat},
                    {"products": pat},
                    {"commodities": pat},
                    {"matchSignals.productKeywords": pat},
                ]
            )
            lower = kw.lower()
            if "bike" in lower or "motorcycle" in lower:
                or_kw.append({"shippingRequirements.bikeTransport": True})
                or_kw.append({"matchSignals.bikeTransport": True})
        and_clauses.append({"$or": or_kw})

    if and_clauses:
        filter_q["$and"] = and_clauses
    return filter_q


def score_company(
    company: Company, criteria: CompanySearchCriteria
) -> tuple[int, list[str], list[str]]:
    """Score a company against criteria (Atlas ScoreCompany)."""
    score = 0
    matched: list[str] = []
    reasons: list[str] = []

    if criteria.country and company.country.lower() == criteria.country.lower():
        score += 25
        matched.append("country")
        reasons.append("Country match")

    if criteria.role:
        role = criteria.role.upper()
        cr = company.buyerSupplierRole.upper()
        ok = False
        if role == "BUYER":
            ok = cr in ("BUYER", "BOTH")
        elif role in ("SUPPLIER", "SELLER"):
            ok = cr in ("SUPPLIER", "BOTH")
        else:
            ok = cr == role
        if ok:
            score += 20
            matched.append("role")
            reasons.append("Role match")

    if criteria.products and _intersects_fold(company.products, criteria.products):
        score += 20
        matched.append("product")
        reasons.append("Product match")

    if criteria.hsCodes and _intersects_fold(company.hsCodes, criteria.hsCodes):
        score += 15
        matched.append("hsCode")
        reasons.append("HS code match")

    if criteria.tradeCountries:
        hit = False
        for tc in criteria.tradeCountries:
            for ms in company.matchSignals.tradeCountries:
                if ms.lower() == tc.lower():
                    hit = True
            for lane in company.tradeLanes:
                if tc.lower() in lane.lower():
                    hit = True
        if hit:
            score += 10
            matched.append("tradeLane")
            reasons.append("Trade country match")

    if criteria.minTeuPerMonth is not None and company.teuPerMonth >= criteria.minTeuPerMonth:
        score += 10
        matched.append("volume")
        reasons.append("Volume match")
    elif criteria.minTeuPerMonth is None and (
        company.matchSignals.volumeBand == "HIGH" or company.teuPerMonth >= 3000
    ):
        for kw in criteria.keywords:
            lower = kw.lower()
            if "high" in lower or "volume" in lower:
                score += 10
                matched.append("volume")
                reasons.append("High shipping volume")
                break

    if criteria.bikeTransport:
        if company.shippingRequirements.bikeTransport or company.matchSignals.bikeTransport:
            score += 10
            matched.append("bikeTransport")
            reasons.append("Bike transport capability")
    else:
        for kw in criteria.keywords:
            lower = kw.lower()
            if "bike" in lower or "motorcycle" in lower:
                if (
                    company.shippingRequirements.bikeTransport
                    or company.matchSignals.bikeTransport
                ):
                    score += 10
                    matched.append("bikeTransport")
                    reasons.append("Bike transport capability")
                    break

    return min(score, 100), matched, reasons


async def search_companies(criteria: CompanySearchCriteria) -> CompanySearchResult:
    limit = criteria.limit if criteria.limit and criteria.limit > 0 else 10
    filter_q = build_company_filter(criteria)
    companies = await companies_repo.find(filter_q)

    hits: list[CompanySearchHit] = []
    for company in companies:
        score, matched, reasons = score_company(company, criteria)
        if score == 0 and filter_q:
            score = 40
            reasons = [*reasons, "Matched search filters"]
        hits.append(
            CompanySearchHit(
                companyId=company.companyId,
                name=company.name,
                city=company.city,
                country=company.country,
                role=company.buyerSupplierRole,
                teuPerMonth=company.teuPerMonth,
                products=company.products,
                hsCodes=company.hsCodes,
                tradeLanes=company.tradeLanes,
                matchedFields=matched,
                matchScore=score,
                matchReasons=reasons,
            )
        )

    hits.sort(key=lambda h: (-h.matchScore, -h.teuPerMonth))
    total = len(hits)
    if len(hits) > limit:
        hits = hits[:limit]
    return CompanySearchResult(totalMatches=total, companies=hits)


async def search_customers(criteria: CustomerSearchCriteria) -> CustomerSearchResult:
    limit = criteria.limit if criteria.limit and criteria.limit > 0 else 10
    filter_q: dict[str, Any] = {}
    if criteria.companyId:
        filter_q["companyId"] = criteria.companyId
    if criteria.country:
        filter_q["country"] = {
            "$regex": f"^{_escape_regex(criteria.country)}$",
            "$options": "i",
        }
    if criteria.name:
        filter_q["name"] = {
            "$regex": _escape_regex(criteria.name),
            "$options": "i",
        }
    if criteria.products:
        filter_q["products"] = {"$in": criteria.products}

    customers = await customers_repo.find(filter_q)
    rows = [
        CustomerSummaryRow(
            customerId=c.customerId,
            name=c.name,
            companyId=c.companyId,
            companyName=c.companyName,
            role=c.role,
            email=c.email,
            phone=c.phone,
            country=c.country,
            products=c.products,
            teu=c.teu,
        )
        for c in customers
    ]
    total = len(rows)
    if len(rows) > limit:
        rows = rows[:limit]
    return CustomerSearchResult(totalMatches=total, customers=rows)
