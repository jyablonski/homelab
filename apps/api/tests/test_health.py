import json
import logging
import sys

import pytest
from fastapi.testclient import TestClient

from config import Settings
from logging_config import JsonFormatter
from main import create_app


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
    assert (
        'http_server_requests_total{method="GET",route="/healthz",status="200"}'
        in response.text
    )
    assert "http_server_request_duration_seconds_bucket" in response.text


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
    assert request_log.status == 200
    assert request_log.duration_ms >= 0
    assert request_log.service == "api"
    assert request_log.environment == "local"


def test_unmatched_paths_share_one_route_label(test_client, caplog):
    with caplog.at_level(logging.INFO, logger="api.access"):
        test_client.get("/does-not-exist/123")

    request_log = next(
        record for record in caplog.records if record.message == "request completed"
    )

    assert request_log.status == 404
    assert request_log.route == "unmatched"


@pytest.fixture()
def failing_client():
    # Built before caplog: create_app's dictConfig replaces root handlers,
    # which would drop caplog's handler if it were installed first.
    app = create_app(Settings())

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("kaboom")

    return TestClient(app, raise_server_exceptions=False)


def test_unhandled_exception_is_logged_and_counted_as_500(failing_client, caplog):
    client = failing_client
    with caplog.at_level(logging.INFO, logger="api.access"):
        response = client.get("/boom")

    failed_log = next(
        record for record in caplog.records if record.message == "request failed"
    )
    metrics = client.get("/metrics").text

    assert response.status_code == 500
    assert failed_log.levelno == logging.ERROR
    assert failed_log.status == 500
    assert failed_log.route == "/boom"
    assert (
        'http_server_requests_total{method="GET",route="/boom",status="500"}' in metrics
    )


def test_json_formatter_outputs_structured_log():
    record = logging.LogRecord(
        name="api.test",
        level=logging.WARNING,
        pathname=__file__,
        lineno=1,
        msg="request completed",
        args=(),
        exc_info=None,
    )
    record.request_id = "test-request"

    payload = json.loads(JsonFormatter().format(record))

    assert payload["level"] == "warn"
    assert payload["logger"] == "api.test"
    assert payload["msg"] == "request completed"
    assert payload["request_id"] == "test-request"
    assert "time" in payload


def test_json_formatter_puts_exception_on_one_line():
    try:
        raise ValueError("bad input")
    except ValueError:
        record = logging.LogRecord(
            name="api.test",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="request failed",
            args=(),
            exc_info=sys.exc_info(),
        )

    line = JsonFormatter().format(record)
    payload = json.loads(line)

    assert "\n" not in line
    assert payload["error"] == "ValueError: bad input"
    assert "Traceback" in payload["exception"]
