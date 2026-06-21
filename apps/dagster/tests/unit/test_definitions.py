import pytest
from dagster import AssetsDefinition, JobDefinition

from dagster_project.definitions import build_definitions, defs
from dagster_project.jobs.utils import REQUIRED_JOB_TAGS, UnresolvedAssetJobDefinition

pytestmark = pytest.mark.unit


def _job_names(definitions) -> set[str]:
    return {job.name for job in (definitions.jobs or [])}


def test_definitions_import_cleanly():
    """The module-level Definitions must build without error."""
    assert defs is not None
    assert _job_names(defs)


def test_real_job_and_schedule_registered():
    definitions = build_definitions(with_examples=False)
    assert "reminders_pipeline" in _job_names(definitions)
    assert "daily_events" in _job_names(definitions)
    assert {"nba_job", "cs_job", "ufc_job"}.isdisjoint(_job_names(definitions))
    assert any(
        s.name == "reminders_pipeline_schedule" for s in (definitions.schedules or [])
    )
    assert any(s.name == "daily_events_schedule" for s in (definitions.schedules or []))


def test_failure_sensor_registered():
    definitions = build_definitions(with_examples=False)
    assert any(
        s.name == "slack_run_failure_sensor" for s in (definitions.sensors or [])
    )


def test_examples_excluded_by_default_and_opt_in():
    without = build_definitions(with_examples=False)
    assert "example_job" not in _job_names(without)

    with_examples = build_definitions(with_examples=True)
    assert "example_job" in _job_names(with_examples)
    assert "reminders_pipeline" in _job_names(with_examples)


def test_include_examples_env_var(monkeypatch):
    monkeypatch.setenv("DAGSTER_INCLUDE_EXAMPLES", "true")
    assert "example_job" in _job_names(build_definitions())

    monkeypatch.setenv("DAGSTER_INCLUDE_EXAMPLES", "false")
    assert "example_job" not in _job_names(build_definitions())


def test_every_job_has_required_tags():
    definitions = build_definitions(with_examples=True)
    for job in definitions.jobs or []:
        assert isinstance(job, (JobDefinition, UnresolvedAssetJobDefinition))
        for tag in REQUIRED_JOB_TAGS:
            assert tag in (job.tags or {}), f"{job.name} missing tag {tag}"


def test_every_asset_has_description():
    definitions = build_definitions(with_examples=True)
    missing = [
        spec.key.to_user_string()
        for assets_def in definitions.assets or []
        if isinstance(assets_def, AssetsDefinition)
        for spec in assets_def.specs
        if not spec.description
    ]
    assert missing == []
