"""Offline stock provider and fallback tests without real API credentials."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stock_providers import _pixabay_json, search_pixabay, StockSearchError
from studio import StudioError, search_stock, _allowed_stock_host


class StockProviderTests(unittest.TestCase):
    def test_pixabay_photo_search(self):
        hits = [{"id": 44, "imageWidth": 1080, "imageHeight": 1920,
                 "largeImageURL": "https://pixabay.com/get/123_1280.jpg",
                 "user": "Sample", "pageURL": "https://pixabay.com/photos/example-44/"}]
        with TemporaryDirectory() as folder:
            with patch("stock_providers._pixabay_json", return_value={"hits": hits}):
                result = search_pixabay("Iceland", "testkey", "9:16", "Grafiki i ilustracje",
                                        set(), Path(folder))
        self.assertEqual(result["provider"], "Pixabay")
        self.assertEqual(result["credit"], "Sample")

    def test_pixabay_video_search(self):
        hits = [{"id": 12, "pageURL": "https://pixabay.com/videos/id-12/",
                 "videos": {"medium": {"url": "https://cdn.pixabay.com/video/12_medium.mp4",
                                      "width": 1280, "height": 720, "size": 5000}}, "user": "Creator"}]
        with TemporaryDirectory() as folder:
            with patch("stock_providers._pixabay_json", return_value={"hits": hits}):
                result = search_pixabay("snow", "testkey", "16:9", "Tylko wideo", set(), Path(folder))
        self.assertEqual(result["kind"], "video")

    def test_24h_response_cache(self):
        data = {"hits": []}
        response = Mock(ok=True, status_code=200)
        response.json.return_value = data
        with TemporaryDirectory() as folder, patch("stock_providers.requests.get", return_value=response) as get:
            path = Path(folder)
            one = _pixabay_json("https://pixabay.com/api/", "my-private-key",
                               {"q": "ice"}, path)
            two = _pixabay_json("https://pixabay.com/api/", "my-private-key",
                               {"q": "ice"}, path)
            self.assertEqual(one, two)
            self.assertEqual(get.call_count, 1)
            cached = list(path.glob("*.json"))
            self.assertEqual(len(cached), 1)
            self.assertNotIn("my-private-key", cached[0].read_text())

    def test_stock_fallback(self):
        pixabay = {"id": "pixabay:photo:1", "provider": "Pixabay", "kind": "photo"}
        with patch("studio.search_media", side_effect=StudioError("Nie znaleziono materiału Pexels dla frazy: snow")), \
             patch("studio.search_pixabay", return_value=pixabay):
            result = search_stock("snow", "pexels", "pixabay", "9:16", "Tylko zdjęcia", set())
        self.assertEqual(result["provider"], "Pixabay")

    def test_stock_hosts(self):
        self.assertTrue(_allowed_stock_host("cdn.pixabay.com"))
        self.assertTrue(_allowed_stock_host("videos.pexels.com"))
        self.assertFalse(_allowed_stock_host("evilpexels.com"))
        self.assertFalse(_allowed_stock_host("example.org"))


if __name__ == "__main__":
    unittest.main()
