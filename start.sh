#!/usr/bin/env bash
set -euo pipefail

export OLLAMA_HOST="0.0.0.0:11434"
export OLLAMA_MODELS="${OLLAMA_MODELS:-/root/.ollama}"

mkdir -p "${OLLAMA_MODELS}"

ollama serve > /tmp/ollama.log 2>&1 &
OLLAMA_PID=$!

cleanup() {
  kill "${OLLAMA_PID}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

for _ in $(seq 1 60); do
  if curl -sf http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if [[ -n "${OLLAMA_MODEL:-}" ]]; then
  if [[ "${OLLAMA_PULL_MODEL:-false}" == "true" ]]; then
    if ollama show "${OLLAMA_MODEL}" >/dev/null 2>&1; then
      echo "Model ${OLLAMA_MODEL} already available locally; skipping pull."
    else
      echo "Pulling model ${OLLAMA_MODEL} for first-time use..."
      ollama pull "${OLLAMA_MODEL}"
    fi
  else
    echo "Automatic model pull is disabled. Set OLLAMA_PULL_MODEL=true to download ${OLLAMA_MODEL} on startup."
  fi
fi

exec python3 -m uvicorn web_app:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1