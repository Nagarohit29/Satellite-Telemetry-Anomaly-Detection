# ─────────────────────────────────────────────────────────
# Stage 1: Build Frontend (Alpine — uses npm, no apt-get)
# ─────────────────────────────────────────────────────────
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY Frontend/package*.json ./
# Remove Windows-generated lock (pins rollup-win32); regenerate for Linux/musl
RUN rm -f package-lock.json && npm install
COPY Frontend/ .
RUN npm run build


# ─────────────────────────────────────────────────────────
# Stage 2: nginx binary source
# nginx:1.25 is Debian bookworm (glibc) — ABI-compatible with Ubuntu 22.04
# We COPY the binary into the pytorch stage so zero apt-get is needed there.
# ─────────────────────────────────────────────────────────
FROM nginx:1.25 AS nginx-source


# ─────────────────────────────────────────────────────────
# Stage 3: Ollama binary source
# Pull the pre-built Ollama binary from the official image.
# Avoids running "curl https://ollama.com/install.sh | sh" inside the container.
# ─────────────────────────────────────────────────────────
FROM ollama/ollama:latest AS ollama-source


# ─────────────────────────────────────────────────────────
# Stage 4: Monolithic Runtime
# pytorch/pytorch ships Python 3.11 + CUDA 12.1 + PyTorch 2.5.1 pre-built.
# NO apt-get calls — all system binaries come from the stages above.
# ─────────────────────────────────────────────────────────
FROM pytorch/pytorch:2.5.1-cuda12.1-cudnn9-runtime

LABEL maintainer="Satellite Telemetry Anomaly Detection Team"
LABEL version="2.0"
LABEL description="Monolithic Satellite Telemetry Anomaly Detection"

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility \
    LITELLM_LOG=ERROR

WORKDIR /app

# ── Copy nginx from official image (no apt-get) ──
# nginx:1.25 (Debian bookworm) shares glibc ABI with Ubuntu 22.04 — compatible.
COPY --from=nginx-source /usr/sbin/nginx          /usr/sbin/nginx
COPY --from=nginx-source /etc/nginx               /etc/nginx
COPY --from=nginx-source /usr/lib/nginx           /usr/lib/nginx
COPY --from=nginx-source /usr/share/nginx         /usr/share/nginx
COPY --from=nginx-source /var/log/nginx           /var/log/nginx
COPY --from=nginx-source /usr/lib/x86_64-linux-gnu/libpcre2-8.so.0 \
    /usr/lib/x86_64-linux-gnu/libpcre2-8.so.0
RUN mkdir -p /var/cache/nginx /run && \
    useradd --system --no-create-home --shell /bin/false --user-group nginx

# ── Copy Ollama binary and GPU runners from official image ──
COPY --from=ollama-source /usr/bin/ollama /usr/bin/ollama
COPY --from=ollama-source /usr/lib/ollama /usr/lib/ollama
RUN mkdir -p /usr/share/ollama

# ── Python deps — skip torch (pre-installed in pytorch base) ──
COPY requirements.txt .
# Install in two passes for resilience against network drops:
# Pass 1 — core server + middleware deps (small, fast)
# Pass 2 — backend ML deps (large wheels, needs more time)
RUN grep -vE "torch|torchvision|--extra-index-url|numpy|pandas|scipy|scikit|matplotlib|seaborn|tqdm" \
        requirements.txt > req_middleware.txt && \
    pip install --no-cache-dir --timeout 120 --retries 5 -r req_middleware.txt && \
    rm req_middleware.txt

RUN grep -E "numpy|pandas|scipy|scikit|matplotlib|seaborn|tqdm|PyYAML" \
        requirements.txt > req_backend.txt && \
    pip install --no-cache-dir --timeout 120 --retries 5 -r req_backend.txt && \
    rm req_backend.txt requirements.txt

# ── Frontend built assets ──
COPY --from=frontend-builder /app/frontend/dist /usr/share/nginx/html

# ── Nginx config ──
# ── Nginx config ──
# The monolithic image runs nginx, middleware, and backend in one container.
COPY Frontend/nginx.monolith.conf /etc/nginx/conf.d/default.conf

# ── Application code ──
COPY Backend/   ./Backend/
COPY Middleware/ ./Middleware/

# ── Data directories ──
RUN mkdir -p Backend/data Backend/models Backend/results Backend/checkpoints

# ── Seed .env files (writable so Settings UI can persist API keys) ──
RUN printf '%s\n' \
    '# Satellite Telemetry Anomaly Detection - Environment Variables' \
    '# This file is managed by the application.' \
    'ANTHROPIC_API_KEY=' \
    'GEMINI_API_KEY=' \
    'OPENAI_API_KEY=' \
    'OLLAMA_API_BASE=http://127.0.0.1:11434' \
    'OLLAMA_MODEL=llama3' \
    'BACKEND_URL=http://127.0.0.1:8001' \
    'DATASET=SMAP' \
    'WINDOW_SIZE=100' \
    'THRESHOLD=0.5' \
    'SERVER_HOST=0.0.0.0' \
    'SERVER_PORT=8001' \
    > /app/.env && chmod 666 /app/.env

RUN printf '%s\n' \
    '# This file is managed by the application.' \
    '# API keys saved via the Settings UI will be written here.' \
    > /app/Middleware/.env && chmod 666 /app/Middleware/.env

# ── Service defaults ──
ENV BACKEND_URL=http://127.0.0.1:8001 \
    OLLAMA_API_BASE=http://127.0.0.1:11434 \
    OLLAMA_MODEL=llama3 \
    OLLAMA_HOST=0.0.0.0 \
    SERVER_HOST=0.0.0.0 \
    SERVER_PORT=8001

# ── Startup script ──
COPY scripts/start.sh /app/start.sh
RUN chmod +x /app/start.sh

EXPOSE 80 8000 8001 11434

VOLUME ["/root/.ollama"]

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=5 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1/api/health', timeout=3)" || exit 1

CMD ["/app/start.sh"]
