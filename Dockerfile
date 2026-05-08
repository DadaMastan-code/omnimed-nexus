FROM python:3.13-slim AS base

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN pip install uv

COPY pyproject.toml .
RUN uv pip install --system -e .

COPY . .

# ── github-app target ────────────────────────────────────────────────────────
FROM base AS github-app
EXPOSE 8000
CMD ["uvicorn", "github_app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
