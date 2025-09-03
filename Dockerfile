
# Use a single-stage build approach to avoid virtual environment issues
FROM python:3.12-slim AS final

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    postgresql-client \
    libpq-dev \
    libpq5 \
    curl \
  && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=etc.settings

WORKDIR /app

COPY pyproject.toml uv.lock* ./

RUN uv sync --frozen --no-dev

COPY . .

ENV PYTHONPATH="/app/.venv/lib/python3.12/site-packages:/app:$PYTHONPATH" \
    PATH="/app/.venv/bin:$PATH"

