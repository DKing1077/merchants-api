class PaymentIntentNotFoundError(Exception):
    pass


class InvalidPaymentIntentStateError(Exception):
    pass


class RefundIntentNotFoundError(Exception):
    pass


class RefundIntentStateError(Exception):
    pass

