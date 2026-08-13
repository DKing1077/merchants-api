from pydantic import BaseModel, HttpUrl, field_validator
from typing import List
from datetime import datetime


class WebhookEndpointCreate(BaseModel):
    merchant_id: str
    url: HttpUrl
    event_types: List[str]

    @field_validator("url")
    @classmethod
    def validate_https_url(cls, value):
        if value.scheme != "https":
            raise ValueError("webhook url must use https")
        return value


class WebhookEndpointResponse(BaseModel):
    id: str
    merchant_id: str
    url: HttpUrl
    event_types: List[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True