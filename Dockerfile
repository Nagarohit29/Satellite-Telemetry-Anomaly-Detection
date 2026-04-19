# --- Stage 1: Build Frontend ---
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY Frontend/package*.json ./
RUN npm install
COPY Frontend/ .
RUN npm run build

# --- Stage 2: Final Monolithic Image ---
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

# Set non-interactive mode for apt
ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-dev \
    python3-pip \
    nginx \
    curl \
    ca-certificates \
    zstd \
    && rm -rf /var/lib/apt/lists/*

# Enable GPU support for Ollama and PyTorch
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Install Ollama using the official script
RUN curl -fsSL https://ollama.com/install.sh | sh

# Set Python 3.11 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 && \
    update-alternatives --set python3 /usr/bin/python3.11

# --- Split Requirements to prevent push failure ---
# First, install heavy dependencies (Torch)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch==2.5.1+cu121 torchvision==0.20.1+cu121 --index-url https://download.pytorch.org/whl/cu121

# Second, install the rest of the requirements
COPY requirements.txt .
RUN grep -vE "torch|--extra-index-url" requirements.txt > req_light.txt && \
    pip install --no-cache-dir -r req_light.txt

# Copy Frontend build from stage 1
COPY --from=frontend-builder /app/frontend/dist /usr/share/nginx/html

# Copy Nginx config
COPY Frontend/nginx.conf /etc/nginx/sites-available/default
RUN ln -sf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default

# Copy Backend and Middleware code
COPY Backend/ ./Backend/
COPY Middleware/ ./Middleware/

# Set default environment variables for internal service connectivity
ENV BACKEND_URL=http://127.0.0.1:8001
ENV OLLAMA_API_BASE=http://127.0.0.1:11434
ENV OLLAMA_MODEL=llama3
ENV OLLAMA_HOST=0.0.0.0
ENV SERVER_HOST=0.0.0.0
ENV SERVER_PORT=8001

# Create data directories
RUN mkdir -p Backend/data Backend/models Backend/results Backend/checkpoints

# Startup script
RUN echo '#!/bin/bash\n\
echo "☁️ Starting Ollama service..."\n\
ollama serve &\n\
\n\
echo "⏳ Waiting for Ollama to be ready..."\n\
until curl -s http://127.0.0.1:11434/api/tags > /dev/null; do\n\
  sleep 2\n\
done\n\
echo "✅ Ollama is up!"\n\
\n\
# Pre-pull llama3 if no models exist (ensures zero-config works)\n\
if [ -z "$(ollama list | grep llama3)" ]; then\n\
  echo "📥 Pulling default model (llama3)..."\n\
  ollama pull llama3\n\
fi\n\
\n\
echo "🚀 Starting Nginx..."\n\
nginx\n\
\n\
echo "🚀 Starting ML Backend..."\n\
cd /app/Backend && python3 serve.py &\n\
\n\
echo "🚀 Starting API Middleware..."\n\
cd /app/Middleware && python3 main.py' > /app/start.sh && chmod +x /app/start.sh

EXPOSE 80 8000 8001 11434

CMD ["/app/start.sh"]
