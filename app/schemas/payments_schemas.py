from enum import Enum
from pydantic import BaseModel


class PaymentIntentStatus(str, Enum):
    requires_payment_method = "requires_payment_method"
    requires_confirmation = "requires_confirmation"
    requires_capture = "requires_capture"
    succeeded = "succeeded"
    canceled = "canceled"


class PaymentIntentResponse(BaseModel):
    id: str
    merchant_id: str
    amount: int
    currency: str
    status: PaymentIntentStatus


class CreatePaymentIntentRequest(BaseModel):
    merchant_id: str
    amount: int
    currency: str