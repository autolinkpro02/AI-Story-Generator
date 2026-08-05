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
  if [[ "${OLLAMA_PULL_MODEL:-true}" == "true" ]]; then
    ollama pull "${OLLAMA_MODEL}"
  fi
fi

exec python3 -m uvicorn web_app:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1