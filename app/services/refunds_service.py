from app.db.models.models import Refunds, PaymentIntent, LedgerAccount
from app.core.exceptions import RefundStateError, RefundNotFoundError, PaymentIntentNotFoundError
from app.schemas.refunds_schemas import RefundStatus
from app.services.events import create_event
from app.services.dispatch import create_dispatches_for_event
from app.services.ledger_service import create_ledger_entry
from sqlalchemy import func
import uuid


def list_refunds(db):
    return db.query(Refunds).all()


def list_flagged_refunds(db):
    return db.query(Refunds).filter(Refunds.is_flagged == True).all()


def create_refund(db, payment_intent_id, refund_amount, idempotency_key=None):
    if idempotency_key:
        existing = db.query(Refunds).filter(Refunds.idempotency_key == idempotency_key).first()
        if existing:
            return existing

    payment_intent = db.query(PaymentIntent).filter(PaymentIntent.id == payment_intent_id).first()
    if not payment_intent:
        raise PaymentIntentNotFoundError(
            f"Payment intent with id {payment_intent_id} not found"
        )

    if refund_amount <= 0:
        raise RefundStateError("Refund amount has to be greater than 0")

    existing_refunded = (
        db.query(func.coalesce(func.sum(Refunds.amount), 0))
        .filter(Refunds.payment_intent_id == payment_intent_id)
        .filter(Refunds.status != RefundStatus.cancelled)
        .scalar()
    )

    if existing_refunded + refund_amount > payment_intent.amount:
        raise RefundStateError("Refund amount exceeds remaining refundable payment amount")

    refund = Refunds(
        id=str(uuid.uuid4()),
        payment_intent_id=payment_intent_id,
        amount=refund_amount,
        status=RefundStatus.pending,
        idempotency_key=idempotency_key,
        merchant_id=payment_intent.merchant_id,
        is_flagged=False,
        review_status=None,
        review_reason=None,
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


def get_refund(refund_id, db):
    refund = db.query(Refunds).filter(Refunds.id == refund_id).first()
    if not refund:
        raise RefundNotFoundError(f"Refund {refund_id} not found")
    return refund


def flag_refund(db, refund_id, reason):
    refund = get_refund(refund_id, db)
    refund.is_flagged = True
    refund.review_status = "pending_review"
    refund.review_reason = reason
    db.commit()
    db.refresh(refund)
    return refund


def review_refund(db, refund_id, review_status):
    refund = get_refund(refund_id, db)
    if not refund.is_flagged:
        raise RefundStateError(f"Refund {refund_id} is not flagged for review")
    refund.review_status = review_status
    db.commit()
    db.refresh(refund)
    return refund


def confirm_refund(refund_id, db):
    refund = get_refund(refund_id, db)
    if refund.status != RefundStatus.pending:
        raise RefundStateError(f"Refund {refund_id} is not in a pending state")
    if refund.review_status == "rejected":
        raise RefundStateError(f"Cannot confirm rejected refund {refund_id}")

    payment_intent = db.query(PaymentIntent).filter(PaymentIntent.id == refund.payment_intent_id).first()
    if not payment_intent:
        raise PaymentIntentNotFoundError(
            f"Payment intent with id {refund.payment_intent_id} not found"
        )
    if payment_intent.status != "succeeded":
        raise RefundStateError("Refund can only be confirmed for succeeded payment intents")

    cash = db.query(LedgerAccount).filter(
        LedgerAccount.merchant_id == payment_intent.merchant_id,
        LedgerAccount.account_type == "cash",
        LedgerAccount.currency == payment_intent.currency,
    ).first()
    payable = db.query(LedgerAccount).filter(
        LedgerAccount.merchant_id == payment_intent.merchant_id,
        LedgerAccount.account_type == "merchant_payable",
        LedgerAccount.currency == payment_intent.currency,
    ).first()

    if not cash or not payable:
        raise RefundStateError(
            f"Missing ledger accounts for merchant {payment_intent.merchant_id} and currency {payment_intent.currency}"
        )

    refund.status = RefundStatus.confirmed

    create_ledger_entry(
        db=db,
        entry_type="refund_confirmed",
        reference_id=refund.id,
        description=f"Refund confirmed for {refund.id}",
        entry_metadata={"merchant_id": payment_intent.merchant_id},
        postings=[
            {"account_id": payable.id, "amount": refund.amount, "currency": payment_intent.currency},
            {"account_id": cash.id, "amount": -refund.amount, "currency": payment_intent.currency},
        ],
    )

    event = create_event(
        db=db,
        event_type="refund.confirmed",
        object_id=refund.id,
        payload={"id": refund.id, "status": refund.status},
    )
    create_dispatches_for_event(db, payment_intent.merchant_id, event)

    db.commit()
    db.refresh(refund)
    return refund


def decline_refund(refund_id, db):
    refund = get_refund(refund_id, db)
    if refund.status != RefundStatus.pending:
        raise RefundStateError(f"Refund {refund_id} is not in a pending state")

    refund.status = RefundStatus.declined
    payment_intent = db.query(PaymentIntent).filter(PaymentIntent.id == refund.payment_intent_id).first()

    event = create_event(
        db=db,
        event_type="refund.declined",
        object_id=refund.id,
        payload={"id": refund.id, "status": refund.status},
    )
    create_dispatches_for_event(db, payment_intent.merchant_id, event)

    db.commit()
    db.refresh(refund)
    return refund


def cancel_refund(refund_id, db):
    refund = get_refund(refund_id, db)
    if refund.status != RefundStatus.pending:
        raise RefundStateError(f"Refund {refund_id} is not in a pending state")

    refund.status = RefundStatus.canceled
    payment_intent = db.query(PaymentIntent).filter(PaymentIntent.id == refund.payment_intent_id).first()

    event = create_event(
        db=db,
        event_type="refund.canceled",
        object_id=refund.id,
        payload={"id": refund.id, "status": refund.status},
    )
    create_dispatches_for_event(db, payment_intent.merchant_id, event)

    db.commit()
    db.refresh(refund)
    return refund

