FROM python:3.13-slim AS base

ENV DEBIAN_FRONTEND=noninteractive \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src" \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DAGSTER_HOME=/opt/dagster/dagster_home

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    git \
    && rm -rf /var/lib/apt/lists/*

FROM base AS deps

ARG INSTALL_DEV_DEPENDENCIES=false

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.11.7-python3.13-trixie /usr/local/bin/uv /bin/uv
COPY pyproject.toml uv.lock ./

RUN if [ "$INSTALL_DEV_DEPENDENCIES" = "true" ]; then \
        uv sync --locked --no-install-project; \
    else \
        uv sync --locked --no-dev --no-install-project; \
    fi

FROM base AS runtime

WORKDIR /app

# Run rootless: create $DAGSTER_HOME up front owned by appuser so compute log
# and local artifact storage are writable without a gosu/chown entrypoint dance.
RUN useradd --create-home appuser \
    && mkdir -p "$DAGSTER_HOME/compute_logs" "$DAGSTER_HOME/artifacts" \
    && chown -R appuser:appuser /opt/dagster

COPY --from=deps /app/.venv /app/.venv
COPY --chown=appuser:appuser dagster.yaml workspace.yaml $DAGSTER_HOME/
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser entrypoint.sh ./

# Add a dbt project here (COPY --chown=appuser:appuser dbt/ ./dbt/) to activate
# the dbt integration in dbt_config.py.

RUN chmod +x /app/entrypoint.sh

USER appuser

# 4000: gRPC code server, 3000: webserver.
EXPOSE 4000 3000

ENTRYPOINT ["./entrypoint.sh"]
CMD ["dagster", "code-server", "start", "-h", "0.0.0.0", "-p", "4000", "-m", "dagster_project.definitions"]
