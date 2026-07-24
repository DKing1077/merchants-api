payment_intents = {}

def create_payment_intent(amount: int, currency: str):
    payment_intent_id = f"pi_{len(payment_intents) + 1}"

    payment_intent = {
        "id": payment_intent_id,
        "amount": amount,
        "currency": currency,
        "status": "requires_payment_method",
    }

    payment_intents[payment_intent_id] = payment_intent
    return payment_intent

def get_payment_intent(payment_intent_id: str):
    return payment_intents.get(payment_intent_id)

def list_payment_intents():
    return list(payment_intents.values())

def confirm_payment_intent(payment_intent_id: str):
    payment_intent = payment_intents.get(payment_intent_id)

    if not payment_intent:
        return None

    payment_intent["status"] = "succeeded"
    return payment_intent

