from app.db.models import WebhookDispatch, WebhookEndpoint, WebhookDelivery
from datetime import datetime, timedelta
import httpx


def process_pending_dispatches(db):
    dispatches = db.query(WebhookDispatch).filter(WebhookDispatch.status == "pending").all()

    for dispatch in dispatches:
        endpoint = db.query(WebhookEndpoint).filter(WebhookEndpoint.id == dispatch.webhook_endpoint_id).first()
        attempts = db.query(WebhookDelivery).filter(WebhookDelivery.webhook_dispatch_id == dispatch.id).count() + 1

        try:
            response = httpx.post(endpoint.url, json=dispatch.payload, timeout=5.0)
            success = 200 <= response.status_code < 300

            db.add(WebhookDelivery(
                webhook_dispatch_id=dispatch.id,
                attempt_number=attempts,
                response_status=response.status_code,
                response_body=response.text,
                status="success" if success else "failed",
                delivered_at=datetime.utcnow() if success else None,
                next_retry_at=None if success or attempts >= 3 else datetime.utcnow() + timedelta(minutes=5),
            ))

            dispatch.status = "success" if success else ("failed" if attempts >= 3 else "pending")

        except Exception as exc:
            db.add(WebhookDelivery(
                webhook_dispatch_id=dispatch.id,
                attempt_number=attempts,
                error_message=str(exc),
                status="failed",
                next_retry_at=None if attempts >= 3 else datetime.utcnow() + timedelta(minutes=5),
            ))
            dispatch.status = "failed" if attempts >= 3 else "pending"

    db.commit()