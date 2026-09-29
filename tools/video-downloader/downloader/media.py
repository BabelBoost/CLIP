import shutil
import subprocess
from pathlib import Path


def build_tiktok_filter() -> str:
    """Create a 1080x1920 layout with blurred background and centered source."""
    return (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,boxblur=20:10[bg];"
        "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease[fg];"
        "[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[v]"
    )


def tiktok_output_path(input_path: str | Path) -> Path:
    source = Path(input_path)
    return source.with_name(f"{source.stem}_tiktok_9x16.mp4")


def prepare_tiktok_9x16(input_path: str | Path, output_path: str | Path | None = None) -> Path:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg nie jest zainstalowany lub nie znajduje się w PATH.")

    source = Path(input_path)
    target = Path(output_path) if output_path else tiktok_output_path(source)

    command = [
        ffmpeg,
        "-y",
        "-i", str(source),
        "-filter_complex", build_tiktok_filter(),
        "-map", "[v]",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        str(target),
    ]

    process = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if process.returncode != 0:
        error_tail = process.stderr[-1800:] if process.stderr else "Nieznany błąd FFmpeg."
        raise RuntimeError(f"FFmpeg nie przygotował wersji 9:16.\n{error_tail}")

    if not target.exists():
        raise RuntimeError("FFmpeg zakończył pracę, ale plik wynikowy nie powstał.")

    return target
