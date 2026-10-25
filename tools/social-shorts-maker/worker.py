from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
import traceback
from pathlib import Path

import yt_dlp

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "viral-clip-studio"))

from viralclip import (  # noqa: E402
    analyze_segments,
    format_time,
    package_clips,
    render_top_clips,
    transcribe_video,
    write_top5_copy,
)


def read_state(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_state(path: Path, state: dict) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def set_status(state_path: Path, state: dict, status: str, message: str, progress: int | None = None, **extra) -> None:
    state.update(status=status, message=message, updated_at=time.time())
    if progress is not None:
        state["progress"] = max(0, min(100, int(progress)))
    state.update(extra)
    write_state(state_path, state)


def source_time_link(source_url: str | None, seconds: float) -> str:
    label = format_time(seconds)
    if not source_url:
        return label
    separator = "&" if "?" in source_url else "?"
    return f"[{label}]({source_url}{separator}t={max(0, int(seconds))}s)"


def quote_opens_clip(clip) -> bool:
    opening = " ".join(
        item.get("text", "")
        for item in clip.subtitles
        if float(item.get("start", 0)) <= 4.0
    ).lower()
    quote_words = re.findall(r"[\w’']+", clip.quote.lower(), flags=re.UNICODE)
    opening_words = re.findall(r"[\w’']+", opening, flags=re.UNICODE)
    if not quote_words or not opening_words:
        return False
    phrase = quote_words[: min(5, len(quote_words))]
    return " ".join(phrase) in " ".join(opening_words)


def editorial_report(candidates, source_url: str | None) -> str:
    lines = [
        "# TikTok @niefiltrowanypl",
        "",
        "Fragmenty 20–35 s. Hooki są propozycjami tekstu ekranowego. Cytat pochodzi z transkrypcji; sprawdź go z odsłuchem.",
        "",
    ]
    for clip in candidates:
        start_link = source_time_link(source_url, clip.start)
        end_link = source_time_link(source_url, clip.end)
        hooks = clip.hook_variants[:3]
        best = next((item for item in hooks if item.get("text") == clip.hook), None)
        if best is None and hooks:
            best = max(hooks, key=lambda item: float(item.get("score", 0)))
        tags = list(dict.fromkeys(clip.hashtags))[:4]
        for fallback in ["#niefiltrowanypl", "#polityka", "#publicystyka", "#dyskusja"]:
            if len(tags) >= 4:
                break
            if fallback not in tags:
                tags.append(fallback)

        lines.extend([
            f"## Klip {clip.rank} | Viral Score {clip.viral_score:.0f}/100",
            "",
            f"**Początek:** {start_link}  ",
            f"**Koniec:** {end_link}  ",
            f"**Długość:** {clip.duration:.1f} s  ",
            f"**Ocena:** {clip.quality_label}",
            "",
            "### Hooki na ekran",
        ])
        for index, item in enumerate(hooks, start=1):
            text = str(item.get("text", ""))
            words = text.split()
            if len(words) > 9:
                text = " ".join(words[:9]).rstrip(".,;:") + "…"
            marker = " **NAJLEPSZY**" if item is best else ""
            lines.append(f"{index}. {text}{marker}")

        lines.extend([
            "",
            f"**Cytat z transkrypcji:** „{clip.quote}”",
            "",
            "### Plan cięć",
            f"1. Otwórz najmocniejszym zdaniem. Źródło zaczyna się przy {start_link}. Hook ekranowy przez 1–3 s.",
            "2. Zachowaj kolejność wypowiedzi. Zostaw krótkie wprowadzenie i zdanie, które potwierdza główną myśl.",
            f"3. Zakończ przy {end_link}, po pełnej myśli lub naturalnej puencie. Nie dopisuj pytania, jeśli nie wynika z materiału.",
            "",
            "### Napisy z transkrypcji",
        ])
        for cue in clip.subtitles:
            begin = clip.start + float(cue.get("start", 0))
            end = clip.start + float(cue.get("end", 0))
            lines.append(f"- {format_time(begin)}–{format_time(end)}: {cue.get('text', '')}")
        lines.extend([
            "",
            "### Komentarz autora, oddzielony od informacji",
            "Moim zdaniem warto wysłuchać całej wypowiedzi, zanim ocenimy ten fragment.",
            "",
            "### Opis",
            clip.tiktok_description,
            "",
            "### Hashtagi",
            " ".join(tags),
            "",
            "Sprawdź timecode, cytat i napisy z oryginalnym nagraniem przed publikacją.",
            "",
        ])
    return "\n".join(lines)


def run_job(job_dir: Path) -> None:
    state_path = job_dir / "job.json"
    state = read_state(state_path)
    source_url = None
    try:
        set_status(state_path, state, "running", "Przygotowanie źródła filmu…", 2)
        if state["source_kind"] == "upload":
            input_path = Path(state["upload_path"])
            if not input_path.is_file():
                raise FileNotFoundError("Nie znaleziono przesłanego pliku.")
        else:
            download_dir = job_dir / "download"
            download_dir.mkdir(exist_ok=True)
            last_percent = [-1]

            def download_progress(data):
                if data.get("status") == "downloading":
                    total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
                    done = data.get("downloaded_bytes") or 0
                    fraction = min(1.0, done / total) if total else 0.0
                    percent = 2 + int(fraction * 12)
                    if percent > last_percent[0]:
                        last_percent[0] = percent
                        set_status(state_path, state, "running", "Pobieranie filmu z YouTube…", percent)
                elif data.get("status") == "finished":
                    set_status(state_path, state, "running", "Scalanie pobranego filmu…", 15)

            options = {
                "format": "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b",
                "outtmpl": str(download_dir / "%(id)s.%(ext)s"),
                "merge_output_format": "mp4",
                "noplaylist": True,
                "retries": 3,
                "fragment_retries": 3,
                "socket_timeout": 30,
                "quiet": True,
                "no_warnings": True,
                "progress_hooks": [download_progress],
            }
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(state["youtube_url"].strip(), download=True)
            if info.get("id"):
                source_url = f"https://www.youtube.com/watch?v={info['id']}"

            valid_extensions = {".mp4", ".mkv", ".webm", ".mov", ".m4v"}
            candidates = [
                path for path in download_dir.iterdir()
                if path.is_file() and path.suffix.lower() in valid_extensions
                and not path.name.endswith((".part", ".ytdl"))
            ]
            priority = {".mp4": 0, ".mkv": 1, ".webm": 2, ".mov": 3, ".m4v": 4}
            candidates.sort(key=lambda path: (priority[path.suffix.lower()], -path.stat().st_size))
            if not candidates:
                raise FileNotFoundError("YouTube nie zwrócił gotowego filmu. Sprawdź link albo prześlij plik.")
            input_path = candidates[0]

        set_status(state_path, state, "running", "Transkrypcja filmu…", 16)
        language = state.get("language") or None

        def transcription_progress(value: float, message: str) -> None:
            percent = 16 + int(min(1.0, max(0.0, value)) * 43)
            set_status(state_path, state, "running", message, percent)

        segments, detected = transcribe_video(
            input_path,
            model_size=state["whisper_model"],
            language=language,
            progress_cb=transcription_progress,
        )
        set_status(state_path, state, "running", f"Analiza fragmentów. Język: {detected or 'nieznany'}", 61)

        niefiltrowany = bool(state["niefiltrowany_mode"])
        candidates = analyze_segments(
            segments,
            top_n=100 if niefiltrowany else int(state["clip_count"]),
            content_mode=state["content_mode"],
            min_viral_score=float(state["min_score"]),
            include_weak=False,
        )
        if niefiltrowany:
            candidates = [c for c in candidates if 20 <= c.duration <= 35 and quote_opens_clip(c)]
            candidates = candidates[: int(state["clip_count"])]
        if not candidates:
            if niefiltrowany:
                message = (
                    "Nie znaleziono wystarczająco mocnego, samodzielnego fragmentu 20–35 s, "
                    "w którym główne zdanie pada na początku. Spróbuj obniżyć próg lub wybrać format uniwersalny."
                )
            else:
                message = "Nie znaleziono fragmentów powyżej ustawionego progu Viral Score."
            set_status(state_path, state, "no_clips", message, 100)
            return

        output_root = job_dir / "output"
        output_root.mkdir(exist_ok=True)
        extras = []
        if niefiltrowany:
            report_path = output_root / "TikTok_niefiltrowanypl_plan.md"
            report_path.write_text(editorial_report(candidates, source_url), encoding="utf-8")
            extras.append(report_path)
        else:
            copy_files = write_top5_copy(
                candidates[: int(state["clip_count"])],
                output_root / "copy",
                count=int(state["clip_count"]),
            )
            extras.extend(copy_files)

        clips_dir = output_root / "clips"
        rendered = []
        total = min(int(state["clip_count"]), len(candidates))
        for index, clip in enumerate(candidates[:total], start=1):
            set_status(state_path, state, "running", f"Renderowanie klipu {index}/{total}…", 62 + int((index - 1) / total * 28))
            rendered.extend(render_top_clips(
                input_path,
                [clip],
                clips_dir,
                count=1,
                burn_subtitles=bool(state["burn_subtitles"]),
                show_hook=bool(state["show_hook"]),
                dynamic_subtitles=bool(state["dynamic_subtitles"]),
                segments=segments,
                highlight_words=True,
                auto_zoom=bool(state["auto_zoom"]),
                trim_silence=bool(state["trim_silence"]),
                silence_threshold=0.8,
            ))

        if niefiltrowany:
            platform_dir = output_root / "platform-copy"
            platform_dir.mkdir(exist_ok=True)
            report_text = editorial_report(candidates[:total], source_url)
            for platform in state["targets"]:
                safe_platform = re.sub(r"[^a-z0-9]+", "-", platform.lower()).strip("-")
                target = platform_dir / f"{safe_platform}_niefiltrowanypl.md"
                target.write_text(report_text, encoding="utf-8")
                extras.append(target)

        zip_path = package_clips(
            rendered,
            output_root / "social_shorts_package.zip",
            extra_files=extras,
        )
        candidate_rows = [
            {
                "rank": clip.rank,
                "start": format_time(clip.start),
                "end": format_time(clip.end),
                "duration": round(clip.duration, 1),
                "score": round(clip.viral_score),
                "quality": clip.quality_label,
                "hook": clip.hook,
            }
            for clip in candidates[:total]
        ]
        report_path = str(output_root / "TikTok_niefiltrowanypl_plan.md") if niefiltrowany else None
        set_status(
            state_path,
            state,
            "complete",
            "Gotowe. Klipy, timecode’y i opisy są zapisane w paczce.",
            100,
            candidates=candidate_rows,
            rendered_files=[str(path) for path in rendered],
            zip_path=str(zip_path),
            report_path=report_path,
            source_url=source_url,
        )
    except Exception as exc:
        with (job_dir / "worker.log").open("a", encoding="utf-8") as log_file:
            traceback.print_exc(file=log_file)
        set_status(state_path, state, "error", str(exc), 100)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-dir", required=True)
    run_job(Path(parser.parse_args().job_dir))
