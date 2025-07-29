from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import logging

# Impor modul-modul yang diperlukan dari proyek Anda
from .. import crud, schemas, auth
from ..database import get_db

# Konfigurasi logger untuk file ini
logger = logging.getLogger(__name__)

# Membuat instance APIRouter
# Semua endpoint di file ini akan memiliki prefix /odds
router = APIRouter(
    prefix="/odds",
    tags=["Odds Management"],
    responses={404: {"description": "Not found"}},
)

@router.delete("/{id}", status_code=status.HTTP_200_OK)
def delete_single_odds_snapshot(
    id: int, 
    db: Session = Depends(get_db), 
    current_user: schemas.User = Depends(auth.get_current_user)
):
    """
    Menghapus satu data odds snapshot berdasarkan ID-nya.
    Endpoint ini memerlukan autentikasi untuk memastikan hanya user yang sah
    yang dapat menghapus data.
    """
    logger.info(f"User '{current_user.username}' meminta untuk menghapus OddsSnapshot ID: {id}")
    
    # Memanggil fungsi dari crud.py untuk melakukan penghapusan
    deleted_snapshot = crud.delete_odds_snapshot_by_id(db, id=id)
    
    # Jika fungsi crud mengembalikan None, berarti data tidak ditemukan
    if not deleted_snapshot:
        logger.warning(f"Gagal menghapus: Odds snapshot dengan ID {id} tidak ditemukan.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Odds snapshot with id {id} not found"
        )
    
    # Jika berhasil, kirim respons sukses
    logger.info(f"✅ Berhasil menghapus Odds snapshot dengan ID: {id}")
    return JSONResponse(
        content={"status": "success", "message": f"Odds snapshot with id {id} has been deleted."},
        status_code=200
    )
