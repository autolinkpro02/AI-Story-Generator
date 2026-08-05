# Ollama Railway API

This folder contains a small FastAPI gateway that starts an Ollama server and exposes an HTTP API you can call from your main app.

## Endpoints
- `GET /health`
- `GET /api/tags`
- `GET /api/version`
- `POST /api/chat`
- `POST /api/generate`

## Environment variables
- `OLLAMA_MODEL` - default model to use, for example `llama3.2:3b`
- `OLLAMA_HOST` - Ollama server URL inside the container, defaults to `http://127.0.0.1:11434`
- `OLLAMA_TIMEOUT_SECONDS` - request timeout for non-streaming calls
- `PORT` - Railway port, defaults to `8000`

## How to use on Railway
1. Deploy this folder as its own Railway service.
2. Set `OLLAMA_MODEL` to the model you want.
3. Use the deployed service URL as your model API base.
4. Point your main app's `OLLAMA_URL` to `https://<your-service>/api/chat`.

## Example request
```bash
curl -X POST https://<your-service>/api/chat \
  -H "Content-Type: application/json" \
  -d '{"model":"llama3.2:3b","messages":[{"role":"user","content":"Write a short story idea."}]}'
```
