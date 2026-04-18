# --- STAGE 1: Frontend Build ---
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY Frontend/package*.json ./
RUN npm install
COPY Frontend/ .
RUN npm run build

# --- STAGE 2: Final Monolith Image ---
FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04

LABEL maintainer="Satellite Telemetry Anomaly Detection Team"
LABEL description="Full-stack Monolithic Image for Satellite Telemetry Anomaly Detection"

WORKDIR /app

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install system dependencies (Python 3.11, Nginx, Curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-dev \
    python3.11-distutils \
    nginx \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install pip and set Python 3.11 as default
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy Frontend build from stage 1
COPY --from=frontend-builder /app/frontend/dist /usr/share/nginx/html
RUN rm /etc/nginx/sites-enabled/default
COPY Frontend/nginx.conf /etc/nginx/sites-available/default
RUN ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default

# Copy Backend and Middleware code
COPY Backend/ ./Backend/
COPY Middleware/ ./Middleware/

# Create data directories for Backend
RUN mkdir -p Backend/data Backend/models Backend/results Backend/checkpoints

# Create a startup script
RUN echo '#!/bin/bash\n\
echo "🚀 Starting Nginx (Frontend)..."\n\
nginx -g "daemon off;" &\n\
\n\
echo "🚀 Starting Backend (AI Engine)..."\n\
export SERVER_HOST=0.0.0.0\n\
export SERVER_PORT=8001\n\
cd /app/Backend && python serve.py &\n\
\n\
echo "🚀 Starting Middleware (Orchestrator)..."\n\
export BACKEND_URL=http://localhost:8001\n\
cd /app/Middleware && uvicorn main:app --host 0.0.0.0 --port 8000\n\
' > /app/start.sh && chmod +x /app/start.sh

# Expose ports (80 for Frontend/Nginx, 8000 for Middleware, 8001 for Backend)
EXPOSE 80 8000 8001

CMD ["/app/start.sh"]
