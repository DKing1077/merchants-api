from enum import Enum
from pydantic import BaseModel, Field, field_validator

class PaymentIntentStatus(str, Enum):
    requires_payment_method = "requires_payment_method"
    succeeded = "succeeded"
    canceled = "canceled"

class PaymentIntentCreate(BaseModel):
    amount: int = Field(..., gt=0, description="Amount in smallest currency unit")
    currency: str = Field(..., min_length=3, max_length=3, description="ISO currency code")

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.strip().lower()

class PaymentIntentResponse(BaseModel):
    id: str
    amount: int
    currency: str
    status: PaymentIntentStatus


