from pydantic import BaseModel
from datetime import datetime


class ApiKeyCreate(BaseModel):
    merchant_id: str


class ApiKeyResponse(BaseModel):
    id: str
    merchant_id: str
    api_key: str
    is_active: bool
    created_at: datetime

