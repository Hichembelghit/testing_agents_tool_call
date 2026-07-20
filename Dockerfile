# ── Streamlit frontend ─────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# System deps for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install Python deps (cached separately for speed)
COPY pyproject.toml ./
RUN uv sync --no-dev

# ── Runtime image ─────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /app /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY . .

# DigitalOcean App Platform sets PORT; Streamlit listens on it
EXPOSE 8080

CMD uv run streamlit run streamlit_app.py \
    --server.headless=true \
    --server.port=${PORT:-8080} \
    --server.enableCORS=false
