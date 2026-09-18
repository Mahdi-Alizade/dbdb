# -------------------------------------------------------------------
# Stage 1: Build & Dependencies
# -------------------------------------------------------------------
FROM python:3.13-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

# -------------------------------------------------------------------
# Stage 2: Minimal & Secure Production Runtime
# -------------------------------------------------------------------
FROM python:3.13-slim AS runner

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="/app"

WORKDIR /app

# Copy only installed dependencies from the builder stage
COPY --from=builder /install /usr/local

# Create non-root user and persistent volume directory for data storage
RUN groupadd -r appgroup && useradd -r -g appgroup -u 10001 appuser \
    && mkdir -p /data \
    && chown -R appuser:appgroup /data /app

# Copy application source code
COPY --chown=appuser:appgroup dbdb /app/dbdb

USER appuser

# Persistence directory for database files
VOLUME ["/data"]

EXPOSE 8888

# Default command listens on 0.0.0.0 and stores data in /data/dbdb.db
ENTRYPOINT ["python", "-m", "dbdb.server"]
CMD ["/data/dbdb.db", "0.0.0.0", "8888"]