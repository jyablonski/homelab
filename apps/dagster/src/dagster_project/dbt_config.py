from __future__ import annotations
from os import getenv
from pathlib import Path

from dagster_dbt import DbtCliResource, DbtProject


def _resolve_project_dir() -> Path | None:
    """Find the dbt project for both local and container runtimes."""
    override = getenv("DAGSTER_DBT_PROJECT_DIR")
    candidates = [Path(override)] if override else []
    # Container layout (Dockerfile copies the project to /app/dbt) ...
    candidates.append(Path("/app/dbt"))
    # ... and the local checkout layout (apps/dagster/dbt).
    candidates.append(Path(__file__).resolve().parents[2] / "dbt")

    for candidate in candidates:
        if candidate.is_dir() and (candidate / "dbt_project.yml").is_file():
            return candidate
    return None


DBT_PROJECT_DIR = _resolve_project_dir()

dbt_project: DbtProject | None = None
dbt_resource: DbtCliResource | None = None

if DBT_PROJECT_DIR is not None:
    dbt_project = DbtProject(project_dir=DBT_PROJECT_DIR)
    dbt_project.prepare_if_dev()
    dbt_resource = DbtCliResource(project_dir=dbt_project)
