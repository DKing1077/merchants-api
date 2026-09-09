from datetime import datetime

from pydantic import BaseModel


class ApiKeyCreate(BaseModel):
    merchant_id: str
    is_admin: bool = False


class ApiKeyResponse(BaseModel):
    id: str
    merchant_id: str
    api_key: str
    is_active: bool
    is_admin: bool
    created_at: datetime