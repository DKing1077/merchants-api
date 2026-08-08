import pytest


MERCHANT_ID = "merchant_1"


def make_payment_intent(client, amount=1000, currency="usd", merchant_id=MERCHANT_ID, **headers):
    return client.post(
        "/v1/payment_intents",
        json={"amount": amount, "currency": currency, "merchant_id": merchant_id},
        headers=headers,
    )


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


def test_create_payment_intent(client):
    response = make_payment_intent(client)
    assert response.status_code == 201
    body = response.json()
    assert body["amount"] == 1000
    assert body["currency"] == "usd"
    assert body["merchant_id"] == MERCHANT_ID
    assert body["status"] == "requires_payment_method"
    assert body["is_flagged"] is False
    assert body["review_status"] is None


def test_create_payment_intent_missing_fields(client):
    response = client.post("/v1/payment_intents", json={"amount": 500})
    assert response.status_code == 422


def test_create_payment_intent_idempotency_key(client):
    headers = {"Idempotency-Key": "key-abc"}
    r1 = make_payment_intent(client, **headers)
    r2 = make_payment_intent(client, **headers)
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]


# ---------------------------------------------------------------------------
# List / Get
# ---------------------------------------------------------------------------


def test_list_payment_intents_empty(client):
    response = client.get("/v1/payment_intents/")
    assert response.status_code == 200
    assert response.json()["payment_intents"] == []


def test_list_payment_intents(client):
    make_payment_intent(client)
    make_payment_intent(client, amount=2000, currency="eur")
    response = client.get("/v1/payment_intents/")
    assert response.status_code == 200
    assert len(response.json()["payment_intents"]) == 2


def test_get_payment_intent(client):
    created = make_payment_intent(client).json()
    response = client.get(f"/v1/payment_intents/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_payment_intent_not_found(client):
    response = client.get("/v1/payment_intents/pi_missing")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Confirm → Capture lifecycle
# ---------------------------------------------------------------------------


def test_confirm_payment_intent(client):
    created = make_payment_intent(client).json()
    response = client.post(f"/v1/payment_intents/{created['id']}/confirm")
    assert response.status_code == 200
    assert response.json()["status"] == "requires_capture"


def test_capture_payment_intent(client):
    created = make_payment_intent(client).json()
    client.post(f"/v1/payment_intents/{created['id']}/confirm")
    response = client.post(f"/v1/payment_intents/{created['id']}/capture")
    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"


def test_cannot_capture_without_confirm(client):
    created = make_payment_intent(client).json()
    response = client.post(f"/v1/payment_intents/{created['id']}/capture")
    assert response.status_code == 409


def test_cannot_confirm_already_confirmed(client):
    created = make_payment_intent(client).json()
    client.post(f"/v1/payment_intents/{created['id']}/confirm")
    response = client.post(f"/v1/payment_intents/{created['id']}/confirm")
    assert response.status_code == 409


def test_cannot_confirm_succeeded_payment_intent(client):
    created = make_payment_intent(client).json()
    client.post(f"/v1/payment_intents/{created['id']}/confirm")
    client.post(f"/v1/payment_intents/{created['id']}/capture")
    response = client.post(f"/v1/payment_intents/{created['id']}/confirm")
    assert response.status_code == 409


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------


def test_cancel_payment_intent(client):
    created = make_payment_intent(client).json()
    response = client.post(f"/v1/payment_intents/{created['id']}/cancel")
    assert response.status_code == 200
    assert response.json()["status"] == "canceled"


def test_cannot_cancel_succeeded_payment_intent(client):
    created = make_payment_intent(client).json()
    client.post(f"/v1/payment_intents/{created['id']}/confirm")
    client.post(f"/v1/payment_intents/{created['id']}/capture")
    response = client.post(f"/v1/payment_intents/{created['id']}/cancel")
    assert response.status_code == 409


def test_cannot_cancel_already_canceled(client):
    created = make_payment_intent(client).json()
    client.post(f"/v1/payment_intents/{created['id']}/cancel")
    response = client.post(f"/v1/payment_intents/{created['id']}/cancel")
    assert response.status_code == 409


def test_cannot_confirm_canceled_payment_intent(client):
    created = make_payment_intent(client).json()
    client.post(f"/v1/payment_intents/{created['id']}/cancel")
    response = client.post(f"/v1/payment_intents/{created['id']}/confirm")
    assert response.status_code == 409


# ---------------------------------------------------------------------------
# Flag / Review
# ---------------------------------------------------------------------------


def test_flag_payment_intent(client):
    created = make_payment_intent(client).json()
    response = client.post(
        f"/v1/payment_intents/{created['id']}/flag",
        json={"reason": "suspicious activity"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["is_flagged"] is True
    assert body["review_status"] == "pending_review"
    assert body["review_reason"] == "suspicious activity"


def test_flag_payment_intent_not_found(client):
    response = client.post(
        "/v1/payment_intents/pi_missing/flag",
        json={"reason": "test"},
    )
    assert response.status_code == 404


def test_list_flagged_payment_intents(client):
    pi1 = make_payment_intent(client).json()
    make_payment_intent(client)
    client.post(f"/v1/payment_intents/{pi1['id']}/flag", json={"reason": "fraud"})
    response = client.get("/v1/payment_intents/admin/flagged")
    assert response.status_code == 200
    flagged = response.json()["payment_intents"]
    assert len(flagged) == 1
    assert flagged[0]["id"] == pi1["id"]


def test_review_payment_intent_approved(client):
    created = make_payment_intent(client).json()
    client.post(f"/v1/payment_intents/{created['id']}/flag", json={"reason": "review"})
    response = client.post(
        f"/v1/payment_intents/admin/{created['id']}/review",
        json={"review_status": "approved"},
    )
    assert response.status_code == 200
    assert response.json()["review_status"] == "approved"


def test_review_payment_intent_rejected(client):
    created = make_payment_intent(client).json()
    client.post(f"/v1/payment_intents/{created['id']}/flag", json={"reason": "review"})
    response = client.post(
        f"/v1/payment_intents/admin/{created['id']}/review",
        json={"review_status": "rejected"},
    )
    assert response.status_code == 200
    assert response.json()["review_status"] == "rejected"


def test_cannot_review_unflagged_payment_intent(client):
    created = make_payment_intent(client).json()
    response = client.post(
        f"/v1/payment_intents/admin/{created['id']}/review",
        json={"review_status": "approved"},
    )
    assert response.status_code == 409


def test_cannot_confirm_rejected_payment_intent(client):
    created = make_payment_intent(client).json()
    client.post(f"/v1/payment_intents/{created['id']}/flag", json={"reason": "review"})
    client.post(
        f"/v1/payment_intents/admin/{created['id']}/review",
        json={"review_status": "rejected"},
    )
    response = client.post(f"/v1/payment_intents/{created['id']}/confirm")
    assert response.status_code == 409
