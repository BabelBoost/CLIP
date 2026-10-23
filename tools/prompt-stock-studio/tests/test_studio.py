"""Offline tests for planning and timing helpers."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from studio import StudioError, _durations, fallback_plan, validate_plan


class StudioTests(unittest.TestCase):
    def test_fallback_has_editable_scenes(self):
        result = fallback_plan("Iceland winter road trip", "English", 35, "Follow Babel Boost")
        self.assertTrue(result["scenes"])
        self.assertIn("search_query", result["scenes"][0])

    def test_validates_empty_plan(self):
        with self.assertRaises(StudioError):
            validate_plan({"scenes": []})

    def test_timing_does_not_cut_audio(self):
        scenes = [{"voiceover": "Hello world"} for _ in range(4)]
        self.assertGreaterEqual(sum(_durations(scenes, 15, 24.5)), 25.25)

    def test_text_trim(self):
        result = validate_plan({"title": "Title", "scenes": [{"voiceover": "Hello", "caption": "Look", "search_query": "Iceland"}]})
        self.assertEqual(result["scenes"][0]["caption"], "Look")


if __name__ == "__main__":
    unittest.main()
