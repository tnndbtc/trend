# Multi-stage build for Django web interface
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

# Copy and install web interface dependencies
COPY services/web-interface/requirements.txt /build/
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

# Copy web interface code
COPY services/web-interface /app/web_interface

# Set working directory to web interface
WORKDIR /app/web_interface

# Set Python path to include packages
ENV PYTHONPATH=/app:/app/packages/trend-agent-core:$PYTHONPATH

# Create non-root user for security
RUN useradd -m -u 1000 webuser && \
    chown -R webuser:webuser /app

# Collect static files (run as root before switching user)
RUN python manage.py collectstatic --noinput --clear || true

# Switch to non-root user
USER webuser

# Expose web interface port
EXPOSE 11800

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:11800/').read()"

# Run gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:11800", "--workers", "4", "--timeout", "120", "web_interface.wsgi:application"]
