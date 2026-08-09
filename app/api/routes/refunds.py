from fastapi import APIRouter, Depends, HTTPException, Header
from app.db.database import get_db
from app.core.exceptions import RefundNotFoundError, RefundStateError
from app.services.refunds_service import (
    confirm_refund,
    decline_refund,
    cancel_refund,
    list_refunds,
    create_refund,
    get_refund,
)

router = APIRouter(prefix="/refunds", tags=["refunds"])


@router.get("")
def list_refunds_route(db=Depends(get_db)):
    return list_refunds(db)


@router.post("/payment_intents/{payment_intent_id}/refunds")
def create_refund_route(
    payment_intent_id: str,
    amount: int,
    db=Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    return create_refund(db, payment_intent_id, amount, idempotency_key)


@router.get("/{refund_id}")
def get_refund_route(refund_id: str, db=Depends(get_db)):
    try:
        return get_refund(refund_id, db)
    except RefundNotFoundError:
        raise HTTPException(status_code=404, detail="Refund not found")


@router.post("/{refund_id}/confirm")
def confirm_refund_route(refund_id: str, db=Depends(get_db)):
    try:
        return confirm_refund(refund_id, db)
    except RefundNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RefundStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/{refund_id}/decline")
def decline_refund_route(refund_id: str, db=Depends(get_db)):
    try:
        return decline_refund(refund_id, db)
    except RefundNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RefundStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/{refund_id}/cancel")
def cancel_refund_route(refund_id: str, db=Depends(get_db)):
    try:
        return cancel_refund(refund_id, db)
    except RefundNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RefundStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))