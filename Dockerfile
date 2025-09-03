# Builder stage - installs dependencies and creates virtual environment
FROM python:3.12-slim AS builder
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
  && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev

# Final stage - runtime image
FROM python:3.12-slim AS final
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    libpq5 \
  && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=etc.settings

WORKDIR /app
# Copy the virtual environment from builder stage
COPY --from=builder /app/.venv /app/.venv
# Copy application code
COPY . .
ENV PYTHONPATH="/app/.venv/lib/python3.12/site-packages:/app:$PYTHONPATH" \
    PATH="/app/.venv/bin:$PATH"
