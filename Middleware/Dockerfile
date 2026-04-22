# ─────────────────────────────────────────────────────────
# Middleware — AI Orchestration Layer
# ─────────────────────────────────────────────────────────
FROM python:3.11-slim

LABEL maintainer="Satellite Telemetry Anomaly Detection Team"
LABEL version="2.0"
LABEL description="AI Orchestration Middleware for Satellite Telemetry Anomaly Detection"

# ── Python optimisations ──
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LITELLM_LOG=ERROR

WORKDIR /app

# ── System packages ──
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ── Python deps (no torch — Middleware doesn't do inference) ──
COPY requirements.txt .
RUN grep -vE "torch|torchvision|--extra-index-url|numpy|pandas|scipy|scikit|matplotlib|seaborn|tqdm|PyYAML" requirements.txt > requirements-mini.txt && \
    pip install --no-cache-dir -r requirements-mini.txt && \
    rm requirements-mini.txt requirements.txt

# ── Application code ──
COPY Middleware/ ./Middleware/

# ─────────────────────────────────────────────────────────
# Seed .env files — writable by the running process so that
# the Settings UI can persist API keys without a restart.
#
# /app/.env       → primary (volume-mounted by docker-compose,
#                   or written here as a seed for standalone use)
# /app/Middleware/.env → kept in sync by config.py _get_env_paths()
#
# docker-compose mounts: - .env:/app/.env
# which overrides this seed at runtime.
# ─────────────────────────────────────────────────────────
RUN printf '%s\n' \
    '# Satellite Telemetry Anomaly Detection - Environment Variables' \
    '# This file is managed by the application.' \
    '# API keys saved via the Settings UI will be written here.' \
    '' \
    '# LLM Provider Configuration' \
    'ANTHROPIC_API_KEY=' \
    'GEMINI_API_KEY=' \
    'OPENAI_API_KEY=' \
    '' \
    '# Ollama Cloud Configuration (Optional)' \
    '# OLLAMA_API_KEY=' \
    '' \
    '# Ollama Local (set by docker-compose env or override)' \
    'OLLAMA_API_BASE=http://ollama:11434' \
    'OLLAMA_MODEL=llama3' \
    '' \
    '# Backend Service' \
    'BACKEND_URL=http://backend:8001' \
    > /app/.env && chmod 666 /app/.env

# Middleware-local .env seed
RUN printf '%s\n' \
    '# This file is managed by the application.' \
    '# API keys saved via the Settings UI will be written here.' \
    > /app/Middleware/.env && chmod 666 /app/Middleware/.env

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Use uvicorn directly — main.py __main__ block also works but uvicorn
# gives us proper signal handling and worker management
CMD ["python", "Middleware/main.py"]
