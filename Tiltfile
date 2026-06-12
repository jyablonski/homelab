# Tilt dev loop for app-owned workloads. Targets `apps/*` releases only.
#
# The dev loop, by file type:
#   - App source (apps/<app>/src, api jobs/): live-synced into the running pod;
#     uvicorn --reload (api/runner via values-dev.yaml), Django runserver
#     autoreload, and a Go process restart pick the changes up in-place.
#   - Dependency/build inputs (pyproject.toml, uv.lock, go.mod, go.sum,
#     Dockerfile, entrypoint.sh): full image rebuild + redeploy. These are the
#     build-context files not covered by a sync() step, so Tilt rebuilds
#     automatically; ignore= keeps tests/values/secrets/.venv out of that set.
#   - Helm inputs (helmfile.yaml, charts/workload/**, values*.yaml,
#     secrets.sops.yaml): watched below, re-render via helmfile and redeploy.
#   - Django migrations stay manual: the entrypoint only migrates an
#     uninitialized DB; run `make migrate` to apply new migrations.

load("ext://restart_process", "docker_build_with_restart")

allow_k8s_contexts("default")

APP_NAMES = ["django", "api", "runner", "workload-chart-example"]

def app_image_ref(name):
    return "registry.home:5000/homelab/%s" % name

# --- Helm rendering ---------------------------------------------------------
# `local()` does not track which files helmfile reads, so watch them
# explicitly; any change re-runs the Tiltfile, which re-renders the releases.
watch_file("helmfile.yaml")
for f in listdir("charts/workload", recursive=True):
    watch_file(f)
for name in APP_NAMES:
    for dep in ["values.yaml", "values-dev.yaml.gotmpl", "secrets.sops.yaml"]:
        path = "apps/%s/%s" % (name, dep)
        if os.path.exists(path):
            watch_file(path)
watch_file("apps/runner/rbac.yaml")

# One render for all app releases. `-e dev` activates the per-app
# values-dev.yaml.gotmpl overlays (uvicorn --reload, single replica Go app).
k8s_yaml(local("helmfile -e dev -l bootstrap=app template", quiet=True))

# make up/sync apply this via a helmfile presync hook, but hooks don't run
# under `helmfile template`, so apply it directly here.
k8s_yaml("apps/runner/rbac.yaml")


# --- Python apps -------------------------------------------------------------
# Files in apps/<app>/ that are not image build inputs (Dockerfiles COPY
# explicitly, so there is no .dockerignore); keep them out of Tilt's context
# watch so editing them never triggers an image rebuild.
PYTHON_NON_IMAGE_FILES = [
    "tests",
    ".venv",
    "htmlcov",
    ".pytest_cache",
    ".coverage",
    "**/__pycache__",
    "*.pyc",
    "values.yaml",
    "values-dev.yaml.gotmpl",
    "secrets.sops.yaml",
    "README.md",
]

def python_app(name, sync_dirs, links=[], objects=[], extra_ignores=[]):
    app_dir = "apps/%s" % name
    docker_build(
        app_image_ref(name),
        app_dir,
        dockerfile="%s/Dockerfile" % app_dir,
        live_update=[sync("%s/%s" % (app_dir, d), "/app/%s" % d) for d in sync_dirs],
        ignore=PYTHON_NON_IMAGE_FILES + extra_ignores,
    )
    k8s_resource(name, links=links, objects=objects)


python_app(
    "django",
    sync_dirs=["src"],
    extra_ignores=["src/staticfiles"],
    links=[
        link("http://apps.home/django/admin", "Django admin"),
        link("http://apps.home/django/healthz", "Health"),
    ],
)

python_app(
    "api",
    sync_dirs=["src", "jobs"],
    links=[
        link("http://apps.home/api/docs", "API docs"),
        link("http://apps.home/api/healthz", "Health"),
        link("http://apps.home/api/metrics", "Metrics"),
    ],
)

python_app(
    "runner",
    sync_dirs=["src"],
    links=[
        link("http://apps.home/runner", "Runner"),
        link("http://apps.home/runner/healthz", "Health"),
    ],
    objects=["runner:role", "runner:rolebinding"],
    extra_ignores=["rbac.yaml"],
)


# --- Go app ------------------------------------------------------------------
# The runtime image only contains a compiled binary, so syncing source files
# would do nothing. Instead: cross-compile locally on source/module changes,
# sync the binary, and restart the process in-place (restart_process wrapper).
local_resource(
    "workload-chart-example-compile",
    "cd apps/workload-chart-example && CGO_ENABLED=0 GOOS=linux GOARCH=amd64" +
    " go build -o build/workload-chart-example ./src/main.go",
    deps=[
        "apps/workload-chart-example/src",
        "apps/workload-chart-example/go.mod",
        "apps/workload-chart-example/go.sum",
    ],
)

docker_build_with_restart(
    app_image_ref("workload-chart-example"),
    "apps/workload-chart-example",
    dockerfile="apps/workload-chart-example/Dockerfile.tilt",
    entrypoint=["/app/workload-chart-example"],
    only=["build"],
    live_update=[
        sync(
            "apps/workload-chart-example/build/workload-chart-example",
            "/app/workload-chart-example",
        ),
    ],
)

k8s_resource(
    "workload-chart-example",
    resource_deps=["workload-chart-example-compile"],
    links=[
        link("http://apps.home/workload-chart/api/health/ready", "Health"),
        link("http://apps.home/workload-chart/api/metrics", "Metrics"),
    ],
)
