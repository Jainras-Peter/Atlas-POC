from typing import Any

from app.db.mongo import get_db
from app.models.customer import Customer


def _normalize(doc: dict[str, Any]) -> dict[str, Any]:
    if doc is None:
        return {}
    out = dict(doc)
    if "_id" in out and out["_id"] is not None:
        out["_id"] = str(out["_id"])
    return out


async def ensure_indexes() -> None:
    db = get_db()
    await db.customers.create_index("customerId", unique=True)
    await db.customers.create_index("companyId")
    await db.customers.create_index("products")
    await db.customers.create_index("hsCodes")


async def find(filter_query: dict[str, Any]) -> list[Customer]:
    db = get_db()
    cursor = db.customers.find(filter_query)
    docs = await cursor.to_list(length=500)
    return [Customer.model_validate(_normalize(doc)) for doc in docs]


async def get_by_customer_id(customer_id: str) -> Customer | None:
    db = get_db()
    doc = await db.customers.find_one({"customerId": customer_id})
    if not doc:
        return None
    return Customer.model_validate(_normalize(doc))


async def replace_all(customers: list[dict[str, Any]]) -> int:
    """Drop and re-insert all customers (seed behaviour)."""
    db = get_db()
    await db.customers.drop()
    if not customers:
        await ensure_indexes()
        return 0
    result = await db.customers.insert_many(customers)
    await ensure_indexes()
    return len(result.inserted_ids)
