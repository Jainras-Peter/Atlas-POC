from datetime import datetime, timezone

from pymongo import ReturnDocument

from app.db.mongo import get_db
from app.models.quote import QuoteCreate, QuoteOut


def _to_quote_out(doc: dict) -> QuoteOut:
    return QuoteOut(
        id=str(doc["_id"]),
        quote_number=doc["quote_number"],
        type=doc.get("type", "QUOTE"),
        customer_id=doc["customer_id"],
        customer_name=doc["customer_name"],
        contact_email=doc["contact_email"],
        mode=doc["mode"],
        origin=doc["origin"],
        destination=doc["destination"],
        cargo=doc["cargo"],
        cut_off_date=doc["cut_off_date"],
        status=doc.get("status", "PENDING"),
        created_at=doc["created_at"],
    )


async def next_quote_number() -> str:
    db = get_db()
    result = await db.counters.find_one_and_update(
        {"_id": "quote_number"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    seq = int(result["seq"])
    return f"QTE{seq:08d}"


async def create_quote(payload: QuoteCreate) -> QuoteOut:
    db = get_db()
    quote_number = await next_quote_number()
    doc = {
        "quote_number": quote_number,
        "type": "QUOTE",
        "customer_id": payload.customer_id,
        "customer_name": payload.customer_name,
        "contact_email": payload.contact_email.lower(),
        "mode": payload.mode.strip().upper(),
        "origin": payload.origin.strip(),
        "destination": payload.destination.strip(),
        "cargo": payload.cargo.strip().upper(),
        "cut_off_date": payload.cut_off_date.strip(),
        "status": "PENDING",
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.quotes.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_quote_out(doc)


async def list_quotes(
    customer_id: str | None = None,
    email: str | None = None,
) -> list[QuoteOut]:
    db = get_db()
    query: dict = {}
    if customer_id:
        query["customer_id"] = customer_id
    elif email:
        query["contact_email"] = email.lower()
    cursor = db.quotes.find(query).sort("created_at", -1)
    return [_to_quote_out(doc) async for doc in cursor]


async def get_quote_by_number(quote_number: str) -> QuoteOut | None:
    db = get_db()
    doc = await db.quotes.find_one({"quote_number": quote_number.upper()})
    return _to_quote_out(doc) if doc else None


async def list_by_customer_id(customer_id: str) -> list[QuoteOut]:
    return await list_quotes(customer_id=customer_id)


async def list_by_email(email: str) -> list[QuoteOut]:
    return await list_quotes(email=email)
