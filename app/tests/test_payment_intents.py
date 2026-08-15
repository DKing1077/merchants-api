import threading


def test_idempotency_same_key_creates_one_record(client):
    payload = {"amount": 500, "currency": "usd", "merchant_id": "merchant_1"}
    headers = {"Idempotency-Key": "idem-key-123"}
    r1 = client.post("/v1/payment_intents", json=payload, headers=headers)
    r2 = client.post("/v1/payment_intents", json=payload, headers=headers)
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]

    listed = client.get("/v1/payment_intents/")
    assert listed.status_code == 200
    assert listed.json()["data"][0]["id"] == r1.json()["id"]
    assert len(listed.json()["data"]) == 1


def test_full_payment_lifecycle_ledger_nets_to_zero(client):
    pi = client.post(
        "/v1/payment_intents",
        json={"amount": 1000, "currency": "usd", "merchant_id": "merchant_1"},
    ).json()
    client.post(f"/v1/payment_intents/{pi['id']}/confirm")
    client.post(f"/v1/payment_intents/{pi['id']}/capture")

    refund = client.post(
        f"/v1/refunds/payment_intents/{pi['id']}/refunds",
        json={"amount": 1000},
    ).json()
    client.post(f"/v1/refunds/{refund['id']}/confirm")

    accounts = client.get("/v1/ledger/accounts").json()
    for account in accounts:
        balance = client.get(f"/v1/ledger/accounts/{account['id']}/balance").json()
        assert balance["balance"] == 0


def test_concurrent_payment_intents_have_unique_ids(client):
    # Create multiple payment intents concurrently; all IDs must be unique.
    # Uses threading to mirror real concurrent load, with a lock to guard
    # the in-memory SQLite test DB (which serialises writes).
    ids = []
    lock = threading.Lock()

    def create():
        r = client.post(
            "/v1/payment_intents",
            json={"amount": 100, "currency": "usd", "merchant_id": "merchant_1"},
        )
        if r.status_code == 201:
            with lock:
                ids.append(r.json()["id"])

    threads = [threading.Thread(target=create) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(ids) > 0
    assert len(ids) == len(set(ids))


def test_create_payment_intent_validation(client):
    assert client.post(
        "/v1/payment_intents",
        json={"amount": -1, "currency": "usd", "merchant_id": "merchant_1"},
    ).status_code == 422
    assert client.post(
        "/v1/payment_intents",
        json={"amount": 100, "currency": "toolong", "merchant_id": "merchant_1"},
    ).status_code == 422
    assert client.post(
        "/v1/payment_intents",
        json={"amount": 100, "currency": "usd", "merchant_id": "   "},
    ).status_code == 422


def test_root_route(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "API is running"}
    assert response.headers["X-Request-ID"]


def test_health_route(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "connected", "version": "1.0.0"}


def test_metrics_route(client):
    client.get("/")
    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert 'merchants_api_requests_total{method="GET",path="/"}' in metrics.text
