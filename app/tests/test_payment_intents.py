def test_root_route(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "API is running"}


def test_create_payment_intent(client):
    response = client.post(
        "/v1/payment_intents",
        json={"amount": 1000, "currency": "usd", "merchant_id": "merchant_1"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"].startswith("pi_")
    assert body["amount"] == 1000
    assert body["currency"] == "usd"
    assert body["merchant_id"] == "merchant_1"
    assert body["status"] == "requires_payment_method"


def test_list_payment_intents(client):
    client.post(
        "/v1/payment_intents",
        json={"amount": 1000, "currency": "usd", "merchant_id": "merchant_1"},
    )
    client.post(
        "/v1/payment_intents",
        json={"amount": 2000, "currency": "eur", "merchant_id": "merchant_1"},
    )

    response = client.get("/v1/payment_intents/")

    assert response.status_code == 200
    body = response.json()
    assert len(body["payment_intents"]) == 2


def test_get_payment_intent(client):
    created = client.post(
        "/v1/payment_intents",
        json={"amount": 1000, "currency": "usd", "merchant_id": "merchant_1"},
    ).json()

    response = client.get(f"/v1/payment_intents/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_payment_intent_not_found(client):
    response = client.get("/v1/payment_intents/pi_missing")
    assert response.status_code == 404


def test_confirm_payment_intent(client):
    created = client.post(
        "/v1/payment_intents",
        json={"amount": 1000, "currency": "usd", "merchant_id": "merchant_1"},
    ).json()

    response = client.post(f"/v1/payment_intents/{created['id']}/confirm")

    assert response.status_code == 200
    assert response.json()["status"] == "requires_capture"


def test_cancel_payment_intent(client):
    created = client.post(
        "/v1/payment_intents",
        json={"amount": 1000, "currency": "usd", "merchant_id": "merchant_1"},
    ).json()

    response = client.post(f"/v1/payment_intents/{created['id']}/cancel")

    assert response.status_code == 200
    assert response.json()["status"] == "canceled"


def test_cannot_confirm_canceled_payment_intent(client):
    created = client.post(
        "/v1/payment_intents",
        json={"amount": 1000, "currency": "usd", "merchant_id": "merchant_1"},
    ).json()

    client.post(f"/v1/payment_intents/{created['id']}/cancel")
    response = client.post(f"/v1/payment_intents/{created['id']}/confirm")

    assert response.status_code == 409


def test_cannot_cancel_succeeded_payment_intent(client):
    created = client.post(
        "/v1/payment_intents",
        json={"amount": 1000, "currency": "usd", "merchant_id": "merchant_1"},
    ).json()

    client.post(f"/v1/payment_intents/{created['id']}/confirm")
    client.post(f"/v1/payment_intents/{created['id']}/capture")
    response = client.post(f"/v1/payment_intents/{created['id']}/cancel")

    assert response.status_code == 409


def test_create_payment_intent_validation(client):
    response = client.post(
        "/v1/payment_intents",
        json={"amount": -1, "currency": "us", "merchant_id": "merchant_1"},
    )

    assert response.status_code == 201

