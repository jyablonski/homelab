import json
import logging

from logging_config import JsonFormatter


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


def test_request_logging_adds_request_id(test_client, caplog):
    with caplog.at_level(logging.INFO, logger="api.access"):
        response = test_client.get("/healthz", headers={"X-Request-ID": "test-request"})

    request_log = next(
        record for record in caplog.records if record.message == "request completed"
    )

    assert response.headers["X-Request-ID"] == "test-request"
    assert request_log.request_id == "test-request"
    assert request_log.method == "GET"
    assert request_log.route == "/healthz"
    assert request_log.status_code == 200
    assert request_log.app == "Homelab API"
    assert request_log.environment == "local"


def test_json_formatter_outputs_structured_log():
    record = logging.LogRecord(
        name="api.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="request completed",
        args=(),
        exc_info=None,
    )
    record.request_id = "test-request"

    payload = json.loads(JsonFormatter().format(record))

    assert payload["level"] == "info"
    assert payload["logger"] == "api.test"
    assert payload["message"] == "request completed"
    assert payload["request_id"] == "test-request"
    assert "timestamp" in payload
