from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from script_generator import ScriptRequest, generate_script
from modules.project_manager import Project
from modules.image_generator import generate_scene_images
from modules.narration_generator import generate_narration_audio
from modules.video_builder import build_video


def run_story_pipeline(
    idea: str,
    story_type: str,
    visual_style: str,
    duration_seconds: int = 45,
    character_description: Optional[str] = None,
    title: Optional[str] = None,
    progress_callback: Optional[callable] = None,
) -> dict:
    if progress_callback:
        progress_callback("Generating script & scene breakdown...", 10)

    request = ScriptRequest(
        idea=idea,
        story_type=story_type,
        visual_style=visual_style,
        duration_seconds=duration_seconds,
        character_description=character_description,
    )
    script_result = generate_script(request)
    script_data = script_result.raw

    if title:
        script_data["title"] = title

    project = Project(script_data["title"])
    project.save_script(script_data)

    if progress_callback:
        progress_callback("Generating scene illustrations...", 30, {"script": script_data})

    generate_scene_images(project, script_data, progress_callback=progress_callback)

    if progress_callback:
        progress_callback("Generating voice narration...", 65)

    generate_narration_audio(project, script_data)

    if progress_callback:
        progress_callback("Rendering video & synchronized captions with FFmpeg...", 85)

    video_assets = build_video(project, script_data, progress_callback=progress_callback)

    if progress_callback:
        progress_callback("Video generation completed!", 100)

    return {
        "project": project.root,
        "script": project.root / "script.json",
        "video": video_assets[0] if video_assets else None,
        "captions": project.subtitles_dir / "captions.srt",
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate a story video from a story idea")
    parser.add_argument("--idea", required=True)
    parser.add_argument("--story-type", default="emotional")
    parser.add_argument("--visual-style", default="cinematic storybook illustration")
    parser.add_argument("--duration", type=int, default=45)
    parser.add_argument("--character", default=None)
    parser.add_argument("--title", default=None)
    args = parser.parse_args()

    result = run_story_pipeline(
        idea=args.idea,
        story_type=args.story_type,
        visual_style=args.visual_style,
        duration_seconds=args.duration,
        character_description=args.character,
        title=args.title,
    )
    print(json.dumps({"project": str(result["project"]), "video": str(result["video"]), "captions": str(result["captions"])}, indent=2))
