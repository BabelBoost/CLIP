from __future__ import annotations

import shutil
import subprocess
import zipfile
from pathlib import Path

from .models import ClipCandidate


def _srt_time(seconds: float) -> str:
    ms = max(0, int(round(seconds * 1000)))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, milli = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{milli:03d}"


def _ass_time(seconds: float) -> str:
    cs = max(0, int(round(seconds * 100)))
    h, rem = divmod(cs, 360_000)
    m, rem = divmod(rem, 6_000)
    s, centi = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{centi:02d}"


def _ass_escape(text: str) -> str:
    return (
        str(text)
        .replace("\\", r"\\")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("\n", r"\N")
        .strip()
    )


def _chunks(text: str, words_per_chunk: int = 3) -> list[str]:
    words = str(text).split()
    return [" ".join(words[i : i + words_per_chunk]) for i in range(0, len(words), words_per_chunk)]


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


def write_dynamic_ass(
    clip: ClipCandidate,
    path: str | Path,
    show_hook: bool = True,
    words_per_chunk: int = 3,
) -> Path:
    """Create TikTok-style ASS captions with a 3-second hook and short caption bursts."""
    path = Path(path)
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes
WrapStyle: 2

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Hook,Arial,62,&H00FFFFFF,&H00FFFFFF,&H00000000,&H78000000,-1,0,0,0,100,100,0,0,3,3,0,8,80,80,170,1
Style: Caption,Arial,58,&H00FFFFFF,&H00FFFFFF,&H00000000,&H50000000,-1,0,0,0,100,100,0,0,3,3,0,2,90,90,245,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    events: list[str] = []

    if show_hook and clip.hook:
        hook_end = min(3.0, max(0.8, clip.duration))
        events.append(
            f"Dialogue: 1,{_ass_time(0)},{_ass_time(hook_end)},Hook,,0,0,0,,{_ass_escape(clip.hook)}"
        )

    for item in clip.subtitles:
        start = max(0.0, float(item.get("start", 0.0)))
        end = min(clip.duration, float(item.get("end", start + 0.4)))
        if end <= start:
            continue
        parts = _chunks(str(item.get("text", "")), max(1, words_per_chunk))
        if not parts:
            continue
        step = (end - start) / len(parts)
        for idx, part in enumerate(parts):
            part_start = start + idx * step
            part_end = end if idx == len(parts) - 1 else start + (idx + 1) * step
            if part_end - part_start < 0.12:
                part_end = min(clip.duration, part_start + 0.12)
            events.append(
                f"Dialogue: 0,{_ass_time(part_start)},{_ass_time(part_end)},Caption,,0,0,0,,{_ass_escape(part)}"
            )

    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8-sig")
    return path


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def _vertical_filter(ass_name: str | None = None) -> str:
    base = (
        "[0:v]split=2[bg][fg];"
        "[bg]scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,gblur=sigma=24[bg2];"
        "[fg]scale=1080:1920:force_original_aspect_ratio=decrease[fg2];"
        "[bg2][fg2]overlay=(W-w)/2:(H-h)/2"
    )
    if ass_name:
        base += f",ass='{ass_name}'"
    return base + "[v]"


def render_clip(
    video_path: str | Path,
    clip: ClipCandidate,
    output_dir: str | Path,
    burn_subtitles: bool = True,
    show_hook: bool = True,
    dynamic_subtitles: bool = True,
) -> Path:
    if not ffmpeg_available():
        raise RuntimeError("Nie znaleziono FFmpeg w PATH. Zainstaluj FFmpeg i uruchom aplikację ponownie.")

    video_path = Path(video_path).resolve()
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    stem = f"clip_{clip.rank:02d}_{int(clip.start):06d}_{int(clip.end):06d}"
    ass_name: str | None = None

    if burn_subtitles:
        if dynamic_subtitles:
            ass_name = f"{stem}.ass"
            write_dynamic_ass(clip, out / ass_name, show_hook=show_hook)
        else:
            srt_name = f"{stem}.srt"
            write_srt(clip, out / srt_name)
            ass_name = None

    target = out / f"{stem}_tiktok.mp4"

    if burn_subtitles and not dynamic_subtitles:
        vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
        vf += (
            f",subtitles='{srt_name}':force_style="
            "'FontName=Arial,FontSize=18,Bold=1,Outline=2,Shadow=0,Alignment=2,MarginV=170'"
        )
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-ss", f"{clip.start:.3f}", "-i", str(video_path), "-t", f"{clip.duration:.3f}",
            "-vf", vf,
            "-r", "30", "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(target),
        ]
    else:
        filter_complex = _vertical_filter(ass_name if burn_subtitles else None)
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-ss", f"{clip.start:.3f}", "-i", str(video_path), "-t", f"{clip.duration:.3f}",
            "-filter_complex", filter_complex,
            "-map", "[v]", "-map", "0:a?",
            "-r", "30", "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(target),
        ]

    subprocess.run(cmd, check=True, cwd=str(out))
    return target


def render_top_clips(
    video_path: str | Path,
    candidates: list[ClipCandidate],
    output_dir: str | Path,
    count: int = 5,
    burn_subtitles: bool = True,
    show_hook: bool = True,
    dynamic_subtitles: bool = True,
) -> list[Path]:
    rendered: list[Path] = []
    for clip in candidates[: max(0, count)]:
        rendered.append(
            render_clip(
                video_path,
                clip,
                output_dir,
                burn_subtitles=burn_subtitles,
                show_hook=show_hook,
                dynamic_subtitles=dynamic_subtitles,
            )
        )
    return rendered


def package_clips(paths: list[str | Path], zip_path: str | Path) -> Path:
    zip_path = Path(zip_path)
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in paths:
            item = Path(path)
            archive.write(item, arcname=item.name)
    return zip_path
