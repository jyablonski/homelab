FROM python:3.14-slim AS base

ENV DEBIAN_FRONTEND=noninteractive \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src" \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

FROM base AS deps

ARG INSTALL_DEV_DEPENDENCIES=false

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.11.7-python3.14-trixie /usr/local/bin/uv /bin/uv
COPY pyproject.toml uv.lock ./

RUN if [ "$INSTALL_DEV_DEPENDENCIES" = "true" ]; then \
        uv sync --locked --no-install-project; \
    else \
        uv sync --locked --no-dev --no-install-project; \
    fi

FROM base AS runtime

WORKDIR /app

RUN useradd --create-home appuser

COPY --from=deps /app/.venv /app/.venv
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser entrypoint.sh ./

RUN chmod +x /app/entrypoint.sh

USER appuser

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--no-access-log"]
