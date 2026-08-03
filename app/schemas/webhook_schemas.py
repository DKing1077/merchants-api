from pydantic import BaseModel, HttpUrl
from typing import List
from datetime import datetime


class WebhookEndpointCreate(BaseModel):
    merchant_id: str
    url: HttpUrl
    event_types: List[str]


class WebhookEndpointResponse(BaseModel):
    id: str
    merchant_id: str
    url: HttpUrl
    event_types: List[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

