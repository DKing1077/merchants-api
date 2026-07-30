from fastapi import APIRouter, Depends, HTTPException
from app.services.timestamp_service import get_created_at, get_updated_at
from app.db.database import get_db

router = APIRouter()


@router.get("/created_at")
def created_at_route(db=Depends(get_db)):
    timestamp = get_created_at(db)
    return timestamp


@router.get("/updated_at")
def updated_at_route(db=Depends(get_db)):
    timestamp = get_updated_at(db)
    return timestamp

