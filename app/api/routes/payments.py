from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from app.auth.dependencies import require_admin_api_key, require_api_key
from app.core.exceptions import (
    InvalidPaymentIntentStateError,
    PaymentIntentNotFoundError,
    RiskRateLimitError,
)
from app.db.database import get_db
from app.schemas.payments_schemas import (
    CapturePaymentIntentRequest,
    CreatePaymentIntentRequest,
    FlagPaymentIntentRequest,
    PaymentIntentResponse,
    ReviewPaymentIntentRequest,
)
from app.services.payment_service import (
    cancel_payment_intent,
    capture_payment_intent,
    confirm_payment_intent,
    create_payment_intent,
    flag_payment_intent,
    get_payment_intent,
    list_flagged_payment_intents,
    list_payment_intent_transactions,
    list_payment_intents,
    list_transactions,
    review_payment_intent,
)

router = APIRouter()


@router.get("/")
def list_payment_intents_route(
    limit: int = Query(default=20, ge=1, le=100),
    starting_after: str | None = Query(default=None),
    status: str | None = Query(default=None),
    created_after: datetime | None = Query(default=None),
    created_before: datetime | None = Query(default=None),
    currency: str | None = Query(default=None),
    db=Depends(get_db),
    api_key=Depends(require_api_key),
):
    if created_after and created_before and created_after > created_before:
        raise HTTPException(status_code=400, detail="created_after must be less than or equal to created_before")
    return list_payment_intents(
        db=db,
        merchant_id=api_key.merchant_id,
        limit=limit,
        starting_after=starting_after,
        status=status,
        created_after=created_after,
        created_before=created_before,
        currency=currency.lower() if currency else None,
    )


@router.post("", response_model=PaymentIntentResponse, status_code=201)
def create_payment_intent_route(
    request: CreatePaymentIntentRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db=Depends(get_db),
    api_key=Depends(require_api_key),
):
    if request.merchant_id != api_key.merchant_id:
        raise HTTPException(status_code=403, detail="merchant mismatch")
    try:
        return create_payment_intent(
            db=db,
            amount=request.amount,
            currency=request.currency,
            merchant_id=request.merchant_id,
            idempotency_key=idempotency_key,
        )
    except RiskRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc))


@router.get("/admin/flagged")
def list_flagged_payment_intents_route(
    limit: int = Query(default=20, ge=1, le=100),
    starting_after: str | None = Query(default=None),
    db=Depends(get_db),
    api_key=Depends(require_admin_api_key),
):
    return list_flagged_payment_intents(db=db, merchant_id=api_key.merchant_id, limit=limit, starting_after=starting_after)


@router.get("/transactions")
def list_transactions_route(
    limit: int = Query(default=20, ge=1, le=100),
    starting_after: str | None = Query(default=None),
    db=Depends(get_db),
    api_key=Depends(require_api_key),
):
    return list_transactions(db=db, merchant_id=api_key.merchant_id, limit=limit, starting_after=starting_after)


@router.get("/{payment_intent_id}/transactions")
def list_payment_intent_transactions_route(
    payment_intent_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    starting_after: str | None = Query(default=None),
    db=Depends(get_db),
    api_key=Depends(require_api_key),
):
    try:
        return list_payment_intent_transactions(
            db=db,
            payment_intent_id=payment_intent_id,
            merchant_id=api_key.merchant_id,
            limit=limit,
            starting_after=starting_after,
        )
    except PaymentIntentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{payment_intent_id}", response_model=PaymentIntentResponse)
def get_payment_intent_route(payment_intent_id: str, db=Depends(get_db), api_key=Depends(require_api_key)):
    try:
        return get_payment_intent(db, payment_intent_id, api_key.merchant_id)
    except PaymentIntentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/admin/{payment_intent_id}/flag", response_model=PaymentIntentResponse)
def flag_payment_intent_route(
    payment_intent_id: str,
    request: FlagPaymentIntentRequest,
    db=Depends(get_db),
    api_key=Depends(require_admin_api_key),
):
    try:
        return flag_payment_intent(db, payment_intent_id, request.reason, api_key.merchant_id)
    except PaymentIntentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except InvalidPaymentIntentStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/admin/{payment_intent_id}/review", response_model=PaymentIntentResponse)
def review_payment_intent_route(
    payment_intent_id: str,
    request: ReviewPaymentIntentRequest,
    db=Depends(get_db),
    api_key=Depends(require_admin_api_key),
):
    try:
        return review_payment_intent(db, payment_intent_id, request.review_status.value, api_key.merchant_id)
    except PaymentIntentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except InvalidPaymentIntentStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/{payment_intent_id}/confirm", response_model=PaymentIntentResponse)
def confirm_payment_intent_route(payment_intent_id: str, db=Depends(get_db), api_key=Depends(require_api_key)):
    try:
        return confirm_payment_intent(db, payment_intent_id, api_key.merchant_id)
    except PaymentIntentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except InvalidPaymentIntentStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/{payment_intent_id}/capture", response_model=PaymentIntentResponse)
def capture_payment_intent_route(
    payment_intent_id: str,
    request: CapturePaymentIntentRequest | None = None,
    db=Depends(get_db),
    api_key=Depends(require_api_key),
):
    try:
        return capture_payment_intent(
            db,
            payment_intent_id,
            api_key.merchant_id,
            amount=request.amount if request else None,
        )
    except PaymentIntentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except InvalidPaymentIntentStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/{payment_intent_id}/cancel", response_model=PaymentIntentResponse)
def cancel_payment_intent_route(payment_intent_id: str, db=Depends(get_db), api_key=Depends(require_api_key)):
    try:
        return cancel_payment_intent(db, payment_intent_id, api_key.merchant_id)
    except PaymentIntentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except InvalidPaymentIntentStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
