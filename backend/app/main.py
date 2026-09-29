from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.config import settings
from app.db.mongo import close_mongo, connect_mongo


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await connect_mongo()
    yield
    await close_mongo()


app = FastAPI(title="AI POC Onboarding", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
