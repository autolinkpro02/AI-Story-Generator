"""Generate narration audio for each scene using a free text-to-speech fallback."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import requests


def _try_gtts(text: str, output_path: Path) -> bool:
    try:
        from gtts import gTTS
    except Exception:
        return False

    try:
        audio = gTTS(text=text, lang="en")
        audio.save(output_path)
        return True
    except Exception:
        return False


def _try_edge_tts(text: str, output_path: Path) -> bool:
    try:
        import edge_tts
    except Exception:
        return False

    try:
        import asyncio

        async def _render() -> None:
            communicate = edge_tts.Communicate(text, voice="en-US-AvaNeural")
            await communicate.save(output_path)

        asyncio.run(_render())
        return True
    except Exception:
        return False


from concurrent.futures import ThreadPoolExecutor


def generate_narration_audio(project: Any, script_data: dict[str, Any]) -> list[Path]:
    """Create per-scene narration audio files concurrently using parallel TTS workers."""
    output_files: list[Path] = []
    project.audio_dir.mkdir(parents=True, exist_ok=True)
    scenes = script_data.get("scenes", [])
    if not scenes:
        return []

    def _render_single_narration(scene):
        scene_number = scene.get("scene_number", 1)
        narration_text = scene.get("narration", "")
        output_path = project.audio_dir / f"scene_{scene_number:02d}.mp3"

        if output_path.exists() and output_path.stat().st_size > 1000:
            return output_path

        if _try_gtts(narration_text, output_path):
            return output_path

        if _try_edge_tts(narration_text, output_path):
            return output_path

        fallback_path = project.audio_dir / f"scene_{scene_number:02d}.txt"
        fallback_path.write_text(narration_text)
        return fallback_path

    with ThreadPoolExecutor(max_workers=min(6, len(scenes))) as executor:
        results = list(executor.map(_render_single_narration, scenes))
        for res in results:
            if res and res.exists():
                output_files.append(res)

    return output_files
