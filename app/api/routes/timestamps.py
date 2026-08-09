from fastapi import APIRouter, Depends
from app.services.timestamp_service import get_created_at, get_updated_at
from app.db.database import get_db
from app.db.models import PaymentIntent

router = APIRouter(prefix="/payment_intents", tags=["payment_intents"])


@router.get("/{payment_intent_id}/created_at")
def created_at_route(payment_intent_id: str, db=Depends(get_db)):
    return get_created_at(db, PaymentIntent, payment_intent_id)


@router.get("/{payment_intent_id}/updated_at")
def updated_at_route(payment_intent_id: str, db=Depends(get_db)):
    return get_updated_at(db, PaymentIntent, payment_intent_id)

