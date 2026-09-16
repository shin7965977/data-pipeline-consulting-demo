# Multi-stage production Dockerfile for Platzi Data Pipeline
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final runtime image
FROM python:3.11-slim

WORKDIR /app

# Copy installed wheels and binaries from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Copy application source
COPY requirements.txt .
COPY pipeline_runner.py .
COPY ingestion/ ingestion/
COPY transform_dbt/ transform_dbt/
COPY docker/entrypoint.sh docker/entrypoint.sh

# Ensure entrypoint is executable
RUN chmod +x docker/entrypoint.sh

# Pre-bake dbt dependencies so container boots without network overhead
RUN dbt deps --project-dir transform_dbt --profiles-dir transform_dbt

ENTRYPOINT ["docker/entrypoint.sh"]
CMD ["--target=all"]
