ARG TRITON_BASE=nvcr.io/nvidia/tritonserver:25.04-py3
ARG OLLAMA_MODEL_DEFAULT=llama3.2

FROM ollama/ollama:latest AS ollama-source

FROM ${TRITON_BASE}
ARG OLLAMA_MODEL_DEFAULT=llama3.2

LABEL maintainer="Satellite Telemetry Anomaly Detection Team"
LABEL version="2.0"
LABEL description="STAD-AI V2.0 monolithic runtime with Triton inference and optional local/cloud LLM support"

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

RUN mkdir -p /etc/nginx/conf.d /usr/share/nginx/html /var/cache/nginx /var/log/nginx /run /usr/share/ollama /app/config /models

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
        '    access_log /var/log/nginx/access.log;' \
        '    error_log /var/log/nginx/error.log warn;' \
        '    include /etc/nginx/conf.d/*.conf;' \
        '}' \
        > /etc/nginx/nginx.conf

COPY --from=ollama-source /usr/bin/ollama /usr/bin/ollama
COPY --from=ollama-source /usr/lib/ollama/include /usr/lib/ollama/include
COPY --from=ollama-source /usr/lib/ollama/libggml-base.so /usr/lib/ollama/libggml-base.so
COPY --from=ollama-source /usr/lib/ollama/libggml-base.so.0 /usr/lib/ollama/libggml-base.so.0
COPY --from=ollama-source /usr/lib/ollama/libggml-base.so.0.0.0 /usr/lib/ollama/libggml-base.so.0.0.0
COPY --from=ollama-source /usr/lib/ollama/libggml-cpu-x64.so /usr/lib/ollama/libggml-cpu-x64.so
COPY --from=ollama-source /usr/lib/ollama/libggml-cpu-sse42.so /usr/lib/ollama/libggml-cpu-sse42.so
COPY --from=ollama-source /usr/lib/ollama/libggml-cpu-sandybridge.so /usr/lib/ollama/libggml-cpu-sandybridge.so
COPY --from=ollama-source /usr/lib/ollama/libggml-cpu-alderlake.so /usr/lib/ollama/libggml-cpu-alderlake.so
COPY --from=ollama-source /usr/lib/ollama/libggml-cpu-haswell.so /usr/lib/ollama/libggml-cpu-haswell.so
COPY --from=ollama-source /usr/lib/ollama/libggml-cpu-icelake.so /usr/lib/ollama/libggml-cpu-icelake.so
COPY --from=ollama-source /usr/lib/ollama/libggml-cpu-skylakex.so /usr/lib/ollama/libggml-cpu-skylakex.so
COPY --from=ollama-source /usr/lib/ollama/vulkan /usr/lib/ollama/vulkan
COPY --from=ollama-source /usr/lib/ollama/cuda_v13 /usr/lib/ollama/cuda_v13
COPY --from=ollama-source /usr/lib/ollama/mlx_cuda_v13 /usr/lib/ollama/mlx_cuda_v13
COPY --from=ollama-source /usr/lib/ollama/cuda_v12 /usr/lib/ollama/cuda_v12

COPY docker/monolith-runtime-requirements.txt /tmp/monolith-runtime-requirements.txt
RUN python3 -m pip install --no-cache-dir --disable-pip-version-check --timeout 240 --retries 20 -r /tmp/monolith-runtime-requirements.txt && \
    rm -f /tmp/monolith-runtime-requirements.txt

COPY triton/model_repository /models
COPY Frontend/dist /usr/share/nginx/html
COPY Frontend/nginx.monolith.conf /etc/nginx/conf.d/default.conf
COPY Backend/ ./Backend/
COPY Middleware/ ./Middleware/
COPY scripts/start.py /app/start.py

EXPOSE 80 8000 8001 11434 8008

VOLUME ["/root/.ollama"]

HEALTHCHECK --interval=30s --timeout=10s --start-period=420s --retries=5 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1/api/health', timeout=3)" || exit 1

CMD ["python3", "/app/start.py"]
