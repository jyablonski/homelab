from __future__ import annotations
from pathlib import Path

import pytest

from dagster_project.dbt_config import _resolve_project_dir

pytestmark = pytest.mark.unit


def test_resolve_project_dir_uses_env_override(monkeypatch, tmp_path: Path):
    (tmp_path / "dbt_project.yml").write_text("name: homelab\n", encoding="utf-8")
    monkeypatch.setenv("DAGSTER_DBT_PROJECT_DIR", str(tmp_path))
    assert _resolve_project_dir() == tmp_path


def test_resolve_project_dir_returns_none_when_no_project_file(
    monkeypatch, tmp_path: Path
):
    monkeypatch.setenv("DAGSTER_DBT_PROJECT_DIR", str(tmp_path))
    assert _resolve_project_dir() is None
