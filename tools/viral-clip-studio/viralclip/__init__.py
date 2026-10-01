from .analyzer import analyze_segments, enrich_with_ollama, format_time
from .models import ClipCandidate, TranscriptSegment
from .renderer import package_clips, render_clip, render_top_clips, write_dynamic_ass
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
    "render_markdown",
    "save_reports",
    "transcribe_video",
]
