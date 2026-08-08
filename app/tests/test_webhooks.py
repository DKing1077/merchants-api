import pytest
from unittest.mock import patch, MagicMock


def create_endpoint(client, merchant_id="merchant_1", url="https://example.com/hook",
                    event_types=None):
    return client.post(
        "/v1/webhooks/endpoints",
        json={
            "merchant_id": merchant_id,
            "url": url,
            "event_types": event_types or ["payment_intent.created"],
        },
    )


# ---------------------------------------------------------------------------
# Webhook endpoints
# ---------------------------------------------------------------------------


def test_create_webhook_endpoint(client):
    response = create_endpoint(client)
    assert response.status_code == 200
    body = response.json()
    assert body["merchant_id"] == "merchant_1"
    assert "example.com" in body["url"]
    assert body["event_types"] == ["payment_intent.created"]
    assert body["is_active"] is True
    assert "id" in body
    assert "created_at" in body


def test_create_webhook_endpoint_multiple_event_types(client):
    response = create_endpoint(
        client,
        event_types=["payment_intent.created", "payment_intent.succeeded"],
    )
    assert response.status_code == 200
    assert len(response.json()["event_types"]) == 2


def test_create_webhook_endpoint_invalid_url(client):
    response = client.post(
        "/v1/webhooks/endpoints",
        json={"merchant_id": "m1", "url": "not-a-url", "event_types": ["x"]},
    )
    assert response.status_code == 422


def test_create_webhook_endpoint_missing_fields(client):
    response = client.post("/v1/webhooks/endpoints", json={"merchant_id": "m1"})
    assert response.status_code == 422


def test_list_webhook_endpoints_empty(client):
    response = client.get("/v1/webhooks/endpoints")
    assert response.status_code == 200
    assert response.json() == []


def test_list_webhook_endpoints(client):
    create_endpoint(client, merchant_id="m1")
    create_endpoint(client, merchant_id="m2", url="https://other.com/hook")
    response = client.get("/v1/webhooks/endpoints")
    assert response.status_code == 200
    assert len(response.json()) == 2


# ---------------------------------------------------------------------------
# Dispatches / Deliveries
# ---------------------------------------------------------------------------


def test_list_dispatches_empty(client):
    response = client.get("/v1/webhooks/dispatches")
    assert response.status_code == 200
    assert response.json() == []


def test_list_deliveries_empty(client):
    response = client.get("/v1/webhooks/deliveries")
    assert response.status_code == 200
    assert response.json() == []


def test_dispatches_created_after_payment_intent(client):
    create_endpoint(
        client,
        merchant_id="merchant_1",
        event_types=["payment_intent.created"],
    )
    client.post(
        "/v1/payment_intents",
        json={"amount": 500, "currency": "usd", "merchant_id": "merchant_1"},
    )
    response = client.get("/v1/webhooks/dispatches")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_process_dispatches_success(client):
    create_endpoint(
        client,
        merchant_id="merchant_1",
        event_types=["payment_intent.created"],
    )
    client.post(
        "/v1/payment_intents",
        json={"amount": 500, "currency": "usd", "merchant_id": "merchant_1"},
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "OK"

    with patch("app.services.delivery.httpx.post", return_value=mock_response):
        response = client.post("/v1/webhooks/dispatches/process")

    assert response.status_code == 200
    assert response.json() == {"message": "dispatches processed"}

    deliveries = client.get("/v1/webhooks/deliveries").json()
    assert len(deliveries) == 1
    assert deliveries[0]["status"] == "success"


def test_process_dispatches_failed_delivery(client):
    create_endpoint(
        client,
        merchant_id="merchant_1",
        event_types=["payment_intent.created"],
    )
    client.post(
        "/v1/payment_intents",
        json={"amount": 500, "currency": "usd", "merchant_id": "merchant_1"},
    )

    with patch("app.services.delivery.httpx.post", side_effect=Exception("timeout")):
        client.post("/v1/webhooks/dispatches/process")

    deliveries = client.get("/v1/webhooks/deliveries").json()
    assert len(deliveries) == 1
    assert deliveries[0]["status"] == "failed"
    assert "timeout" in deliveries[0]["error_message"]


def test_endpoint_not_dispatched_for_unsubscribed_event(client):
    create_endpoint(
        client,
        merchant_id="merchant_1",
        event_types=["refund.created"],
    )
    client.post(
        "/v1/payment_intents",
        json={"amount": 500, "currency": "usd", "merchant_id": "merchant_1"},
    )
    dispatches = client.get("/v1/webhooks/dispatches").json()
    assert dispatches == []
