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
