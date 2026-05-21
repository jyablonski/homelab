def test_healthz_returns_ok(test_client):
    response = test_client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_metrics_endpoint_returns_prometheus_metrics(test_client):
    test_client.get("/healthz")

    response = test_client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "runner_http_requests_total" in response.text


def test_home_page_loads_runner_shell(test_client):
    response = test_client.get("/")

    assert response.status_code == 200
    assert "homelab / runner" in response.text
    assert "Runnables" in response.text
    assert "/api/jobs" in response.text
    assert "app.js" in response.text


def test_static_assets_are_served_at_unprefixed_paths(test_client):
    response = test_client.get("/static/styles.css")

    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]
    assert "--bg:" in response.text


def test_list_jobs_returns_json(test_client):
    response = test_client.get("/api/jobs")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["app"] == "api"
    assert payload[0]["name"] == "print-reminders-rows"
    assert payload[0]["schedule"]["manual"] is True
    assert payload[0]["status"] == "running"
    assert "history" in payload[0]


def test_list_job_runs_returns_full_history(test_client):
    response = test_client.get("/api/jobs/api/print-reminders-rows/runs")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 3
    assert payload[0]["status"] == "running"
    assert payload[0]["id"] == "api-print-reminders-rows-manual-20260521000002"


def test_run_job_returns_run_id_and_grafana_url(test_client, fake_runner_client):
    response = test_client.post("/api/jobs/api/print-reminders-rows/run")

    assert response.status_code == 200
    assert response.json()["runId"] == "api-print-reminders-rows-manual-test"
    assert response.json()["grafanaUrl"] == "http://grafana.home/explore?left=test"
    assert fake_runner_client.created_runs == [("apps", "api-print-reminders-rows")]


def test_list_runnables_returns_json(test_client):
    response = test_client.get("/api/runnables")

    assert response.status_code == 200
    assert response.json()[0]["job"] == "print-reminders-rows"


def test_list_runs_returns_json(test_client, fake_runner_client):
    response = test_client.get("/api/runnables/apps/api-print-reminders-rows/runs")

    assert response.status_code == 200
    assert response.json()[0]["status"] == "Running"
