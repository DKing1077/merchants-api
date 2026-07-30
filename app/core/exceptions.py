class PaymentIntentNotFoundError(Exception):
    pass


class InvalidPaymentIntentStateError(Exception):
    pass


class RefundNotFoundError(Exception):
    pass


class RefundStateError(Exception):
    pass


class InvalidTimestamp(Exception):
    pass

