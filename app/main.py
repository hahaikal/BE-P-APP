import joblib
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis
import os

from fastapi.middleware.cors import CORSMiddleware

from .database import engine, Base
from .routers import matches

model = joblib.load("trained_model.joblib")
encoder = joblib.load("label_encoder.joblib")
feature_columns = joblib.load("feature_columns.joblib")

@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis = aioredis.from_url(redis_url)
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
    print("Model, Encoder, Kolom Fitur, dan Redis Cache siap digunakan.")
    yield

app = FastAPI(
    title="P-APP Backend API",
    lifespan=lifespan
)

origins = [
    "http://localhost:5173",
    "http://localhost",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, # Mengizinkan origin spesifik
    allow_credentials=True,
    allow_methods=["*"], # Mengizinkan semua metode (GET, POST, dll.)
    allow_headers=["*"], # Mengizinkan semua header
)

app.include_router(matches.router, prefix="/api/v1")

@app.get("/health", tags=["Monitoring"])
def health_check():
    """
    Endpoint untuk memastikan layanan API berjalan dengan benar.
    """
    return {"status": "ok", "message": "P-APP Backend service is up and running"}

app.state.model = model
app.state.encoder = encoder
app.state.feature_columns = feature_columns