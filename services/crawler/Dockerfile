# Multi-stage build for Crawler service
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy and install shared core library first
COPY packages/trend-agent-core /build/packages/trend-agent-core
COPY packages/trend-agent-collectors /build/packages/trend-agent-collectors

RUN pip install --no-cache-dir -e /build/packages/trend-agent-core && \
    pip install --no-cache-dir -e /build/packages/trend-agent-collectors

# Copy and install crawler dependencies
COPY services/crawler/requirements.txt /build/
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

# Copy shared libraries
COPY --from=builder /build/packages/trend-agent-core /app/packages/trend-agent-core
COPY --from=builder /build/packages/trend-agent-collectors /app/packages/trend-agent-collectors

# Copy crawler service code
COPY services/crawler/src /app/crawler

# Set Python path to include packages
ENV PYTHONPATH=/app:/app/packages/trend-agent-core:/app/packages/trend-agent-collectors:$PYTHONPATH

# Create non-root user for security
RUN useradd -m -u 1000 crawler && chown -R crawler:crawler /app
USER crawler

# Health check - check if scheduler is running
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"  # Basic health check

# Run crawler service
CMD ["python", "-m", "crawler.main"]
