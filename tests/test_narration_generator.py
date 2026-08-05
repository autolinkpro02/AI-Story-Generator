import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modules.project_manager import Project
from modules.narration_generator import generate_narration_audio


class NarrationGeneratorTests(unittest.TestCase):
    def test_generate_narration_audio_creates_audio_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Project("Narration Test")
            project.root = Path(tmp_dir) / project.slug
            project.root.mkdir(parents=True, exist_ok=True)
            project.audio_dir = project.root / "audio"
            project.audio_dir.mkdir(parents=True, exist_ok=True)
            project.state_path = project.root / "project.json"

            script_data = {
                "title": "Narration Test",
                "hook": "Hook",
                "character_description": "A brave child",
                "scenes": [
                    {"scene_number": 1, "narration": "First scene", "image_prompt": "A brave child in a forest", "duration_seconds": 5},
                    {"scene_number": 2, "narration": "Second scene", "image_prompt": "A brave child by a river", "duration_seconds": 5},
                ],
                "closing_line": "The end",
            }

            def fake_try_gtts(text: str, output_path: Path) -> bool:
                output_path.write_bytes(b"fake-audio")
                return True

            with patch("modules.narration_generator._try_gtts", side_effect=fake_try_gtts):
                output_files = generate_narration_audio(project, script_data)

            self.assertEqual(len(output_files), 2)
            self.assertTrue(all(path.exists() for path in output_files))
            self.assertTrue(all(path.suffix in {".mp3", ".wav"} for path in output_files))


if __name__ == "__main__":
    unittest.main()
