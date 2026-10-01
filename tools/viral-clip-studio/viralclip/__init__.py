from .analyzer import analyze_segments, enrich_with_ollama, format_time
from .models import ClipCandidate, TranscriptSegment
from .renderer import (
    build_speech_ranges,
    package_clips,
    remap_words,
    render_clip,
    render_top_clips,
    words_for_clip,
    write_dynamic_ass,
    write_social_copy,
    write_top5_copy,
)
from .report import render_markdown, save_reports


def transcribe_video(*args, **kwargs):
    from .transcriber import transcribe_video as _transcribe_video
    return _transcribe_video(*args, **kwargs)


__all__ = [
    "analyze_segments",
    "enrich_with_ollama",
    "format_time",
    "ClipCandidate",
    "TranscriptSegment",
    "render_clip",
    "render_top_clips",
    "package_clips",
    "write_dynamic_ass",
    "words_for_clip",
    "build_speech_ranges",
    "remap_words",
    "write_social_copy",
    "write_top5_copy",
    "render_markdown",
    "save_reports",
    "transcribe_video",
]
