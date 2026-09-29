from typing import Any

from app.db.mongo import get_db
from app.models.company import Company


def _normalize(doc: dict[str, Any]) -> dict[str, Any]:
    """Ensure _id is a string for Pydantic."""
    if doc is None:
        return {}
    out = dict(doc)
    if "_id" in out and out["_id"] is not None:
        out["_id"] = str(out["_id"])
    return out


async def ensure_indexes() -> None:
    db = get_db()
    await db.companies.create_index("companyId", unique=True)
    await db.companies.create_index("country")
    await db.companies.create_index("industry")
    await db.companies.create_index("products")
    await db.companies.create_index("hsCodes")
    await db.companies.create_index("buyerSupplierRole")
    await db.companies.create_index("teuPerMonth")


async def find(filter_query: dict[str, Any]) -> list[Company]:
    db = get_db()
    cursor = db.companies.find(filter_query)
    docs = await cursor.to_list(length=500)
    return [Company.model_validate(_normalize(doc)) for doc in docs]


async def get_by_company_id(company_id: str) -> Company | None:
    db = get_db()
    doc = await db.companies.find_one({"companyId": company_id})
    if not doc:
        return None
    return Company.model_validate(_normalize(doc))


async def replace_all(companies: list[dict[str, Any]]) -> int:
    """Drop and re-insert all companies (seed behaviour)."""
    db = get_db()
    await db.companies.drop()
    if not companies:
        await ensure_indexes()
        return 0
    result = await db.companies.insert_many(companies)
    await ensure_indexes()
    return len(result.inserted_ids)
