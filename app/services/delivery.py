from app.db.models import WebhookDispatch, WebhookEndpoint, WebhookDelivery
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import httpx


def process_pending_dispatches(db):
    dispatches = db.query(WebhookDispatch).filter(WebhookDispatch.status == "pending").all()

    for dispatch in dispatches:
        endpoint = db.query(WebhookEndpoint).filter(WebhookEndpoint.id == dispatch.webhook_endpoint_id).first()
        attempts = db.query(WebhookDelivery).filter(WebhookDelivery.webhook_dispatch_id == dispatch.id).count() + 1

        try:
            payload_json = json.dumps(dispatch.payload, separators=(",", ":"), sort_keys=True)

            key = bytes.fromhex(endpoint.secret)
            signature = hmac.new(
                key,
                payload_json.encode(),
                hashlib.sha256,
            ).hexdigest()

            response = httpx.post(
                endpoint.url,
                content=payload_json,
                headers={
                    "Content-Type": "application/json",
                    "X-Webhook-Signature": f"sha256={signature}",
                },
                timeout=5.0,
            )
            success = 200 <= response.status_code < 300

            db.add(WebhookDelivery(
                webhook_dispatch_id=dispatch.id,
                attempt_number=attempts,
                response_status=response.status_code,
                response_body=response.text,
                status="success" if success else "failed",
                delivered_at=datetime.now(timezone.utc) if success else None,
                next_retry_at=None if success or attempts >= 3 else datetime.now(timezone.utc) + timedelta(minutes=5),
            ))

            dispatch.status = "success" if success else ("failed" if attempts >= 3 else "pending")

        except Exception as exc:
            db.add(WebhookDelivery(
                webhook_dispatch_id=dispatch.id,
                attempt_number=attempts,
                error_message=str(exc),
                status="failed",
                next_retry_at=None if attempts >= 3 else datetime.now(timezone.utc) + timedelta(minutes=5),
            ))
            dispatch.status = "failed" if attempts >= 3 else "pending"

    db.commit()