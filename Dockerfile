FROM ollama/ollama:latest AS ollama-source

FROM python:3.11-slim-bookworm

LABEL maintainer="Satellite Telemetry Anomaly Detection Team"
LABEL version="1.0"
LABEL description="Satellite Telemetry Anomaly Detection"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility \
    LITELLM_LOG=ERROR \
    INFERENCE_DEVICE=auto \
    ENABLE_TRAINING=false \
    BACKEND_URL=http://127.0.0.1:8001 \
    OLLAMA_API_BASE=http://127.0.0.1:11434 \
    OLLAMA_MODEL=llama3.2 \
    OLLAMA_PREFETCH_MODEL=true \
    OLLAMA_HOST=0.0.0.0 \
    SERVER_HOST=0.0.0.0 \
    SERVER_PORT=8001

WORKDIR /app

RUN mkdir -p /etc/nginx/conf.d /usr/share/nginx/html /var/cache/nginx /var/log/nginx /run /usr/share/ollama

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
COPY --from=ollama-source /usr/lib/ollama /usr/lib/ollama

COPY docker/wheels /tmp/wheels
COPY docker/runtime-requirements.txt /tmp/runtime-requirements.txt
RUN python -m pip install --no-index --find-links /tmp/wheels -r /tmp/runtime-requirements.txt && \
    rm -rf /tmp/wheels

COPY Frontend/dist /usr/share/nginx/html
COPY Frontend/nginx.monolith.conf /etc/nginx/conf.d/default.conf
RUN chown -R www-data:www-data /var/cache/nginx /var/log/nginx /usr/share/nginx/html

COPY Backend/ ./Backend/
COPY Middleware/ ./Middleware/

RUN mkdir -p Backend/data Backend/models Backend/results Backend/checkpoints

COPY scripts/start.py /app/start.py

EXPOSE 80 8000 8001 11434

VOLUME ["/root/.ollama"]

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=5 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1/api/health', timeout=3)" || exit 1

CMD ["python3", "/app/start.py"]
