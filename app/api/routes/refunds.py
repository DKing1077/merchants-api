from app.services.refunds_service import confirm_refund, decline_refund, cancel_refund
from app.services.refunds_service import list_refunds, create_refund, get_refund
from app.core.exceptions import RefundNotFoundError, RefundStateError
from fastapi import APIRouter, Depends, HTTPException
from app.db.database import get_db

router = APIRouter()

@router("/")
def list_refunds_route(db = Depends(get_db)):
    return list_refunds(db)


@router("")
def create_refund_route(payment_intent_id, db = Depends(get_db)):
    return create_refund(db)


@router("")
def get_refund_route(payment_intent_id, db = Depends(get_db)):
    try:
        get_refund(payment_intent_id, db)
    except RefundNotFoundError:
        raise HTTPException(status_code=404, detail="Refund not found")


@router("")
def confirm_refund_route(payment_intent_id, db = Depends(get_db)):
    try:
        confirm_refund(payment_intent_id, db)
    except RefundNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RefundStateError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router("")
def decline_refund_route(payment_intent_id, db = Depends(get_db)):
    try:
        decline_refund(payment_intent_id, db)
    except RefundNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RefundStateError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router("")
def cancel_refund_route(payment_intent_id, db = Depends(get_db)):
    try:
        cancel_refund(payment_intent_id, db)
    except RefundIntentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RefundIntentStateError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

