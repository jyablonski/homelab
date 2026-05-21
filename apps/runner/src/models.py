from dataclasses import dataclass


@dataclass(frozen=True)
class Runnable:
    namespace: str
    cronjob_name: str
    app: str
    job: str
    description: str
    schedule: str
    suspended: bool
    active_run: str | None = None
    last_run: str | None = None
    last_status: str | None = None
    last_logs_url: str | None = None


@dataclass(frozen=True)
class JobRun:
    namespace: str
    name: str
    app: str
    job: str
    status: str
    started_at: str | None = None
    completed_at: str | None = None
    logs_url: str | None = None
