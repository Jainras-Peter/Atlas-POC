from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


async def connect_mongo() -> AsyncIOMotorDatabase:
    global _client, _db
    _client = AsyncIOMotorClient(settings.mongodb_uri)
    _db = _client[settings.mongodb_db]
    await _db.users.create_index("email", unique=True)
    await _db.conversations.create_index("thread_id", unique=True)
    await _db.conversations.create_index("updated_at")
    await _db.quotes.create_index("quote_number", unique=True)
    await _db.quotes.create_index("customer_id")
    await _db.quotes.create_index("contact_email")
    # Atlas SDR collections (safe if empty — seed script fills them)
    await _db.companies.create_index("companyId", unique=True)
    await _db.companies.create_index("country")
    await _db.companies.create_index("hsCodes")
    await _db.companies.create_index("products")
    await _db.companies.create_index("buyerSupplierRole")
    await _db.customers.create_index("customerId", unique=True)
    await _db.customers.create_index("companyId")
    return _db


async def close_mongo() -> None:
    global _client, _db
    if _client is not None:
        _client.close()
    _client = None
    _db = None


def get_db() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("MongoDB is not connected")
    return _db
