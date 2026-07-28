from app.core.exceptions import InvalidPaymentIntentStateError, PaymentIntentNotFoundError
from app.schemas.payments_schemas import PaymentIntentStatus
from app.db.models.models import PaymentIntent


def create_payment_intent(db, amount, currency):
    payment_intent_count = db.query(PaymentIntent).count()
    payment_intent_id = f"pi_{payment_intent_count + 1}"

    payment_intent = PaymentIntent(
        id=payment_intent_id,
        amount=amount,
        currency=currency,
        status=PaymentIntentStatus.requires_payment_method.value,
    )

    db.add(payment_intent)
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

    payment_intent.status = PaymentIntentStatus.succeeded.value
    db.commit()
    db.refresh(payment_intent)
    return payment_intent


def cancel_payment_intent(db, payment_intent_id):
    payment_intent = get_payment_intent(db, payment_intent_id)
    if payment_intent.status == PaymentIntentStatus.succeeded.value:
        raise InvalidPaymentIntentStateError(f"Cannot cancel succeeded payment intent {payment_intent_id}")

    payment_intent.status = PaymentIntentStatus.canceled.value
    db.commit()
    db.refresh(payment_intent)
    return payment_intent

