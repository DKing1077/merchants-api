from fastapi.testclient import TestClient

from app.main import app
from app.services import payment_service

client = TestClient(app)


def setup_function():
    payment_service.payment_intents.clear()


def test_root_route():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "API is running"}


def test_create_payment_intent():
    response = client.post(
        "/v1/payment_intents/",
        json={"amount": 1000, "currency": "usd"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "pi_1"
    assert body["amount"] == 1000
    assert body["currency"] == "usd"
    assert body["status"] == "requires_payment_method"


def test_list_payment_intents():
    client.post("/v1/payment_intents/", json={"amount": 1000, "currency": "usd"})
    client.post("/v1/payment_intents/", json={"amount": 2000, "currency": "eur"})

    response = client.get("/v1/payment_intents/")

    assert response.status_code == 200
    body = response.json()
    assert len(body["payment_intents"]) == 2


def test_get_payment_intent():
    created = client.post(
        "/v1/payment_intents/",
        json={"amount": 1000, "currency": "usd"},
    ).json()

    response = client.get(f"/v1/payment_intents/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_payment_intent_not_found():
    response = client.get("/v1/payment_intents/pi_missing")

    assert response.status_code == 404


def test_confirm_payment_intent():
    created = client.post(
        "/v1/payment_intents/",
        json={"amount": 1000, "currency": "usd"},
    ).json()

    response = client.post(f"/v1/payment_intents/{created['id']}/confirm")

    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"


def test_cancel_payment_intent():
    created = client.post(
        "/v1/payment_intents/",
        json={"amount": 1000, "currency": "usd"},
    ).json()

    response = client.post(f"/v1/payment_intents/{created['id']}/cancel")

    assert response.status_code == 200
    assert response.json()["status"] == "canceled"


def test_cannot_confirm_canceled_payment_intent():
    created = client.post(
        "/v1/payment_intents/",
        json={"amount": 1000, "currency": "usd"},
    ).json()

    client.post(f"/v1/payment_intents/{created['id']}/cancel")
    response = client.post(f"/v1/payment_intents/{created['id']}/confirm")

    assert response.status_code == 409


def test_cannot_cancel_succeeded_payment_intent():
    created = client.post(
        "/v1/payment_intents/",
        json={"amount": 1000, "currency": "usd"},
    ).json()

    client.post(f"/v1/payment_intents/{created['id']}/confirm")
    response = client.post(f"/v1/payment_intents/{created['id']}/cancel")

    assert response.status_code == 409


def test_create_payment_intent_validation():
    response = client.post(
        "/v1/payment_intents/",
        json={"amount": -1, "currency": "us"},
    )

    assert response.status_code == 422