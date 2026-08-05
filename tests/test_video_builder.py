import subprocess
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from modules.project_manager import Project
from modules.video_builder import build_video


class VideoBuilderTests(unittest.TestCase):
    def test_build_video_outputs_a_multi_second_mp4(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Project("Video Test")
            project.root = Path(tmp_dir) / project.slug
            project.root.mkdir(parents=True, exist_ok=True)
            project.scenes_dir = project.root / "scenes"
            project.scenes_dir.mkdir(parents=True, exist_ok=True)
            project.audio_dir = project.root / "audio"
            project.audio_dir.mkdir(parents=True, exist_ok=True)
            project.subtitles_dir = project.root / "subtitles"
            project.subtitles_dir.mkdir(parents=True, exist_ok=True)
            project.output_dir = project.root / "output"
            project.output_dir.mkdir(parents=True, exist_ok=True)
            project.state_path = project.root / "project.json"

            for number in (1, 2):
                image_path = project.scenes_dir / f"scene_{number:02d}.png"
                Image.new("RGB", (64, 64), color=(255, 0, 0)).save(image_path)

            script_data = {
                "title": "Video Test",
                "hook": "Hook",
                "character_description": "A brave child",
                "scenes": [
                    {"scene_number": 1, "narration": "First scene", "image_prompt": "A brave child in a forest", "duration_seconds": 3},
                    {"scene_number": 2, "narration": "Second scene", "image_prompt": "A brave child by a river", "duration_seconds": 3},
                ],
                "closing_line": "The end",
            }

            output_files = build_video(project, script_data)
            self.assertTrue(output_files)
            output_path = output_files[0]
            self.assertTrue(output_path.exists())

            ffprobe = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(output_path)],
                check=True,
                capture_output=True,
                text=True,
            )
            duration = float(ffprobe.stdout.strip())
            self.assertGreater(duration, 2.0)


if __name__ == "__main__":
    unittest.main()
