# Build stage for Middleware
FROM python:3.11-slim

# Metadata labels for Docker Hub
LABEL maintainer="Satellite Telemetry Anomaly Detection Team"
LABEL version="1.3"
LABEL description="AI Orchestration Middleware for Satellite Telemetry Anomaly Detection"

WORKDIR /app

# Performance and logging optimizations
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN useradd -m appuser && \
    touch .env && \
    chown -R appuser:appuser /app

# Copy requirements from root context
COPY --chown=appuser:appuser requirements.txt .

# Switch to appuser
USER appuser

# Install python dependencies (filtering out heavy AI libraries to keep image small)
RUN grep -vE "torch|torchvision|--extra-index-url" requirements.txt > requirements-mini.txt && \
    pip install --no-cache-dir --user -r requirements-mini.txt && \
    rm requirements-mini.txt

# Add user bin to PATH
ENV PATH="/home/appuser/.local/bin:${PATH}"

# Copy only Middleware files from root context
COPY --chown=appuser:appuser Middleware/ .

EXPOSE 8000

# Start the Middleware API
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]