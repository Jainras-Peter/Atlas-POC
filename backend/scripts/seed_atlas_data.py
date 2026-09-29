"""Seed Atlas company + customer dummy data into MongoDB.

Usage (from CRM-Agent-POC/backend):

    python -m scripts.seed_atlas_data

Replaces the `companies` and `customers` collections (does not touch users/quotes).
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

# Allow `python -m scripts.seed_atlas_data` from backend/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import companies_repo, customers_repo
from app.db.mongo import close_mongo, connect_mongo

DATA_PATH = Path(__file__).resolve().parents[1] / "app" / "data" / "atlas_dummy_data.json"


async def main() -> None:
    if not DATA_PATH.exists():
        raise SystemExit(f"Seed file not found: {DATA_PATH}")

    raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    companies = raw.get("companies") or []
    customers = raw.get("customers") or []

    await connect_mongo()
    try:
        n_companies = await companies_repo.replace_all(companies)
        n_customers = await customers_repo.replace_all(customers)
        print(f"Seeded {n_companies} companies and {n_customers} customers from {DATA_PATH.name}")
    finally:
        await close_mongo()


if __name__ == "__main__":
    asyncio.run(main())
