"""Babel Boost AutoClip Studio: prompt-to-stock-video engine."""
from __future__ import annotations

import asyncio
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import requests
from PIL import Image, ImageDraw, ImageFont
from mutagen.mp3 import MP3
from stock_providers import StockSearchError, search_pixabay


PEXELS_API = "https://api.pexels.com/v1"
PEXELS_VIDEO_API = "https://api.pexels.com/v1/videos"
SIZES = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080)}
MAX_BYTES = 150 * 1024 * 1024


class StudioError(RuntimeError):
    pass


def _clean(value: object, limit: int = 1000) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def fallback_plan(prompt: str, language: str, seconds: int, cta: str) -> dict:
    """A transparent non-AI draft for use without a paid AI key."""
    topic = _clean(prompt, 140)
    if not topic:
        raise StudioError("Wpisz temat filmu.")
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", _clean(prompt, 2500)) if p.strip()]
    if len(parts) < 3:
        if language == "Polski":
            parts = [
                "Co naprawdę warto wiedzieć o: " + topic + "?",
                "Przyjrzyjmy się temu tematowi z bliska.",
                "Sprawdź źródła i szczegóły, zanim wyciągniesz wnioski.",
                cta or "Obserwuj po więcej.",
            ]
        else:
            parts = [
                "What should you know about " + topic + "?",
                "Let's take a closer look at the story.",
                "Check the sources and details before drawing conclusions.",
                cta or "Follow for more.",
            ]
    return {
        "title": topic[:90],
        "scenes": [
            {
                "voiceover": part,
                "caption": part[:90],
                "search_query": re.sub(r"[^\w\s-]", "", topic, flags=re.UNICODE)[:90],
            }
            for part in parts[:7]
        ],
        "planning": "Szablon bez AI. Popraw tekst przed renderowaniem.",
    }


def ai_plan(prompt: str, language: str, seconds: int, cta: str, api_key: str, model: str = "gpt-4.1-mini") -> dict:
    if not api_key:
        return fallback_plan(prompt, language, seconds, cta)
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key, timeout=70)
        response = client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You write short, engaging social media videos. Return JSON only: "
                        '{"title":"...","scenes":[{"voiceover":"...","caption":"...","search_query":"..."}]}. '
                        "Write 3 to 7 scenes. Use the requested language for voiceover and caption. "
                        "Use short English visual search queries that work in the Pexels stock library. "
                        "Start with a strong but accurate hook. Finish with the requested CTA. "
                        "Total narration is about " + str(int(seconds * (2.0 if language == "Polski" else 2.25))) + " words. "
                        "Do not make up statistics, quotes, events, citations, locations, or eyewitness footage. "
                        "Never claim stock media shows the actual incident/person or a verified location. "
                        "Stock is illustrative. Keep caption under 75 characters. "
                        "For news, make claims only if explicitly provided by the user; otherwise use cautious questions."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps({"topic_or_prompt": prompt, "language": language, "length_seconds": seconds, "cta": cta}, ensure_ascii=False),
                },
            ],
        )
        raw = json.loads(response.choices[0].message.content or "{}")
        return validate_plan(raw)
    except Exception as exc:
        raise StudioError("Nie udało się przygotować scenariusza AI: " + str(exc)) from exc


def validate_plan(plan: dict) -> dict:
    if not isinstance(plan, dict) or not isinstance(plan.get("scenes"), list):
        raise StudioError("Scenariusz AI ma nieprawidłową strukturę.")
    scenes = []
    for entry in plan["scenes"][:8]:
        if not isinstance(entry, dict):
            continue
        voiceover = _clean(entry.get("voiceover"), 600)
        caption = _clean(entry.get("caption"), 110)
        query = _clean(entry.get("search_query"), 110)
        if voiceover and query:
            scenes.append({"voiceover": voiceover, "caption": caption or voiceover[:85], "search_query": query})
    if not 1 <= len(scenes) <= 8:
        raise StudioError("Scenariusz nie zawiera użytecznych scen.")
    return {"title": _clean(plan.get("title"), 110) or "AutoClip", "scenes": scenes, "planning": plan.get("planning", "AI")}


def _pexels_get(url: str, key: str, params: dict) -> dict:
    try:
        response = requests.get(url, headers={"Authorization": key}, params=params, timeout=25)
        if response.status_code == 429:
            raise StudioError("Pexels: limit zapytań API. Spróbuj później.")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise StudioError("Pexels API: " + str(exc)) from exc


def _video_candidate(data: dict) -> dict | None:
    options = [
        f for f in data.get("video_files", [])
        if (f.get("file_type") == "video/mp4" or str(f.get("link", "")).lower().split("?")[0].endswith(".mp4"))
        and f.get("link") and f.get("width") and f.get("height")
    ]
    if not options:
        return None
    # Prefer practical HD sizes rather than downloading huge 4K files.
    options.sort(key=lambda f: (abs((f["width"] or 1) - 1080) + abs((f["height"] or 1) - 1920), 0 if 720 <= f["width"] <= 1920 else 1))
    media = options[0]
    return {
        "kind": "video", "id": "video:" + str(data.get("id")), "url": media["link"],
        "page": data.get("url", ""), "credit": data.get("user", {}).get("name", "Pexels creator"),
    }


def _photo_candidate(data: dict) -> dict | None:
    src = data.get("src") or {}
    url = src.get("large2x") or src.get("large") or src.get("original")
    if not url:
        return None
    return {
        "kind": "photo", "id": "photo:" + str(data.get("id")), "url": url,
        "page": data.get("url", ""), "credit": data.get("photographer", "Pexels photographer"),
    }


def search_media(query: str, key: str, format_name: str, preference: str, seen: set) -> dict:
    orientation = {"9:16": "portrait", "16:9": "landscape", "1:1": "square"}[format_name]
    attempts = ["video", "photo"] if preference == "Mix wideo i zdjęć" else (
        ["video"] if preference == "Tylko wideo" else ["photo"]
    )
    for kind in attempts:
        for orient in (orientation, None):
            params = {"query": query, "per_page": 12}
            if orient:
                params["orientation"] = orient
            endpoint = PEXELS_VIDEO_API + "/search" if kind == "video" else PEXELS_API + "/search"
            raw = _pexels_get(endpoint, key, params)
            candidates = raw.get("videos", []) if kind == "video" else raw.get("photos", [])
            mapper = _video_candidate if kind == "video" else _photo_candidate
            mapped = [m for item in candidates if (m := mapper(item))]
            unique = next((m for m in mapped if m["id"] not in seen), None)
            if unique:
                seen.add(unique["id"])
                return unique
    raise StudioError("Nie znaleziono materiału Pexels dla frazy: " + query + ". Zmień wyszukiwanie sceny.")


def search_stock(query: str, pexels_key: str, pixabay_key: str, format_name: str,
                 preference: str, seen: set, source: str = "Auto") -> dict:
    """Choose suitable stock from Pexels/Pixabay without silently fabricating visuals."""
    if not (pexels_key or pixabay_key):
        raise StudioError("Podaj klucz Pexels lub Pixabay.")
    if preference == "Grafiki i ilustracje" and not pixabay_key:
        raise StudioError("Grafiki i ilustracje wymagają klucza Pixabay API.")
    providers = (["Pixabay"] if preference == "Grafiki i ilustracje" else
                 ["Pexels", "Pixabay"] if source == "Auto" else [source])
    for provider in providers:
        if provider == "Pexels" and pexels_key:
            try:
                result = search_media(query, pexels_key, format_name, preference, seen)
                result["provider"] = "Pexels"
                return result
            except StudioError as exc:
                if not str(exc).startswith("Nie znaleziono materiału Pexels"):
                    raise
        if provider == "Pixabay" and pixabay_key:
            try:
                result = search_pixabay(query, pixabay_key, format_name, preference, seen,
                                        Path(__file__).resolve().parent / ".cache" / "pixabay")
            except StockSearchError as exc:
                raise StudioError(str(exc)) from exc
            if result:
                return result
    raise StudioError("Brak pasujących materiałów Pexels/Pixabay dla: " + query +
                      ". Zmień frazę sceny lub bibliotekę.")


def _allowed_stock_host(host: str) -> bool:
    return host in {"pexels.com", "pixabay.com"} or any(
        host.endswith("." + suffix) for suffix in ("pexels.com", "pixabay.com", "pixabaycdn.com")
    )


def _safe_download(url: str, path: Path) -> None:
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not _allowed_stock_host(hostname):
        raise StudioError("Niedozwolony adres stock. Wymagany link HTTPS Pexels lub Pixabay.")
    try:
        with requests.get(url, timeout=(12, 90), stream=True, allow_redirects=True) as res:
            res.raise_for_status()
            final = urlparse(res.url)
            host = (final.hostname or "").lower()
            if final.scheme != "https" or not _allowed_stock_host(host):
                raise StudioError("Materiał przekierowuje poza dozwolone domeny stock.")
            if int(res.headers.get("Content-Length", 0)) > MAX_BYTES:
                raise StudioError("Plik stock jest zbyt duży (limit 150 MB).")
            n = 0
            with path.open("wb") as f:
                for chunk in res.iter_content(256 * 1024):
                    n += len(chunk)
                    if n > MAX_BYTES:
                        raise StudioError("Plik stock jest zbyt duży (limit 150 MB).")
                    f.write(chunk)
        if path.stat().st_size < 1000:
            raise StudioError("Pobrany plik multimedialny jest pusty.")
    except requests.RequestException as exc:
        raise StudioError("Pobieranie materiału: " + str(exc)) from exc


def create_voiceover(scenes: list, voice: str, output_path: Path) -> float:
    try:
        import edge_tts

        async def render() -> None:
            communicate = edge_tts.Communicate(
                text=" ".join(scene["voiceover"] for scene in scenes),
                voice=voice,
                rate="+0%",
            )
            await communicate.save(str(output_path))

        asyncio.run(render())
        length = float(MP3(str(output_path)).info.length)
        if length <= 0:
            raise StudioError("Lektor ma pustą ścieżkę audio.")
        return length
    except Exception as exc:
        raise StudioError("Nie udało się wygenerować lektora. Sprawdź połączenie z internetem: " + str(exc)) from exc


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    paths = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
    ]
    for filename in paths:
        if Path(filename).is_file():
            return ImageFont.truetype(filename, size)
    return ImageFont.load_default()


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int, max_lines: int = 5) -> str:
    lines = []
    current = ""
    for word in _clean(text, 350).split():
        trial = (current + " " + word).strip()
        if draw.textlength(trial, font=font) > max_width and current:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(".") + "..."
    return "\n".join(lines)


def draw_overlay(path: Path, width: int, height: int, title: str, caption: str, brand: str, cta: str, index: int, count: int) -> None:
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    factor = min(width / 1080, height / 1920) if height > width else width / 1920
    factor = max(factor, 0.55)
    margin = int(width * 0.065)
    accent = (56, 219, 200, 255)
    draw.rounded_rectangle((margin, int(height * 0.06), margin + int(width * 0.13), int(height * 0.066)), radius=3, fill=accent)
    header_font = _font(max(27, int(42 * factor)), True)
    brand_font = _font(max(20, int(29 * factor)), True)
    caption_font = _font(max(34, int(62 * factor)), True)
    small_font = _font(max(21, int(35 * factor)), True)
    draw.text((margin, int(height * 0.08)), _clean(brand, 55), font=brand_font, fill="white", stroke_width=1, stroke_fill="black")
    if index == 0:
        top = _wrap(draw, title.upper(), header_font, width - margin * 2, 3)
        draw.multiline_text((margin, int(height * 0.15)), top, font=header_font, fill=accent, spacing=10, stroke_width=3, stroke_fill=(0, 0, 0))
    text = cta if index == count - 1 and cta else caption
    wrapped = _wrap(draw, text, caption_font, width - 2 * margin - 40, 4)
    bbox = draw.multiline_textbbox((0, 0), wrapped, font=caption_font, spacing=15, align="center")
    box_h = bbox[3] - bbox[1] + int(height * 0.075)
    top_y = min(int(height * 0.73), height - box_h - int(height * 0.11))
    draw.rounded_rectangle((margin, top_y, width - margin, top_y + box_h), radius=int(25 * factor), fill=(7, 17, 25, 198))
    draw.multiline_text((width / 2, top_y + box_h / 2 - (bbox[3] - bbox[1]) / 2 - bbox[1]),
                        wrapped, font=caption_font, fill="white", spacing=15,
                        anchor="ma", align="center", stroke_width=1, stroke_fill="#08151c")
    draw.text((width - margin, height - int(height * 0.065)),
              str(index + 1) + "/" + str(count), anchor="ra", font=small_font, fill=accent)
    image.save(path)


def _ffmpeg_exe() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def _run(args: list[str], cwd: Path | None = None) -> None:
    result = subprocess.run(args, cwd=str(cwd) if cwd else None, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise StudioError("FFmpeg: " + result.stderr[-2200:])


def _durations(scenes: list, requested: int, audio_duration: float) -> list[float]:
    actual_total = max(float(requested), audio_duration + 0.75, len(scenes) * 2.5)
    weights = [max(3, len(item["voiceover"].split())) for item in scenes]
    baseline = 1.7
    extra = actual_total - baseline * len(scenes)
    return [baseline + extra * w / sum(weights) for w in weights]


def create_video(plan: dict, *, pexels_key: str, seconds: int, format_name: str,
                 preference: str, voice: str, brand: str, cta: str,
                 destination: Path, user_media: list[Path] | None = None,
                 music: Path | None = None, progress=None, pixabay_key: str = "",
                 stock_source: str = "Auto") -> tuple[Path, Path]:
    """Download visual sources and render a complete MP4 with narration and scene captions."""
    plan = validate_plan(plan)
    if format_name not in SIZES:
        raise StudioError("Nieznany format filmu.")
    if not (pexels_key or pixabay_key) and len(user_media or []) < len(plan["scenes"]):
        raise StudioError("Wpisz klucz Pexels/Pixabay albo prześlij własny plik dla każdej sceny.")
    width, height = SIZES[format_name]
    destination.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="autoclip_"))
    ffmpeg = _ffmpeg_exe()
    assets = []
    try:
        if progress:
            progress("Generuję lektora AI...")
        speech = work / "speech.mp3"
        duration_audio = create_voiceover(plan["scenes"], voice, speech)
        timings = _durations(plan["scenes"], seconds, duration_audio)
        seen: set[str] = set()
        segments = []
        for i, (scene, duration) in enumerate(zip(plan["scenes"], timings)):
            if progress:
                progress("Scena " + str(i + 1) + "/" + str(len(plan["scenes"])) + ": dobieram obraz i montuję...")
            if user_media and i < len(user_media):
                source = Path(user_media[i])
                if not source.is_file():
                    raise StudioError("Nie znaleziono przesłanego materiału: " + str(source))
                extension = source.suffix.lower()
                if extension not in {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".m4v"}:
                    raise StudioError("Nieobsługiwany plik: " + source.name)
                asset = {"kind": "video" if extension in {".mp4", ".mov", ".m4v"} else "photo",
                         "id": "user:" + str(i + 1), "page": "", "credit": "Własny materiał"}
                local = source
            else:
                asset = search_stock(scene["search_query"], pexels_key, pixabay_key,
                                     format_name, preference, seen, stock_source)
                local = work / ("stock_" + str(i) + (".mp4" if asset["kind"] == "video" else ".jpg"))
                _safe_download(asset["url"], local)
            assets.append({"scene": i + 1, "query": scene["search_query"], "kind": asset["kind"],
                           "credit": asset["credit"], "source_page": asset["page"], "source_id": asset["id"],
                           "provider": asset.get("provider", "Własny materiał"), "media_type": asset.get("media_type", asset["kind"]),
                           "note": "Materiał ilustracyjny, nie dowód konkretnego zdarzenia."})
            overlay = work / ("overlay_" + str(i) + ".png")
            draw_overlay(overlay, width, height, plan["title"], scene["caption"], brand, cta, i, len(plan["scenes"]))
            output = work / ("segment_" + str(i).zfill(2) + ".mp4")
            source_input = (["-stream_loop", "-1", "-i", str(local)] if asset["kind"] == "video"
                            else ["-loop", "1", "-framerate", "30", "-i", str(local)])
            vf = ("[0:v]scale=" + str(width) + ":" + str(height) +
                  ":force_original_aspect_ratio=increase,crop=" + str(width) + ":" + str(height) +
                  ",setsar=1,fps=30[bg];[bg][1:v]overlay=0:0:shortest=1,format=yuv420p[v]")
            _run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", *source_input,
                  "-loop", "1", "-framerate", "30", "-i", str(overlay),
                  "-filter_complex", vf, "-map", "[v]", "-t", f"{duration:.3f}",
                  "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
                  "-pix_fmt", "yuv420p", "-r", "30", str(output)])
            segments.append(output)
        concat = work / "clips.txt"
        concat.write_text("".join("file '" + p.name + "'\n" for p in segments), encoding="utf-8")
        total = sum(timings)
        out = destination / "autoclip.mp4"
        args = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                "-f", "concat", "-safe", "0", "-i", str(concat),
                "-i", str(speech)]
        if music is not None:
            args += ["-stream_loop", "-1", "-i", str(music)]
            fc = ("[1:a]apad,atrim=duration=" + f"{total:.3f}" + "[voice];"
                  "[2:a]volume=0.12,atrim=duration=" + f"{total:.3f}" + "[music];"
                  "[voice][music]amix=inputs=2:duration=first:dropout_transition=1[a]")
            args += ["-filter_complex", fc, "-map", "0:v", "-map", "[a]"]
        else:
            args += ["-map", "0:v", "-map", "1:a", "-af", "apad"]
        args += ["-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                 "-t", f"{total:.3f}", "-movflags", "+faststart", str(out)]
        if progress:
            progress("Łączę wideo, napisy i dźwięk...")
        _run(args)
        manifest = destination / "sources.json"
        manifest.write_text(json.dumps({
            "title": plan["title"], "scenes": plan["scenes"], "media": assets,
            "requested_seconds": seconds, "actual_seconds_approx": round(total, 2),
            "providers": ["Pexels", "Pixabay"], "licenses": {
                "Pexels": "https://www.pexels.com/license/",
                "Pixabay": "https://pixabay.com/service/license-summary/"},
            "review_before_publication": True,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        if progress:
            progress("Film gotowy.")
        return out, manifest
    finally:
        shutil.rmtree(work, ignore_errors=True)
