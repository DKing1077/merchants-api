from fastapi import APIRouter, Depends, Header, HTTPException, Query
from app.auth.dependencies import require_admin_api_key, require_api_key
from app.core.exceptions import PaymentIntentNotFoundError, RefundNotFoundError, RefundStateError
from app.db.database import get_db
from app.schemas.refunds_schemas import CreateRefundRequest
from app.services.refunds_service import (
    cancel_refund,
    confirm_refund,
    create_refund,
    decline_refund,
    flag_refund,
    get_refund,
    list_flagged_refunds,
    list_refunds,
    review_refund,
)

router = APIRouter(tags=["refunds"])


@router.post("/payment_intents/{payment_intent_id}/refunds")
def create_refund_route(payment_intent_id: str, body: CreateRefundRequest, db=Depends(get_db),
    api_key=Depends(require_api_key), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    try:
        return create_refund(db, payment_intent_id, body.amount, idempotency_key, api_key.merchant_id)
    except PaymentIntentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RefundStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/{refund_id}/flag")
def flag_refund_route(refund_id: str, reason: str, db=Depends(get_db), api_key=Depends(require_api_key)):
    try:
        return flag_refund(db, refund_id, reason, api_key.merchant_id)
    except RefundNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/admin/{refund_id}/review")
def review_refund_route(refund_id: str, review_status: str,
    db=Depends(get_db), api_key=Depends(require_admin_api_key)):
    try:
        return review_refund(db, refund_id, review_status, api_key.merchant_id)
    except RefundNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RefundStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.get("/{refund_id}")
def get_refund_route(refund_id: str, db=Depends(get_db), api_key=Depends(require_api_key)):
    try:
        return get_refund(refund_id, db, api_key.merchant_id)
    except RefundNotFoundError:
        raise HTTPException(status_code=404, detail="Refund not found")


@router.post("/{refund_id}/confirm")
def confirm_refund_route(refund_id: str, db=Depends(get_db), api_key=Depends(require_api_key)):
    try:
        return confirm_refund(refund_id, db, api_key.merchant_id)
    except RefundNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RefundStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/{refund_id}/decline")
def decline_refund_route(refund_id: str, db=Depends(get_db), api_key=Depends(require_api_key)):
    try:
        return decline_refund(refund_id, db, api_key.merchant_id)
    except RefundNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RefundStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/{refund_id}/cancel")
def cancel_refund_route(refund_id: str, db=Depends(get_db), api_key=Depends(require_api_key)):
    try:
        return cancel_refund(refund_id, db, api_key.merchant_id)
    except RefundNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RefundStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.get("")
def list_refunds_route(limit: int = Query(default=20, ge=1, le=100), starting_after: str | None = Query(default=None),
    payment_intent_id: str | None = Query(default=None), status: str | None = Query(default=None),
    db=Depends(get_db), api_key=Depends(require_api_key)):
    return list_refunds(
        db=db,
        merchant_id=api_key.merchant_id,
        limit=limit,
        starting_after=starting_after,
        payment_intent_id=payment_intent_id,
        status=status,
    )


@router.get("/admin/flagged")
def list_flagged_refunds_route(limit: int = Query(default=20, ge=1, le=100), starting_after: str | None = Query(default=None),
    db=Depends(get_db), api_key=Depends(require_admin_api_key)):
    return list_flagged_refunds(db=db, merchant_id=api_key.merchant_id, limit=limit, starting_after=starting_after)