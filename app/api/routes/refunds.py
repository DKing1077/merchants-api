from fastapi import APIRouter, Depends, HTTPException, Header
from app.db.database import get_db
from app.auth.dependencies import require_api_key
from app.schemas.refunds_schemas import CreateRefundRequest
from app.core.exceptions import RefundNotFoundError, RefundStateError
from app.services.refunds_service import (
    confirm_refund,
    decline_refund,
    cancel_refund,
    list_refunds,
    create_refund,
    get_refund,
    flag_refund,
    review_refund,
    list_flagged_refunds,
)

router = APIRouter(tags=["refunds"])


@router.get("")
def list_refunds_route(
    db=Depends(get_db),
    api_key=Depends(require_api_key),
):
    return list_refunds(db, api_key.merchant_id)


@router.get("/admin/flagged")
def list_flagged_refunds_route(
    db=Depends(get_db),
    api_key=Depends(require_api_key),
):
    return list_flagged_refunds(db, api_key.merchant_id)


@router.post("/payment_intents/{payment_intent_id}/refunds")
def create_refund_route(
    payment_intent_id: str,
    body: CreateRefundRequest,
    db=Depends(get_db),
    api_key=Depends(require_api_key),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    return create_refund(
        db,
        payment_intent_id,
        body.amount,
        idempotency_key,
        api_key.merchant_id,
    )


@router.get("/{refund_id}")
def get_refund_route(
    refund_id: str,
    db=Depends(get_db),
    api_key=Depends(require_api_key),
):
    try:
        refund = get_refund(refund_id, db)
        if refund.merchant_id != api_key.merchant_id:
            raise HTTPException(status_code=404, detail="Refund not found")
        return refund
    except RefundNotFoundError:
        raise HTTPException(status_code=404, detail="Refund not found")


@router.post("/{refund_id}/flag")
def flag_refund_route(
    refund_id: str,
    reason: str,
    db=Depends(get_db),
    api_key=Depends(require_api_key),
):
    try:
        refund = get_refund(refund_id, db)
        if refund.merchant_id != api_key.merchant_id:
            raise HTTPException(status_code=404, detail="Refund not found")
        return flag_refund(db, refund_id, reason)
    except RefundNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/admin/{refund_id}/review")
def review_refund_route(
    refund_id: str,
    review_status: str,
    db=Depends(get_db),
    api_key=Depends(require_api_key),
):
    try:
        refund = get_refund(refund_id, db)
        if refund.merchant_id != api_key.merchant_id:
            raise HTTPException(status_code=404, detail="Refund not found")
        return review_refund(db, refund_id, review_status)
    except RefundNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RefundStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/{refund_id}/confirm")
def confirm_refund_route(
    refund_id: str,
    db=Depends(get_db),
    api_key=Depends(require_api_key),
):
    try:
        refund = get_refund(refund_id, db)
        if refund.merchant_id != api_key.merchant_id:
            raise HTTPException(status_code=404, detail="Refund not found")
        return confirm_refund(refund_id, db)
    except RefundNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RefundStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/{refund_id}/decline")
def decline_refund_route(
    refund_id: str,
    db=Depends(get_db),
    api_key=Depends(require_api_key),
):
    try:
        refund = get_refund(refund_id, db)
        if refund.merchant_id != api_key.merchant_id:
            raise HTTPException(status_code=404, detail="Refund not found")
        return decline_refund(refund_id, db)
    except RefundNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RefundStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/{refund_id}/cancel")
def cancel_refund_route(
    refund_id: str,
    db=Depends(get_db),
    api_key=Depends(require_api_key),
):
    try:
        refund = get_refund(refund_id, db)
        if refund.merchant_id != api_key.merchant_id:
            raise HTTPException(status_code=404, detail="Refund not found")
        return cancel_refund(refund_id, db)
    except RefundNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RefundStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))