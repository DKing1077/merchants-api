from app.core.exceptions import (
    InvalidPaymentIntentStateError,
    PaymentIntentNotFoundError,
)
from app.schemas.payment_intents import PaymentIntentStatus

payment_intents = {}


def create_payment_intent(amount: int, currency: str):
    payment_intent_id = f"pi_{len(payment_intents) + 1}"

    payment_intent = {
        "id": payment_intent_id,
        "amount": amount,
        "currency": currency,
        "status": PaymentIntentStatus.requires_payment_method,
    }

    payment_intents[payment_intent_id] = payment_intent
    return payment_intent


def get_payment_intent(payment_intent_id: str):
    payment_intent = payment_intents.get(payment_intent_id)

    if not payment_intent:
        raise PaymentIntentNotFoundError(f"Payment intent {payment_intent_id} not found")

    return payment_intent


def list_payment_intents():
    return list(payment_intents.values())


def confirm_payment_intent(payment_intent_id: str):
    payment_intent = get_payment_intent(payment_intent_id)

    if payment_intent["status"] == PaymentIntentStatus.canceled:
        raise InvalidPaymentIntentStateError(
            f"Cannot confirm canceled payment intent {payment_intent_id}"
        )

    payment_intent["status"] = PaymentIntentStatus.succeeded
    return payment_intent


def cancel_payment_intent(payment_intent_id: str):
    payment_intent = get_payment_intent(payment_intent_id)

    if payment_intent["status"] == PaymentIntentStatus.succeeded:
        raise InvalidPaymentIntentStateError(
            f"Cannot cancel succeeded payment intent {payment_intent_id}"
        )

    payment_intent["status"] = PaymentIntentStatus.canceled
    return payment_intent

