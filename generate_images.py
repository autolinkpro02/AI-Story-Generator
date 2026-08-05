from pathlib import Path
import json

from modules.image_generator import generate_scene_images
from modules.project_manager import Project


if __name__ == "__main__":
    project_dir = Path("projects") / "the-little-firefly-guide"
    script_path = project_dir / "script.json"

    if not script_path.exists():
        raise FileNotFoundError(f"No script found at {script_path}")

    with script_path.open() as handle:
        script_data = json.load(handle)

    project = Project(script_data["title"])
    project.root = project_dir
    project.scenes_dir = project_dir / "scenes"
    project.audio_dir = project_dir / "audio"
    project.subtitles_dir = project_dir / "subtitles"
    project.output_dir = project_dir / "output"
    project.state_path = project_dir / "project.json"

    output_files = generate_scene_images(project, script_data)
    print(f"Generated {len(output_files)} scene images")
    for path in output_files:
        print(path)
