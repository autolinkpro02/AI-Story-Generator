import unittest

from web_app import parse_story_form


class WebAppTests(unittest.TestCase):
    def test_parse_story_form_collects_inputs(self) -> None:
        payload = {
            "idea": ["A child finds courage"],
            "story_type": ["motivational"],
            "visual_style": ["storybook watercolor"],
            "duration": ["20"],
            "character_description": ["A brave child"],
            "title": ["Brave Child"],
        }

        parsed = parse_story_form(payload)

        self.assertEqual(parsed["idea"], "A child finds courage")
        self.assertEqual(parsed["story_type"], "motivational")
        self.assertEqual(parsed["duration_seconds"], 20)
        self.assertEqual(parsed["character_description"], "A brave child")
        self.assertEqual(parsed["title"], "Brave Child")


if __name__ == "__main__":
    unittest.main()
