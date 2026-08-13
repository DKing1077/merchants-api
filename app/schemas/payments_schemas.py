from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


class PaymentIntentStatus(str, Enum):
    requires_payment_method = "requires_payment_method"
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
    created_at: datetime
    updated_at: datetime


class CreatePaymentIntentRequest(BaseModel):
    merchant_id: str
    amount: int = Field(..., gt=0)
    currency: str = Field(..., min_length=3, max_length=3)


class FlagPaymentIntentRequest(BaseModel):
    reason: str


class ReviewPaymentIntentRequest(BaseModel):
    review_status: ReviewStatus

