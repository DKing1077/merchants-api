from app.core.exceptions import InvalidPaymentIntentStateError, PaymentIntentNotFoundError
from app.schemas.payments_schemas import PaymentIntentStatus
from app.db.models.models import PaymentIntent, LedgerAccount
from app.services.events import create_event
from app.services.dispatch import create_dispatches_for_event
from app.services.ledger_service import create_ledger_entry
import uuid


def create_payment_intent(db, amount, currency, merchant_id, idempotency_key=None):
    if idempotency_key:
        existing = (
            db.query(PaymentIntent)
            .filter(PaymentIntent.idempotency_key == idempotency_key)
            .first()
        )
        if existing:
            return existing

    payment_intent_id = f"pi_{uuid.uuid4()}"

    payment_intent = PaymentIntent(
        id=payment_intent_id,
        merchant_id=merchant_id,
        amount=amount,
        currency=currency,
        status=PaymentIntentStatus.requires_payment_method.value,
        idempotency_key=idempotency_key,
        is_flagged=False,
        review_status=None,
        review_reason=None,
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
            "currency": payment_intent.currency,
            "status": payment_intent.status,
        },
    )
    create_dispatches_for_event(db, payment_intent.merchant_id, event)

    db.commit()
    db.refresh(payment_intent)
    return payment_intent


def get_payment_intent(db, payment_intent_id):
    payment_intent = (
        db.query(PaymentIntent)
        .filter(PaymentIntent.id == payment_intent_id)
        .first()
    )
    if not payment_intent:
        raise PaymentIntentNotFoundError(f"Payment intent {payment_intent_id} not found")
    return payment_intent


def list_payment_intents(db):
    return db.query(PaymentIntent).all()


def list_payment_intent_transactions(db, payment_intent_id):
    payment_intent = get_payment_intent(db, payment_intent_id)

    transactions = []

    transactions.append(
        {
            "id": f"txn_{payment_intent.id}_created",
            "type": "payment_intent.created",
            "payment_intent_id": payment_intent.id,
            "amount": payment_intent.amount,
            "currency": payment_intent.currency,
            "status": payment_intent.status,
        }
    )

    if payment_intent.status in [
        PaymentIntentStatus.requires_capture.value,
        PaymentIntentStatus.succeeded.value,
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

    if payment_intent.status == PaymentIntentStatus.succeeded.value:
        transactions.append(
            {
                "id": f"txn_{payment_intent.id}_captured",
                "type": "payment_intent.captured",
                "payment_intent_id": payment_intent.id,
                "amount": payment_intent.amount,
                "currency": payment_intent.currency,
                "status": PaymentIntentStatus.succeeded.value,
            }
        )

    if payment_intent.status == PaymentIntentStatus.canceled.value:
        transactions.append(
            {
                "id": f"txn_{payment_intent.id}_canceled",
                "type": "payment_intent.canceled",
                "payment_intent_id": payment_intent.id,
                "amount": payment_intent.amount,
                "currency": payment_intent.currency,
                "status": PaymentIntentStatus.canceled.value,
            }
        )

    return transactions


def list_transactions(db):
    payment_intents = db.query(PaymentIntent).all()
    transactions = []

    for payment_intent in payment_intents:
        transactions.extend(list_payment_intent_transactions(db, payment_intent.id))

    return transactions


def list_flagged_payment_intents(db):
    return db.query(PaymentIntent).filter(PaymentIntent.is_flagged == True).all()


def flag_payment_intent(db, payment_intent_id, reason):
    payment_intent = get_payment_intent(db, payment_intent_id)
    payment_intent.is_flagged = True
    payment_intent.review_status = "pending_review"
    payment_intent.review_reason = reason
    db.commit()
    db.refresh(payment_intent)
    return payment_intent


def review_payment_intent(db, payment_intent_id, review_status):
    payment_intent = get_payment_intent(db, payment_intent_id)

    if not payment_intent.is_flagged:
        raise InvalidPaymentIntentStateError(
            f"Payment intent {payment_intent_id} is not flagged for review"
        )

    payment_intent.review_status = review_status
    db.commit()
    db.refresh(payment_intent)
    return payment_intent


def confirm_payment_intent(db, payment_intent_id):
    payment_intent = get_payment_intent(db, payment_intent_id)
    if payment_intent.status == PaymentIntentStatus.canceled.value:
        raise InvalidPaymentIntentStateError(f"Cannot confirm canceled payment intent {payment_intent_id}")
    if payment_intent.status == PaymentIntentStatus.succeeded.value:
        raise InvalidPaymentIntentStateError(f"Cannot confirm succeeded payment intent {payment_intent_id}")
    if payment_intent.status == PaymentIntentStatus.requires_capture.value:
        raise InvalidPaymentIntentStateError(f"Payment intent {payment_intent_id} already requires capture")
    if payment_intent.review_status == "rejected":
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


def capture_payment_intent(db, payment_intent_id):
    payment_intent = get_payment_intent(db, payment_intent_id)
    if payment_intent.status == PaymentIntentStatus.canceled.value:
        raise InvalidPaymentIntentStateError(f"Cannot capture canceled payment intent {payment_intent_id}")
    if payment_intent.status == PaymentIntentStatus.succeeded.value:
        raise InvalidPaymentIntentStateError(f"Payment intent {payment_intent_id} has already succeeded")
    if payment_intent.status != PaymentIntentStatus.requires_capture.value:
        raise InvalidPaymentIntentStateError(f"Payment intent {payment_intent_id} is not in a capturable state")
    if payment_intent.review_status == "rejected":
        raise InvalidPaymentIntentStateError(f"Cannot capture rejected payment intent {payment_intent_id}")

    cash = db.query(LedgerAccount).filter(
        LedgerAccount.merchant_id == payment_intent.merchant_id,
        LedgerAccount.account_type == "cash",
        LedgerAccount.currency == payment_intent.currency,
    ).first()

    if not cash:
        cash = LedgerAccount(
            merchant_id=payment_intent.merchant_id,
            name="Cash",
            account_type="cash",
            currency=payment_intent.currency,
        )
        db.add(cash)
        db.flush()

    payable = db.query(LedgerAccount).filter(
        LedgerAccount.merchant_id == payment_intent.merchant_id,
        LedgerAccount.account_type == "merchant_payable",
        LedgerAccount.currency == payment_intent.currency,
    ).first()

    if not payable:
        payable = LedgerAccount(
            merchant_id=payment_intent.merchant_id,
            name="Merchant Payable",
            account_type="merchant_payable",
            currency=payment_intent.currency,
        )
        db.add(payable)
        db.flush()

    payment_intent.status = PaymentIntentStatus.succeeded.value

    create_ledger_entry(
        db=db,
        entry_type="payment_succeeded",
        reference_id=payment_intent.id,
        description=f"Payment captured for {payment_intent.id}",
        entry_metadata={"merchant_id": payment_intent.merchant_id},
        postings=[
            {"account_id": cash.id, "amount": payment_intent.amount, "currency": payment_intent.currency},
            {"account_id": payable.id, "amount": -payment_intent.amount, "currency": payment_intent.currency},
        ],
    )

    event = create_event(
        db=db,
        event_type="payment_intent.succeeded",
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


def cancel_payment_intent(db, payment_intent_id):
    payment_intent = get_payment_intent(db, payment_intent_id)
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
            "status": payment_intent.status,
        },
    )
    create_dispatches_for_event(db, payment_intent.merchant_id, event)

    db.commit()
    db.refresh(payment_intent)
    return payment_intent