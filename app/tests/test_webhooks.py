from unittest.mock import MagicMock, patch

from app.db.models import WebhookDispatch, WebhookEndpoint
from app.services.delivery import verify_webhook_signature


def create_endpoint(client, merchant_id="merchant_1", url="https://example.com/hook", event_types=None):
    return client.post(
        "/v1/webhooks/endpoints",
        json={
            "merchant_id": merchant_id,
            "url": url,
            "event_types": event_types or ["payment_intent.created"],
        },
    )


def test_webhook_signature_verification_and_dispatch_detail(client, db):
    endpoint_response = create_endpoint(client)
    endpoint = db.query(WebhookEndpoint).filter(WebhookEndpoint.id == endpoint_response.json()["id"]).first()

    payment_intent = client.post(
        "/v1/payment_intents",
        json={"amount": 500, "currency": "usd", "merchant_id": "merchant_1"},
    ).json()

    mock_response = MagicMock(status_code=200, text="OK")

    def fake_post(url, content, headers, timeout):
        assert url == endpoint.url
        assert verify_webhook_signature(endpoint.secret, content, headers["X-Webhook-Signature"])
        return mock_response

    with patch("app.services.delivery.httpx.post", side_effect=fake_post):
        response = client.post("/v1/webhooks/dispatches/process")

    assert response.status_code == 200
    dispatch = client.get("/v1/webhooks/dispatches").json()[0]
    detail = client.get(f"/v1/webhooks/dispatches/{dispatch['id']}")
    deliveries = client.get(f"/v1/webhooks/endpoints/{endpoint.id}/deliveries")

    assert detail.status_code == 200
    assert detail.json()["deliveries"][0]["status"] == "success"
    assert deliveries.status_code == 200
    assert deliveries.json()[0]["webhook_dispatch_id"] == dispatch["id"]
    assert payment_intent["id"] in detail.json()["payload"]["id"]


def test_process_dispatches_skips_future_retry(client, db):
    create_endpoint(client)
    client.post(
        "/v1/payment_intents",
        json={"amount": 500, "currency": "usd", "merchant_id": "merchant_1"},
    )
    dispatch = db.query(WebhookDispatch).first()
    from datetime import datetime, timedelta, timezone

    dispatch.next_retry_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    db.commit()

    with patch("app.services.delivery.httpx.post") as mock_post:
        response = client.post("/v1/webhooks/dispatches/process")

    assert response.status_code == 200
    assert mock_post.called is False
    assert client.get("/v1/webhooks/deliveries").json() == []
