# Tilt dev loop for app-owned workloads.
# This file intentionally targets `apps/*` releases only.

allow_k8s_contexts("default")

def app_image_ref(name):
    return "registry.home:5000/homelab/%s" % name

def render_app_release(name):
    return local("helmfile -l name=%s template" % name, quiet=True)

def app_release(name, context_dir, live_update_steps=[]):
    docker_build(
        app_image_ref(name),
        context_dir,
        dockerfile="%s/Dockerfile" % context_dir,
        live_update=live_update_steps,
    )
    k8s_yaml(render_app_release(name))
    k8s_resource(name)


# Django: live sync source changes, rebuild when dependency/build files change.
app_release(
    "django",
    "apps/django",
    live_update_steps=[
        fall_back_on("apps/django/pyproject.toml"),
        fall_back_on("apps/django/uv.lock"),
        fall_back_on("apps/django/Dockerfile"),
        fall_back_on("apps/django/entrypoint.sh"),
        sync("apps/django/src", "/app/src"),
        sync("apps/django/tests", "/app/tests"),
    ],
)


# workload-chart-example (Go): live sync source changes, rebuild on module/build changes.
app_release(
    "workload-chart-example",
    "apps/workload-chart-example",
    live_update_steps=[
        fall_back_on("apps/workload-chart-example/go.mod"),
        fall_back_on("apps/workload-chart-example/go.sum"),
        fall_back_on("apps/workload-chart-example/Dockerfile"),
        sync("apps/workload-chart-example/src", "/app/src"),
    ],
)
