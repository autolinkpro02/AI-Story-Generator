"""
modules/script_generator.py

Turns a story idea into a structured script + scene breakdown using a local
Ollama model. Everything talks to localhost:11434 (or OLLAMA_URL) -- no cloud
APIs involved.

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

print(f"[script_generator] LOADED FROM: {__file__}  (fox-fix build)")

MAX_RETRIES = 1

# The old code hardcoded timeout=6, ignoring config.OLLAMA_TIMEOUT_SECONDS entirely.
# 6 seconds is not enough for a real generation call to a remote model, so every
# run was silently timing out and falling back to the generic template script.
# Capped here (instead of using the full 600s from config) so a bad/slow endpoint
# still fails fast enough to keep the overall pipeline quick.
_is_local = ("localhost" in OLLAMA_URL) or ("127.0.0.1" in OLLAMA_URL)
if _is_local:
    # Local CPU inference of even a 3B model can genuinely take past 25s, especially
    # on the first call which also has to load the model into memory. No network
    # flakiness to protect against here, so give it real room - up to config's value.
    REQUEST_TIMEOUT_SECONDS = OLLAMA_TIMEOUT_SECONDS
else:
    # Remote/free-tier endpoint - fail fast rather than hang the whole pipeline on it.
    REQUEST_TIMEOUT_SECONDS = min(OLLAMA_TIMEOUT_SECONDS, 25)
print(f"[script_generator] OLLAMA_URL={OLLAMA_URL}  timeout={REQUEST_TIMEOUT_SECONDS}s  local={_is_local}")

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
    """Used only when Ollama is unreachable/too slow/returns bad JSON.
    IMPORTANT: this must still describe the user's actual idea/character -
    the old version hardcoded a generic human photo here regardless of the
    idea, which is why a "fox learns to fly" story rendered as a random man."""
    clean_idea = request.idea.strip()
    char_desc = request.character_description or f"the main character from: {clean_idea}"
    title = f"The Legend of {clean_idea[:30].title()}"
    per_scene_dur = max(3, request.duration_seconds // 6)

    narration_idea = re.sub(r'\s*\([^)]*\)', '', clean_idea).strip()
    if narration_idea.lower().startswith("a "):
        narration_idea = narration_idea[2:].strip()
    elif narration_idea.lower().startswith("an "):
        narration_idea = narration_idea[3:].strip()

    # hero_name is just for narration text readability - "the fox", "our hero", etc.
    # Only use a real name if the user actually gave one via --character.
    raw_char = (request.character_description or "").strip()
    hero_name = "our hero"
    if raw_char:
        name_match = re.search(r'\b([A-Z][a-z]+)\b', raw_char)
        if name_match and name_match.group(1).lower() not in ["handsome", "male", "female", "photographer", "explorer", "young"]:
            hero_name = name_match.group(1)

    # hero_anchor drives the image_prompt - this MUST reflect the actual idea/character,
    # not a fixed stock description, or every scene renders as an unrelated generic photo.
    hero_anchor = request.character_description.strip() if request.character_description else narration_idea
    style_hint = request.visual_style or "cinematic illustration"

    scenes = [
        {
            "scene_number": 1,
            "narration": f"Every great journey begins with a single step. {hero_name} set out on an inspiring path: {narration_idea}.",
            "image_prompt": f"{hero_anchor}, {style_hint}, walking down a sunlit avenue with atmospheric background, sharp focus, deep depth of field, highly detailed, consistent character design",
            "duration_seconds": per_scene_dur
        },
        {
            "scene_number": 2,
            "narration": f"Guided by curiosity and passion, {hero_name} ventured deeper, discovering a fascinating secret that opened up new possibilities.",
            "image_prompt": f"{hero_anchor}, {style_hint}, exploring an intricate detailed environment full of curious objects, sharp focus, deep depth of field, highly detailed, consistent character design",
            "duration_seconds": per_scene_dur
        },
        {
            "scene_number": 3,
            "narration": f"Suddenly, an unexpected challenge arose. Determination and quick thinking tested {hero_name}'s true resolve.",
            "image_prompt": f"{hero_anchor}, {style_hint}, facing a dramatic obstacle, tense dynamic pose, sharp focus, deep depth of field, highly detailed, consistent character design",
            "duration_seconds": per_scene_dur
        },
        {
            "scene_number": 4,
            "narration": f"Drawing upon inner strength and focus, a clear path forward revealed itself for {hero_name}.",
            "image_prompt": f"{hero_anchor}, {style_hint}, a moment of quiet focus and realization, soft directional lighting, sharp focus, deep depth of field, highly detailed, consistent character design",
            "duration_seconds": per_scene_dur
        },
        {
            "scene_number": 5,
            "narration": f"With a moment of breakthrough and pride, {hero_name} achieved a meaningful victory.",
            "image_prompt": f"{hero_anchor}, {style_hint}, a triumphant victorious moment, dramatic lighting, sharp focus, deep depth of field, highly detailed, consistent character design",
            "duration_seconds": per_scene_dur
        },
        {
            "scene_number": 6,
            "narration": f"As warm evening light settled across the horizon, peace returned, leaving {hero_name}'s journey as an unforgettable story.",
            "image_prompt": f"{hero_anchor}, {style_hint}, standing peacefully against a warm sunset sky, sharp focus, deep depth of field, highly detailed, consistent character design",
            "duration_seconds": per_scene_dur
        }
    ]

    return ScriptResult(raw={
        "title": title,
        "hook": f"Discover the story of {narration_idea}",
        "character_description": char_desc,
        "scenes": scenes,
        "closing_line": f"The story of {narration_idea} lives on forever."
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
                timeout=REQUEST_TIMEOUT_SECONDS,
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