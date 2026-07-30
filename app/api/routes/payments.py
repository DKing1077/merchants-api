from fastapi import APIRouter, Depends, HTTPException
from app.db.database import get_db
from app.core.exceptions import InvalidPaymentIntentStateError, PaymentIntentNotFoundError
from app.schemas.payments_schemas import PaymentIntentResponse
from app.services.payment_service import cancel_payment_intent, confirm_payment_intent, create_payment_intent
from app.services.payment_service import get_payment_intent, list_payment_intents

router = APIRouter()


@router.get("/")
def list_payment_intents_route(db = Depends(get_db)):
    return {"payment_intents": list_payment_intents(db)}


@router.post("/", response_model=PaymentIntentResponse)
def create_payment_intent_route(payload, db = Depends(get_db),):
    return create_payment_intent(db, payload.amount, payload.currency)


@router.get("/{payment_intent_id}", response_model=PaymentIntentResponse)
def get_payment_intent_route(payment_intent_id, db = Depends(get_db),):
    try:
        return get_payment_intent(db, payment_intent_id)
    except PaymentIntentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{payment_intent_id}/confirm", response_model=PaymentIntentResponse)
def confirm_payment_intent_route(payment_intent_id, db = Depends(get_db),):
    try:
        return confirm_payment_intent(db, payment_intent_id)
    except PaymentIntentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except InvalidPaymentIntentStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/{payment_intent_id}/cancel", response_model=PaymentIntentResponse)
def cancel_payment_intent_route(payment_intent_id, db = Depends(get_db),):
    try:
        return cancel_payment_intent(db, payment_intent_id)
    except PaymentIntentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except InvalidPaymentIntentStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))