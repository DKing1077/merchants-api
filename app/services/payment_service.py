from app.core.exceptions import InvalidPaymentIntentStateError, PaymentIntentNotFoundError
from app.schemas.payments_schemas import PaymentIntentStatus
from app.db.models.models import PaymentIntent
from app.services.events import create_event


def create_payment_intent(db, amount, currency, idempotency_key=None):
    if idempotency_key:
        existing = (
            db.query(PaymentIntent)
            .filter(PaymentIntent.idempotency_key == idempotency_key)
            .first()
        )
        if existing:
            return existing

    payment_intent_count = db.query(PaymentIntent).count()
    payment_intent_id = f"pi_{payment_intent_count + 1}"

    payment_intent = PaymentIntent(
        id=payment_intent_id,
        amount=amount,
        currency=currency,
        status=PaymentIntentStatus.requires_payment_method.value,
        idempotency_key=idempotency_key,
    )
    db.add(payment_intent)
    db.flush()

    create_event(
        db=db,
        event_type="payment_intent.created",
        object_id=payment_intent.id,
        payload={
            "id": payment_intent.id,
            "amount": payment_intent.amount,
            "currency": payment_intent.currency,
            "status": payment_intent.status,
        },
    )

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


def confirm_payment_intent(db, payment_intent_id):
    payment_intent = get_payment_intent(db, payment_intent_id)
    if payment_intent.status == PaymentIntentStatus.canceled.value:
        raise InvalidPaymentIntentStateError(f"Cannot confirm canceled payment intent {payment_intent_id}")
    if payment_intent.status == PaymentIntentStatus.succeeded.value:
        raise InvalidPaymentIntentStateError(f"Cannot confirm succeeded payment intent {payment_intent_id}")
    if payment_intent.status == PaymentIntentStatus.requires_capture.value:
        raise InvalidPaymentIntentStateError(f"Payment intent {payment_intent_id} already requires capture")

    payment_intent.status = PaymentIntentStatus.requires_capture.value

    create_event(
        db=db,
        event_type="payment_intent.confirmed",
        object_id=payment_intent.id,
        payload={
            "id": payment_intent.id,
            "status": payment_intent.status,
        },
    )

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

    payment_intent.status = PaymentIntentStatus.succeeded.value

    create_event(
        db=db,
        event_type="payment_intent.captured",
        object_id=payment_intent.id,
        payload={
            "id": payment_intent.id,
            "status": payment_intent.status,
        },
    )

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

    create_event(
        db=db,
        event_type="payment_intent.canceled",
        object_id=payment_intent.id,
        payload={
            "id": payment_intent.id,
            "status": payment_intent.status,
        },
    )

    db.commit()
    db.refresh(payment_intent)
    return payment_intent