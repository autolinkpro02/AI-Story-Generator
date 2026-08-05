"""Regenerate a single scene (image + narration) for an existing project.

Usage:
  python regenerate_scene.py --project projects/the-story --scene 3
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from modules.project_manager import Project
from modules.image_generator import generate_scene_images
from modules.narration_generator import generate_narration_audio
from modules.video_builder import build_video


def regenerate_scene(project_path: str, scene_number: int) -> dict:
    project_dir = Path(project_path)
    script_path = project_dir / "script.json"
    if not script_path.exists():
        raise FileNotFoundError(f"No script found at {script_path}")

    script_data = json.loads(script_path.read_text())

    # Find the requested scene
    scenes = script_data.get("scenes", [])
    target = None
    for s in scenes:
        if int(s.get("scene_number", 0)) == int(scene_number):
            target = s
            break
    if not target:
        raise ValueError(f"Scene {scene_number} not found in script")

    project = Project(script_data.get("title", "untitled"))
    # Override project paths to point to the requested project directory
    project.root = project_dir
    project.scenes_dir = project_dir / "scenes"
    project.audio_dir = project_dir / "audio"
    project.subtitles_dir = project_dir / "subtitles"
    project.output_dir = project_dir / "output"
    project.state_path = project_dir / "project.json"

    single_scene_script = {
        "title": script_data.get("title"),
        "hook": script_data.get("hook"),
        "character_description": script_data.get("character_description"),
        "scenes": [target],
        "closing_line": script_data.get("closing_line"),
    }

    # Regenerate image and narration for the single scene
    generated_images = generate_scene_images(project, single_scene_script)
    generated_audio = generate_narration_audio(project, single_scene_script)

    # Remove any zero-length .mp3 files which break ffmpeg concat
    for p in project.audio_dir.glob("scene_*.mp3"):
        try:
            if p.exists() and p.stat().st_size == 0:
                p.unlink()
        except Exception:
            pass

    # Rebuild the final video using the full script_data
    video_assets = build_video(project, script_data)

    return {
        "images": [str(p) for p in generated_images],
        "audio": [str(p) for p in generated_audio],
        "video": str(video_assets[0]) if video_assets else None,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Regenerate a single scene's image and narration")
    parser.add_argument("--project", required=True)
    parser.add_argument("--scene", required=True, type=int)
    args = parser.parse_args()

    res = regenerate_scene(args.project, args.scene)
    print(json.dumps(res, indent=2))
