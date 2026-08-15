from __future__ import annotations

import uuid
from datetime import datetime

from app.core.config import settings
from app.core.exceptions import InvalidPaymentIntentStateError, PaymentIntentNotFoundError
from app.db.models import LedgerAccount, PaymentIntent
from app.schemas.payments_schemas import PaymentIntentStatus, ReviewStatus
from app.services.dispatch import create_dispatches_for_event
from app.services.events import create_event
from app.services.ledger_service import create_ledger_entry
from app.services.risk_service import calculate_risk_score, enforce_velocity_limit


def create_payment_intent(db, amount, currency, merchant_id, idempotency_key=None):
    if idempotency_key:
        existing = (
            db.query(PaymentIntent)
            .filter(
                PaymentIntent.idempotency_key == idempotency_key,
                PaymentIntent.merchant_id == merchant_id,
            )
            .first()
        )
        if existing:
            return existing

    enforce_velocity_limit(db, merchant_id)
    risk_score = calculate_risk_score(db, merchant_id, amount)
    is_flagged = amount > settings.high_value_payment_threshold
    payment_intent = PaymentIntent(
        id=f"pi_{uuid.uuid4()}",
        merchant_id=merchant_id,
        amount=amount,
        captured_amount=0,
        risk_score=risk_score,
        currency=currency.lower(),
        status=PaymentIntentStatus.requires_payment_method.value,
        idempotency_key=idempotency_key,
        is_flagged=is_flagged,
        review_status=ReviewStatus.pending_review.value if is_flagged else None,
        review_reason="auto_flagged_high_value" if is_flagged else None,
    )
    db.add(payment_intent)
    db.flush()

    event = create_event(
        db=db,
        event_type="payment_intent.created",
        object_id=payment_intent.id,
        payload={
            "id": payment_intent.id,
            "merchant_id": payment_intent.merchant_id,
            "amount": payment_intent.amount,
            "captured_amount": payment_intent.captured_amount,
            "currency": payment_intent.currency,
            "risk_score": payment_intent.risk_score,
            "status": payment_intent.status,
        },
    )
    create_dispatches_for_event(db, payment_intent.merchant_id, event)
    db.commit()
    db.refresh(payment_intent)
    return payment_intent


def get_payment_intent(db, payment_intent_id, merchant_id):
    payment_intent = (
        db.query(PaymentIntent)
        .filter(
            PaymentIntent.id == payment_intent_id,
            PaymentIntent.merchant_id == merchant_id,
        )
        .first()
    )
    if not payment_intent:
        raise PaymentIntentNotFoundError(f"Payment intent {payment_intent_id} not found")
    return payment_intent


def list_payment_intents(
    db,
    merchant_id,
    limit=20,
    starting_after=None,
    status=None,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
    currency: str | None = None,
):
    query = (
        db.query(PaymentIntent)
        .filter(PaymentIntent.merchant_id == merchant_id)
        .order_by(PaymentIntent.created_at.desc(), PaymentIntent.id.desc())
    )
    if status:
        query = query.filter(PaymentIntent.status == status)
    if created_after:
        query = query.filter(PaymentIntent.created_at >= created_after)
    if created_before:
        query = query.filter(PaymentIntent.created_at <= created_before)
    if currency:
        query = query.filter(PaymentIntent.currency == currency)
    if starting_after:
        cursor = (
            db.query(PaymentIntent)
            .filter(
                PaymentIntent.id == starting_after,
                PaymentIntent.merchant_id == merchant_id,
            )
            .first()
        )
        if cursor:
            query = query.filter(
                (PaymentIntent.created_at < cursor.created_at)
                | (
                    (PaymentIntent.created_at == cursor.created_at)
                    & (PaymentIntent.id < cursor.id)
                )
            )
    rows = query.limit(limit + 1).all()
    return {"data": rows[:limit], "has_more": len(rows) > limit}


def list_payment_intent_transactions(db, payment_intent_id, merchant_id, limit=20, starting_after=None):
    payment_intent = get_payment_intent(db, payment_intent_id, merchant_id)
    transactions = [
        {
            "id": f"txn_{payment_intent.id}_created",
            "type": "payment_intent.created",
            "payment_intent_id": payment_intent.id,
            "amount": payment_intent.amount,
            "currency": payment_intent.currency,
            "status": PaymentIntentStatus.requires_payment_method.value,
        }
    ]
    if payment_intent.status in [
        PaymentIntentStatus.requires_capture.value,
        PaymentIntentStatus.succeeded.value,
        PaymentIntentStatus.canceled.value,
    ]:
        transactions.append(
            {
                "id": f"txn_{payment_intent.id}_confirmed",
                "type": "payment_intent.confirmed",
                "payment_intent_id": payment_intent.id,
                "amount": payment_intent.amount,
                "currency": payment_intent.currency,
                "status": PaymentIntentStatus.requires_capture.value,
            }
        )
    if payment_intent.captured_amount:
        transactions.append(
            {
                "id": f"txn_{payment_intent.id}_captured",
                "type": "payment_intent.captured",
                "payment_intent_id": payment_intent.id,
                "amount": payment_intent.captured_amount,
                "currency": payment_intent.currency,
                "status": payment_intent.status,
            }
        )
    if payment_intent.status == PaymentIntentStatus.canceled.value:
        transactions.append(
            {
                "id": f"txn_{payment_intent.id}_canceled",
                "type": "payment_intent.canceled",
                "payment_intent_id": payment_intent.id,
                "amount": payment_intent.amount - payment_intent.captured_amount,
                "currency": payment_intent.currency,
                "status": PaymentIntentStatus.canceled.value,
            }
        )
    if starting_after:
        start_index = next((i for i, txn in enumerate(transactions) if txn["id"] == starting_after), None)
        if start_index is not None:
            transactions = transactions[start_index + 1 :]
    sliced = transactions[: limit + 1]
    return {"data": sliced[:limit], "has_more": len(sliced) > limit}


def list_transactions(db, merchant_id, limit=20, starting_after=None):
    payment_intents = (
        db.query(PaymentIntent)
        .filter(PaymentIntent.merchant_id == merchant_id)
        .order_by(PaymentIntent.created_at.desc(), PaymentIntent.id.desc())
        .all()
    )
    transactions = []
    for payment_intent in payment_intents:
        transactions.extend(
            list_payment_intent_transactions(
                db=db,
                payment_intent_id=payment_intent.id,
                merchant_id=merchant_id,
                limit=10_000,
            )["data"]
        )
    if starting_after:
        start_index = next((i for i, txn in enumerate(transactions) if txn["id"] == starting_after), None)
        if start_index is not None:
            transactions = transactions[start_index + 1 :]
    sliced = transactions[: limit + 1]
    return {"data": sliced[:limit], "has_more": len(sliced) > limit}


def list_flagged_payment_intents(db, merchant_id, limit=20, starting_after=None):
    query = (
        db.query(PaymentIntent)
        .filter(PaymentIntent.merchant_id == merchant_id, PaymentIntent.is_flagged.is_(True))
        .order_by(PaymentIntent.created_at.desc(), PaymentIntent.id.desc())
    )
    if starting_after:
        cursor = (
            db.query(PaymentIntent)
            .filter(
                PaymentIntent.id == starting_after,
                PaymentIntent.merchant_id == merchant_id,
                PaymentIntent.is_flagged.is_(True),
            )
            .first()
        )
        if cursor:
            query = query.filter(
                (PaymentIntent.created_at < cursor.created_at)
                | ((PaymentIntent.created_at == cursor.created_at) & (PaymentIntent.id < cursor.id))
            )
    rows = query.limit(limit + 1).all()
    return {"data": rows[:limit], "has_more": len(rows) > limit}


def flag_payment_intent(db, payment_intent_id, reason, merchant_id):
    payment_intent = get_payment_intent(db, payment_intent_id, merchant_id)
    payment_intent.is_flagged = True
    payment_intent.review_status = ReviewStatus.pending_review.value
    payment_intent.review_reason = reason
    db.commit()
    db.refresh(payment_intent)
    return payment_intent


def review_payment_intent(db, payment_intent_id, review_status, merchant_id):
    payment_intent = get_payment_intent(db, payment_intent_id, merchant_id)
    if not payment_intent.is_flagged:
        raise InvalidPaymentIntentStateError(
            f"Payment intent {payment_intent_id} is not flagged for review"
        )
    payment_intent.review_status = review_status
    db.commit()
    db.refresh(payment_intent)
    return payment_intent


def confirm_payment_intent(db, payment_intent_id, merchant_id):
    payment_intent = get_payment_intent(db, payment_intent_id, merchant_id)
    if payment_intent.status == PaymentIntentStatus.canceled.value:
        raise InvalidPaymentIntentStateError(f"Cannot confirm canceled payment intent {payment_intent_id}")
    if payment_intent.status == PaymentIntentStatus.succeeded.value:
        raise InvalidPaymentIntentStateError(f"Cannot confirm succeeded payment intent {payment_intent_id}")
    if payment_intent.status == PaymentIntentStatus.requires_capture.value:
        raise InvalidPaymentIntentStateError(f"Payment intent {payment_intent_id} already requires capture")
    if payment_intent.review_status == ReviewStatus.rejected.value:
        raise InvalidPaymentIntentStateError(f"Cannot confirm rejected payment intent {payment_intent_id}")
    payment_intent.status = PaymentIntentStatus.requires_capture.value
    event = create_event(
        db=db,
        event_type="payment_intent.confirmed",
        object_id=payment_intent.id,
        payload={
            "id": payment_intent.id,
            "merchant_id": payment_intent.merchant_id,
            "status": payment_intent.status,
        },
    )
    create_dispatches_for_event(db, payment_intent.merchant_id, event)
    db.commit()
    db.refresh(payment_intent)
    return payment_intent


def _get_or_create_ledger_account(db, payment_intent, account_type: str, name: str):
    account = (
        db.query(LedgerAccount)
        .filter(
            LedgerAccount.merchant_id == payment_intent.merchant_id,
            LedgerAccount.account_type == account_type,
            LedgerAccount.currency == payment_intent.currency,
        )
        .first()
    )
    if account:
        return account
    account = LedgerAccount(
        merchant_id=payment_intent.merchant_id,
        name=name,
        account_type=account_type,
        currency=payment_intent.currency,
    )
    db.add(account)
    db.flush()
    return account


def capture_payment_intent(db, payment_intent_id, merchant_id, amount=None):
    payment_intent = get_payment_intent(db, payment_intent_id, merchant_id)
    if payment_intent.status == PaymentIntentStatus.canceled.value:
        raise InvalidPaymentIntentStateError(f"Cannot capture canceled payment intent {payment_intent_id}")
    if payment_intent.status == PaymentIntentStatus.succeeded.value:
        raise InvalidPaymentIntentStateError(f"Payment intent {payment_intent_id} has already succeeded")
    if payment_intent.status != PaymentIntentStatus.requires_capture.value:
        raise InvalidPaymentIntentStateError(f"Payment intent {payment_intent_id} is not in a capturable state")
    if payment_intent.review_status == ReviewStatus.rejected.value:
        raise InvalidPaymentIntentStateError(f"Cannot capture rejected payment intent {payment_intent_id}")

    remaining = payment_intent.amount - payment_intent.captured_amount
    capture_amount = amount or remaining
    if capture_amount > remaining:
        raise InvalidPaymentIntentStateError("Capture amount exceeds remaining capturable amount")
    if capture_amount <= 0:
        raise InvalidPaymentIntentStateError("Capture amount must be greater than 0")

    cash = _get_or_create_ledger_account(db, payment_intent, "cash", "Cash")
    payable = _get_or_create_ledger_account(db, payment_intent, "merchant_payable", "Merchant Payable")

    payment_intent.captured_amount += capture_amount
    payment_intent.status = (
        PaymentIntentStatus.succeeded.value
        if payment_intent.captured_amount == payment_intent.amount
        else PaymentIntentStatus.requires_capture.value
    )

    create_ledger_entry(
        db=db,
        entry_type="payment_capture",
        reference_id=f"{payment_intent.id}:{payment_intent.captured_amount}",
        description=f"Payment captured for {payment_intent.id}",
        entry_metadata={"merchant_id": payment_intent.merchant_id},
        postings=[
            {"account_id": cash.id, "amount": capture_amount, "currency": payment_intent.currency},
            {"account_id": payable.id, "amount": -capture_amount, "currency": payment_intent.currency},
        ],
    )

    event_type = (
        "payment_intent.succeeded"
        if payment_intent.status == PaymentIntentStatus.succeeded.value
        else "payment_intent.partially_captured"
    )
    event = create_event(
        db=db,
        event_type=event_type,
        object_id=payment_intent.id,
        payload={
            "id": payment_intent.id,
            "merchant_id": payment_intent.merchant_id,
            "captured_amount": payment_intent.captured_amount,
            "status": payment_intent.status,
        },
    )
    create_dispatches_for_event(db, payment_intent.merchant_id, event)
    db.commit()
    db.refresh(payment_intent)
    return payment_intent


def cancel_payment_intent(db, payment_intent_id, merchant_id):
    payment_intent = get_payment_intent(db, payment_intent_id, merchant_id)
    if payment_intent.status == PaymentIntentStatus.succeeded.value:
        raise InvalidPaymentIntentStateError(f"Cannot cancel succeeded payment intent {payment_intent_id}")
    if payment_intent.status == PaymentIntentStatus.canceled.value:
        raise InvalidPaymentIntentStateError(f"Payment intent {payment_intent_id} is already canceled")
    payment_intent.status = PaymentIntentStatus.canceled.value
    event = create_event(
        db=db,
        event_type="payment_intent.canceled",
        object_id=payment_intent.id,
        payload={
            "id": payment_intent.id,
            "merchant_id": payment_intent.merchant_id,
            "captured_amount": payment_intent.captured_amount,
            "status": payment_intent.status,
        },
    )
    create_dispatches_for_event(db, payment_intent.merchant_id, event)
    db.commit()
    db.refresh(payment_intent)
    return payment_intent
