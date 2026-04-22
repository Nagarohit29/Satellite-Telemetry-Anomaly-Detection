#!/bin/bash
# ─────────────────────────────────────────────
# Ollama Init — starts the server and ensures
# llama3 is available (pulled if missing).
# Used by the docker-compose `ollama` service.
# ─────────────────────────────────────────────
set -e

# Model to ensure is available (matches OLLAMA_MODEL default)
MODEL="${OLLAMA_MODEL:-llama3}"

echo "🤖 Starting Ollama server..."
ollama serve &
OLLAMA_PID=$!

echo "⏳ Waiting for Ollama API to be ready..."
until curl -s http://127.0.0.1:11434/api/tags > /dev/null 2>&1; do
    sleep 2
done
echo "✅ Ollama API is up!"

# Pull the model only if it isn't already cached in the volume
if ! ollama list 2>/dev/null | grep -q "^${MODEL}"; then
    echo "📥 Pulling model: ${MODEL} (this runs once — cached in ollama_data volume)"
    ollama pull "${MODEL}"
    echo "✅ ${MODEL} ready!"
else
    echo "✅ ${MODEL} already cached — skipping pull"
fi

echo "🤖 Ollama ready — serving ${MODEL} on :11434"

# Hand off to the Ollama server process
wait $OLLAMA_PID
