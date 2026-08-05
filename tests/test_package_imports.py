import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modules.project_manager import Project, slugify
from modules.script_generator import ScriptRequest, _extract_json, _validate, generate_script


class PackageImportTests(unittest.TestCase):
    def test_slugify(self) -> None:
        self.assertEqual(slugify("My Story!"), "my-story")

    def test_extract_json_handles_fenced_output(self) -> None:
        text = "```json\n{\"title\": \"Example\"}\n```"
        self.assertEqual(_extract_json(text), {"title": "Example"})

    def test_validate_flags_missing_scene_keys(self) -> None:
        data = {
            "title": "Example",
            "hook": "Hook",
            "character_description": "A hero",
            "scenes": [{"scene_number": 1, "narration": "Hi"}],
            "closing_line": "Bye",
        }
        problems = _validate(data)
        self.assertTrue(any("expected 6-10 scenes" in p for p in problems))

    def test_project_creates_expected_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            import modules.project_manager as project_manager_module

            original_projects_dir = project_manager_module.PROJECTS_DIR
            project_manager_module.PROJECTS_DIR = Path(tmp_dir)
            try:
                project = Project("Test Story")
                self.assertTrue((project.root / "project.json").exists())
                self.assertTrue((project.root / "script.json").exists() is False)
            finally:
                project_manager_module.PROJECTS_DIR = original_projects_dir

    def test_generate_script_uses_configured_timeout(self) -> None:
        request = ScriptRequest(
            idea="A test story",
            story_type="emotional",
            visual_style="watercolor",
            duration_seconds=45,
            character_description="A curious child",
        )
        valid_json = '{"title":"Example","hook":"Hook","character_description":"A curious child","scenes":[{"scene_number":1,"narration":"One","image_prompt":"A curious child","duration_seconds":5},{"scene_number":2,"narration":"Two","image_prompt":"A curious child","duration_seconds":5},{"scene_number":3,"narration":"Three","image_prompt":"A curious child","duration_seconds":5},{"scene_number":4,"narration":"Four","image_prompt":"A curious child","duration_seconds":5},{"scene_number":5,"narration":"Five","image_prompt":"A curious child","duration_seconds":5},{"scene_number":6,"narration":"Six","image_prompt":"A curious child","duration_seconds":5}],"closing_line":"Bye"}'

        class FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict:
                return {"message": {"content": valid_json}}

        with patch("script_generator.requests.post") as mock_post:
            mock_post.return_value = FakeResponse()
            generate_script(request)

        self.assertEqual(mock_post.call_args.kwargs["timeout"], 600)


if __name__ == "__main__":
    unittest.main()
