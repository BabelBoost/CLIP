import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch

from bs4 import BeautifulSoup
from PIL import Image

from commons_stock import _cc0_photo, _file_pages
from offline_studio import (StudioError, _tokens, choose_local, create_video,
                            make_original_graphic, make_plan, validate_plan)


class NoApiTests(unittest.TestCase):
    def test_script_without_api(self):
        p = make_plan("Iceland winter road trip", "English", 30, "Follow BabelBoost.com")
        self.assertGreaterEqual(len(p["scenes"]),3)
        self.assertTrue(p["scenes"][0]["voiceover"])
        self.assertNotIn("key",p)

    def test_plan_validator(self):
        with self.assertRaises(StudioError):
            validate_plan({"scenes":[]})

    def test_local_stock_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            Image.new("RGB",(600,1000),"navy").save(folder/"iceland_winter_road.jpg")
            Image.new("RGB",(600,1000),"green").save(folder/"cooking_dinner.jpg")
            hit=choose_local("winter road iceland",folder,set())
            self.assertEqual(hit.name,"iceland_winter_road.jpg")

    def test_generated_original_graphic(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest=Path(tmp)/"image.jpg"
            make_original_graphic(dest,"aurora iceland",1,(540,960))
            with Image.open(dest) as img:
                self.assertEqual(img.size,(540,960))

    def test_commons_requires_cc0(self):
        by=BeautifulSoup('<a href="https://creativecommons.org/licenses/by/4.0/"></a>'
                         '<meta property="og:image" content="https://upload.wikimedia.org/a.jpg">',"html.parser")
        self.assertIsNone(_cc0_photo(by,"https://commons.wikimedia.org/wiki/File:A"))
        cc0=BeautifulSoup('<a href="https://creativecommons.org/publicdomain/zero/1.0/"></a>'
                          '<meta property="og:image" content="https://upload.wikimedia.org/a.jpg">',"html.parser")
        self.assertEqual(_cc0_photo(cc0,"https://commons.wikimedia.org/wiki/File:B")[1]["license"],"CC0 1.0")

    def test_commons_page_extraction(self):
        parsed=BeautifulSoup('<div class="mw-search-result-heading">'
                             '<a href="/wiki/File:Snow.jpg">Snow</a></div>',"html.parser")
        self.assertEqual(len(_file_pages(parsed)),1)

    def test_render_without_network_api_and_no_voice(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            stock=root/"stock"
            stock.mkdir()
            Image.new("RGB",(640,1000),(30,80,130)).save(stock/"iceland_winter.jpg")
            plan={"title":"Iceland winter","scenes":[
                {"voiceover":"Hello Iceland","caption":"Travel Iceland","search_query":"iceland winter"},
                {"voiceover":"Beautiful mountain","caption":"Be prepared","search_query":"mountain"}]}
            with patch("commons_stock.search_commons_image", side_effect=AssertionError("No web required")):
                video,manifest=create_video(
                    plan,stock_folder=stock,output_dir=root/"out",
                    duration=4,quality="540p",with_voice=False,
                    search_commons=False,
                )
            self.assertGreater(video.stat().st_size,10000)
            meta=json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(meta["media"][0]["media"],"Lokalny stock")
            self.assertEqual(meta["media"][1]["media"],"Grafika oryginalna")
            self.assertTrue((root/"out"/"credits.txt").exists())


if __name__ == "__main__":
    unittest.main()
