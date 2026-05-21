import pytest
from fastapi.testclient import TestClient

from jobs_api import runnable_to_job
from main import create_app, get_runner_client
from models import JobRun, Runnable


class FakeRunnerClient:
    def __init__(self) -> None:
        self.runnables = [
            Runnable(
                namespace="apps",
                cronjob_name="api-print-reminders-rows",
                app="api",
                job="print-reminders-rows",
                description="Print reminder table row count",
                schedule="0 0 * * *",
                suspended=True,
                last_run="api-print-reminders-rows-manual-20260521000000",
                last_status="Succeeded",
                last_logs_url="http://grafana.home/explore?left=test",
            )
        ]
        self.runs = [
            JobRun(
                namespace="apps",
                name="api-print-reminders-rows-manual-20260521000002",
                app="api",
                job="print-reminders-rows",
                status="Running",
                started_at="2026-05-21T16:00:00+00:00",
            ),
            JobRun(
                namespace="apps",
                name="api-print-reminders-rows-manual-20260521000001",
                app="api",
                job="print-reminders-rows",
                status="Failed",
                started_at="2026-05-21T14:00:00+00:00",
                completed_at="2026-05-21T14:01:00+00:00",
            ),
            JobRun(
                namespace="apps",
                name="api-print-reminders-rows-manual-20260521000000",
                app="api",
                job="print-reminders-rows",
                status="Succeeded",
                started_at="2026-05-21T12:00:00+00:00",
                completed_at="2026-05-21T12:00:30+00:00",
                logs_url="http://grafana.home/explore?left=test",
            ),
        ]
        self.created_runs: list[tuple[str, str]] = []

    def list_jobs(self) -> list[dict[str, object]]:
        return [
            runnable_to_job(runnable, runs=self.runs) for runnable in self.runnables
        ]

    def list_runnables(self) -> list[Runnable]:
        return self.runnables

    def list_job_runs(self, *, app: str, name: str) -> list[dict[str, object]]:
        from jobs_api import run_to_history_item

        return [run_to_history_item(run) for run in self.runs]

    def run_job(self, *, app: str, name: str) -> dict[str, object]:
        run = self.run(namespace="apps", cronjob_name=f"{app}-{name}")
        return {
            "runId": run.name,
            "namespace": run.namespace,
            "grafanaUrl": run.logs_url,
        }

    def list_runs(self, *, namespace: str, cronjob_name: str) -> list[JobRun]:
        self.created_runs.append((namespace, f"list:{cronjob_name}"))
        return self.runs

    def run(self, *, namespace: str, cronjob_name: str) -> JobRun:
        self.created_runs.append((namespace, cronjob_name))
        return JobRun(
            namespace=namespace,
            name=f"{cronjob_name}-manual-test",
            app="api",
            job="print-reminders-rows",
            status="Running",
            logs_url="http://grafana.home/explore?left=test",
        )


@pytest.fixture()
def fake_runner_client():
    return FakeRunnerClient()


@pytest.fixture()
def test_client(fake_runner_client):
    app = create_app()
    app.dependency_overrides[get_runner_client] = lambda: fake_runner_client
    return TestClient(app)
