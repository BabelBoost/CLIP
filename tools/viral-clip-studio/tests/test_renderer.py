from pathlib import Path

import pytest

from viralclip.models import ClipCandidate, TranscriptSegment
from viralclip.renderer import (
    build_speech_ranges,
    package_clips,
    remap_words,
    words_for_clip,
    write_dynamic_ass,
    write_social_copy,
)


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
        share_potential=78,
        context_dependency=18,
        quality_label="DOBRY MATERIAŁ",
        emotion="ciekawość",
        suggested_length=30,
        cut_before="start",
        cut_after="end",
        subtitles=[
            {"start": 0.0, "end": 4.0, "text": "Pierwsze krótkie zdanie do napisów"},
            {"start": 4.0, "end": 8.0, "text": "Drugie zdanie ma kilka słów więcej"},
        ],
        tiktok_description="Opis do publikacji",
        hashtags=["#tiktok", "#test"],
        cta="Co o tym myślisz?",
        topic="test",
        text="Pełny tekst fragmentu",
        hook_variants=[
            {"kind": "pytanie", "text": "Czy naprawdę to powiedział?", "score": 91},
            {"kind": "cytat", "text": "To jest najmocniejsze zdanie.", "score": 84},
            {"kind": "ciekawość", "text": "Co wydarzyło się dalej?", "score": 76},
        ],
        selected_hook_score=91,
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


def test_dynamic_ass_highlights_active_word(tmp_path: Path):
    words = [
        {"start": 0.0, "end": 0.5, "text": "To"},
        {"start": 0.5, "end": 1.0, "text": "jest"},
        {"start": 1.0, "end": 1.5, "text": "ważne"},
    ]
    path = write_dynamic_ass(
        sample_clip(),
        tmp_path / "captions.ass",
        show_hook=False,
        word_timeline=words,
        highlight_words=True,
    )
    content = path.read_text(encoding="utf-8-sig")
    assert r"\c&H0000FFFF&" in content
    assert "To" in content and "ważne" in content
    assert content.count("Dialogue:") == 3


def test_words_for_clip_uses_whisper_word_timestamps():
    clip = sample_clip()
    segments = [
        TranscriptSegment(
            10.0,
            12.0,
            "Ala ma kota",
            words=[
                {"start": 10.0, "end": 10.4, "text": "Ala"},
                {"start": 10.5, "end": 10.8, "text": "ma"},
                {"start": 10.9, "end": 11.4, "text": "kota"},
            ],
        )
    ]
    words = words_for_clip(clip, segments)
    assert words[0]["text"] == "Ala"
    assert words[0]["start"] == pytest.approx(0.0)
    assert words[-1]["end"] == pytest.approx(1.4)


def test_speech_ranges_remove_only_longer_pause():
    clip = sample_clip()
    words = [
        {"start": 0.2, "end": 0.8, "text": "A"},
        {"start": 1.0, "end": 1.4, "text": "B"},
        {"start": 4.0, "end": 4.5, "text": "C"},
    ]
    ranges = build_speech_ranges(clip, words, silence_threshold=0.8, padding=0.1)
    assert len(ranges) == 2
    assert ranges[0][0] == pytest.approx(0.1)
    assert ranges[0][1] == pytest.approx(1.5)
    assert ranges[1][0] == pytest.approx(3.9)


def test_remap_words_closes_removed_gap():
    words = [
        {"start": 0.2, "end": 0.8, "text": "A"},
        {"start": 4.0, "end": 4.5, "text": "B"},
    ]
    ranges = [(0.1, 0.9), (3.9, 4.6)]
    remapped = remap_words(words, ranges)
    assert len(remapped) == 2
    assert remapped[0]["start"] == pytest.approx(0.1)
    assert remapped[1]["start"] == pytest.approx(0.9)


def test_social_copy_contains_description_hashtags_and_cta(tmp_path: Path):
    target = write_social_copy(sample_clip(), tmp_path / "copy.txt")
    content = target.read_text(encoding="utf-8")
    assert "3 WARIANTY HOOKA" in content
    assert "WYNIK HOOKA: 91/100" in content
    assert "<- WYBRANY" in content
    assert "OPIS TIKTOK" in content
    assert "Opis do publikacji" in content
    assert "#tiktok #test" in content
    assert "Co o tym myślisz?" in content


def test_package_clips_creates_zip_with_extra_copy(tmp_path: Path):
    a = tmp_path / "clip1.mp4"
    b = tmp_path / "clip2.mp4"
    copy = tmp_path / "clip1.txt"
    a.write_bytes(b"one")
    b.write_bytes(b"two")
    copy.write_text("copy", encoding="utf-8")
    target = package_clips([a, b], tmp_path / "top5.zip", extra_files=[copy])
    assert target.exists()
    assert target.stat().st_size > 0
