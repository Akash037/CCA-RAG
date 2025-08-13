# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash raguser \
    && chown -R raguser:raguser /app

# Expose port (Cloud Run requires port 8080)
EXPOSE 8080

# Health check - optimized for Cloud Run with longer startup time
# Use PORT environment variable for health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD sh -c 'curl -f http://localhost:${PORT:-8080}/health || exit 1'

# Switch to non-root user
USER raguser

# Run with Gunicorn as recommended by Google Cloud Run
# Use PORT environment variable provided by Cloud Run
CMD ["sh", "-c", "gunicorn --bind :${PORT:-8080} --workers 1 --threads 8 --timeout 0 app.main:app"]
