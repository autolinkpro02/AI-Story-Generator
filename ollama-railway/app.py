from __future__ import annotations

import os
from typing import Any, Iterator

import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")
TIMEOUT_SECONDS = float(os.environ.get("OLLAMA_TIMEOUT_SECONDS", "600"))

app = FastAPI(title="Ollama API Gateway", version="1.0.0")


@app.get("/")
async def root() -> dict[str, Any]:
    return {
        "service": "ollama-api-gateway",
        "ollama_host": OLLAMA_HOST,
        "default_model": DEFAULT_MODEL,
        "endpoints": ["/health", "/api/chat", "/api/generate", "/api/tags"],
    }


@app.get("/health")
async def health() -> dict[str, Any]:
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=10)
        response.raise_for_status()
        return {"status": "ok", "ollama": "reachable", "models": response.json()}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Ollama not reachable: {exc}")


@app.get("/api/tags")
async def api_tags() -> JSONResponse:
    return _proxy_json("GET", "/api/tags")


@app.post("/api/generate")
async def api_generate(request: Request):
    payload = await request.json()
    payload.setdefault("model", DEFAULT_MODEL)
    return await _proxy_ollama_json_or_stream("/api/generate", payload)


@app.post("/api/chat")
async def api_chat(request: Request):
    payload = await request.json()
    payload.setdefault("model", DEFAULT_MODEL)
    return await _proxy_ollama_json_or_stream("/api/chat", payload)


@app.get("/api/version")
async def api_version() -> JSONResponse:
    return _proxy_json("GET", "/api/version")


def _proxy_json(method: str, path: str, payload: dict[str, Any] | None = None) -> JSONResponse:
    try:
        response = requests.request(
            method,
            f"{OLLAMA_HOST}{path}",
            json=payload,
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return JSONResponse(response.json(), status_code=response.status_code)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Failed to reach Ollama: {exc}")


async def _proxy_ollama_json_or_stream(path: str, payload: dict[str, Any]):
    stream = bool(payload.get("stream", False))
    try:
        response = requests.post(
            f"{OLLAMA_HOST}{path}",
            json=payload,
            timeout=None if stream else TIMEOUT_SECONDS,
            stream=stream,
        )
        response.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Failed to reach Ollama: {exc}")

    if stream:
        def iterator() -> Iterator[bytes]:
            try:
                for chunk in response.iter_content(chunk_size=4096):
                    if chunk:
                        yield chunk
            finally:
                response.close()

        return StreamingResponse(iterator(), media_type="application/x-ndjson")

    try:
        return JSONResponse(response.json(), status_code=response.status_code)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Invalid JSON from Ollama: {exc}")


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("app:app", host="0.0.0.0", port=port, log_level="info")
