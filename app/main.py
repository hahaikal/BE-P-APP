from fastapi import FastAPI
from .database import engine, Base 

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="P-APP Backend API",
    description="Backend service for football prediction platform P-APP.",
    version="1.0.0"
)

@app.get("/health", tags=["Monitoring"])
def health_check():
    """
    Endpoint untuk memastikan layanan API berjalan dengan benar.
    """
    return {"status": "ok", "message": "P-APP Backend service is up and running"}