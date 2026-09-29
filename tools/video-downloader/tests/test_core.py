from downloader.core import build_ydl_options, human_size, is_supported_url


def test_supported_urls():
    assert is_supported_url("https://www.youtube.com/watch?v=abc123")
    assert is_supported_url("https://youtu.be/abc123")
    assert is_supported_url("https://x.com/example/status/123")
    assert is_supported_url("https://www.facebook.com/watch/?v=123")


def test_rejects_unsupported_urls():
    assert not is_supported_url("https://example.com/video.mp4")
    assert not is_supported_url("javascript:alert(1)")
    assert not is_supported_url("not-a-url")


def test_human_size():
    assert human_size(1024) == "1.0 KB"
    assert human_size(1024 * 1024) == "1.0 MB"


def test_mp3_options_include_ffmpeg_postprocessor(tmp_path):
    options = build_ydl_options(
        str(tmp_path),
        mode="MP3",
        quality="Najlepsza dostępna",
        browser="Bez logowania",
    )
    assert options["format"] == "ba/b"
    assert options["postprocessors"][0]["key"] == "FFmpegExtractAudio"


def test_video_options_respect_quality(tmp_path):
    options = build_ydl_options(
        str(tmp_path),
        mode="Wideo MP4",
        quality="720p",
        browser="Bez logowania",
    )
    assert "height<=720" in options["format"]
    assert options["merge_output_format"] == "mp4"
