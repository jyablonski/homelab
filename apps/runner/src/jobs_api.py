from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from cron import describe_schedule
from models import JobRun, Runnable

HISTORY_LIMIT = 8


def runnable_to_job(runnable: Runnable, *, runs: list[JobRun]) -> dict[str, Any]:
    manual = runnable.suspended
    schedule_cron = runnable.schedule if not manual else "manual"
    history = [_history_state(run.status) for run in reversed(runs[:HISTORY_LIMIT])]
    last = runs[0] if runs else None

    return {
        "app": runnable.app,
        "name": runnable.job,
        "namespace": runnable.namespace,
        "cronjobName": runnable.cronjob_name,
        "description": runnable.description,
        "schedule": {
            "cron": schedule_cron,
            "human": describe_schedule(runnable.schedule, manual=manual),
            "manual": manual,
        },
        "status": _row_status(runnable, last),
        "lastRun": _last_run_payload(last),
        "history": history,
        "activeRunId": runnable.active_run,
    }


def run_to_response(run: JobRun) -> dict[str, Any]:
    return {
        "runId": run.name,
        "namespace": run.namespace,
        "grafanaUrl": run.logs_url,
    }


def run_to_history_item(run: JobRun) -> dict[str, Any]:
    timestamp = run.completed_at or run.started_at
    return {
        "id": run.name,
        "status": _history_state(run.status),
        "k8sStatus": run.status,
        "startedAt": run.started_at,
        "completedAt": run.completed_at,
        "relative": _relative_time(timestamp),
        "grafanaUrl": run.logs_url,
    }


def _row_status(runnable: Runnable, last: JobRun | None) -> str:
    if runnable.active_run:
        return "running"
    if last is None:
        return "idle"
    if last.status == "Succeeded":
        return "success"
    if last.status == "Failed":
        return "failed"
    if last.status == "Running":
        return "running"
    return "idle"


def _history_state(status: str) -> str:
    if status == "Succeeded":
        return "success"
    if status == "Failed":
        return "failed"
    if status == "Running":
        return "running"
    return "pending"


def _last_run_payload(last: JobRun | None) -> dict[str, Any] | None:
    if last is None:
        return None
    timestamp = last.completed_at or last.started_at
    return {
        "id": last.name,
        "at": timestamp,
        "relative": _relative_time(timestamp),
        "grafanaUrl": last.logs_url,
    }


def _relative_time(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    delta = datetime.now(UTC) - parsed.astimezone(UTC)
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}m ago"
    if seconds < 86400:
        hours = seconds // 3600
        return f"{hours}h ago"
    days = seconds // 86400
    return f"{days}d ago"
