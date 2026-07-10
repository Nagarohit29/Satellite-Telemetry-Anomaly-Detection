# ── Legacy Middleware Dockerfile (v1) ──
# DEPRECATED: Use Middleware/Dockerfile.v2 with docker-compose.v2.yml
# Kept for backward compatibility with docker-compose.split.yml
FROM python:3.11-slim-bookworm

LABEL version="1.1-legacy"
LABEL description="AI Orchestration Middleware (legacy — use Dockerfile.v2)"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    LITELLM_LOG=ERROR

WORKDIR /app

COPY requirements.txt .
RUN grep -vE "torch|torchvision|--extra-index-url|numpy|pandas|scipy|scikit|matplotlib|seaborn|tqdm|PyYAML" requirements.txt > requirements-mini.txt && \
    pip install --no-cache-dir -r requirements-mini.txt && \
    rm requirements-mini.txt requirements.txt && \
    find /usr/local/lib/python3.11 -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true

COPY Middleware/ ./Middleware/

RUN printf 'OLLAMA_API_BASE=http://ollama:11434\nOLLAMA_MODEL=llama3.2\nBACKEND_URL=http://backend:8001\n' > /app/.env && \
    printf '# Managed by application\n' > /app/Middleware/.env && \
    chmod 666 /app/.env /app/Middleware/.env

RUN useradd -r -s /sbin/nologin appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)" || exit 1

CMD ["python", "Middleware/main.py"]
