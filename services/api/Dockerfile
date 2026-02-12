# Multi-stage build for FastAPI service
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy and install shared core library first
COPY packages/trend-agent-core /build/packages/trend-agent-core
RUN pip install --no-cache-dir -e /build/packages/trend-agent-core

# Copy and install API dependencies
COPY services/api/requirements.txt /build/
RUN pip install --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy shared core library
COPY --from=builder /build/packages/trend-agent-core /app/packages/trend-agent-core

# Copy API service code
COPY services/api /app/api

# Set Python path to include packages
ENV PYTHONPATH=/app:/app/packages/trend-agent-core:$PYTHONPATH

# Create non-root user for security
RUN useradd -m -u 1000 apiuser && chown -R apiuser:apiuser /app
USER apiuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health').read()"

# Expose API port
EXPOSE 8000

# Run uvicorn
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
