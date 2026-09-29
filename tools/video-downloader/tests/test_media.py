from pathlib import Path

from downloader.media import build_tiktok_filter, tiktok_output_path


def test_tiktok_filter_targets_vertical_full_hd():
    video_filter = build_tiktok_filter()
    assert "1080:1920" in video_filter
    assert "boxblur" in video_filter
    assert "overlay" in video_filter


def test_tiktok_output_path():
    source = Path("example.mp4")
    assert tiktok_output_path(source).name == "example_tiktok_9x16.mp4"
