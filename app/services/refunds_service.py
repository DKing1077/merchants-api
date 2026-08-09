from app.db.models.models import Refunds, PaymentIntent
from app.core.exceptions import RefundStateError, RefundNotFoundError
from app.schemas.refunds_schemas import RefundStatus
from app.services.events import create_event
from app.services.dispatch import create_dispatches_for_event


def list_refunds(db):
    return db.query(Refunds).all()


def create_refund(db, payment_intent_id, refund_amount, idempotency_key=None):
    if idempotency_key:
        existing = (
            db.query(Refunds)
            .filter(Refunds.idempotency_key == idempotency_key)
            .first()
        )
        if existing:
            return existing

    payment_intent = (
        db.query(PaymentIntent)
        .filter(PaymentIntent.id == payment_intent_id)
        .first()
    )
    if not payment_intent:
        raise RefundNotFoundError(
            f"Refund intent with payment_intent_id {payment_intent_id} not found"
        )

    payment_amount = payment_intent.amount

    if refund_amount <= 0:
        raise RefundStateError("Refund amount has to be greater than 0")
    elif refund_amount > payment_amount:
        raise RefundStateError("Refund amount should not be greater than payment amount")

    refund = Refunds(
        payment_intent_id=payment_intent_id,
        amount=refund_amount,
        status=RefundStatus.pending,
        idempotency_key=idempotency_key,
    )
    db.add(refund)
    db.flush()

    event = create_event(
        db=db,
        event_type="refund.created",
        object_id=refund.id,
        payload={
            "id": refund.payment_intent_id,
            "amount": refund.amount,
            "status": refund.status,
        },
    )
    create_dispatches_for_event(db, payment_intent.merchant_id, event)

    db.commit()
    db.refresh(refund)
    return refund


def get_refund(payment_intent_id, db):
    refund = (
        db.query(Refunds)
        .filter(Refunds.payment_intent_id == payment_intent_id)
        .first()
    )
    if not refund:
        raise RefundNotFoundError(
            f"Refund intent with payment_intent_id {payment_intent_id} not found"
        )
    return refund


def confirm_refund(payment_intent_id, db):
    refund = get_refund(payment_intent_id, db)
    if refund.status != RefundStatus.pending:
        raise RefundStateError(
            f"Refund intent with payment_intent_id {payment_intent_id} is not in a pending state"
        )

    refund.status = RefundStatus.confirmed

    payment_intent = (
        db.query(PaymentIntent)
        .filter(PaymentIntent.id == refund.payment_intent_id)
        .first()
    )

    event = create_event(
        db=db,
        event_type="refund.confirmed",
        object_id=refund.id,
        payload={
            "id": refund.id,
            "status": refund.status,
        },
    )
    create_dispatches_for_event(db, payment_intent.merchant_id, event)

    db.commit()
    return refund


def decline_refund(payment_intent_id, db):
    refund = get_refund(payment_intent_id, db)
    if refund.status != RefundStatus.pending:
        raise RefundStateError(
            f"Refund intent with payment_intent_id {payment_intent_id} is not in a pending state"
        )

    refund.status = RefundStatus.declined

    payment_intent = (
        db.query(PaymentIntent)
        .filter(PaymentIntent.id == refund.payment_intent_id)
        .first()
    )

    event = create_event(
        db=db,
        event_type="refund.declined",
        object_id=refund.id,
        payload={
            "id": refund.id,
            "status": refund.status,
        },
    )
    create_dispatches_for_event(db, payment_intent.merchant_id, event)

    db.commit()
    return refund


def cancel_refund(payment_intent_id, db):
    refund = get_refund(payment_intent_id, db)
    if refund.status != RefundStatus.pending:
        raise RefundStateError(
            f"Refund intent with payment_intent_id {payment_intent_id} is not in a pending state"
        )

    refund.status = RefundStatus.canceled

    payment_intent = (
        db.query(PaymentIntent)
        .filter(PaymentIntent.id == refund.payment_intent_id)
        .first()
    )

    event = create_event(
        db=db,
        event_type="refund.canceled",
        object_id=refund.id,
        payload={
            "id": refund.id,
            "status": refund.status,
        },
    )
    create_dispatches_for_event(db, payment_intent.merchant_id, event)

    db.commit()
    return refund