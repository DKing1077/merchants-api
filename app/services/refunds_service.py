from app.db.models.models import Refunds, PaymentIntent, Timestamp
from app.core.exceptions import RefundStateError, RefundNotFoundError
from app.schemas.refunds_schemas import RefundStatus


def list_refunds(db):
    return db.query(Refunds).all()


def create_refund(payment_intent_id, refund_amount, db):
    payment_amount = db.query(PaymentIntent).filter(PaymentIntent.id == payment_intent_id).first().amount
    if refund_amount <= 0:
        raise RefundStateError(f"Refund amount has to be greater than 0")
    elif refund_amount > payment_amount:
        raise RefundStateError(f"Refund amount should not be greater than payment amount")
    refund = Refunds(
        payment_intent_id=payment_intent_id,
        amount=refund_amount,
        status=RefundStatus.pending,
    )
    db.add(refund)
    db.flush()
    refund_id = refund.id
    timestamp = Timestamp(
        refund_id=refund_id,
    )
    db.add(timestamp)
    db.flush()
    db.commit()
    db.refresh(refund)
    return refund


def get_refund(payment_intent_id, db):
    refund = db.filter(Refunds.payment_intent_id == payment_intent_id).first()
    if not refund:
        raise RefundNotFoundError(f"Refund intent with payment_intent_id {payment_intent_id} not found")
    return refund


def confirm_refund(payment_intent_id, db):
    succeeded_payment_intent(payment_intent_id, db)
    refund = get_refund(payment_intent_id, db)
    if refund.status != RefundStatus.pending:
        raise RefundStateError(f"Refund intent with payment_intent_id {payment_intent_id} is not in a pending state")

    refund.status = RefundStatus.confirmed
    db.commit()
    db.refresh(refund)
    return refund


def decline_refund(payment_intent_id, db):
    succeeded_payment_intent(payment_intent_id, db)
    refund = get_refund(payment_intent_id, db)
    if refund.status != RefundStatus.pending:
        raise RefundStateError(f"Refund intent with payment_intent_id {payment_intent_id} is not in a pending state")

    refund.status = RefundStatus.declined
    db.commit()
    db.refresh(refund)
    return refund


def cancel_refund(payment_intent_id, db):
    succeeded_payment_intent(payment_intent_id, db)
    refund = get_refund(payment_intent_id, db)
    if refund.status != RefundStatus.pending:
        raise RefundStateError(f"Refund intent with payment_intent_id {payment_intent_id} is not in a pending state")

    refund.status = RefundStatus.canceled
    db.commit()
    db.refresh(refund)
    return refund


def succeeded_payment_intent(payment_intent_id, db):
    payment_intent = db.query(PaymentIntent).filter(PaymentIntent.id == payment_intent_id).first()
    if payment_intent.status != 'canceled':
        raise RefundStateError(f"Payment intent with id {payment_intent_id} is not in a canceled state")


