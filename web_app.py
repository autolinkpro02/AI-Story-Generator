from __future__ import annotations

from pathlib import Path
from typing import Any
import os
import uuid
import time
import json
from urllib.parse import quote, unquote

from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse

from app import run_story_pipeline
from regenerate_scene import regenerate_scene

ROOT = Path(__file__).resolve().parent
INDEX_PATH = ROOT / "index.html"
GENERATED_FILES: dict[str, Path] = {}
JOBS: dict[str, dict] = {}

app = FastAPI()


def _register_generated_file(path: Path | None) -> str | None:
    if not path:
        return None
    resolved = Path(path).resolve()
    token = quote(str(resolved), safe="")
    GENERATED_FILES[token] = resolved
    return f"/generated/{token}"


def _parse_story_form(data: dict[str, Any]) -> dict[str, Any]:
    idea = (data.get("idea") or "").strip()
    if not idea:
        raise ValueError("Story idea is required.")

    duration = int(str(data.get("duration", "30") or "30").strip() or "30")
    if duration <= 0:
        raise ValueError("Duration must be greater than zero.")

    return {
        "idea": idea,
        "story_type": str(data.get("story_type", "emotional") or "emotional").strip(),
        "visual_style": str(data.get("visual_style", "storybook watercolor illustration") or "storybook watercolor illustration").strip(),
        "duration_seconds": duration,
        "character_description": (str(data.get("character_description", "") or "").strip() or None),
        "title": (str(data.get("title", "") or "").strip() or None),
    }


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(INDEX_PATH.read_text(encoding="utf-8"))


@app.get("/generated/{token}")
async def get_generated(token: str):
    target = GENERATED_FILES.get(token)
    if target and target.exists() and target.is_file():
        media_type = "application/octet-stream"
        if target.suffix.lower() == ".mp4":
            media_type = "video/mp4"
        elif target.suffix.lower() == ".srt":
            media_type = "text/plain; charset=utf-8"
        elif target.suffix.lower() == ".png":
            media_type = "image/png"
        return FileResponse(path=target, media_type=media_type)

    # Fallback: try decoding token as an encoded absolute path
    try:
        decoded = unquote(token)
        candidate = Path(decoded)
        if candidate.exists() and candidate.is_file():
            return FileResponse(path=candidate)
    except Exception:
        pass
    raise HTTPException(status_code=404, detail="file not found")


@app.get("/status/{token}")
async def status(token: str):
    job = JOBS.get(unquote(token))
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    payload = {
        "status": job.get("status"),
        "step": job.get("step", "Processing..."),
        "progress": job.get("progress", 0),
        "script": job.get("script"),
    }
    if job.get("status") == "finished":
        result = job.get("result") or {}
        payload.update({
            "project": str(result.get("project", "")).replace("\\", "/"),
            "video": _register_generated_file(result.get("video")) if result.get("video") else None,
            "captions": _register_generated_file(result.get("captions")) if result.get("captions") else None,
        })
    elif job.get("status") == "error":
        payload.update({"error": job.get("error")})
    return JSONResponse(payload)


@app.post("/regenerate_scene")
async def api_regenerate_scene(request: Request):
    data = await request.json()
    project = data.get("project")
    scene = data.get("scene")
    if not project or not scene:
        raise HTTPException(status_code=400, detail="project and scene are required")
    try:
        res = regenerate_scene(project, int(scene))
        return JSONResponse(res)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate")
async def generate(request: Request, background_tasks: BackgroundTasks):
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        data = await request.json()
    else:
        form = await request.form()
        data = dict(form)

    try:
        req = _parse_story_form(data)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    token = str(uuid.uuid4())
    JOBS[token] = {
        "status": "queued",
        "step": "Queued in pipeline...",
        "progress": 0,
        "result": None,
        "error": None,
        "started": time.time(),
    }

    def _worker(tok: str, req_params: dict) -> None:
        JOBS[tok]["status"] = "running"
        
        def _cb(step: str, pct: int, extra: dict = None):
            JOBS[tok]["step"] = step
            JOBS[tok]["progress"] = pct
            if extra and "script" in extra:
                JOBS[tok]["script"] = extra["script"]

        try:
            res = run_story_pipeline(**req_params, progress_callback=_cb)
            JOBS[tok]["result"] = res
            JOBS[tok]["status"] = "finished"
            JOBS[tok]["progress"] = 100
            JOBS[tok]["step"] = "Completed!"
        except Exception as e:
            JOBS[tok]["error"] = str(e)
            JOBS[tok]["status"] = "error"

    background_tasks.add_task(_worker, token, req)
    return JSONResponse({"status": "queued", "token": token, "status_url": f"/status/{token}"})


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run("web_app:app", host=host, port=port, log_level="info")
