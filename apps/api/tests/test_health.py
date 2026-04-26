def test_healthz_returns_ok(test_client):
    response = test_client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz_returns_ok_when_database_is_available(db_test_client):
    response = db_test_client.get("/readyz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_readyz_returns_503_when_database_is_unavailable(unavailable_database_client):
    response = unavailable_database_client.get("/readyz")

    assert response.status_code == 503
    assert response.json() == {"detail": "database unavailable"}


def test_metrics_endpoint_returns_prometheus_metrics(test_client):
    test_client.get("/healthz")

    response = test_client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "api_http_requests_total" in response.text
