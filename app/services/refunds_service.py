from app.db.models import Refunds
from app.core.exceptions import RefundStateError, RefundNotFoundError
from app.schemas.refunds_schemas import RefundStatus


def list_refunds(db):
    return db.query(Refunds).all()


def create_refund(payment_intent_id, db):
    refund = Refunds(
        payment_intent_id=payment_intent_id,
        status=RefundStatus.pending,
    )
    db.add(refund)
    db.commit()
    db.flush()
    db.refresh(refund)
    return refund


def get_refund(payment_intent_id, db):
    refund = db.filter(Refunds.payment_intent_id == payment_intent_id).first()
    if not refund:
        raise RefundNotFoundError(f"Refund intent with payment_intent_id {payment_intent_id} not found")
    return refund


def confirm_refund(payment_intent_id, db):
    refund = get_refund(payment_intent_id, db)
    if refund.status != RefundStatus.pending:
        raise RefundStateError(f"Refund intent with payment_intent_id {payment_intent_id} is not in a pending state")

    refund.status = RefundStatus.confirmed
    db.commit()
    db.refresh(refund)
    return refund


def decline_refund(payment_intent_id, db):
    refund = get_refund(payment_intent_id, db)
    if refund.status != RefundStatus.pending:
        raise RefundStateError(f"Refund intent with payment_intent_id {payment_intent_id} is not in a pending state")

    refund.status = RefundStatus.declined
    db.commit()
    db.refresh(refund)
    return refund


def cancel_refund(payment_intent_id, db):
    refund = get_refund(payment_intent_id, db)
    if refund.status != RefundStatus.pending:
        raise RefundStateError(f"Refund intent with payment_intent_id {payment_intent_id} is not in a pending state")

    refund.status = RefundStatus.canceled
    db.commit()
    db.refresh(refund)
    return refund

