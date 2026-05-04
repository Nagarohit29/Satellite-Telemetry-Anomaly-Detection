#!/bin/bash
set -euo pipefail

MODEL="${OLLAMA_MODEL:-llama3.2}"

echo "Starting Ollama server..."
ollama serve &
OLLAMA_PID=$!

cleanup() {
  if kill -0 "${OLLAMA_PID}" 2>/dev/null; then
    kill "${OLLAMA_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

echo "Waiting for Ollama API..."
for _ in $(seq 1 60); do
  if ollama list >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

if ! ollama list 2>/dev/null | grep -q "^${MODEL}"; then
  echo "Pulling Ollama model: ${MODEL}"
  if ! ollama pull "${MODEL}"; then
    echo "Warning: failed to pull ${MODEL}"
  fi
else
  echo "Ollama model already cached: ${MODEL}"
fi

echo "Ollama ready on :11434"
wait "${OLLAMA_PID}"
