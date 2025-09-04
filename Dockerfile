# -------- Stage 1: Builder --------
FROM python:3.12-slim AS builder
WORKDIR /app

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
  && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Copy project dependency files and install Python packages
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev

# # -------- Stage 2: Testing --------
# FROM builder AS test
#
# # Run automated tests using uv environment
# RUN uv run pytest --maxfail=1 --disable-warnings

# -------- Stage 3: Runtime --------
FROM python:3.12-slim AS final

# Install only runtime dependencies (no compilers/tools needed here)
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    libpq5 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create non-root runtime user
RUN useradd --create-home --shell /bin/bash appuser
USER appuser
WORKDIR /app

# Set Python and Django environment defaults
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=etc.settings

# Copy virtual environment and source code with correct ownership
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --chown=appuser:appuser . .

# Ensure app uses the installed virtual environment and project path
ENV PYTHONPATH="/app/.venv/lib/python3.12/site-packages:/app" \
    PATH="/app/.venv/bin:$PATH"
