# trunk-ignore-all(checkov/CKV_DOCKER_3): container requires root for Nginx port 80 and Triton
ARG TRITON_BASE=nvcr.io/nvidia/tritonserver:25.04-py3
ARG OLLAMA_MODEL_DEFAULT=llama3.2

FROM ollama/ollama:0.5.7 AS ollama-source

FROM node:22-slim AS frontend-build
WORKDIR /build
COPY Frontend/package.json Frontend/package-lock.json ./
RUN npm ci
COPY Frontend/ ./
RUN npm run build

# trunk-ignore(checkov/CKV_DOCKER_7)
FROM ${TRITON_BASE}
ARG OLLAMA_MODEL_DEFAULT=llama3.2

LABEL maintainer="Satellite Telemetry Anomaly Detection Team"
LABEL version="3.0"
LABEL description="STAD-AI V3.0 monolithic runtime — Triton inference, LLM orchestration, full observability"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility \
    LITELLM_LOG=ERROR \
    ENABLE_TRAINING=false \
    BACKEND_URL=http://127.0.0.1:8001 \
    OLLAMA_API_BASE=http://127.0.0.1:11434 \
    OLLAMA_MODEL=${OLLAMA_MODEL_DEFAULT} \
    OLLAMA_PREFETCH_MODEL=true \
    OLLAMA_PULL_RETRIES=5 \
    OLLAMA_PULL_RETRY_DELAY=10 \
    OLLAMA_MODELS=/root/.ollama/models \
    OLLAMA_HOST=0.0.0.0 \
    TRITON_URL=http://127.0.0.1:8008 \
    TRITON_MODEL_NAME=tranad \
    TRITON_METRICS_URL=http://127.0.0.1:8010/metrics \
    TRITON_EXPORT_MANIFEST=/models/tranad/export_manifest.json \
    SERVER_HOST=0.0.0.0 \
    SERVER_PORT=8001

WORKDIR /app

# Nginx setup — single layer
RUN mkdir -p /etc/nginx/conf.d /usr/share/nginx/html /var/cache/nginx /var/log/nginx /run /app/config /models
COPY docker/nginx-runtime/nginx /usr/sbin/nginx
COPY docker/nginx-runtime/mime.types /etc/nginx/mime.types
COPY docker/nginx-runtime/libcrypt.so.1 /lib/x86_64-linux-gnu/libcrypt.so.1
COPY docker/nginx-runtime/libpcre2-8.so.0 /lib/x86_64-linux-gnu/libpcre2-8.so.0
COPY docker/nginx-runtime/libssl.so.3 /lib/x86_64-linux-gnu/libssl.so.3
COPY docker/nginx-runtime/libcrypto.so.3 /lib/x86_64-linux-gnu/libcrypto.so.3
COPY docker/nginx-runtime/libz.so.1 /lib/x86_64-linux-gnu/libz.so.1
RUN chmod +x /usr/sbin/nginx && \
    printf '%s\n' \
        'user www-data;' \
        'events {}' \
        'http {' \
        '    include /etc/nginx/mime.types;' \
        '    default_type application/octet-stream;' \
        '    sendfile on;' \
        '    gzip on;' \
        '    gzip_min_length 1024;' \
        '    access_log /var/log/nginx/access.log;' \
        '    error_log /var/log/nginx/error.log warn;' \
        '    include /etc/nginx/conf.d/*.conf;' \
        '}' \
        > /etc/nginx/nginx.conf

# Ollama — CUDA 12 and CPU runners (skip CUDA 11 and other unused drivers for ~2.3GB savings)
COPY --from=ollama-source /usr/bin/ollama /usr/bin/ollama
COPY --from=ollama-source /usr/lib/ollama/runners/cpu_avx /usr/lib/ollama/runners/cpu_avx
COPY --from=ollama-source /usr/lib/ollama/runners/cpu_avx2 /usr/lib/ollama/runners/cpu_avx2
COPY --from=ollama-source /usr/lib/ollama/runners/cuda_v12_avx /usr/lib/ollama/runners/cuda_v12_avx
COPY --from=ollama-source /usr/lib/ollama/libcublas.so.12* /usr/lib/ollama/
COPY --from=ollama-source /usr/lib/ollama/libcublasLt.so.12* /usr/lib/ollama/
COPY --from=ollama-source /usr/lib/ollama/libcudart.so.12* /usr/lib/ollama/

# Python deps — single layer with cleanup
COPY docker/monolith-runtime-requirements.txt /tmp/requirements.txt
RUN python3 -m pip install --no-cache-dir --disable-pip-version-check --timeout 240 --retries 20 \
        -r /tmp/requirements.txt && \
    rm -f /tmp/requirements.txt && \
    find /usr/local/lib/python3.*/dist-packages -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; \
    find /usr/local/lib/python3.*/dist-packages -name '*.pyc' -delete 2>/dev/null; \
    rm -rf /root/.cache /tmp/* /var/tmp/*; true

# Application code
COPY triton/model_repository /models
COPY --from=frontend-build /build/dist /usr/share/nginx/html
COPY Frontend/nginx.monolith.conf /etc/nginx/conf.d/default.conf
COPY Backend/ ./Backend/
COPY Middleware/ ./Middleware/
COPY scripts/start.py /app/start.py

# Cleanup .pyc from app code
RUN find /app -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true

EXPOSE 80 8000 8001 11434 8008

VOLUME ["/root/.ollama"]

HEALTHCHECK --interval=30s --timeout=10s --start-period=420s --retries=5 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1/api/health', timeout=3)" || exit 1

CMD ["python3", "/app/start.py"]
