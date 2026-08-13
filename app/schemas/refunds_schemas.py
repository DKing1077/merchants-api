from pydantic import BaseModel, Field
from enum import Enum


class RefundStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    declined = "declined"
    canceled = "canceled"


class CreateRefundRequest(BaseModel):
    amount: int = Field(..., gt=0)


