from enum import Enum
from pydantic import BaseModel


class PaymentIntentStatus(str, Enum):
    requires_payment_method = "requires_payment_method"
    requires_confirmation = "requires_confirmation"
    requires_capture = "requires_capture"
    succeeded = "succeeded"
    canceled = "canceled"


class ReviewStatus(str, Enum):
    pending_review = "pending_review"
    approved = "approved"
    rejected = "rejected"


class PaymentIntentResponse(BaseModel):
    id: str
    merchant_id: str
    amount: int
    currency: str
    status: PaymentIntentStatus
    is_flagged: bool
    review_status: ReviewStatus | None = None
    review_reason: str | None = None


class CreatePaymentIntentRequest(BaseModel):
    merchant_id: str
    amount: int
    currency: str


class FlagPaymentIntentRequest(BaseModel):
    reason: str


class ReviewPaymentIntentRequest(BaseModel):
    review_status: ReviewStatus

