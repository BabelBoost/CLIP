import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SilenceInterval:
    start: float
    end: float

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


@dataclass
class SpeechSegment:
    start: float
    end: float
    text: str


def parse_silencedetect_output(stderr: str) -> list[SilenceInterval]:
    starts = []
    intervals: list[SilenceInterval] = []
    for line in (stderr or "").splitlines():
        start_match = re.search(r"silence_start:\s*([0-9.]+)", line)
        if start_match:
            starts.append(float(start_match.group(1)))
            continue

        end_match = re.search(r"silence_end:\s*([0-9.]+)", line)
        if end_match and starts:
            start = starts.pop(0)
            end = float(end_match.group(1))
            if end > start:
                intervals.append(SilenceInterval(start, end))
    return intervals


def detect_silences(
    input_path: str | Path,
    noise_db: float = -35.0,
    min_duration: float = 0.45,
) -> list[SilenceInterval]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg nie jest zainstalowany lub nie znajduje się w PATH.")

    command = [
        ffmpeg,
        "-hide_banner",
        "-i", str(input_path),
        "-af", f"silencedetect=noise={noise_db}dB:d={min_duration}",
        "-f", "null",
        "-",
    ]
    process = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    return parse_silencedetect_output(process.stderr)


def overlap_duration(start: float, end: float, intervals: list[SilenceInterval]) -> float:
    total = 0.0
    for interval in intervals:
        left = max(start, interval.start)
        right = min(end, interval.end)
        if right > left:
            total += right - left
    return total


def speech_ratio(start: float, end: float, silences: list[SilenceInterval]) -> float:
    duration = max(0.0, end - start)
    if duration <= 0:
        return 0.0
    silent = min(duration, overlap_duration(start, end, silences))
    return max(0.0, min(1.0, 1.0 - silent / duration))


def srt_timestamp(seconds: float) -> str:
    milliseconds = max(0, int(round(float(seconds) * 1000)))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def write_srt(segments: list[SpeechSegment], output_path: str | Path) -> Path:
    target = Path(output_path)
    blocks = []
    for index, segment in enumerate(segments, start=1):
        text = " ".join((segment.text or "").strip().split())
        if not text:
            continue
        blocks.append(
            f"{index}\n{srt_timestamp(segment.start)} --> {srt_timestamp(segment.end)}\n{text}\n"
        )
    target.write_text("\n".join(blocks), encoding="utf-8")
    return target


def transcribe_video(
    input_path: str | Path,
    output_path: str | Path | None = None,
    language: str = "auto",
    model_size: str = "base",
) -> tuple[list[SpeechSegment], dict, Path]:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError(
            "Brakuje Faster-Whisper. Uruchom ponownie run_windows.bat, aby doinstalować zależności 3.1."
        ) from exc

    source = Path(input_path)
    target = Path(output_path) if output_path else source.with_name(f"{source.stem}_auto.srt")
    selected_language = None if language in {"", "auto", "Auto"} else language

    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    raw_segments, info = model.transcribe(
        str(source),
        language=selected_language,
        vad_filter=True,
        beam_size=5,
    )

    segments = [
        SpeechSegment(float(segment.start), float(segment.end), segment.text.strip())
        for segment in raw_segments
        if (segment.text or "").strip()
    ]
    write_srt(segments, target)

    metadata = {
        "language": getattr(info, "language", selected_language or "unknown"),
        "language_probability": float(getattr(info, "language_probability", 0.0) or 0.0),
        "model": model_size,
        "segments": len(segments),
    }
    return segments, metadata, target


def transcript_for_window(
    segments: list[SpeechSegment],
    start: float,
    end: float,
    max_chars: int = 260,
) -> str:
    text = " ".join(
        segment.text.strip()
        for segment in segments
        if segment.end > start and segment.start < end and segment.text.strip()
    )
    text = " ".join(text.split())
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 1)].rstrip() + "…"


def clip_segments(
    segments: list[SpeechSegment],
    start: float,
    end: float,
) -> list[SpeechSegment]:
    clipped: list[SpeechSegment] = []
    for segment in segments:
        left = max(start, segment.start)
        right = min(end, segment.end)
        if right <= left:
            continue
        clipped.append(
            SpeechSegment(
                start=left - start,
                end=right - start,
                text=segment.text,
            )
        )
    return clipped


def write_clip_srt(
    segments: list[SpeechSegment],
    start: float,
    end: float,
    output_path: str | Path,
) -> Path:
    return write_srt(clip_segments(segments, start, end), output_path)


def escape_subtitle_filter_path(path: str | Path) -> str:
    value = str(Path(path).resolve()).replace("\\", "/")
    value = value.replace(":", r"\:")
    value = value.replace("'", r"\'")
    return value


def burn_subtitle_filter(path: str | Path) -> str:
    escaped = escape_subtitle_filter_path(path)
    style = "FontName=Arial,FontSize=22,Outline=2,Shadow=0,Alignment=2,MarginV=105"
    return f"subtitles='{escaped}':force_style='{style}'"
