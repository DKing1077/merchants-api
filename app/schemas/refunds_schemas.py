from enum import Enum


class RefundStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    declined = "declined"
    canceled = "canceled"

