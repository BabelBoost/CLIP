from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .models import ClipCandidate


def _srt_time(seconds: float) -> str:
    ms = max(0, int(round(seconds * 1000)))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, milli = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{milli:03d}"


def write_srt(clip: ClipCandidate, path: str | Path) -> Path:
    path = Path(path)
    lines: list[str] = []
    for i, item in enumerate(clip.subtitles, start=1):
        lines.extend([
            str(i),
            f"{_srt_time(float(item['start']))} --> {_srt_time(float(item['end']))}",
            str(item["text"]),
            "",
        ])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def render_clip(video_path: str | Path, clip: ClipCandidate, output_dir: str | Path, burn_subtitles: bool = True) -> Path:
    if not ffmpeg_available():
        raise RuntimeError("Nie znaleziono FFmpeg w PATH. Zainstaluj FFmpeg i uruchom aplikację ponownie.")

    video_path = Path(video_path).resolve()
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    stem = f"clip_{clip.rank:02d}_{int(clip.start):06d}_{int(clip.end):06d}"
    srt_name = f"{stem}.srt"
    write_srt(clip, out / srt_name)
    target = out / f"{stem}_9x16.mp4"

    vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
    if burn_subtitles and clip.subtitles:
        vf += (
            f",subtitles='{srt_name}':force_style="
            "'FontName=Arial,FontSize=18,Bold=1,Outline=2,Shadow=0,Alignment=2,MarginV=170'"
        )

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(video_path),
        "-ss", f"{clip.start:.3f}",
        "-t", f"{clip.duration:.3f}",
        "-vf", vf,
        "-r", "30",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        str(target),
    ]
    subprocess.run(cmd, check=True, cwd=str(out))
    return target
