from downloader.core import (
    build_ydl_options,
    find_primary_media,
    human_size,
    is_supported_url,
    parse_subtitle_languages,
    parse_urls,
)


def test_supported_urls():
    assert is_supported_url("https://www.youtube.com/watch?v=abc123")
    assert is_supported_url("https://youtu.be/abc123")
    assert is_supported_url("https://x.com/example/status/123")
    assert is_supported_url("https://www.facebook.com/watch/?v=123")


def test_rejects_unsupported_urls():
    assert not is_supported_url("https://example.com/video.mp4")
    assert not is_supported_url("javascript:alert(1)")
    assert not is_supported_url("not-a-url")


def test_parse_urls_deduplicates_and_cleans_punctuation():
    text = """
    https://youtu.be/abc123
    https://x.com/demo/status/1,
    https://youtu.be/abc123
    """
    assert parse_urls(text) == [
        "https://youtu.be/abc123",
        "https://x.com/demo/status/1",
    ]


def test_subtitle_languages():
    assert parse_subtitle_languages("pl, en, is") == ["pl", "en", "is"]
    assert parse_subtitle_languages("") == ["pl", "en"]


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


def test_subtitles_thumbnail_and_progress_hook_options(tmp_path):
    hook = lambda data: None
    options = build_ydl_options(
        str(tmp_path),
        mode="Wideo MP4",
        quality="1080p",
        browser="Bez logowania",
        subtitles=True,
        subtitle_languages=["pl", "en"],
        thumbnail=True,
        progress_hook=hook,
    )
    assert options["writesubtitles"] is True
    assert options["writeautomaticsub"] is True
    assert options["subtitleslangs"] == ["pl", "en"]
    assert options["writethumbnail"] is True
    assert options["progress_hooks"] == [hook]


def test_find_primary_media_ignores_thumbnail_and_tiktok_copy(tmp_path):
    (tmp_path / "film.webp").write_bytes(b"thumb")
    (tmp_path / "film_tiktok_9x16.mp4").write_bytes(b"vertical")
    source = tmp_path / "film.mp4"
    source.write_bytes(b"source")
    assert find_primary_media(str(tmp_path)) == source
