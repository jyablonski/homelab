import json
from datetime import UTC, datetime
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import HTTPException
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException

from config import Settings
from kubernetes_runner import (
    KubernetesRunnerClient,
    _as_utc,
    _grafana_time,
    _isoformat,
    _job_status,
    _load_k8s_apis,
)


def test_list_runnables_includes_status_from_matching_jobs():
    batch_api = FakeBatchApi(
        cronjobs=[_cronjob()],
        jobs=[
            _job(
                name="api-print-reminders-rows-manual-active",
                active=1,
            )
        ],
    )
    runner = KubernetesRunnerClient(
        settings=Settings(namespace="apps"),
        batch_api=batch_api,
    )

    runnables = runner.list_runnables()

    assert len(runnables) == 1
    assert runnables[0].cronjob_name == "api-print-reminders-rows"
    assert runnables[0].active_run == "api-print-reminders-rows-manual-active"
    assert runnables[0].last_status == "Running"
    assert runnables[0].last_logs_url is not None


def test_run_refuses_when_matching_job_is_active():
    batch_api = FakeBatchApi(
        cronjobs=[_cronjob()],
        jobs=[
            _job(
                name="api-print-reminders-rows-manual-active",
                active=1,
            )
        ],
    )
    runner = KubernetesRunnerClient(
        settings=Settings(namespace="apps"),
        batch_api=batch_api,
    )

    with pytest.raises(HTTPException) as exc:
        runner.run(namespace="apps", cronjob_name="api-print-reminders-rows")

    assert exc.value.status_code == 409
    assert batch_api.created_jobs == []


def test_run_creates_manual_job_from_cronjob_template():
    batch_api = FakeBatchApi(cronjobs=[_cronjob()])
    runner = KubernetesRunnerClient(
        settings=Settings(namespace="apps"),
        batch_api=batch_api,
    )

    run = runner.run(namespace="apps", cronjob_name="api-print-reminders-rows")

    assert run.status == "Pending"
    assert run.name.startswith("api-print-reminders-rows-manual-")
    assert len(batch_api.created_jobs) == 1
    assert (
        batch_api.created_jobs[0].metadata.labels["homelab.jacob/manual-run"] == "true"
    )
    assert batch_api.created_jobs[0].spec.template.spec.restart_policy == "OnFailure"


def test_list_runs_maps_completed_jobs():
    completed_at = datetime(2026, 5, 21, 12, 0, tzinfo=UTC)
    started_at = datetime(2026, 5, 21, 11, 0, tzinfo=UTC)
    batch_api = FakeBatchApi(
        cronjobs=[_cronjob()],
        jobs=[
            _job(
                name="api-print-reminders-rows-manual-done",
                succeeded=1,
                started_at=started_at,
                completed_at=completed_at,
            )
        ],
    )
    runner = KubernetesRunnerClient(
        settings=Settings(namespace="apps"),
        batch_api=batch_api,
        core_api=None,
    )

    runs = runner.list_runs(namespace="apps", cronjob_name="api-print-reminders-rows")

    assert runs[0].status == "Succeeded"
    assert runs[0].completed_at == completed_at.isoformat()
    assert runs[0].logs_url is not None
    parsed = urlparse(runs[0].logs_url)
    params = parse_qs(parsed.query)
    left = json.loads(params["left"][0])
    assert parsed.path == "/explore"
    assert "panes" not in params
    assert "schemaVersion" not in params
    assert left[2] == "Loki"
    assert left[0] == "2026-05-21T10:58:00Z"
    assert left[1] == "2026-05-21T12:05:00Z"
    assert (
        left[3]["expr"]
        == '{namespace="apps", container="print-reminders-rows", pod=~"api-print-reminders-rows-manual-done-.+"}'
    )
    assert left[3]["editorMode"] == "builder"


def test_logs_url_uses_pods_for_job_name_label():
    batch_api = FakeBatchApi(
        cronjobs=[_cronjob()],
        jobs=[_job(name="api-print-reminders-rows-manual-done", succeeded=1)],
    )
    core_api = FakeCoreApi(
        pods={
            (
                "apps",
                "api-print-reminders-rows-manual-done",
            ): ["api-print-reminders-rows-manual-done-abc12"]
        }
    )
    runner = KubernetesRunnerClient(
        settings=Settings(namespace="apps"),
        batch_api=batch_api,
        core_api=core_api,
    )

    runs = runner.list_runs(namespace="apps", cronjob_name="api-print-reminders-rows")

    left = json.loads(parse_qs(urlparse(runs[0].logs_url).query)["left"][0])
    assert (
        left[3]["expr"]
        == '{namespace="apps", container="print-reminders-rows", pod="api-print-reminders-rows-manual-done-abc12"}'
    )


def test_list_jobs_returns_serialized_jobs():
    batch_api = FakeBatchApi(
        cronjobs=[_cronjob(), _cronjob(name="other-job", app="web", job="cleanup")],
        jobs=[_job(name="api-print-reminders-rows-manual-done", succeeded=1)],
    )
    runner = KubernetesRunnerClient(
        settings=Settings(namespace="apps"),
        batch_api=batch_api,
    )

    jobs = runner.list_jobs()

    assert len(jobs) == 2
    assert jobs[0]["app"] == "api"
    assert jobs[1]["app"] == "web"


def test_list_jobs_skips_cronjobs_without_runnable_label():
    cronjob = _cronjob()
    cronjob.metadata.labels["homelab.jacob/runnable"] = "false"
    batch_api = FakeBatchApi(cronjobs=[cronjob])
    runner = KubernetesRunnerClient(
        settings=Settings(namespace="apps"),
        batch_api=batch_api,
    )

    assert runner.list_jobs() == []


def test_run_job_and_list_job_runs_use_app_job_lookup():
    batch_api = FakeBatchApi(
        cronjobs=[_cronjob()],
        jobs=[_job(name="api-print-reminders-rows-manual-done", succeeded=1)],
    )
    runner = KubernetesRunnerClient(
        settings=Settings(namespace="apps"),
        batch_api=batch_api,
    )

    runs = runner.list_job_runs(app="api", name="print-reminders-rows")
    assert runs[0]["status"] == "success"

    batch_api.jobs = []
    created = runner.run_job(app="api", name="print-reminders-rows")
    assert created["runId"].startswith("api-print-reminders-rows-manual-")
    assert batch_api.created_jobs


def test_get_cronjob_by_app_job_returns_404_when_missing():
    runner = KubernetesRunnerClient(
        settings=Settings(namespace="apps"),
        batch_api=FakeBatchApi(cronjobs=[]),
    )

    with pytest.raises(HTTPException) as exc:
        runner.run_job(app="missing", name="job")

    assert exc.value.status_code == 404


def test_get_cronjob_reraises_non_404_api_errors():
    class ErrorBatchApi(FakeBatchApi):
        def read_namespaced_cron_job(self, name: str, namespace: str):
            raise ApiException(status=500, reason="server error")

    runner = KubernetesRunnerClient(
        settings=Settings(namespace="apps"),
        batch_api=ErrorBatchApi(cronjobs=[_cronjob()]),
    )

    with pytest.raises(ApiException):
        runner.list_runs(namespace="apps", cronjob_name="api-print-reminders-rows")


def test_get_cronjob_returns_404_for_missing_name():
    runner = KubernetesRunnerClient(
        settings=Settings(namespace="apps"),
        batch_api=FakeBatchApi(cronjobs=[_cronjob()]),
    )

    with pytest.raises(HTTPException) as exc:
        runner.list_runs(namespace="apps", cronjob_name="missing")

    assert exc.value.status_code == 404


def test_run_returns_404_when_cronjob_not_runnable():
    cronjob = _cronjob()
    cronjob.metadata.labels["homelab.jacob/runnable"] = "false"
    runner = KubernetesRunnerClient(
        settings=Settings(namespace="apps"),
        batch_api=FakeBatchApi(cronjobs=[cronjob]),
    )

    with pytest.raises(HTTPException) as exc:
        runner.run(namespace="apps", cronjob_name="api-print-reminders-rows")

    assert exc.value.status_code == 404


def test_list_runs_maps_failed_jobs():
    batch_api = FakeBatchApi(
        cronjobs=[_cronjob()],
        jobs=[_job(name="api-print-reminders-rows-manual-failed", failed=1)],
    )
    runner = KubernetesRunnerClient(
        settings=Settings(namespace="apps"),
        batch_api=batch_api,
    )

    runs = runner.list_runs(namespace="apps", cronjob_name="api-print-reminders-rows")

    assert runs[0].status == "Failed"


def test_logs_url_uses_regex_when_multiple_pods_exist():
    batch_api = FakeBatchApi(
        cronjobs=[_cronjob()],
        jobs=[_job(name="api-print-reminders-rows-manual-done", succeeded=1)],
    )
    core_api = FakeCoreApi(
        pods={
            (
                "apps",
                "api-print-reminders-rows-manual-done",
            ): [
                "api-print-reminders-rows-manual-done-abc12",
                "api-print-reminders-rows-manual-done-def34",
            ]
        }
    )
    runner = KubernetesRunnerClient(
        settings=Settings(namespace="apps"),
        batch_api=batch_api,
        core_api=core_api,
    )

    left = json.loads(
        parse_qs(
            urlparse(
                runner.list_runs(
                    namespace="apps",
                    cronjob_name="api-print-reminders-rows",
                )[0].logs_url
            ).query
        )["left"][0]
    )
    assert "pod=~" in left[3]["expr"]
    assert "abc12" in left[3]["expr"]


def test_pod_logql_filter_falls_back_when_core_api_errors():
    batch_api = FakeBatchApi(
        cronjobs=[_cronjob()],
        jobs=[_job(name="api-print-reminders-rows-manual-done", succeeded=1)],
    )
    core_api = FakeCoreApi(raise_on_list=True)
    runner = KubernetesRunnerClient(
        settings=Settings(namespace="apps"),
        batch_api=batch_api,
        core_api=core_api,
    )

    assert 'pod=~"' in runner._pod_logql_filter(
        namespace="apps",
        job_name="api-print-reminders-rows-manual-done",
    )


def test_logs_time_range_without_start_time_uses_default_window():
    runner = KubernetesRunnerClient(
        settings=Settings(),
        batch_api=object(),
        core_api=None,
    )
    job = client.V1Job(metadata=client.V1ObjectMeta(name="job"))

    assert runner._logs_time_range(job) == {"from": "now-1h", "to": "now"}


def test_helper_functions_cover_status_and_time_formatting():
    pending = client.V1Job(metadata=client.V1ObjectMeta(name="pending"))
    assert _job_status(pending) == "Pending"

    naive = datetime(2026, 5, 21, 12, 0)
    assert _as_utc(naive).tzinfo == UTC
    assert (
        _grafana_time(datetime(2026, 5, 21, 12, 0, tzinfo=UTC))
        == "2026-05-21T12:00:00Z"
    )
    assert _isoformat(None) is None


def test_load_k8s_apis_falls_back_to_kubeconfig(monkeypatch):
    monkeypatch.setattr(
        config,
        "load_incluster_config",
        lambda: (_ for _ in ()).throw(config.ConfigException()),
    )
    monkeypatch.setattr(config, "load_kube_config", lambda: None)
    monkeypatch.setattr(client, "BatchV1Api", lambda api_client: "batch")
    monkeypatch.setattr(client, "CoreV1Api", lambda api_client: "core")

    batch_api, core_api = _load_k8s_apis()

    assert batch_api == "batch"
    assert core_api == "core"


def test_runner_init_uses_load_k8s_apis_when_clients_omitted(monkeypatch):
    monkeypatch.setattr(
        "kubernetes_runner._load_k8s_apis",
        lambda: (FakeBatchApi(cronjobs=[_cronjob()]), FakeCoreApi()),
    )
    runner = KubernetesRunnerClient(settings=Settings(namespace="apps"))

    assert runner.list_runnables()[0].job == "print-reminders-rows"


def test_logs_url_encodes_logql_in_query_string():
    runner = KubernetesRunnerClient(
        settings=Settings(loki_datasource_uid="P8E80F9AEF21F6940"),
        batch_api=object(),
        core_api=None,
    )
    job = client.V1Job(
        metadata=client.V1ObjectMeta(
            name="api-print-reminders-rows-manual-20260521164412",
            namespace="apps",
        )
    )
    url = runner._logs_url(namespace="apps", job=job, container="print-reminders-rows")
    assert "schemaVersion" not in url
    assert "panes" not in url
    assert "left=" in url
    assert "P8E80F9AEF21F6940" in url
    assert "print-reminders-rows" in url
    assert "api-print-reminders-rows-manual-20260521164412" in url


class FakeBatchApi:
    def __init__(
        self,
        *,
        cronjobs: list[client.V1CronJob],
        jobs: list[client.V1Job] | None = None,
    ) -> None:
        self.cronjobs = {cronjob.metadata.name: cronjob for cronjob in cronjobs}
        self.jobs = jobs or []
        self.created_jobs: list[client.V1Job] = []

    def list_namespaced_cron_job(self, namespace: str, label_selector: str):
        return client.V1CronJobList(items=list(self.cronjobs.values()))

    def read_namespaced_cron_job(self, name: str, namespace: str):
        if name not in self.cronjobs:
            raise ApiException(status=404, reason="Not Found")
        return self.cronjobs[name]

    def list_namespaced_job(self, namespace: str, label_selector: str):
        return client.V1JobList(items=self.jobs)

    def create_namespaced_job(self, namespace: str, body: client.V1Job):
        self.created_jobs.append(body)
        return body


class FakeCoreApi:
    def __init__(
        self,
        *,
        pods: dict[tuple[str, str], list[str]] | None = None,
        raise_on_list: bool = False,
    ) -> None:
        self.pods = pods or {}
        self.raise_on_list = raise_on_list

    def list_namespaced_pod(self, namespace: str, label_selector: str):
        if self.raise_on_list:
            raise ApiException(status=500, reason="error")
        job_name = label_selector.removeprefix("job-name=")
        names = self.pods.get((namespace, job_name), [])
        return client.V1PodList(
            items=[
                client.V1Pod(
                    metadata=client.V1ObjectMeta(name=name, namespace=namespace)
                )
                for name in names
            ]
        )


def _cronjob(
    *,
    name: str = "api-print-reminders-rows",
    app: str = "api",
    job: str = "print-reminders-rows",
) -> client.V1CronJob:
    labels = {
        "homelab.jacob/runnable": "true",
        "homelab.jacob/app": app,
        "homelab.jacob/job": job,
    }
    return client.V1CronJob(
        metadata=client.V1ObjectMeta(
            name=name,
            namespace="apps",
            labels=labels,
            annotations={"homelab.jacob/description": "Print reminder table row count"},
        ),
        spec=client.V1CronJobSpec(
            schedule="0 0 * * *",
            suspend=True,
            job_template=client.V1JobTemplateSpec(
                metadata=client.V1ObjectMeta(labels=labels),
                spec=client.V1JobSpec(
                    template=client.V1PodTemplateSpec(
                        spec=client.V1PodSpec(
                            restart_policy="OnFailure",
                            containers=[
                                client.V1Container(
                                    name=job,
                                    image="registry.home:5000/homelab/api:dev",
                                )
                            ],
                        )
                    )
                ),
            ),
        ),
    )


def _job(
    *,
    name: str,
    active: int | None = None,
    succeeded: int | None = None,
    failed: int | None = None,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
) -> client.V1Job:
    labels = {
        "homelab.jacob/app": "api",
        "homelab.jacob/job": "print-reminders-rows",
    }
    conditions = []
    if completed_at:
        conditions.append(
            client.V1JobCondition(
                status="True",
                type="Complete",
                last_transition_time=completed_at,
            )
        )
    return client.V1Job(
        metadata=client.V1ObjectMeta(
            name=name,
            namespace="apps",
            labels=labels,
        ),
        status=client.V1JobStatus(
            active=active,
            succeeded=succeeded,
            failed=failed,
            start_time=started_at or datetime(2026, 5, 21, 11, 0, tzinfo=UTC),
            conditions=conditions,
        ),
    )
