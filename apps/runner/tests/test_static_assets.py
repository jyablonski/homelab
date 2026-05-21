from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from config import Settings
from main import create_app

RUNNER_ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = RUNNER_ROOT / "src" / "static"
TEMPLATES_DIR = RUNNER_ROOT / "src" / "templates"


@pytest.fixture()
def prefixed_client():
    app = create_app(Settings(url_prefix="/runner"))
    return TestClient(app)


def test_stylesheet_file_contains_design_tokens():
    css = (STATIC_DIR / "styles.css").read_text(encoding="utf-8")

    assert ":root" in css
    assert "--accent:" in css
    assert "oklch" in css
    assert ".jobs-table" in css
    assert ".job-detail" in css
    assert ".status-pill" in css
    assert "data-accent" not in css


def test_app_js_file_contains_runner_behaviors():
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")

    assert "apiJobsUrl" in js
    assert "showDetailView" in js
    assert "loadDetailRuns" in js
    assert "triggerRun" in js
    assert "sparklineHtml" in js
    assert "localStorage" not in js


def test_templates_wire_static_assets_and_views():
    layout = (TEMPLATES_DIR / "layout.html").read_text(encoding="utf-8")
    runnables = (TEMPLATES_DIR / "runnables.html").read_text(encoding="utf-8")

    assert "{{ url_prefix }}/static/styles.css" in layout
    assert "{{ url_prefix }}/static/app.js" in layout
    assert "job-detail-view" in runnables
    assert "jobs-list-view" in runnables
    assert "tweaks-panel" not in runnables
    assert "tweaks-toggle" not in runnables


def test_static_assets_served_at_app_paths(prefixed_client):
    # The app mounts /static; Traefik adds /runner in production for browsers.
    for path in ("/static/styles.css", "/static/app.js"):
        response = prefixed_client.get(path)
        assert response.status_code == 200
        assert len(response.text) > 100


def test_home_page_links_prefixed_static_assets(prefixed_client):
    response = prefixed_client.get("/")

    assert response.status_code == 200
    assert 'href="/runner/static/styles.css"' in response.text
    assert 'src="/runner/static/app.js"' in response.text
    assert 'data-api-jobs-url="/runner/api/jobs"' in response.text
