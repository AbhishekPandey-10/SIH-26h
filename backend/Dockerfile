# ==============================================================================
# MediKiosk Backend Dockerfile
# Python 3.12 + FastAPI + LangGraph + uv
# ==============================================================================

FROM python:3.12-slim as builder

# Install uv binary
COPY --from=ghcr.io/astral-sh/uv:0.8.19 /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies using uv
COPY pyproject.toml README.md ./
RUN uv pip install --system -e .

# Copy application source code and data
COPY app/ ./app/
COPY data/ ./data/
COPY migrations/ ./migrations/
COPY alembic.ini .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
