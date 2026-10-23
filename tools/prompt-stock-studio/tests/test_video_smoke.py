"""Offline end-to-end MP4 rendering smoke test."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image
from studio import _ffmpeg_exe, create_video, draw_overlay


class VideoSmokeTest(unittest.TestCase):
    def test_overlay_renders(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "overlay.png"
            draw_overlay(path, 1080, 1920, "Iceland winter", "Drive safely", "BABEL BOOST", "Follow us", 0, 2)
            with Image.open(path) as result:
                self.assertEqual(result.size, (1080, 1920))

    def test_one_scene_generates_mp4_without_pexels_network(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            photo = root / "own_photo.jpg"
            Image.new("RGB", (800, 1200), (42, 89, 115)).save(photo)
            plan = {"title": "Iceland", "scenes": [{"voiceover": "Hello Iceland.", "caption": "Hello Iceland", "search_query": "Iceland"}]}

            def fake_voice(scenes, voice, speech):
                subprocess.run(
                    [_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y",
                     "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
                     "-c:a", "libmp3lame", str(speech)],
                    check=True, capture_output=True,
                )
                return 1.0

            with patch("studio.create_voiceover", fake_voice):
                video, manifest = create_video(
                    plan, pexels_key="", seconds=3, format_name="9:16",
                    preference="Tylko zdjęcia", voice="en-US-GuyNeural",
                    brand="BABEL BOOST", cta="Follow us", destination=root / "output",
                    user_media=[photo],
                )
            self.assertGreater(video.stat().st_size, 10000)
            data = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(data["media"][0]["source_id"], "user:1")


if __name__ == "__main__":
    unittest.main()
