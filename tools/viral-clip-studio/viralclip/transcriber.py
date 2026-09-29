from __future__ import annotations

from pathlib import Path
from typing import Callable

from faster_whisper import WhisperModel

from .models import TranscriptSegment


def transcribe_video(
    video_path: str | Path,
    model_size: str = "small",
    language: str | None = "pl",
    progress_cb: Callable[[float, str], None] | None = None,
) -> tuple[list[TranscriptSegment], str | None]:
    """Transcribe a local media file with faster-whisper."""
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(video_path)

    if progress_cb:
        progress_cb(0.05, "Ładowanie modelu Whisper…")

    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments_iter, info = model.transcribe(
        str(video_path),
        language=language or None,
        vad_filter=True,
        word_timestamps=False,
        beam_size=5,
        condition_on_previous_text=True,
    )

    segments: list[TranscriptSegment] = []
    duration = max(float(getattr(info, "duration", 0.0) or 0.0), 1.0)
    for seg in segments_iter:
        text = (seg.text or "").strip()
        if not text:
            continue
        segments.append(TranscriptSegment(float(seg.start), float(seg.end), text))
        if progress_cb:
            progress_cb(min(0.95, float(seg.end) / duration), f"Transkrypcja: {seg.end:.0f}s")

    if progress_cb:
        progress_cb(1.0, "Transkrypcja gotowa")

    return segments, getattr(info, "language", None)
