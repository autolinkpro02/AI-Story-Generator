import os
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from modules.project_manager import Project
from modules.image_generator import generate_scene_images


class ImageGeneratorTests(unittest.TestCase):
    def test_generate_scene_images_creates_png_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Project("Image Test")
            project.root = Path(tmp_dir) / project.slug
            project.root.mkdir(parents=True, exist_ok=True)
            project.scenes_dir = project.root / "scenes"
            project.scenes_dir.mkdir(parents=True, exist_ok=True)
            project.state_path = project.root / "project.json"

            script_data = {
                "title": "Image Test",
                "hook": "Hook",
                "character_description": "A brave child",
                "scenes": [
                    {"scene_number": 1, "narration": "First scene", "image_prompt": "A brave child in a forest", "duration_seconds": 5},
                    {"scene_number": 2, "narration": "Second scene", "image_prompt": "A brave child by a river", "duration_seconds": 5},
                ],
                "closing_line": "The end",
            }

            output_files = generate_scene_images(project, script_data)

            self.assertEqual(len(output_files), 2)
            self.assertTrue(all(path.exists() for path in output_files))
            self.assertTrue(all(path.suffix == ".png" for path in output_files))

    def test_generate_scene_images_uses_pollinations_when_no_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Project("Image Test")
            project.root = Path(tmp_dir) / project.slug
            project.root.mkdir(parents=True, exist_ok=True)
            project.scenes_dir = project.root / "scenes"
            project.scenes_dir.mkdir(parents=True, exist_ok=True)
            project.state_path = project.root / "project.json"

            script_data = {
                "title": "Image Test",
                "hook": "Hook",
                "character_description": "A brave child",
                "scenes": [
                    {"scene_number": 1, "narration": "First scene", "image_prompt": "A brave child in a forest", "duration_seconds": 5},
                ],
                "closing_line": "The end",
            }

            image_bytes = BytesIO()
            Image.new("RGB", (64, 64), color=(255, 0, 0)).save(image_bytes, format="PNG")

            with patch("modules.image_generator.requests.get") as mock_get, patch.dict(os.environ, {}, clear=True):
                mock_get.return_value.raise_for_status.return_value = None
                mock_get.return_value.content = image_bytes.getvalue()

                output_files = generate_scene_images(project, script_data)

            self.assertTrue(mock_get.called)
            self.assertTrue(output_files[0].exists())

    def test_generate_scene_images_normalizes_jpeg_payloads_to_png(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Project("Image Test")
            project.root = Path(tmp_dir) / project.slug
            project.root.mkdir(parents=True, exist_ok=True)
            project.scenes_dir = project.root / "scenes"
            project.scenes_dir.mkdir(parents=True, exist_ok=True)
            project.state_path = project.root / "project.json"

            script_data = {
                "title": "Image Test",
                "hook": "Hook",
                "character_description": "A brave child",
                "scenes": [
                    {"scene_number": 1, "narration": "First scene", "image_prompt": "A brave child in a forest", "duration_seconds": 5},
                ],
                "closing_line": "The end",
            }

            image_bytes = BytesIO()
            Image.new("RGB", (64, 64), color=(255, 0, 0)).save(image_bytes, format="JPEG")

            with patch("modules.image_generator.requests.get") as mock_get, patch.dict(os.environ, {}, clear=True):
                mock_get.return_value.raise_for_status.return_value = None
                mock_get.return_value.content = image_bytes.getvalue()
                mock_get.return_value.headers = {"content-type": "image/jpeg"}

                output_files = generate_scene_images(project, script_data)

            with Image.open(output_files[0]) as img:
                self.assertEqual(img.format, "PNG")
            self.assertTrue(output_files[0].exists())

    def test_generate_scene_images_uses_huggingface_when_configured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Project("Image Test")
            project.root = Path(tmp_dir) / project.slug
            project.root.mkdir(parents=True, exist_ok=True)
            project.scenes_dir = project.root / "scenes"
            project.scenes_dir.mkdir(parents=True, exist_ok=True)
            project.state_path = project.root / "project.json"

            script_data = {
                "title": "Image Test",
                "hook": "Hook",
                "character_description": "A brave child",
                "scenes": [
                    {"scene_number": 1, "narration": "First scene", "image_prompt": "A brave child in a forest", "duration_seconds": 5},
                ],
                "closing_line": "The end",
            }

            image_bytes = BytesIO()
            Image.new("RGB", (64, 64), color=(255, 0, 0)).save(image_bytes, format="PNG")

            with patch("modules.image_generator.requests.post") as mock_post, patch.dict(os.environ, {"HUGGINGFACE_API_TOKEN": "test-token"}, clear=False):
                mock_post.return_value.raise_for_status.return_value = None
                mock_post.return_value.headers = {"content-type": "image/png"}
                mock_post.return_value.content = image_bytes.getvalue()

                output_files = generate_scene_images(project, script_data)

            self.assertTrue(mock_post.called)
            self.assertTrue(output_files[0].exists())


if __name__ == "__main__":
    unittest.main()
