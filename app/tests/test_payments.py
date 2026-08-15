MERCHANT_ID = "merchant_1"


def make_payment_intent(client, amount=1_000, currency="usd", merchant_id=MERCHANT_ID, headers=None):
    return client.post(
        "/v1/payment_intents",
        json={"amount": amount, "currency": currency, "merchant_id": merchant_id},
        headers=headers,
    )


def test_create_payment_intent(client):
    response = make_payment_intent(client)
    assert response.status_code == 201
    body = response.json()
    assert body["amount"] == 1_000
    assert body["captured_amount"] == 0
    assert body["total_refunded"] == 0
    assert body["risk_score"] >= 0
    assert body["status"] == "requires_payment_method"


def test_high_value_payment_auto_flagged(client):
    response = make_payment_intent(client, amount=100_001)
    assert response.status_code == 201
    body = response.json()
    assert body["is_flagged"] is True
    assert body["review_status"] == "pending_review"


def test_velocity_limit_returns_429(client):
    for _ in range(10):
        assert make_payment_intent(client).status_code == 201
    response = make_payment_intent(client)
    assert response.status_code == 429


def test_partial_capture_and_cancel_remaining(client):
    created = make_payment_intent(client).json()
    client.post(f"/v1/payment_intents/{created['id']}/confirm")

    partial = client.post(
        f"/v1/payment_intents/{created['id']}/capture",
        json={"amount": 400},
    )
    assert partial.status_code == 200
    assert partial.json()["captured_amount"] == 400
    assert partial.json()["status"] == "requires_capture"

    canceled = client.post(f"/v1/payment_intents/{created['id']}/cancel")
    assert canceled.status_code == 200
    assert canceled.json()["captured_amount"] == 400
    assert canceled.json()["status"] == "canceled"


def test_partial_refund_cannot_exceed_captured_amount(client):
    created = make_payment_intent(client).json()
    client.post(f"/v1/payment_intents/{created['id']}/confirm")
    client.post(f"/v1/payment_intents/{created['id']}/capture")

    refund = client.post(
        f"/v1/refunds/payment_intents/{created['id']}/refunds",
        json={"amount": 400},
    )
    assert refund.status_code == 200
    confirm = client.post(f"/v1/refunds/{refund.json()['id']}/confirm")
    assert confirm.status_code == 200

    payment_intent = client.get(f"/v1/payment_intents/{created['id']}")
    assert payment_intent.status_code == 200
    assert payment_intent.json()["total_refunded"] == 400

    too_large = client.post(
        f"/v1/refunds/payment_intents/{created['id']}/refunds",
        json={"amount": 700},
    )
    assert too_large.status_code == 409


def test_admin_risk_summary(client, admin_headers):
    high = make_payment_intent(client, amount=120_000).json()
    client.post(
        f"/v1/payment_intents/admin/{high['id']}/review",
        json={"review_status": "approved"},
        headers=admin_headers,
    )
    make_payment_intent(client, amount=1_000)

    response = client.get("/v1/admin/risk/summary", headers=admin_headers)
    assert response.status_code == 200
    summary = response.json()[0]
    assert summary["merchant_id"] == MERCHANT_ID
    assert summary["flagged"] == 1
    assert summary["approved"] == 1
    assert summary["average_risk_score"] > 0
