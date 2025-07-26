from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import logging

from .. import crud, schemas, auth
from ..database import get_db

router = APIRouter(
    prefix="/odds",
    tags=["Odds Management"],
    responses={404: {"description": "Not found"}},
)

@router.delete("/{odds_id}", status_code=status.HTTP_200_OK)
def delete_odds_snapshot(
    odds_id: int, 
    db: Session = Depends(get_db), 
    current_user: schemas.User = Depends(auth.get_current_user)
):
    """
    Menghapus satu data odds snapshot berdasarkan ID-nya.
    Endpoint ini dilindungi dan memerlukan autentikasi.
    """
    logging.info(f"Menerima permintaan untuk menghapus OddsSnapshot ID: {odds_id} oleh user: {current_user.username}")
    
    deleted_snapshot = crud.delete_odds_snapshot_by_id(db, odds_id=odds_id)
    
    if not deleted_snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Odds snapshot with id {odds_id} not found"
        )
    
    return JSONResponse(
        content={"status": "success", "message": f"Odds snapshot with id {odds_id} has been deleted."},
        status_code=200
    )
