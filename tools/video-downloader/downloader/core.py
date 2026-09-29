import os
import re
from pathlib import Path
from urllib.parse import urlparse

SUPPORTED_HOSTS = {
    "youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be",
    "x.com", "www.x.com", "mobile.x.com",
    "twitter.com", "www.twitter.com", "mobile.twitter.com",
    "facebook.com", "www.facebook.com", "m.facebook.com",
    "fb.watch", "www.fb.watch",
}

# Prefer MP4 video + M4A/AAC audio first. This combination is the most reliable
# for playback on Windows and avoids MP4 files containing an audio codec that
# some players treat as silent. If a source does not expose M4A, yt-dlp falls
# back to the best separate video/audio pair and finally to a combined format.
QUALITY_FORMATS = {
    "Najlepsza dostępna": (
        "bv[ext=mp4]+ba[ext=m4a]/"
        "bv+ba/"
        "b[ext=mp4]/b"
    ),
    "1080p": (
        "bv[height<=1080][ext=mp4]+ba[ext=m4a]/"
        "bv[height<=1080]+ba/"
        "b[height<=1080][ext=mp4]/"
        "b[height<=1080]/b"
    ),
    "720p": (
        "bv[height<=720][ext=mp4]+ba[ext=m4a]/"
        "bv[height<=720]+ba/"
        "b[height<=720][ext=mp4]/"
        "b[height<=720]/b"
    ),
    "480p": (
        "bv[height<=480][ext=mp4]+ba[ext=m4a]/"
        "bv[height<=480]+ba/"
        "b[height<=480][ext=mp4]/"
        "b[height<=480]/b"
    ),
}

MEDIA_EXTENSIONS = {
    ".mp4", ".mkv", ".webm", ".mov", ".m4v",
    ".mp3", ".m4a", ".aac", ".opus", ".ogg", ".wav",
}


def normalize_host(host: str) -> str:
    return (host or "").lower().split(":")[0]


def is_supported_url(url: str) -> bool:
    try:
        parsed = urlparse(url.strip())
        return (
            parsed.scheme in {"http", "https"}
            and normalize_host(parsed.netloc) in SUPPORTED_HOSTS
        )
    except Exception:
        return False


def parse_urls(text: str) -> list[str]:
    """Extract, clean and deduplicate supported-looking HTTP(S) links."""
    candidates = re.findall(r"https?://[^\s]+", text or "")
    cleaned = []
    seen = set()
    for candidate in candidates:
        url = candidate.rstrip(",.;)]}>\"'")
        if url not in seen:
            seen.add(url)
            cleaned.append(url)
    return cleaned


def human_size(num_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    value = float(num_bytes)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{num_bytes} B"


def format_duration(seconds) -> str:
    try:
        seconds = int(seconds or 0)
    except (TypeError, ValueError):
        return ""
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def cookie_option(browser: str):
    if browser == "Bez logowania":
        return None
    return (browser.lower(),)


def build_info_options(browser: str):
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "skip_download": True,
    }
    cookies = cookie_option(browser)
    if cookies:
        opts["cookiesfrombrowser"] = cookies
    return opts


def parse_subtitle_languages(value: str) -> list[str]:
    languages = [item.strip() for item in (value or "").split(",") if item.strip()]
    return languages or ["pl", "en"]


def build_ydl_options(
    output_dir: str,
    mode: str,
    quality: str,
    browser: str,
    *,
    subtitles: bool = False,
    subtitle_languages: list[str] | None = None,
    thumbnail: bool = False,
    progress_hook=None,
):
    opts = {
        "outtmpl": os.path.join(output_dir, "%(title).180B [%(id)s].%(ext)s"),
        "noplaylist": True,
        "restrictfilenames": False,
        "windowsfilenames": True,
        "quiet": True,
        "no_warnings": True,
        "continuedl": True,
        "retries": 3,
        "fragment_retries": 3,
    }

    cookies = cookie_option(browser)
    if cookies:
        opts["cookiesfrombrowser"] = cookies

    if progress_hook:
        opts["progress_hooks"] = [progress_hook]

    if subtitles:
        opts.update({
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": subtitle_languages or ["pl", "en"],
            "subtitlesformat": "srt/vtt/best",
        })

    if thumbnail:
        opts["writethumbnail"] = True

    if mode == "MP3":
        opts.update({
            "format": "ba/b",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        })
    else:
        opts.update({
            "format": QUALITY_FORMATS[quality],
            "merge_output_format": "mp4",
            "audio_multistreams": False,
            "video_multistreams": False,
        })

    return opts


def list_output_files(folder: str) -> list[Path]:
    files = [
        p for p in Path(folder).iterdir()
        if p.is_file() and not p.name.endswith((".part", ".ytdl", ".temp"))
    ]
    files.sort(key=lambda p: (p.suffix.lower(), p.name.lower()))
    return files


def find_primary_media(folder: str) -> Path | None:
    files = [
        p for p in list_output_files(folder)
        if p.suffix.lower() in MEDIA_EXTENSIONS
        and "_tiktok_9x16" not in p.stem.lower()
        and "_smartclip_" not in p.stem.lower()
    ]
    if not files:
        return None

    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0]


def find_output_file(folder: str) -> Path | None:
    """Backward-compatible alias used by v1 code and tests."""
    return find_primary_media(folder)
