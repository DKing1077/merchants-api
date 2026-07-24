from fastapi import APIRouter, HTTPException
from app.core.exceptions import (
    InvalidPaymentIntentStateError,
    PaymentIntentNotFoundError,
)
from app.schemas.payment_intents import PaymentIntentCreate, PaymentIntentResponse
from app.services.payment_service import (
    create_payment_intent,
    get_payment_intent,
    list_payment_intents,
    confirm_payment_intent,
    cancel_payment_intent,
)

router = APIRouter()


@router.get("/")
def list_payment_intents_route():
    return {"payment_intents": list_payment_intents()}


@router.post("/", response_model=PaymentIntentResponse)
def create_payment_intent_route(payload: PaymentIntentCreate):
    return create_payment_intent(payload.amount, payload.currency)


@router.get("/{payment_intent_id}", response_model=PaymentIntentResponse)
def get_payment_intent_route(payment_intent_id: str):
    try:
        return get_payment_intent(payment_intent_id)
    except PaymentIntentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{payment_intent_id}/confirm", response_model=PaymentIntentResponse)
def confirm_payment_intent_route(payment_intent_id: str):
    try:
        return confirm_payment_intent(payment_intent_id)
    except PaymentIntentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except InvalidPaymentIntentStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/{payment_intent_id}/cancel", response_model=PaymentIntentResponse)
def cancel_payment_intent_route(payment_intent_id: str):
    try:
        return cancel_payment_intent(payment_intent_id)
    except PaymentIntentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except InvalidPaymentIntentStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))