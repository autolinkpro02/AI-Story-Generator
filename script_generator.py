"""
modules/script_generator.py

Turns a story idea into a structured script + scene breakdown using a local
Ollama model. Everything talks to localhost:11434 -- no cloud APIs involved.

Requires: `ollama serve` running, and the model pulled once via
    ollama pull llama3.2:3b
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import requests
import sys

sys.path.append(str(Path(__file__).parent.parent))
from config import OLLAMA_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT_SECONDS

MAX_RETRIES = 1

SYSTEM_PROMPT = (
    "You are a master scriptwriter for short vertical story videos (Instagram Reels / "
    "TikTok / YouTube Shorts). You always respond with ONLY a single valid JSON "
    "object -- no markdown, no commentary, no code fences. Follow the exact "
    "schema you are given every time.\n"
    "CRITICAL REQUIREMENT FOR IMAGES: Every scene's `image_prompt` MUST explicitly depict "
    "the specific main character or subject of the story idea (e.g. if the story is about a firefly, "
    "fox, dragon, or girl, that specific character MUST be described in detail in every scene's image_prompt)."
)

REQUIRED_TOP_KEYS = {"title", "hook", "character_description", "scenes", "closing_line"}
REQUIRED_SCENE_KEYS = {"scene_number", "narration", "image_prompt", "duration_seconds"}


@dataclass
class ScriptRequest:
    idea: str
    story_type: str            # emotional | motivational | mystery | moral
    visual_style: str          # e.g. "children's book watercolor illustration"
    duration_seconds: int = 45
    character_description: Optional[str] = None
    model: str = OLLAMA_MODEL


@dataclass
class ScriptResult:
    raw: dict
    warnings: list = field(default_factory=list)


def _schema_instructions() -> str:
    return """Return a JSON object with EXACTLY this shape:

{
  "title": string,
  "hook": string,
  "character_description": string,
  "scenes": [
    {
      "scene_number": integer,
      "narration": string,
      "image_prompt": string,
      "duration_seconds": number
    }
  ],
  "closing_line": string
}

Rules:
- Use between 6 and 10 scenes total, matching the requested duration.
- Every "image_prompt" must restate the exact character/subject description word-for-word so
  every scene stays visually consistent and matches the story.
- Durations should sum to roughly the requested video length.
- Output raw JSON only, nothing else."""


def _extract_json(text: str) -> dict:
    """Ollama sometimes wraps JSON in ```json fences despite instructions -- strip that."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text)
    text = re.sub(r"```$", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in model output")
    return json.loads(text[start:end + 1])


def _validate(data: dict) -> list:
    problems = []
    missing = REQUIRED_TOP_KEYS - data.keys()
    if missing:
        problems.append(f"missing top-level keys: {missing}")
        return problems

    scenes = data.get("scenes", [])
    if not (6 <= len(scenes) <= 10):
        problems.append(f"expected 6-10 scenes, got {len(scenes)}")

    return problems


def _generate_fallback_script(request: ScriptRequest) -> ScriptResult:
    clean_idea = request.idea.strip()
    char_desc = request.character_description or clean_idea
    title = f"Story of {clean_idea[:30].title()}"
    per_scene_dur = max(3, request.duration_seconds // 6)
    
    scenes = [
        {
            "scene_number": 1,
            "narration": f"Once upon a time, a story unfolded: {clean_idea[:90]}.",
            "image_prompt": f"Masterpiece digital art depicting {char_desc}, standing in a scenic landscape at dawn, {request.visual_style}",
            "duration_seconds": per_scene_dur
        },
        {
            "scene_number": 2,
            "narration": f"As the sun rose, a mysterious discovery changed everything.",
            "image_prompt": f"Masterpiece digital art depicting {char_desc}, discovering a magical glowing wonder, {request.visual_style}",
            "duration_seconds": per_scene_dur
        },
        {
            "scene_number": 3,
            "narration": "A sudden challenge appeared, testing true courage and resolve.",
            "image_prompt": f"Masterpiece digital art depicting {char_desc}, facing a stormy mystical challenge, {request.visual_style}",
            "duration_seconds": per_scene_dur
        },
        {
            "scene_number": 4,
            "narration": "Through inner strength and hope, a path through darkness opened.",
            "image_prompt": f"Masterpiece digital art depicting {char_desc}, surrounded by warm magical light rays, {request.visual_style}",
            "duration_seconds": per_scene_dur
        },
        {
            "scene_number": 5,
            "narration": "With every step forward, peace and joy returned once more.",
            "image_prompt": f"Masterpiece digital art depicting {char_desc}, celebrating joyfully in a glowing world, {request.visual_style}",
            "duration_seconds": per_scene_dur
        },
        {
            "scene_number": 6,
            "narration": "And so, an unforgettable journey taught a timeless lesson.",
            "image_prompt": f"Masterpiece digital art depicting {char_desc}, looking out at a stunning golden sunset, {request.visual_style}",
            "duration_seconds": per_scene_dur
        }
    ]

    return ScriptResult(raw={
        "title": title,
        "hook": f"Discover the story of {clean_idea[:30]}",
        "character_description": char_desc,
        "scenes": scenes,
        "closing_line": "Every great journey starts with a single step."
    })


def generate_script(request: ScriptRequest) -> ScriptResult:
    character_line = (
        f"Character: {request.character_description}"
        if request.character_description
        else "Invent a simple, consistent main character."
    )

    user_prompt = f"""Story idea: {request.idea}
Story type: {request.story_type}
Visual style: {request.visual_style}
Target duration: {request.duration_seconds} seconds
{character_line}

{_schema_instructions()}"""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    is_generate_endpoint = "/api/generate" in OLLAMA_URL

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if is_generate_endpoint:
                full_prompt = f"{SYSTEM_PROMPT}\n\n{user_prompt}"
                if attempt > 1 and len(messages) > 2:
                    full_prompt += f"\n\nNote: Previous attempt had formatting issues: {messages[-1]['content']}. Output pure valid JSON."
                
                payload = {
                    "model": request.model,
                    "prompt": full_prompt,
                    "format": "json",
                    "stream": False,
                }
            else:
                payload = {
                    "model": request.model,
                    "messages": messages,
                    "format": "json",
                    "stream": False,
                }

            resp = requests.post(
                OLLAMA_URL,
                json=payload,
                timeout=6,  # 6 second timeout for instant response
            )
            resp.raise_for_status()
            res_json = resp.json()

            if "response" in res_json:
                content = res_json["response"]
            elif "message" in res_json and "content" in res_json["message"]:
                content = res_json["message"]["content"]
            else:
                content = str(res_json)

            data = _extract_json(content)
            problems = _validate(data)

            if not problems:
                return ScriptResult(raw=data)

            if attempt == MAX_RETRIES:
                return ScriptResult(raw=data, warnings=problems)

            messages.append({"role": "assistant", "content": content})
            messages.append({
                "role": "user",
                "content": "That JSON had problems: " + "; ".join(problems)
                + ". Return a corrected, complete JSON object only.",
            })

        except Exception as e:
            print(f"Ollama generation attempt {attempt} failed ({e}). Using smart fallback generator...")
            if attempt == MAX_RETRIES:
                return _generate_fallback_script(request)

    return _generate_fallback_script(request)
