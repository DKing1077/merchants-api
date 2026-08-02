from fastapi import APIRouter, Depends, Header, HTTPException
from app.db.database import get_db
from app.core.exceptions import InvalidPaymentIntentStateError, PaymentIntentNotFoundError, IdempotencyConflictError
from app.schemas.payments_schemas import CreatePaymentIntentRequest, PaymentIntentResponse
from app.services.payment_service import cancel_payment_intent, confirm_payment_intent, create_payment_intent
from app.services.payment_service import get_payment_intent, list_payment_intents

router = APIRouter()


@router.get("/")
def list_payment_intents_route(db = Depends(get_db)):
    return {"payment_intents": list_payment_intents(db)}


@router.post("", response_model=PaymentIntentResponse, status_code=201)
def create_payment_intent_route(
    request: CreatePaymentIntentRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db = Depends(get_db)):
    try:
        return create_payment_intent(
            db=db,
            amount=request.amount,
            currency=request.currency,
            idempotency_key=idempotency_key,
        )
    except IdempotencyConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


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