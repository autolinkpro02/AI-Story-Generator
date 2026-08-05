"""
modules/project_manager.py

Creates the per-story project folder (matching the spec's layout) and tracks
which pipeline stage has completed, so a crash resumes instead of restarting
the whole story from scratch.

    projects/
      story-name/
        project.json
        script.txt
        script.json
        scenes/
        audio/
        subtitles/
        output/
"""

import json
import re
import time
from pathlib import Path

import sys

sys.path.append(str(Path(__file__).parent.parent))
from config import PROJECTS_DIR

STAGES = ["script", "images", "narration", "captions", "assembly"]


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "untitled-story"


class Project:
    def __init__(self, title: str):
        self.slug = slugify(title)
        # Allow tests or compatibility wrappers to override the projects directory
        # by setting `modules.project_manager.PROJECTS_DIR`. This keeps the
        # behavior stable when the compatibility package (modules.project_manager)
        # is used in tests which assign a temporary path.
        try:
            import sys

            override_mod = sys.modules.get("modules.project_manager")
            if override_mod and hasattr(override_mod, "PROJECTS_DIR"):
                base_projects_dir = getattr(override_mod, "PROJECTS_DIR")
            else:
                base_projects_dir = PROJECTS_DIR
        except Exception:
            base_projects_dir = PROJECTS_DIR

        self.root = base_projects_dir / self.slug
        self.scenes_dir = self.root / "scenes"
        self.audio_dir = self.root / "audio"
        self.subtitles_dir = self.root / "subtitles"
        self.output_dir = self.root / "output"
        self.state_path = self.root / "project.json"

        for d in (self.root, self.scenes_dir, self.audio_dir, self.subtitles_dir, self.output_dir):
            d.mkdir(parents=True, exist_ok=True)

        self.state = self._load_or_init_state(title)

    def _load_or_init_state(self, title: str) -> dict:
        if self.state_path.exists():
            return json.loads(self.state_path.read_text())
        state = {
            "title": title,
            "created": time.time(),
            "completed_stages": [],
            "current_stage": STAGES[0],
        }
        self._save(state)
        return state

    def _save(self, state: dict) -> None:
        self.state_path.write_text(json.dumps(state, indent=2))

    def mark_stage_complete(self, stage: str) -> None:
        if stage not in self.state["completed_stages"]:
            self.state["completed_stages"].append(stage)
        remaining = [s for s in STAGES if s not in self.state["completed_stages"]]
        self.state["current_stage"] = remaining[0] if remaining else "done"
        self._save(self.state)

    def is_stage_complete(self, stage: str) -> bool:
        return stage in self.state["completed_stages"]

    def save_script(self, script_data: dict) -> None:
        (self.root / "script.json").write_text(json.dumps(script_data, indent=2))

        narration_lines = "\n\n".join(
            f"Scene {s['scene_number']}: {s['narration']}" for s in script_data["scenes"]
        )
        (self.root / "script.txt").write_text(
            f"{script_data['title']}\n\n{script_data['hook']}\n\n"
            f"{narration_lines}\n\n{script_data['closing_line']}"
        )
        self.mark_stage_complete("script")
