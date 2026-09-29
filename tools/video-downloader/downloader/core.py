import os
from pathlib import Path
from urllib.parse import urlparse

SUPPORTED_HOSTS = {
    "youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be",
    "x.com", "www.x.com", "mobile.x.com",
    "twitter.com", "www.twitter.com", "mobile.twitter.com",
    "facebook.com", "www.facebook.com", "m.facebook.com",
    "fb.watch", "www.fb.watch",
}

QUALITY_FORMATS = {
    "Najlepsza dostępna": "bv*+ba/b",
    "1080p": "bv*[height<=1080]+ba/b[height<=1080]/b",
    "720p": "bv*[height<=720]+ba/b[height<=720]/b",
    "480p": "bv*[height<=480]+ba/b[height<=480]/b",
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


def human_size(num_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    value = float(num_bytes)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{num_bytes} B"


def cookie_option(browser: str):
    if browser == "Bez logowania":
        return None
    return (browser.lower(),)


def build_ydl_options(output_dir: str, mode: str, quality: str, browser: str):
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
        })

    return opts


def find_output_file(folder: str) -> Path | None:
    files = [
        p for p in Path(folder).iterdir()
        if p.is_file() and not p.name.endswith((".part", ".ytdl"))
    ]
    if not files:
        return None

    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0]
