from datetime import datetime
from typing import Any

from pydantic import BaseModel, HttpUrl, field_validator


class WebhookEndpointCreate(BaseModel):
    merchant_id: str
    url: HttpUrl
    event_types: list[str]

    @field_validator("url")
    @classmethod
    def validate_https_url(cls, value: HttpUrl) -> HttpUrl:
        if value.scheme != "https":
            raise ValueError("webhook url must use https")
        return value


class WebhookEndpointResponse(BaseModel):
    id: str
    merchant_id: str
    url: HttpUrl
    event_types: list[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class WebhookDeliveryResponse(BaseModel):
    id: str
    webhook_dispatch_id: str
    attempt_number: int
    response_status: int | None
    response_body: str | None
    error_message: str | None
    status: str
    next_retry_at: datetime | None
    delivered_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class WebhookDispatchResponse(BaseModel):
    id: str
    event_id: str
    webhook_endpoint_id: str
    payload: dict[str, Any]
    status: str
    next_retry_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class WebhookDispatchDetailResponse(WebhookDispatchResponse):
    deliveries: list[WebhookDeliveryResponse]
