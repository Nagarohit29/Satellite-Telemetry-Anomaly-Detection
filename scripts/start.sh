#!/bin/bash
set -e

# Satellite Telemetry - one-image startup.
# Starts Ollama, nginx, the ML backend, and the API middleware in one container.

cleanup() {
    for pid in "${MIDDLEWARE_PID:-}" "${BACKEND_PID:-}" "${OLLAMA_PID:-}"; do
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
        fi
    done
}
trap cleanup EXIT INT TERM

if [ ! -f /app/.env ]; then
    cat > /app/.env <<'ENVEOF'
ANTHROPIC_API_KEY=
GEMINI_API_KEY=
OPENAI_API_KEY=
OLLAMA_API_BASE=http://127.0.0.1:11434
OLLAMA_MODEL=llama3
BACKEND_URL=http://127.0.0.1:8001
DATASET=SMAP
WINDOW_SIZE=100
THRESHOLD=0.5
SERVER_HOST=0.0.0.0
SERVER_PORT=8001
ENVEOF
fi

if [ ! -f /app/Middleware/.env ]; then
    printf '# This file is managed by the application.\n# API keys saved via the Settings UI will be written here.\n' \
        > /app/Middleware/.env
    chmod 644 /app/Middleware/.env
fi

set -a
sed 's/\r$//' /app/.env > /tmp/.env_clean
# shellcheck source=/dev/null
source /tmp/.env_clean
set +a

http_ok() {
    python3 -c "
import urllib.request, sys
try:
    urllib.request.urlopen('$1', timeout=2)
except Exception:
    sys.exit(1)
" 2>/dev/null
}

echo "Starting Ollama..."
OLLAMA_HOST=0.0.0.0 ollama serve &
OLLAMA_PID=$!

echo "Waiting for Ollama..."
until http_ok "http://127.0.0.1:11434/api/tags"; do
    sleep 2
done

MODEL="${OLLAMA_MODEL:-llama3}"
if ! ollama list 2>/dev/null | grep -q "^${MODEL}"; then
    echo "Pulling Ollama model: ${MODEL}. This runs once when /root/.ollama is cached."
    if ! ollama pull "${MODEL}"; then
        echo "Warning: failed to pull ${MODEL}. Chat will still work with cloud keys if configured."
    fi
else
    echo "Ollama model already cached: ${MODEL}"
fi

echo "Starting nginx..."
nginx

echo "Starting ML backend on port 8001..."
cd /app/Backend && python3 serve.py &
BACKEND_PID=$!

echo "Waiting for backend..."
for _ in $(seq 1 30); do
    if http_ok "http://127.0.0.1:8001/health"; then
        break
    fi
    sleep 2
done

if ! http_ok "http://127.0.0.1:8001/health"; then
    echo "Backend failed to become healthy."
    exit 1
fi

echo "Starting API middleware on port 8000..."
cd /app/Middleware && python3 main.py &
MIDDLEWARE_PID=$!

echo "All services started."
echo "Frontend:   http://localhost/"
echo "Middleware: http://localhost:8000"
echo "Backend:    http://localhost:8001"
echo "Ollama:     http://localhost:11434"

while true; do
    if ! kill -0 "$OLLAMA_PID" 2>/dev/null; then
        echo "Ollama exited."
        exit 1
    fi
    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo "Backend exited."
        exit 1
    fi
    if ! kill -0 "$MIDDLEWARE_PID" 2>/dev/null; then
        echo "Middleware exited."
        exit 1
    fi
    sleep 5
done
