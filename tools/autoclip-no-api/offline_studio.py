"""AutoClip Offline: no API keys or paid cloud services required."""
from __future__ import annotations

import json
import math
import random
import re
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1080, 1920
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".m4v"}
KEYWORDS = {
    "iceland": ("islandia", "island", "icelandic", "reykjavik", "landscape"),
    "winter": ("zima", "snow", "snowy", "ice", "icy", "frost"),
    "volcano": ("wulkan", "lava", "eruption", "grindavik", "reyjkanes"),
    "road": ("droga", "car", "drive", "route", "trip"),
    "food": ("jedzenie", "cook", "kitchen", "meal", "recipe"),
    "book": ("ebook", "books", "reading", "kindle"),
    "aurora": ("northern", "lights", "zorza"),
    "travel": ("podroz", "tourism", "adventure", "trip"),
}
STOP = {"the", "this", "with", "about", "your", "from", "that", "film", "video", "short",
        "create", "make", "oraz", "jest", "ktory", "ktora", "przez", "stwor", "stworz",
        "filmu", "klip", "klipu", "będzie", "ktore"}


class StudioError(RuntimeError):
    pass


def _normal(text: str) -> str:
    import unicodedata
    text = unicodedata.normalize("NFKD", text.casefold())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _tokens(text: str) -> set[str]:
    tokens = {word for word in _normal(text).split() if len(word) > 2 and word not in STOP}
    expanded = set(tokens)
    for key, variants in KEYWORDS.items():
        words = {key, *variants}
        if tokens.intersection(words):
            expanded |= words
    return expanded


def make_plan(prompt: str, language: str, seconds: int, cta: str,
              use_local_ai: bool = False, model: str = "llama3.2:3b") -> dict:
    prompt = prompt.strip()
    if not prompt:
        raise StudioError("Wpisz prompt z tematem filmu.")
    if use_local_ai:
        executable = shutil.which("ollama")
        if not executable:
            raise StudioError("Nie znaleziono Ollama. Wyłącz AI lokalne lub zainstaluj Ollama i model.")
        prompt_for_ai = (
            "Return ONLY valid JSON with keys title and scenes. scenes is a list of 4 to 7 "
            "objects, each with voiceover, caption, search_query. Write in " + language +
            ". Stock search_query should be 2-5 English words. "
            "Keep the narration accurate, avoid inventing facts, news, quotes or figures. "
            "First scene must be a strong hook. Final scene must have this CTA: " + cta +
            ". Total around " + str(int(seconds * (2.0 if language == "Polski" else 2.2))) +
            " spoken words. Topic: " + prompt[:3500]
        )
        try:
            response = subprocess.run([executable, "run", model, prompt_for_ai],
                                      capture_output=True, text=True, timeout=150, check=True)
            text = response.stdout.strip()
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if not match:
                raise ValueError("Brak struktury JSON")
            return validate_plan(json.loads(match.group(0)))
        except (subprocess.SubprocessError, ValueError, json.JSONDecodeError) as exc:
            raise StudioError("Ollama nie przygotowała scenariusza. Sprawdź pobrany model: " + str(exc)[:160]) from exc

    # Deterministic offline storyboard. The program does not pretend this is AI narration.
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", prompt[:3000]) if len(s.strip()) > 4]
    subject = sentences[0][:110].strip(". ")
    if len(sentences) >= 3:
        parts = sentences[:6]
    else:
        if language == "Polski":
            parts = [
                "Co naprawdę wiesz o: " + subject + "?",
                "Temat dzisiejszego filmu: " + subject + ".",
                "Przyjrzyj się temu uważnie i sprawdź szczegóły w wiarygodnych źródłach.",
                cta or "Obserwuj po kolejne materiały.",
            ]
        else:
            parts = [
                "What do you really know about " + subject + "?",
                "Today's topic: " + subject + ".",
                "Take a closer look and check reliable sources for the details.",
                cta or "Follow for more.",
            ]
    if len(sentences) >= 3 and cta:
        parts.append(cta)
    keywords = [s for s in sorted(_tokens(subject), key=len, reverse=True) if len(s) > 3][:5]
    visual = " ".join(keywords) or "nature abstract background"
    scenes = [{"voiceover": item, "caption": item[:90], "search_query": visual}
              for item in parts[:8]]
    return {"title": subject, "scenes": scenes, "mode": "template"}


def validate_plan(plan: dict) -> dict:
    if not isinstance(plan, dict) or not isinstance(plan.get("scenes"), list):
        raise StudioError("Scenariusz musi zawierać sceny.")
    scenes = []
    for row in plan["scenes"][:9]:
        if not isinstance(row, dict):
            continue
        voice = str(row.get("voiceover", "")).strip()[:700]
        caption = str(row.get("caption", "")).strip()[:120]
        query = str(row.get("search_query", "")).strip()[:160]
        if voice:
            scenes.append({"voiceover": voice, "caption": caption or voice[:85],
                           "search_query": query or str(plan.get("title", "nature"))[:80]})
    if not scenes:
        raise StudioError("Nie ma poprawnych scen.")
    return {"title": str(plan.get("title", "AutoClip")).strip()[:140], "scenes": scenes}


def choose_local(query: str, stock_folder: Path, seen: set[str]) -> Path | None:
    if not stock_folder.exists():
        return None
    candidates = [p for p in stock_folder.rglob("*") if p.is_file() and p.suffix.lower() in EXTENSIONS]
    if not candidates:
        return None
    words = _tokens(query)
    ranked = []
    for p in candidates:
        if str(p.resolve()) in seen:
            continue
        names = _tokens(" ".join(p.with_suffix("").parts[-3:]))
        common = len(words & names)
        score = common * 10 + (2 if p.suffix.lower() in {".mp4", ".mov", ".m4v"} else 0)
        if common:
            ranked.append((score, p))
    if not ranked:
        # Choose a generic landscape only when the user has explicitly provided stock.
        generic = [p for p in candidates if str(p.resolve()) not in seen]
        if not generic:
            return None
        selected = sorted(generic, key=lambda p: str(p).lower())[0]
    else:
        selected = sorted(ranked, key=lambda x: (-x[0], str(x[1]).lower()))[0][1]
    seen.add(str(selected.resolve()))
    return selected


def _font(size: int, bold: bool = True):
    choices = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for name in choices:
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, width: int, max_lines: int = 5) -> str:
    lines, current = [], ""
    for word in str(text).split():
        attempt = (current + " " + word).strip()
        if current and draw.textlength(attempt, font=font) > width:
            lines.append(current)
            current = word
        else:
            current = attempt
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] += "…"
    return "\n".join(lines)


def make_original_graphic(target: Path, query: str, scene_index: int,
                          size: tuple[int, int]) -> None:
    """Draw original procedural motion backgrounds. These are not stock photographs."""
    w, h = size
    seed = sum(ord(c) for c in query) + scene_index * 907
    rng = random.Random(seed)
    tokens = _tokens(query)
    warm = bool(tokens & {"food", "cook", "recipe", "cooking", "jedzenie"})
    tones = ((28, 16, 29), (141, 53, 37)) if warm else ((7, 25, 48), (29, 97, 100))
    img = Image.new("RGB", size)
    draw = ImageDraw.Draw(img)
    for y in range(h):
        mix = y / max(1, h - 1)
        rgb = tuple(int(tones[0][k] * (1 - mix) + tones[1][k] * mix) for k in range(3))
        draw.line((0, y, w, y), fill=rgb)
    # Luminous ribbons, stars and mountain-like shapes create an original graphic.
    for i in range(65):
        x = rng.randint(0, w - 1)
        y = rng.randint(0, int(h * .65))
        r = rng.randint(1, max(2, w // 180))
        draw.ellipse((x-r, y-r, x+r, y+r), fill=(172, 224, 231))
    for layer in range(4):
        y = int(h * (0.57 + layer * .09))
        points = [(0, h), (0, y)]
        for x in range(0, w + 80, max(40, w // 12)):
            points.append((x, y + rng.randint(-int(h * .12), int(h * .11))))
        points.append((w, h))
        fill = (14 + layer * 10, 37 + layer * 10, 61 + layer * 8)
        draw.polygon(points, fill=fill)
    draw.ellipse((int(w * .68), int(h * .16), int(w * .84), int(h * .16 + w * .16)),
                 fill=(203, 237, 231))
    img.save(target, quality=91)


def create_overlay(path: Path, size: tuple[int, int], title: str, caption: str,
                   brand: str, index: int, count: int, style: str) -> None:
    w, h = size
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    k = w / 1080
    pad = int(w * .06)
    accent = ((251, 192, 69, 255) if style == "Energetyczny" else (93, 235, 213, 255))
    brand_font = _font(max(13, int(35*k)))
    title_font = _font(max(19, int(56*k)))
    captions = _font(max(22, int(70*k)))
    draw.rounded_rectangle((pad, int(h*.045), w-pad, int(h*.095)), radius=15,
                           fill=(7, 18, 30, 190))
    draw.text((pad+int(20*k), int(h*.055)), brand[:45], font=brand_font, fill=accent)
    if index == 0:
        txt = _wrap(draw, title.upper(), title_font, w - pad*2, 4)
        draw.multiline_text((pad, int(h*.17)), txt, font=title_font, fill="white",
                            stroke_width=max(1, int(3*k)), stroke_fill="#0b1620", spacing=11)
    txt = _wrap(draw, caption, captions, w-pad*2-int(55*k), 4)
    bbox = draw.multiline_textbbox((0,0), txt, font=captions, spacing=int(12*k), align="center")
    text_h = bbox[3]-bbox[1]
    box_h = text_h + int(h*.07)
    top = max(int(h*.63), h-int(h*.18)-box_h)
    draw.rounded_rectangle((pad,top,w-pad,top+box_h),radius=max(8,int(25*k)),
                           fill=(5, 15, 24, 213))
    draw.multiline_text((w/2,top+(box_h-text_h)/2-bbox[1]),txt,font=captions,
                        align="center",anchor="ma",fill="white",spacing=int(12*k))
    draw.text((w-pad,h-int(h*.06)), f"{index+1}/{count}",anchor="ra",
              font=brand_font,fill=accent)
    img.save(path)


def offline_voice(scenes: list[dict], output_dir: Path, voice_hint: str = "") -> list[Path]:
    """Use local Windows SAPI voices. No cloud TTS or API used."""
    try:
        import pyttsx3
        engine = pyttsx3.init()
        voices = engine.getProperty("voices")
        for v in voices:
            labels = (v.id + " " + v.name).lower()
            if voice_hint and voice_hint.lower() in labels:
                engine.setProperty("voice", v.id)
                break
        engine.setProperty("rate", 165)
        result = []
        for index, scene in enumerate(scenes):
            outfile = output_dir / ("speech_" + str(index) + ".wav")
            engine.save_to_file(scene["voiceover"], str(outfile))
            result.append(outfile)
        engine.runAndWait()
        if not all(p.exists() and p.stat().st_size > 44 for p in result):
            raise RuntimeError("Silnik głosowy nie zapisał wszystkich plików.")
        return result
    except Exception as exc:
        raise StudioError("Nie udało się uruchomić lektora offline. "
                          "Zainstaluj głos Windows lub wyłącz lektora: " + str(exc)[:180]) from exc


def _wav_duration(file: Path) -> float:
    with wave.open(str(file), "rb") as f:
        return f.getnframes()/f.getframerate()


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        raise StudioError("FFmpeg: " + result.stderr[-1400:])


def _ffmpeg() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def create_video(plan: dict, *, stock_folder: Path, output_dir: Path, duration: int = 35,
                 quality: str = "1080p", brand: str = "BABEL BOOST",
                 style: str = "Dokumentalny", with_voice: bool = True,
                 voice_hint: str = "", music: Path | None = None,
                 search_commons: bool = False, progress=None) -> tuple[Path, Path]:
    """Render video fully offline; optional Commons HTML search requires internet, no API."""
    from commons_stock import search_commons_image
    plan = validate_plan(plan)
    if quality not in ("1080p", "720p", "540p"):
        raise StudioError("Nieznana jakość renderingu.")
    w = {"1080p":1080,"720p":720,"540p":540}[quality]
    size = (w, round(w*16/9))
    output_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg = _ffmpeg()
    seen = set()
    sources = []
    with tempfile.TemporaryDirectory(prefix="autoclip_no_api_") as folder:
        work = Path(folder)
        speech = offline_voice(plan["scenes"],work,voice_hint) if with_voice else []
        segments = []
        for i, scene in enumerate(plan["scenes"]):
            if progress:
                progress(f"Scena {i+1}/{len(plan['scenes'])}: dobieram obraz, głos i napisy")
            source = choose_local(scene["search_query"] + " " + plan["title"], stock_folder, seen)
            media_source = "Lokalny stock" if source is not None else ""
            source_info = {"creator": "Plik użytkownika", "url": "", "license": "Sprawdź licencję własnego pliku"}
            if source is None and search_commons:
                try:
                    downloaded = search_commons_image(scene["search_query"],work,i,seen)
                    if downloaded:
                        source, source_info = downloaded
                        media_source = "Wikimedia Commons (CC0)"
                except Exception:
                    # Website search is best-effort; never stop the offline renderer.
                    pass
            if source is None:
                source = work / f"original_{i}.jpg"
                make_original_graphic(source,scene["search_query"],i,size)
                media_source = "Grafika oryginalna"
                source_info = {"creator": "Babel Boost AutoClip Studio", "url": "", "license": "Grafika wygenerowana lokalnie"}
            sources.append({"scene":i+1,"media":media_source,"file":source.name,
                            "query":scene["search_query"],**source_info})
            overlay = work/f"caption_{i}.png"
            create_overlay(overlay,size,plan["title"],scene["caption"],brand,
                           i,len(plan["scenes"]),style)
            voice_dur = _wav_duration(speech[i]) if speech else 0
            sec = max(duration/len(plan["scenes"]),voice_dur+0.45,2.3)
            video = work/f"clip_{i:03d}.mp4"
            is_video = source.suffix.lower() in {".mp4",".mov",".m4v"}
            media_args = ["-stream_loop","-1","-i",str(source)] if is_video else [
                "-loop","1","-framerate","30","-i",str(source)]
            voice_args = ["-i",str(speech[i])] if speech else [
                "-f","lavfi","-i","anullsrc=r=44100:cl=mono"]
            # Keep the overlays as PNG and encode each scene at the same dimensions.
            filters = (f"[0:v]scale={size[0]}:{size[1]}:force_original_aspect_ratio=increase,"
                       f"crop={size[0]}:{size[1]},setsar=1,fps=30[background];"
                       "[background][1:v]overlay=0:0:shortest=1,format=yuv420p[v]")
            _run([ffmpeg,"-hide_banner","-loglevel","error","-y",*media_args,
                  "-loop","1","-framerate","30","-i",str(overlay),*voice_args,
                  "-filter_complex",filters,"-map","[v]","-map","2:a",
                  "-af","apad","-t",f"{sec:.3f}","-c:v","libx264","-preset","veryfast",
                  "-crf","22","-pix_fmt","yuv420p","-r","30","-c:a","aac",
                  "-ar","44100","-ac","1",str(video)])
            segments.append(video)
        concat = work/"inputs.txt"
        concat.write_text("".join("file '"+p.name+"'\n" for p in segments), encoding="utf-8")
        master = work/"master.mp4"
        _run([ffmpeg,"-hide_banner","-loglevel","error","-y","-f","concat","-safe","0",
              "-i",str(concat),"-c","copy",str(master)])
        output = output_dir/"AutoClip_No_API.mp4"
        if music and music.is_file():
            _run([ffmpeg,"-hide_banner","-loglevel","error","-y","-i",str(master),
                  "-stream_loop","-1","-i",str(music),
                  "-filter_complex","[0:a]volume=1[a];[1:a]volume=0.12[b];"
                  "[a][b]amix=inputs=2:duration=first[out]",
                  "-map","0:v","-map","[out]","-c:v","copy","-c:a","aac",
                  "-shortest","-movflags","+faststart",str(output)])
        else:
            shutil.copy2(master,output)
    manifest = output_dir/"sources.json"
    manifest.write_text(json.dumps({"title":plan["title"],"scenes":plan["scenes"],
                                    "media":sources,"api_keys_needed":False,
                                    "warning":"Review factual claims and rights before posting"},
                                    ensure_ascii=False,indent=2),encoding="utf-8")
    credit_lines = ["Materiały wideo: Babel Boost AutoClip Studio",""]
    for entry in sources:
        credit_lines.append(
            f"Scena {entry['scene']}: {entry['media']} | {entry['creator']} | "
            f"{entry['license']} | {entry['url']}"
        )
    (output_dir/"credits.txt").write_text("\n".join(credit_lines),encoding="utf-8")
    if progress:
        progress("Film gotowy.")
    return output, manifest
