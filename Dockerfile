# --- build stage: install locked dependencies into /app/.venv with uv ---
FROM python:3.12-slim AS build

COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never

WORKDIR /app
# Separate layer: dependencies are rebuilt only when pyproject.toml / uv.lock change.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-cache

# --- runtime stage: same base image, no uv, non-root user ---
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

RUN useradd --uid 1000 --no-create-home --shell /usr/sbin/nologin sattrack

WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY app ./app
COPY data/snapshot ./data/snapshot

USER sattrack
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
