import importlib.metadata
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from config import Settings
from main import _fastapi_version, create_app, get_runner_client


@pytest.fixture()
def prefixed_client(fake_runner_client):
    app = create_app(Settings(url_prefix="/runner"))
    app.dependency_overrides[get_runner_client] = lambda: fake_runner_client
    return TestClient(app)


def test_fastapi_version_unknown_when_package_missing():
    with patch(
        "main.importlib.metadata.version",
        side_effect=importlib.metadata.PackageNotFoundError,
    ):
        assert _fastapi_version() == "unknown"


def test_legacy_run_runnable_endpoint(prefixed_client, fake_runner_client):
    response = prefixed_client.post(
        "/api/runnables/apps/api-print-reminders-rows/runs",
    )

    assert response.status_code == 200
    assert response.json()["runId"] == "api-print-reminders-rows-manual-test"
    assert ("apps", "api-print-reminders-rows") in fake_runner_client.created_runs


def test_legacy_run_from_form_redirects_home(prefixed_client, fake_runner_client):
    response = prefixed_client.post(
        "/runs",
        data={"namespace": "apps", "cronjob_name": "api-print-reminders-rows"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "http://testserver/"
    assert ("apps", "api-print-reminders-rows") in fake_runner_client.created_runs


def test_list_job_runs_not_found():
    from kubernetes_runner import KubernetesRunnerClient
    from main import get_runner_client
    from test_kubernetes_runner import FakeBatchApi

    runner = KubernetesRunnerClient(
        settings=Settings(namespace="apps"),
        batch_api=FakeBatchApi(cronjobs=[]),
    )
    app = create_app()
    app.dependency_overrides[get_runner_client] = lambda: runner
    client = TestClient(app)

    response = client.get("/api/jobs/missing/job/runs")

    assert response.status_code == 404
