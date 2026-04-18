# Build stage for Middleware
FROM python:3.11-slim

# Metadata labels for Docker Hub
LABEL maintainer="Satellite Telemetry Anomaly Detection Team"
LABEL version="1.0"
LABEL description="AI Orchestration Middleware for Satellite Telemetry Anomaly Detection"

WORKDIR /app

# Ensure logs are sent straight to terminal
ENV PYTHONUNBUFFERED=1

# Copy requirements from root context
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only Middleware files from root context
COPY Middleware/ .

EXPOSE 8000

# Start the Middleware API
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]