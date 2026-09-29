from datetime import datetime, timezone

from pymongo.errors import DuplicateKeyError

from app.db.mongo import get_db
from app.models.user import UserCreate, UserOut


def _to_user_out(doc: dict) -> UserOut:
    return UserOut(
        id=str(doc["_id"]),
        name=doc["name"],
        email=doc["email"],
        age=doc.get("age"),
        contact_number=doc.get("contact_number"),
        is_active=doc.get("is_active", True),
        created_at=doc["created_at"],
    )


def _escape(value: str) -> str:
    import re

    return re.escape(value.strip())


async def create_user(payload: UserCreate) -> UserOut:
    db = get_db()
    doc = {
        "name": payload.name.strip(),
        "email": str(payload.email).lower(),
        "age": payload.age,
        "contact_number": payload.contact_number,
        "is_active": payload.is_active,
        "created_at": datetime.now(timezone.utc),
    }
    try:
        result = await db.users.insert_one(doc)
    except DuplicateKeyError as exc:
        raise ValueError(f"A user with email {payload.email} already exists") from exc
    doc["_id"] = result.inserted_id
    return _to_user_out(doc)


async def list_users() -> list[UserOut]:
    db = get_db()
    cursor = db.users.find().sort("created_at", -1)
    return [_to_user_out(doc) async for doc in cursor]


async def get_user_by_id(user_id: str) -> UserOut | None:
    from bson import ObjectId
    from bson.errors import InvalidId

    db = get_db()
    try:
        oid = ObjectId(user_id)
    except InvalidId:
        return None
    doc = await db.users.find_one({"_id": oid})
    return _to_user_out(doc) if doc else None


async def get_user_by_email(email: str) -> UserOut | None:
    db = get_db()
    doc = await db.users.find_one({"email": email.lower()})
    return _to_user_out(doc) if doc else None


async def delete_user(user_id: str) -> bool:
    from bson import ObjectId
    from bson.errors import InvalidId

    db = get_db()
    try:
        oid = ObjectId(user_id)
    except InvalidId:
        return False
    result = await db.users.delete_one({"_id": oid})
    return result.deleted_count > 0


async def find_by_name(name: str) -> list[UserOut]:
    """Exact match first; if none, case-insensitive substring (e.g. Arun → Arun Kumar)."""
    db = get_db()
    needle = (name or "").strip()
    if not needle:
        return []
    exact = [
        _to_user_out(doc)
        async for doc in db.users.find(
            {"name": {"$regex": f"^{_escape(needle)}$", "$options": "i"}}
        ).sort("created_at", -1)
    ]
    if exact:
        return exact
    return [
        _to_user_out(doc)
        async for doc in db.users.find(
            {"name": {"$regex": _escape(needle), "$options": "i"}}
        ).sort("created_at", -1)
    ]


async def find_created_between(start: datetime, end: datetime) -> list[UserOut]:
    db = get_db()
    cursor = db.users.find({"created_at": {"$gte": start, "$lt": end}}).sort(
        "created_at", -1
    )
    return [_to_user_out(doc) async for doc in cursor]
