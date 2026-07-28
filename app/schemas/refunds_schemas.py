from enum import Enum


class RefundStatus(str, Enum):
    pending = "pending"
    cofirmed = "cofirmed"
    declined = "declined"
    canceled = "canceled"