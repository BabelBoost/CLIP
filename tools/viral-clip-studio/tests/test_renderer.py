from pathlib import Path

from viralclip.models import ClipCandidate
from viralclip.renderer import package_clips, write_dynamic_ass


def sample_clip() -> ClipCandidate:
    return ClipCandidate(
        rank=1,
        start=10.0,
        end=30.0,
        duration=20.0,
        quote="To jest najmocniejsze zdanie tego fragmentu.",
        hook="Czy naprawdę to powiedział?",
        screen_text="Mocna wypowiedź",
        reason="Samodzielny fragment.",
        viral_score=82,
        hook_score=88,
        emotion_score=70,
        comment_potential=84,
        retention_score=80,
        context_dependency=18,
        emotion="ciekawość",
        suggested_length=30,
        cut_before="start",
        cut_after="end",
        subtitles=[
            {"start": 0.0, "end": 4.0, "text": "Pierwsze krótkie zdanie do napisów"},
            {"start": 4.0, "end": 8.0, "text": "Drugie zdanie ma kilka słów więcej"},
        ],
        tiktok_description="Opis",
        hashtags=["#tiktok"],
        cta="Co o tym myślisz?",
        topic="test",
        text="Pełny tekst fragmentu",
    )


def test_dynamic_ass_contains_hook_and_caption_chunks(tmp_path: Path):
    path = write_dynamic_ass(sample_clip(), tmp_path / "captions.ass", show_hook=True, words_per_chunk=3)
    content = path.read_text(encoding="utf-8-sig")
    assert "Style: Hook" in content
    assert "Style: Caption" in content
    assert "Czy naprawdę to powiedział?" in content
    assert "Pierwsze krótkie zdanie" in content
    assert content.count("Dialogue:") >= 5


def test_dynamic_ass_can_hide_hook(tmp_path: Path):
    path = write_dynamic_ass(sample_clip(), tmp_path / "captions.ass", show_hook=False)
    content = path.read_text(encoding="utf-8-sig")
    assert "Czy naprawdę to powiedział?" not in content
    assert "Pierwsze krótkie zdanie" in content


def test_package_clips_creates_zip(tmp_path: Path):
    a = tmp_path / "clip1.mp4"
    b = tmp_path / "clip2.mp4"
    a.write_bytes(b"one")
    b.write_bytes(b"two")
    target = package_clips([a, b], tmp_path / "top5.zip")
    assert target.exists()
    assert target.stat().st_size > 0
