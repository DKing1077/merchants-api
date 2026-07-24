from pydantic import BaseModel

class PaymentIntentCreate(BaseModel):
    amount: int
    currency: str

class PaymentIntentResponse(BaseModel):
    id: str
    amount: int
    currency: str
    status: str

