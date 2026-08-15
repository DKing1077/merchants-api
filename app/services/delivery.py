from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json

import httpx
from sqlalchemy import or_

from app.db.models import WebhookDelivery, WebhookDispatch, WebhookEndpoint


MAX_ATTEMPTS = 3
RETRY_DELAY = timedelta(minutes=5)


def generate_webhook_signature(secret: str, payload_json: str) -> str:
    key = bytes.fromhex(secret)
    digest = hmac.new(key, payload_json.encode(), hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify_webhook_signature(secret: str, payload_json: str, signature: str) -> bool:
    return hmac.compare_digest(generate_webhook_signature(secret, payload_json), signature)


def process_pending_dispatches(db):
    now = datetime.now(timezone.utc)
    dispatches = (
        db.query(WebhookDispatch)
        .filter(
            WebhookDispatch.status == "pending",
            or_(WebhookDispatch.next_retry_at.is_(None), WebhookDispatch.next_retry_at <= now),
        )
        .all()
    )

    for dispatch in dispatches:
        endpoint = (
            db.query(WebhookEndpoint)
            .filter(WebhookEndpoint.id == dispatch.webhook_endpoint_id)
            .first()
        )
        attempts = (
            db.query(WebhookDelivery)
            .filter(WebhookDelivery.webhook_dispatch_id == dispatch.id)
            .count()
            + 1
        )
        try:
            payload_json = json.dumps(dispatch.payload, separators=(",", ":"), sort_keys=True)
            response = httpx.post(
                endpoint.url,
                content=payload_json,
                headers={
                    "Content-Type": "application/json",
                    "X-Webhook-Signature": generate_webhook_signature(endpoint.secret, payload_json),
                },
                timeout=5.0,
            )
            success = 200 <= response.status_code < 300
            next_retry_at = None if success or attempts >= MAX_ATTEMPTS else now + RETRY_DELAY
            db.add(
                WebhookDelivery(
                    webhook_dispatch_id=dispatch.id,
                    attempt_number=attempts,
                    response_status=response.status_code,
                    response_body=response.text,
                    status="success" if success else "failed",
                    delivered_at=now if success else None,
                    next_retry_at=next_retry_at,
                )
            )
            dispatch.status = "success" if success else ("failed" if attempts >= MAX_ATTEMPTS else "pending")
            dispatch.next_retry_at = next_retry_at
        except Exception as exc:
            next_retry_at = None if attempts >= MAX_ATTEMPTS else now + RETRY_DELAY
            db.add(
                WebhookDelivery(
                    webhook_dispatch_id=dispatch.id,
                    attempt_number=attempts,
                    error_message=str(exc),
                    status="failed",
                    next_retry_at=next_retry_at,
                )
            )
            dispatch.status = "failed" if attempts >= MAX_ATTEMPTS else "pending"
            dispatch.next_retry_at = next_retry_at
    db.commit()
