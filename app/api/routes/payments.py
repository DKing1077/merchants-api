from fastapi import APIRouter, Depends, Header, HTTPException
from app.auth.dependencies import require_api_key
from app.db.database import get_db
from app.core.exceptions import (
    InvalidPaymentIntentStateError,
    PaymentIntentNotFoundError,
    IdempotencyConflictError,
)
from app.schemas.payments_schemas import (
    CreatePaymentIntentRequest,
    PaymentIntentResponse,
    FlagPaymentIntentRequest,
    ReviewPaymentIntentRequest,
)
from app.services.payment_service import (
    cancel_payment_intent,
    capture_payment_intent,
    confirm_payment_intent,
    create_payment_intent,
    get_payment_intent,
    list_payment_intents,
    flag_payment_intent,
    review_payment_intent,
    list_flagged_payment_intents,
    list_payment_intent_transactions,
    list_transactions,
)

router = APIRouter()


@router.get("/")
def list_payment_intents_route(db=Depends(get_db)):
    return {"payment_intents": list_payment_intents(db)}


@router.post("", response_model=PaymentIntentResponse, status_code=201)
def create_payment_intent_route(
    request: CreatePaymentIntentRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db=Depends(get_db),
    api_key=Depends(require_api_key),
):
    try:
        return create_payment_intent(
            db=db,
            amount=request.amount,
            currency=request.currency,
            merchant_id=request.merchant_id,
            idempotency_key=idempotency_key,
        )
    except IdempotencyConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.get("/admin/flagged")
def list_flagged_payment_intents_route(db=Depends(get_db)):
    return {"payment_intents": list_flagged_payment_intents(db)}


@router.get("/transactions")
def list_transactions_route(db=Depends(get_db)):
    return {"transactions": list_transactions(db)}


@router.get("/{payment_intent_id}/transactions")
def list_payment_intent_transactions_route(payment_intent_id, db=Depends(get_db)):
    try:
        return {"transactions": list_payment_intent_transactions(db, payment_intent_id)}
    except PaymentIntentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{payment_intent_id}", response_model=PaymentIntentResponse)
def get_payment_intent_route(payment_intent_id, db=Depends(get_db)):
    try:
        return get_payment_intent(db, payment_intent_id)
    except PaymentIntentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{payment_intent_id}/flag", response_model=PaymentIntentResponse)
def flag_payment_intent_route(
    payment_intent_id, request: FlagPaymentIntentRequest, db=Depends(get_db)
):
    try:
        return flag_payment_intent(db, payment_intent_id, request.reason)
    except PaymentIntentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except InvalidPaymentIntentStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/admin/{payment_intent_id}/review", response_model=PaymentIntentResponse)
def review_payment_intent_route(
    payment_intent_id, request: ReviewPaymentIntentRequest, db=Depends(get_db)
):
    try:
        return review_payment_intent(db, payment_intent_id, request.review_status.value)
    except PaymentIntentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except InvalidPaymentIntentStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/{payment_intent_id}/confirm", response_model=PaymentIntentResponse)
def confirm_payment_intent_route(payment_intent_id, db=Depends(get_db)):
    try:
        return confirm_payment_intent(db, payment_intent_id)
    except PaymentIntentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except InvalidPaymentIntentStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/{payment_intent_id}/capture", response_model=PaymentIntentResponse)
def capture_payment_intent_route(payment_intent_id, db=Depends(get_db)):
    try:
        return capture_payment_intent(db, payment_intent_id)
    except PaymentIntentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except InvalidPaymentIntentStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/{payment_intent_id}/cancel", response_model=PaymentIntentResponse)
def cancel_payment_intent_route(payment_intent_id, db=Depends(get_db)):
    try:
        return cancel_payment_intent(db, payment_intent_id)
    except PaymentIntentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except InvalidPaymentIntentStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


