import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import HTTPException, status
from kubernetes import client, config
from kubernetes.client import V1CronJob, V1Job
from kubernetes.client.exceptions import ApiException

from config import Settings
from jobs_api import runnable_to_job, run_to_history_item, run_to_response
from models import JobRun, Runnable

RUNNABLE_LABEL = "homelab.jacob/runnable"
APP_LABEL = "homelab.jacob/app"
JOB_LABEL = "homelab.jacob/job"


class KubernetesRunnerClient:
    def __init__(
        self,
        *,
        settings: Settings,
        batch_api: Any | None = None,
        core_api: Any | None = None,
    ) -> None:
        self.settings = settings
        if batch_api is None or core_api is None:
            loaded_batch_api, loaded_core_api = _load_k8s_apis()
            batch_api = batch_api or loaded_batch_api
            core_api = core_api if core_api is not None else loaded_core_api
        self.batch_api = batch_api
        self.core_api = core_api

    def list_jobs(self) -> list[dict[str, object]]:
        cronjobs = self.batch_api.list_namespaced_cron_job(
            namespace=self.settings.namespace,
            label_selector=f"{RUNNABLE_LABEL}=true",
        )
        jobs: list[dict[str, object]] = []
        for cronjob in sorted(
            cronjobs.items, key=lambda item: item.metadata.name or ""
        ):
            if _label(cronjob, RUNNABLE_LABEL) != "true":
                continue
            namespace = cronjob.metadata.namespace or self.settings.namespace
            runs = self.list_runs(
                namespace=namespace, cronjob_name=cronjob.metadata.name
            )
            runnable = self._runnable_from_cronjob(cronjob, runs=runs)
            jobs.append(runnable_to_job(runnable, runs=runs))
        return jobs

    def list_runnables(self) -> list[Runnable]:
        cronjobs = self.batch_api.list_namespaced_cron_job(
            namespace=self.settings.namespace,
            label_selector=f"{RUNNABLE_LABEL}=true",
        )
        return [
            self._runnable_from_cronjob(cronjob)
            for cronjob in cronjobs.items
            if _label(cronjob, RUNNABLE_LABEL) == "true"
        ]

    def run_job(self, *, app: str, name: str) -> dict[str, object]:
        cronjob = self._get_cronjob_by_app_job(app=app, name=name)
        run = self.run(
            namespace=cronjob.metadata.namespace or self.settings.namespace,
            cronjob_name=cronjob.metadata.name,
        )
        return run_to_response(run)

    def list_job_runs(self, *, app: str, name: str) -> list[dict[str, object]]:
        cronjob = self._get_cronjob_by_app_job(app=app, name=name)
        namespace = cronjob.metadata.namespace or self.settings.namespace
        runs = self.list_runs(
            namespace=namespace,
            cronjob_name=cronjob.metadata.name or "",
        )
        return [run_to_history_item(run) for run in runs]

    def list_runs(self, *, namespace: str, cronjob_name: str) -> list[JobRun]:
        cronjob = self._get_cronjob(namespace=namespace, name=cronjob_name)
        label_selector = self._job_label_selector(cronjob)
        jobs = self.batch_api.list_namespaced_job(
            namespace=namespace,
            label_selector=label_selector,
        )
        return sorted(
            [
                self._job_run_from_job(namespace=namespace, job=job)
                for job in jobs.items
            ],
            key=lambda run: run.started_at or run.name,
            reverse=True,
        )

    def run(self, *, namespace: str, cronjob_name: str) -> JobRun:
        cronjob = self._get_cronjob(namespace=namespace, name=cronjob_name)
        if _label(cronjob, RUNNABLE_LABEL) != "true":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="runnable not found",
            )

        active_run = self._active_run(namespace=namespace, cronjob=cronjob)
        if active_run is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"{cronjob_name} is already running as {active_run.name}",
            )

        manual_job = self._manual_job_from_cronjob(cronjob)
        created = self.batch_api.create_namespaced_job(
            namespace=namespace,
            body=manual_job,
        )
        return self._job_run_from_job(namespace=namespace, job=created)

    def _get_cronjob_by_app_job(self, *, app: str, name: str) -> V1CronJob:
        cronjobs = self.batch_api.list_namespaced_cron_job(
            namespace=self.settings.namespace,
            label_selector=f"{RUNNABLE_LABEL}=true,{APP_LABEL}={app},{JOB_LABEL}={name}",
        )
        if not cronjobs.items:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="job not found",
            )
        return cronjobs.items[0]

    def _get_cronjob(self, *, namespace: str, name: str) -> V1CronJob:
        try:
            return self.batch_api.read_namespaced_cron_job(
                name=name,
                namespace=namespace,
            )
        except ApiException as exc:
            if exc.status == status.HTTP_404_NOT_FOUND:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="runnable not found",
                ) from exc
            raise

    def _runnable_from_cronjob(
        self,
        cronjob: V1CronJob,
        *,
        runs: list[JobRun] | None = None,
    ) -> Runnable:
        namespace = cronjob.metadata.namespace or self.settings.namespace
        if runs is None:
            runs = self.list_runs(
                namespace=namespace, cronjob_name=cronjob.metadata.name
            )
        active = next((run for run in runs if run.status == "Running"), None)
        last = runs[0] if runs else None
        return Runnable(
            namespace=namespace,
            cronjob_name=cronjob.metadata.name,
            app=_label(cronjob, APP_LABEL),
            job=_label(cronjob, JOB_LABEL),
            description=_annotation(cronjob, "homelab.jacob/description"),
            schedule=cronjob.spec.schedule,
            suspended=bool(cronjob.spec.suspend),
            active_run=active.name if active else None,
            last_run=last.name if last else None,
            last_status=last.status if last else None,
            last_logs_url=last.logs_url if last else None,
        )

    def _active_run(self, *, namespace: str, cronjob: V1CronJob) -> JobRun | None:
        runs = self.batch_api.list_namespaced_job(
            namespace=namespace,
            label_selector=self._job_label_selector(cronjob),
        )
        for job in runs.items:
            if _job_status(job) == "Running":
                return self._job_run_from_job(namespace=namespace, job=job)
        return None

    def _manual_job_from_cronjob(self, cronjob: V1CronJob) -> V1Job:
        now = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        name = f"{cronjob.metadata.name}-manual-{now}"
        labels = dict(cronjob.spec.job_template.metadata.labels or {})
        labels["homelab.jacob/manual-run"] = "true"

        job = V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=client.V1ObjectMeta(
                name=name,
                namespace=cronjob.metadata.namespace,
                labels=labels,
            ),
            spec=cronjob.spec.job_template.spec,
        )
        return job

    def _job_run_from_job(self, *, namespace: str, job: V1Job) -> JobRun:
        app = _label(job, APP_LABEL)
        runnable_job = _label(job, JOB_LABEL)
        return JobRun(
            namespace=namespace,
            name=job.metadata.name,
            app=app,
            job=runnable_job,
            status=_job_status(job),
            started_at=_isoformat(getattr(job.status, "start_time", None)),
            completed_at=_completed_at(job),
            logs_url=self._logs_url(
                namespace=namespace,
                job=job,
                container=runnable_job,
            ),
        )

    def _job_label_selector(self, cronjob: V1CronJob) -> str:
        app = _label(cronjob, APP_LABEL)
        job = _label(cronjob, JOB_LABEL)
        return f"{APP_LABEL}={app},{JOB_LABEL}={job}"

    def _logql_for_run(self, *, namespace: str, job_name: str, container: str) -> str:
        # container matches the workload chart container name (homelab.jacob/job).
        # Pods for a Job carry job-name=<k8s Job.metadata.name>; match those pods
        # so the link covers every attempt in that run, not other runs of the job.
        pod_filter = self._pod_logql_filter(namespace=namespace, job_name=job_name)
        return f'{{namespace="{namespace}", container="{container}", {pod_filter}}}'

    def _pod_logql_filter(self, *, namespace: str, job_name: str) -> str:
        if self.core_api is not None:
            try:
                pods = self.core_api.list_namespaced_pod(
                    namespace=namespace,
                    label_selector=f"job-name={job_name}",
                )
                pod_names = sorted(
                    pod.metadata.name
                    for pod in pods.items
                    if pod.metadata and pod.metadata.name
                )
                if len(pod_names) == 1:
                    return f'pod="{pod_names[0]}"'
                if pod_names:
                    pattern = "|".join(pod_names)
                    return f'pod=~"{pattern}"'
            except ApiException:
                pass

        # Pod not created yet (Pending Job) — fall back to the Job name prefix.
        return f'pod=~"{job_name}-.+"'

    def _logs_time_range(self, job: V1Job) -> dict[str, str]:
        start = getattr(job.status, "start_time", None) if job.status else None
        end = _completion_time(job)
        if start is not None:
            start_utc = _as_utc(start)
            time_range = {
                "from": _grafana_time(start_utc - timedelta(minutes=2)),
                "to": "now",
            }
            if end is not None:
                time_range["to"] = _grafana_time(_as_utc(end) + timedelta(minutes=5))
            return time_range
        return {"from": "now-1h", "to": "now"}

    def _logs_url(self, *, namespace: str, job: V1Job, container: str) -> str:
        # Grafana Explore v0 "left" array URL — matches the label filters used in the UI
        # (namespace, container, pod). Do not use schemaVersion=1 / panes; Grafana
        # rewrites those to builder mode with an empty expr on load.
        query = self._logql_for_run(
            namespace=namespace,
            job_name=job.metadata.name,
            container=container,
        )
        uid = self.settings.loki_datasource_uid
        time_range = self._logs_time_range(job)
        left = [
            time_range["from"],
            time_range["to"],
            uid,
            {
                "refId": "A",
                "expr": query,
                "editorMode": "builder",
                "queryType": "range",
            },
        ]
        left_param = quote(json.dumps(left, separators=(",", ":")), safe="")
        return f"{self.settings.grafana_base_url}/explore?orgId=1&left={left_param}"


def _load_k8s_apis() -> tuple[client.BatchV1Api, client.CoreV1Api]:
    try:
        config.load_incluster_config()
        api_client = client.ApiClient()
        token = Path("/var/run/secrets/kubernetes.io/serviceaccount/token").read_text(
            encoding="utf-8"
        )
        api_client.default_headers["Authorization"] = f"Bearer {token.strip()}"
    except config.ConfigException:
        config.load_kube_config()
        api_client = client.ApiClient()
    return client.BatchV1Api(api_client=api_client), client.CoreV1Api(
        api_client=api_client
    )


def _label(resource: Any, key: str) -> str:
    return (resource.metadata.labels or {}).get(key, "")


def _annotation(resource: Any, key: str) -> str:
    return (resource.metadata.annotations or {}).get(key, "")


def _job_status(job: V1Job) -> str:
    if job.status is None:
        return "Pending"
    if getattr(job.status, "active", None):
        return "Running"
    if getattr(job.status, "succeeded", None):
        return "Succeeded"
    if getattr(job.status, "failed", None):
        return "Failed"
    return "Pending"


def _completed_at(job: V1Job) -> str | None:
    completed = _completion_time(job)
    return _isoformat(completed) if completed else None


def _completion_time(job: V1Job) -> datetime | None:
    if job.status is None:
        return None
    for condition in job.status.conditions or []:
        if condition.type in {"Complete", "Failed"} and condition.last_transition_time:
            return condition.last_transition_time
    return None


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _grafana_time(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _isoformat(value: Any) -> str | None:
    return value.isoformat() if value else None
