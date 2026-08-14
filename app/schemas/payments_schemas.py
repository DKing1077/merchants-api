from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


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
    captured_amount: int
    total_refunded: int
    risk_score: int
    currency: str
    status: PaymentIntentStatus
    is_flagged: bool
    review_status: ReviewStatus | None = None
    review_reason: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CreatePaymentIntentRequest(BaseModel):
    merchant_id: str
    amount: int = Field(..., gt=0)
    currency: str = Field(..., min_length=3, max_length=3)

    @field_validator("merchant_id")
    @classmethod
    def validate_merchant_id(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("merchant_id must not be blank")
        return value

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        if not value.isalpha() or len(value) != 3:
            raise ValueError("currency must be exactly 3 letters")
        return value.lower()


class CapturePaymentIntentRequest(BaseModel):
    amount: int | None = Field(default=None, gt=0)


class FlagPaymentIntentRequest(BaseModel):
    reason: str


class ReviewPaymentIntentRequest(BaseModel):
    review_status: ReviewStatus
