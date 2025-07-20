import joblib
import os
import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
# --- [MODIFIKASI] ---
# Mengubah cara impor untuk fastapi-cache2
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis

from .database import engine
from . import model
from .routers import matches, auth

logging.basicConfig(level=logging.INFO)

import asyncio
from sqlalchemy.exc import OperationalError

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Mengelola event saat aplikasi dimulai dan dihentikan.
    """
    logging.info("Memulai aplikasi...")

    # ... (Kode koneksi database tidak berubah) ...
    max_retries = 10
    retry_delay = 3  
    for attempt in range(max_retries):
        try:
            logging.info("Memeriksa dan membuat tabel database jika belum ada...")
            model.Base.metadata.create_all(bind=engine)
            logging.info("Tabel database siap.")
            break
        except OperationalError as e:
            logging.warning(f"Database belum siap, mencoba lagi dalam {retry_delay} detik... (Attempt {attempt + 1}/{max_retries})")
            await asyncio.sleep(retry_delay)
        except Exception as e:
            logging.error(f"Terjadi kesalahan saat membuat tabel database: {e}")
            raise
    else:
        logging.error("Gagal membuat tabel database setelah beberapa kali percobaan.")
        raise RuntimeError("Database tidak tersedia.")

    # --- [MODIFIKASI] ---
    # Mengubah cara inisialisasi cache
    try:
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        redis = aioredis.from_url(redis_url)
        # Inisialisasi sekarang adalah fungsi async
        await FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
        logging.info("Koneksi ke Redis Cache berhasil diinisialisasi.")
    except Exception as e:
        logging.error(f"Gagal terhubung ke Redis: {e}")

    # ... (Kode loading model tidak berubah) ...
    try:
        logging.info("Mencoba memuat artefak model Machine Learning...")
        app.state.model = joblib.load("artifacts/trained_model.joblib")
        app.state.encoder = joblib.load("artifacts/label_encoder.joblib")
        app.state.feature_columns = joblib.load("artifacts/feature_columns.joblib")
        logging.info("✅ Model, Encoder, dan Kolom Fitur berhasil dimuat.")
    except FileNotFoundError:
        logging.warning("⚠️ File model tidak ditemukan. Aplikasi akan berjalan tanpa kemampuan prediksi.")
        app.state.model = None
        app.state.encoder = None
        app.state.feature_columns = None
    except Exception as e:
        logging.error(f"Terjadi kesalahan tidak terduga saat memuat model ML: {e}")
        app.state.model = None
        app.state.encoder = None
        app.state.feature_columns = None

    yield  

    logging.info("Aplikasi dihentikan.")


app = FastAPI(
    title="P-APP Backend API",
    description="API untuk platform prediksi hasil sepak bola P-APP.",
    version="1.0.0",
    lifespan=lifespan
)

# ... (Kode middleware dan router tidak berubah) ...
origins = [
    "http://localhost:5173",  
    "http://127.0.0.1:5173", 
    "http://localhost",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(matches.router, prefix="/api/v1/matches")


@app.get("/health", tags=["Monitoring"])
def health_check():
    """
    Endpoint untuk memeriksa apakah layanan API berjalan dengan baik.
    """
    return {"status": "ok", "message": "P-APP Backend service is up and running"}
