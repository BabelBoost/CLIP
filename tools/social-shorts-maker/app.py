from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
import sys
import re

import streamlit as st
import yt_dlp

ROOT = Path(__file__).resolve().parents[1]
VIRAL_STUDIO = ROOT / "viral-clip-studio"
sys.path.insert(0, str(VIRAL_STUDIO))

from viralclip import (  # noqa: E402
    analyze_segments,
    format_time,
    package_clips,
    render_top_clips,
    transcribe_video,
    write_top5_copy,
)


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
    opening_phrase = " ".join(opening_words)
    return " ".join(phrase) in opening_phrase


def editorial_report(candidates, source_url: str | None) -> str:
    lines = [
        "# TikTok @niefiltrowanypl",
        "",
        "Fragmenty 20–35 s. Hooki są propozycjami tekstu ekranowego. Cytat oznaczony niżej pochodzi z transkrypcji i wymaga sprawdzenia z odsłuchem.",
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
            f"**Ocena fragmentu:** {clip.quality_label}",
            "",
            "### Hooki na ekran",
        ])
        for index, item in enumerate(hooks, start=1):
            marker = " **NAJLEPSZY**" if item is best else ""
            text = str(item.get("text", ""))
            words = text.split()
            if len(words) > 9:
                text = " ".join(words[:9]).rstrip(".,;:") + "…"
            lines.append(f"{index}. {text}{marker}")
        lines.extend([
            "",
            f"**Cytat z transkrypcji:** „{clip.quote}”",
            "",
            "### Plan cięć",
            f"1. Otwórz najmocniejszym zdaniem. Początek źródła: {start_link}. Hook na ekranie przez pierwsze 1–3 s.",
            "2. Zachowaj wypowiedź w kolejności. Zostaw krótkie wprowadzenie i zdanie, które uzasadnia główną tezę.",
            f"3. Zakończ przy {end_link}, po pełnej myśli lub naturalnej puencie. Nie dopisuj pytania, jeśli nie wynika z materiału.",
            "",
            "### Napisy z transkrypcji",
        ])
        for cue in clip.subtitles:
            absolute_start = clip.start + float(cue.get("start", 0))
            absolute_end = clip.start + float(cue.get("end", 0))
            lines.append(f"- {format_time(absolute_start)}–{format_time(absolute_end)}: {cue.get('text', '')}")
        lines.extend([
            "",
            "### Komentarz autora, oddzielony od informacji",
            "Moim zdaniem warto wysłuchać całej wypowiedzi, zanim ocenimy ten fragment.",
            "",
            f"### Opis",
            clip.tiktok_description,
            "",
            f"### Hashtagi",
            " ".join(tags),
            "",
            "Sprawdź timecode, cytat i napisy z oryginalnym nagraniem przed publikacją.",
            "",
        ])
    return "\n".join(lines)

st.set_page_config(page_title="Babel Boost Social Shorts Maker", page_icon="✂️", layout="wide")
st.title("Babel Boost Social Shorts Maker")
st.caption("Z długiego filmu do krótkich klipów na TikTok, X, Facebook Reels i YouTube Shorts.")

st.info(
    "Przetwarzaj materiały, które należą do Ciebie albo do których masz zgodę. "
    "Aplikacja nie omija zabezpieczeń ani DRM. Wynik rankingu jest wskazówką, nie obietnicą zasięgu."
)

with st.sidebar:
    st.header("Ustawienia klipów")
    editorial_format = st.selectbox(
        "Format analizy",
        ["TikTok @niefiltrowanypl · 20–35 s", "Uniwersalny short"],
    )
    niefiltrowany_mode = editorial_format.startswith("TikTok")
    language_label = st.selectbox("Język filmu", ["Automatycznie", "Polski", "English", "Íslenska"])
    language = {"Automatycznie": None, "Polski": "pl", "English": "en", "Íslenska": "is"}[language_label]
    whisper_model = st.selectbox("Model transkrypcji", ["base", "small", "medium"], index=1)
    content_label = st.selectbox("Rodzaj materiału", ["Ogólny", "Polityka / publicystyka"])
    content_mode = "public_affairs" if niefiltrowany_mode or content_label.startswith("Polityka") else "general"
    clip_count = st.slider("Maksymalna liczba klipów", 1, 5, 5)
    min_score = st.slider("Minimalny Viral Score", 40, 85, 55)
    targets = st.multiselect(
        "Platformy do przygotowania",
        ["TikTok", "X", "Facebook Reels", "YouTube Shorts"],
        default=["TikTok", "X", "Facebook Reels", "YouTube Shorts"],
    )
    burn_subtitles = st.checkbox("Wypal napisy w klipach", value=True)
    show_hook = st.checkbox("Pokaż hook na początku", value=True)
    dynamic_subtitles = st.checkbox("Dynamiczne napisy", value=True)
    auto_zoom = st.checkbox("Kadruj na mówcę", value=True)
    trim_silence = st.checkbox("Wycinaj dłuższe cisze", value=True)

if niefiltrowany_mode:
    st.caption("Tryb @niefiltrowanypl szuka samodzielnych fragmentów 20–35 s i zachowuje neutralne, wierne źródłu copy.")

source_kind = st.radio(
    "Źródło filmu",
    ["Link YouTube", "Prześlij plik"],
    horizontal=True,
)
youtube_url = ""
uploaded = None
if source_kind == "Link YouTube":
    youtube_url = st.text_input("Link do filmu", placeholder="https://www.youtube.com/watch?v=...")
    st.caption("Obsługiwane są publiczne linki YouTube dostępne bez omijania zabezpieczeń.")
else:
    uploaded = st.file_uploader(
        "Wybierz długi film",
        type=["mp4", "mov", "mkv", "webm", "m4v"],
        help="Maksymalny rozmiar pliku: 1 GB. Film jest przetwarzany lokalnie.",
    )

has_source = uploaded is not None if source_kind == "Prześlij plik" else bool(youtube_url.strip())

if not targets:
    st.warning("Wybierz przynajmniej jedną platformę.")
elif has_source and st.button("ANALIZUJ I UTWÓRZ KLIPY", type="primary", use_container_width=True):
    work = Path(tempfile.mkdtemp(prefix="babel_social_shorts_"))
    input_path: Path | None = None
    source_url: str | None = None
    try:
        if source_kind == "Prześlij plik":
            input_path = work / Path(uploaded.name).name
            uploaded.seek(0)
            with input_path.open("wb") as destination:
                shutil.copyfileobj(uploaded, destination, length=8 * 1024 * 1024)
        else:
            options = {
                "format": "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b",
                "outtmpl": str(work / "%(id)s.%(ext)s"),
                "merge_output_format": "mp4",
                "noplaylist": True,
                "retries": 3,
                "fragment_retries": 3,
                "socket_timeout": 30,
                "quiet": True,
                "no_warnings": True,
            }
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(youtube_url.strip(), download=True)
            if info.get("id"):
                source_url = f"https://www.youtube.com/watch?v={info['id']}"

            video_extensions = {".mp4", ".mkv", ".webm", ".mov", ".m4v"}
            media_files = [
                path for path in work.iterdir()
                if path.is_file()
                and path.suffix.lower() in video_extensions
                and not path.name.endswith((".part", ".ytdl"))
            ]
            extension_priority = {".mp4": 0, ".mkv": 1, ".webm": 2, ".mov": 3, ".m4v": 4}
            media_files.sort(key=lambda path: (extension_priority[path.suffix.lower()], -path.stat().st_size))
            if not media_files:
                raise FileNotFoundError(
                    "YouTube nie zwrócił gotowego pliku wideo. Spróbuj ponownie albo prześlij plik z komputera."
                )
            input_path = media_files[0]

        if not input_path.exists():
            raise FileNotFoundError("Nie udało się przygotować pliku źródłowego.")

        progress = st.progress(0)
        status = st.empty()

        def progress_cb(value: float, message: str) -> None:
            progress.progress(min(35, int(value * 35)))
            status.write(message)

        status.write("Transkrypcja filmu…")
        segments, detected = transcribe_video(
            input_path,
            model_size=whisper_model,
            language=language,
            progress_cb=progress_cb,
        )
        progress.progress(40)
        status.write(f"Analiza fragmentów. Wykryty język: {detected or 'nieznany'}")

        candidates = analyze_segments(
            segments,
            top_n=100 if niefiltrowany_mode else clip_count,
            content_mode=content_mode,
            min_viral_score=float(min_score),
            include_weak=False,
        )
        if niefiltrowany_mode:
            candidates = [
                clip for clip in candidates
                if 20 <= clip.duration <= 35 and quote_opens_clip(clip)
            ][:clip_count]
        if not candidates:
            if niefiltrowany_mode:
                st.warning(
                    "Materiał nie dostarczył wystarczająco mocnego, samodzielnego fragmentu 20–35 s, "
                    "w którym główne zdanie pada na początku. Nie wymuszam wyboru. Możesz obniżyć próg "
                    "albo przełączyć format na uniwersalny short."
                )
            else:
                st.warning("Nie znaleziono fragmentów powyżej wybranego progu. Obniż próg i spróbuj ponownie.")
            st.stop()

        editorial_path = None
        if niefiltrowany_mode:
            editorial_path = work / "TikTok_niefiltrowanypl_plan.md"
            editorial_path.write_text(editorial_report(candidates, source_url), encoding="utf-8")

        output_root = work / "output"
        rendered = []
        for index, clip in enumerate(candidates[:clip_count], start=1):
            status.write(f"Renderowanie klipu {index}/{min(clip_count, len(candidates))}…")
            rendered.extend(render_top_clips(
                input_path,
                [clip],
                output_root / "clips",
                count=1,
                burn_subtitles=burn_subtitles,
                show_hook=show_hook,
                dynamic_subtitles=dynamic_subtitles,
                segments=segments,
                highlight_words=True,
                auto_zoom=auto_zoom,
                trim_silence=trim_silence,
                silence_threshold=0.8,
            ))
            progress.progress(40 + int(index / max(1, min(clip_count, len(candidates))) * 45))

        copy_files = write_top5_copy(candidates[:clip_count], output_root / "copy", count=clip_count)
        platform_copy = output_root / "platform-copy"
        platform_copy.mkdir(parents=True, exist_ok=True)
        extra_files = [] if niefiltrowany_mode else list(copy_files)
        if editorial_path:
            extra_files.append(editorial_path)
        for platform in targets:
            for index, clip in enumerate(candidates[:clip_count], start=1):
                source_copy = Path(copy_files[index - 1]) if index <= len(copy_files) else None
                source_text = source_copy.read_text(encoding="utf-8") if source_copy and source_copy.exists() else ""
                if niefiltrowany_mode:
                    source_text = editorial_report([clip], source_url)
                path = platform_copy / f"clip_{index:02d}_{platform.lower().replace(' ', '-').replace('/', '-')}.txt"
                path.write_text(
                    f"PLATFORMA: {platform}\n"
                    f"KLIP: {index:02d}\n"
                    f"TIMECODE źródła: {source_time_link(source_url, clip.start)}–{source_time_link(source_url, clip.end)}\n"
                    f"HOOK: {clip.hook}\n\n"
                    f"{source_text}\n\n"
                    "Format wideo: pionowy 9:16, 1080×1920. Sprawdź opis i napisy przed publikacją.\n",
                    encoding="utf-8",
                )
                extra_files.append(path)

        zip_path = package_clips(
            rendered,
            output_root / "social_shorts_package.zip",
            extra_files=extra_files,
        )
        st.session_state["shorts_workspace"] = str(work)
        st.session_state["shorts_rendered"] = [str(path) for path in rendered]
        st.session_state["shorts_zip"] = str(zip_path)
        st.session_state["shorts_editorial_report"] = editorial_report(candidates, source_url) if niefiltrowany_mode else ""
        st.session_state["shorts_candidates"] = [
            {
                "rank": clip.rank,
                "start": format_time(clip.start),
                "end": format_time(clip.end),
                "score": round(clip.viral_score),
                "hook": clip.hook,
            }
            for clip in candidates[:clip_count]
        ]
        progress.progress(100)
        status.success("Gotowe. Klipy i teksty platform są w paczce ZIP.")
    except Exception as exc:
        st.error(f"Nie udało się przetworzyć filmu: {exc}")
    finally:
        # Keep successful outputs available for downloads; clean only failed/empty runs.
        if not st.session_state.get("shorts_zip") or not Path(st.session_state["shorts_zip"]).exists():
            shutil.rmtree(work, ignore_errors=True)

if st.session_state.get("shorts_candidates"):
    st.subheader("Propozycje klipów")
    st.dataframe(st.session_state["shorts_candidates"], use_container_width=True, hide_index=True)
    if st.session_state.get("shorts_editorial_report"):
        st.markdown(st.session_state["shorts_editorial_report"])
        st.download_button(
            "Pobierz plan TikToka @niefiltrowanypl",
            st.session_state["shorts_editorial_report"].encode("utf-8"),
            file_name="TikTok_niefiltrowanypl_plan.md",
            mime="text/markdown",
            key="niefiltrowany-plan-download",
        )
    for index, value in enumerate(st.session_state.get("shorts_rendered", []), start=1):
        path = Path(value)
        if path.exists():
            st.markdown(f"**Klip {index}**")
            st.video(str(path))
            st.download_button(
                f"Pobierz klip {index}",
                path.read_bytes(),
                file_name=path.name,
                mime="video/mp4",
                key=f"social-clip-{index}",
                use_container_width=True,
            )
    zip_value = st.session_state.get("shorts_zip")
    if zip_value and Path(zip_value).exists():
        st.download_button(
            "POBIERZ PACZKĘ KLIPÓW I OPISÓW",
            Path(zip_value).read_bytes(),
            file_name="social_shorts_package.zip",
            mime="application/zip",
            type="primary",
            use_container_width=True,
        )

st.caption("Wszystkie klipy są renderowane pionowo 9:16. Każdy portal ma własny plik copy do sprawdzenia przed publikacją.")
