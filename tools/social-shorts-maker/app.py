from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
import sys

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

st.set_page_config(page_title="Babel Boost Social Shorts Maker", page_icon="✂️", layout="wide")
st.title("Babel Boost Social Shorts Maker")
st.caption("Z długiego filmu do krótkich klipów na TikTok, X, Facebook Reels i YouTube Shorts.")

st.info(
    "Przetwarzaj materiały, które należą do Ciebie albo do których masz zgodę. "
    "Aplikacja nie omija zabezpieczeń ani DRM. Wynik rankingu jest wskazówką, nie obietnicą zasięgu."
)

with st.sidebar:
    st.header("Ustawienia klipów")
    language_label = st.selectbox("Język filmu", ["Automatycznie", "Polski", "English", "Íslenska"])
    language = {"Automatycznie": None, "Polski": "pl", "English": "en", "Íslenska": "is"}[language_label]
    whisper_model = st.selectbox("Model transkrypcji", ["base", "small", "medium"], index=1)
    content_label = st.selectbox("Rodzaj materiału", ["Ogólny", "Polityka / publicystyka"])
    content_mode = "public_affairs" if content_label.startswith("Polityka") else "general"
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
                ydl.extract_info(youtube_url.strip(), download=True)

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
            top_n=clip_count,
            content_mode=content_mode,
            min_viral_score=float(min_score),
            include_weak=False,
        )
        if not candidates:
            st.warning("Nie znaleziono fragmentów powyżej wybranego progu. Obniż próg i spróbuj ponownie.")
            st.stop()

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
        extra_files = list(copy_files)
        for platform in targets:
            for index, clip in enumerate(candidates[:clip_count], start=1):
                source_copy = Path(copy_files[index - 1]) if index <= len(copy_files) else None
                source_text = source_copy.read_text(encoding="utf-8") if source_copy and source_copy.exists() else ""
                path = platform_copy / f"clip_{index:02d}_{platform.lower().replace(' ', '-').replace('/', '-')}.txt"
                path.write_text(
                    f"PLATFORMA: {platform}\n"
                    f"KLIP: {index:02d}\n"
                    f"TIMEcode źródła: {format_time(clip.start)}–{format_time(clip.end)}\n"
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
