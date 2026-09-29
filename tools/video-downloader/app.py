import mimetypes
import shutil
import tempfile
from dataclasses import asdict
from pathlib import Path

import streamlit as st
import yt_dlp

from downloader import (
    CandidateClip,
    QUALITY_FORMATS,
    SpeechSegment,
    analyze_video_for_clips,
    build_info_options,
    build_ydl_options,
    find_primary_media,
    format_duration,
    human_size,
    is_supported_url,
    list_output_files,
    parse_subtitle_languages,
    parse_urls,
    prepare_tiktok_9x16,
    render_smart_clip,
    transcript_for_window,
    transcribe_video,
    write_analysis_report,
    write_clip_srt,
)

st.set_page_config(
    page_title="Babel Boost Video Downloader 3.1",
    page_icon="🎬",
    layout="wide",
)

if "download_results" not in st.session_state:
    st.session_state.download_results = []
if "previews" not in st.session_state:
    st.session_state.previews = []


def guess_mime(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".mp3":
        return "audio/mpeg"
    if suffix == ".mp4":
        return "video/mp4"
    if suffix == ".srt":
        return "application/x-subrip"
    if suffix == ".vtt":
        return "text/vtt"
    if suffix == ".json":
        return "application/json"
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def file_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    stem = path.stem.lower()
    if "_smartclip_" in stem and suffix == ".mp4":
        return "Smart Clip 9:16"
    if "_smartclip_" in stem and suffix == ".srt":
        return "Napisy Smart Clip"
    if "_tiktok_9x16" in stem:
        return "TikTok 9:16 pełne wideo"
    if "_auto" in stem and suffix == ".srt":
        return "Automatyczna transkrypcja"
    if path.name == "smartclip_analysis.json":
        return "Raport Smart Clips"
    if suffix in {".srt", ".vtt", ".ass", ".lrc"}:
        return "Napisy"
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".avif"}:
        return "Miniatura"
    if suffix in {".mp3", ".m4a", ".aac", ".opus", ".ogg", ".wav"}:
        return "Audio"
    return "Wideo"


def clear_results():
    folders = {
        item.get("temp_dir")
        for item in st.session_state.download_results
        if item.get("temp_dir")
    }
    for folder in folders:
        shutil.rmtree(folder, ignore_errors=True)
    st.session_state.download_results = []
    st.session_state.previews = []


st.title("Babel Boost Video Downloader 3.1")
st.caption(
    "YouTube • X/Twitter • Facebook • Smart Clips • analiza mowy i ciszy • "
    "automatyczne napisy • podgląd przed renderowaniem"
)

st.info(
    "Pobieraj tylko materiały, do których masz prawa lub zgodę. "
    "Narzędzie nie omija DRM ani zabezpieczeń prywatnych treści."
)

urls_text = st.text_area(
    "Wklej jeden lub wiele linków",
    placeholder=(
        "https://www.youtube.com/watch?v=...\n"
        "https://x.com/.../status/...\n"
        "https://www.facebook.com/watch/?v=..."
    ),
    height=150,
    help="Możesz wkleić kilka adresów, po jednym w wierszu. Duplikaty są usuwane.",
)

urls = parse_urls(urls_text)
valid_urls = [url for url in urls if is_supported_url(url)]
invalid_urls = [url for url in urls if not is_supported_url(url)]

if valid_urls:
    st.caption(f"W kolejce: {len(valid_urls)}")
if invalid_urls:
    st.warning("Pominięte nieobsługiwane linki:\n" + "\n".join(invalid_urls))

settings_a, settings_b, settings_c, settings_d = st.columns(4)
with settings_a:
    mode = st.selectbox("Format", ["Wideo MP4", "MP3"])
    quality = st.selectbox(
        "Jakość",
        list(QUALITY_FORMATS),
        disabled=(mode == "MP3"),
    )

with settings_b:
    download_thumbnail = st.checkbox("Pobierz miniaturę", value=True)
    download_subtitles = st.checkbox("Pobierz napisy ze źródła", value=False)
    subtitle_languages_text = st.text_input(
        "Języki napisów źródłowych",
        value="pl,en",
        disabled=not download_subtitles,
        help="Kody języków oddzielone przecinkami, np. pl,en,is.",
    )

with settings_c:
    make_tiktok = st.checkbox(
        "Pełne wideo TikTok 9:16",
        value=False,
        disabled=(mode == "MP3"),
        help="Tworzy pełną pionową kopię z rozmytym tłem.",
    )
    make_smart_clips = st.checkbox(
        "Smart Clips 3.1",
        value=False,
        disabled=(mode == "MP3"),
        help=(
            "Analizuje twarze, ruch, sceny oraz mowę/ciszę. Najpierw pokazuje "
            "proponowane fragmenty, a dopiero potem pozwala je renderować."
        ),
    )

with settings_d:
    browser = st.selectbox(
        "Cookies przeglądarki",
        ["Bez logowania", "Chrome", "Edge", "Firefox"],
        help="Używaj tylko do treści, do których masz legalny dostęp.",
    )

smart_clip_count = 3
smart_clip_length = 20
smart_sample_interval = 0.8
auto_subtitles = False
burn_subtitles = False
whisper_language = "auto"
whisper_model = "base"

if make_smart_clips:
    st.subheader("Smart Clips 3.1")
    st.caption(
        "Ranking jest heurystyczny: mowa/cisza + twarz + ruch + zmiany scen. "
        "Nie ocenia znaczenia ani prawdziwości wypowiedzi."
    )

    smart_1, smart_2, smart_3 = st.columns(3)
    with smart_1:
        smart_clip_count = st.slider("Liczba propozycji", 1, 5, 3)
    with smart_2:
        smart_clip_length = st.slider("Długość klipu", 10, 45, 20, step=5)
    with smart_3:
        analysis_mode = st.selectbox(
            "Dokładność analizy obrazu",
            ["Standard", "Dokładna", "Szybka"],
        )
        smart_sample_interval = {
            "Dokładna": 0.5,
            "Standard": 0.8,
            "Szybka": 1.2,
        }[analysis_mode]

    st.markdown("**Automatyczne napisy 3.1**")
    sub_1, sub_2, sub_3, sub_4 = st.columns(4)
    with sub_1:
        auto_subtitles = st.checkbox(
            "Transkrybuj mowę",
            value=True,
            help="Faster-Whisper działa lokalnie. Przy pierwszym użyciu pobierze model językowy.",
        )
    with sub_2:
        burn_subtitles_choice = st.checkbox(
            "Wypal napisy w klipach",
            value=True,
            disabled=not auto_subtitles,
        )
        burn_subtitles = bool(auto_subtitles and burn_subtitles_choice)
    with sub_3:
        language_label = st.selectbox(
            "Język mowy",
            ["Auto", "Polski", "Angielski", "Islandzki"],
            disabled=not auto_subtitles,
        )
        whisper_language = {
            "Auto": "auto",
            "Polski": "pl",
            "Angielski": "en",
            "Islandzki": "is",
        }[language_label]
    with sub_4:
        model_label = st.selectbox(
            "Model Whisper",
            ["Base — polecany", "Tiny — najszybszy", "Small — dokładniejszy"],
            disabled=not auto_subtitles,
        )
        whisper_model = {
            "Base — polecany": "base",
            "Tiny — najszybszy": "tiny",
            "Small — dokładniejszy": "small",
        }[model_label]

ffmpeg_found = shutil.which("ffmpeg") is not None
if not ffmpeg_found:
    st.warning(
        "FFmpeg nie jest wykryty. MP3, analiza ciszy, pionowe wideo i Smart Clips "
        "nie będą działać. Instrukcja instalacji jest w README."
    )

preview_button, download_button, clear_button = st.columns([1, 1, 1])
with preview_button:
    check_links = st.button("Sprawdź linki", use_container_width=True)
with download_button:
    start_download = st.button("Pobierz i analizuj", type="primary", use_container_width=True)
with clear_button:
    if st.button("Wyczyść wyniki", use_container_width=True):
        clear_results()
        st.rerun()

if check_links:
    if not valid_urls:
        st.error("Wklej przynajmniej jeden poprawny link z YouTube, X/Twitter lub Facebooka.")
    else:
        previews = []
        info_opts = build_info_options(browser)
        with st.spinner("Sprawdzanie tytułów i miniatur..."):
            for url in valid_urls:
                try:
                    with yt_dlp.YoutubeDL(info_opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                    previews.append({
                        "url": url,
                        "title": info.get("title") or "Bez tytułu",
                        "thumbnail": info.get("thumbnail"),
                        "uploader": info.get("uploader") or info.get("channel") or "",
                        "duration": format_duration(info.get("duration")),
                        "error": None,
                    })
                except Exception as exc:
                    previews.append({
                        "url": url,
                        "title": url,
                        "thumbnail": None,
                        "uploader": "",
                        "duration": "",
                        "error": str(exc),
                    })
        st.session_state.previews = previews

if st.session_state.previews:
    st.subheader("Podgląd kolejki")
    for preview in st.session_state.previews:
        col_image, col_info = st.columns([1, 3])
        with col_image:
            if preview.get("thumbnail"):
                st.image(preview["thumbnail"], use_container_width=True)
        with col_info:
            st.markdown(f"**{preview['title']}**")
            details = " • ".join(
                item for item in [preview.get("uploader"), preview.get("duration")] if item
            )
            if details:
                st.caption(details)
            st.caption(preview["url"])
            if preview.get("error"):
                st.error(preview["error"])

if start_download:
    if not valid_urls:
        st.error("Wklej przynajmniej jeden poprawny link z YouTube, X/Twitter lub Facebooka.")
    elif (mode == "MP3" or make_tiktok or make_smart_clips) and not ffmpeg_found:
        st.error("Ta operacja wymaga FFmpeg. Zainstaluj FFmpeg i uruchom aplikację ponownie.")
    else:
        progress = st.progress(0.0)
        status = st.empty()
        results = []
        subtitle_languages = parse_subtitle_languages(subtitle_languages_text)
        total_jobs = len(valid_urls)

        for index, url in enumerate(valid_urls):
            temp_dir = tempfile.mkdtemp(prefix="babelboost_video_")
            status.write(f"{index + 1}/{total_jobs}: przygotowanie {url}")

            def progress_hook(data, job_index=index, job_url=url):
                if data.get("status") == "downloading":
                    total_bytes = data.get("total_bytes") or data.get("total_bytes_estimate")
                    downloaded = data.get("downloaded_bytes") or 0
                    local_progress = (downloaded / total_bytes) if total_bytes else 0.05
                    overall = (job_index + min(max(local_progress, 0.0), 0.78)) / total_jobs
                    progress.progress(min(max(overall, 0.0), 0.99))
                    status.write(f"{job_index + 1}/{total_jobs}: pobieranie {job_url}")
                elif data.get("status") == "finished":
                    overall = (job_index + 0.80) / total_jobs
                    progress.progress(min(overall, 0.99))
                    status.write(f"{job_index + 1}/{total_jobs}: obróbka pobranego pliku")

            smart_candidates = []
            transcript_segments = []
            transcript_meta = None
            warnings = []

            try:
                opts = build_ydl_options(
                    temp_dir,
                    mode,
                    quality,
                    browser,
                    subtitles=download_subtitles,
                    subtitle_languages=subtitle_languages,
                    thumbnail=download_thumbnail,
                    progress_hook=progress_hook,
                )

                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=True)

                primary_file = find_primary_media(temp_dir)
                if not primary_file:
                    raise RuntimeError("Nie udało się znaleźć pobranego pliku multimedialnego.")

                if make_tiktok and mode != "MP3":
                    status.write(f"{index + 1}/{total_jobs}: tworzenie pełnej wersji TikTok 9:16")
                    prepare_tiktok_9x16(primary_file)

                metadata = None
                if make_smart_clips and mode != "MP3":
                    status.write(f"{index + 1}/{total_jobs}: analiza obrazu, mowy i ciszy")

                    def analysis_progress(local_value, job_index=index):
                        overall = (job_index + 0.82 + min(max(local_value, 0.0), 1.0) * 0.08) / total_jobs
                        progress.progress(min(overall, 0.99))

                    candidates, metadata = analyze_video_for_clips(
                        primary_file,
                        clip_length=smart_clip_length,
                        max_clips=smart_clip_count,
                        sample_interval=smart_sample_interval,
                        progress_callback=analysis_progress,
                    )
                    if not candidates:
                        raise RuntimeError("Smart Clips nie znalazł fragmentów do zaproponowania.")

                    if auto_subtitles:
                        try:
                            status.write(
                                f"{index + 1}/{total_jobs}: transkrypcja mowy — przy pierwszym użyciu model może się pobierać"
                            )
                            segments, transcript_meta, _ = transcribe_video(
                                primary_file,
                                language=whisper_language,
                                model_size=whisper_model,
                            )
                            transcript_segments = [asdict(segment) for segment in segments]
                            metadata["transcription"] = transcript_meta
                        except Exception as exc:
                            warnings.append(f"Transkrypcja nie powiodła się: {exc}")

                    smart_candidates = []
                    segment_objects = [SpeechSegment(**segment) for segment in transcript_segments]
                    for candidate in candidates:
                        item = asdict(candidate)
                        item["transcript"] = transcript_for_window(
                            segment_objects,
                            candidate.start,
                            candidate.end,
                        ) if segment_objects else ""
                        smart_candidates.append(item)

                    write_analysis_report(
                        temp_dir,
                        primary_file.name,
                        candidates,
                        metadata,
                    )

                files = list_output_files(temp_dir)
                results.append({
                    "url": url,
                    "title": info.get("title") or primary_file.stem,
                    "thumbnail": info.get("thumbnail"),
                    "temp_dir": temp_dir,
                    "primary_file": str(primary_file),
                    "files": [str(path) for path in files],
                    "smart_candidates": smart_candidates,
                    "transcript_segments": transcript_segments,
                    "transcript_meta": transcript_meta,
                    "burn_subtitles": burn_subtitles,
                    "metadata": metadata,
                    "rendered_smart_clips": [],
                    "warnings": warnings,
                    "error": None,
                })
            except Exception as exc:
                results.append({
                    "url": url,
                    "title": url,
                    "thumbnail": None,
                    "temp_dir": temp_dir,
                    "primary_file": "",
                    "files": [str(path) for path in list_output_files(temp_dir)],
                    "smart_candidates": smart_candidates,
                    "transcript_segments": transcript_segments,
                    "transcript_meta": transcript_meta,
                    "burn_subtitles": burn_subtitles,
                    "metadata": None,
                    "rendered_smart_clips": [],
                    "warnings": warnings,
                    "error": str(exc),
                })

            progress.progress((index + 1) / total_jobs)

        st.session_state.download_results = results
        status.write("Analiza zakończona. Smart Clips możesz teraz obejrzeć i wybrać przed renderowaniem.")

if st.session_state.download_results:
    st.subheader("Wyniki")

    for item_index, item in enumerate(st.session_state.download_results):
        title = item.get("title") or item.get("url")
        with st.expander(title, expanded=True):
            if item.get("error"):
                st.error(item["error"])

            for warning in item.get("warnings", []):
                st.warning(warning)

            if item.get("thumbnail"):
                st.image(item["thumbnail"], width=240)

            candidates = item.get("smart_candidates") or []
            primary_path = Path(item.get("primary_file") or "")

            if candidates and primary_path.exists():
                st.markdown("### Proponowane Smart Clips 3.1 — obejrzyj przed renderowaniem")
                st.caption(
                    "Każdy podgląd uruchamia oryginalny film od początku proponowanego fragmentu. "
                    "Sprawdź go i zaznacz tylko te klipy, które chcesz utworzyć."
                )

                metadata = item.get("metadata") or {}
                if metadata.get("speech_analysis"):
                    st.caption(
                        f"Analiza ciszy: {metadata.get('silence_intervals', 0)} odcinków, "
                        f"łącznie {metadata.get('silence_seconds', 0.0):.1f} s ciszy."
                    )

                if item.get("transcript_meta"):
                    transcript_meta = item["transcript_meta"]
                    st.caption(
                        f"Whisper: język {transcript_meta.get('language', '?')} • "
                        f"model {transcript_meta.get('model', '?')} • "
                        f"segmenty {transcript_meta.get('segments', 0)}"
                    )

                for candidate_index, candidate_data in enumerate(candidates, start=1):
                    candidate = CandidateClip(**{
                        key: candidate_data[key]
                        for key in [
                            "start", "end", "score", "face_ratio", "motion_score",
                            "scene_score", "focus_x", "speech_ratio"
                        ]
                    })
                    st.markdown(f"**Propozycja {candidate_index}**")
                    left, right = st.columns([2, 1])
                    with left:
                        st.video(str(primary_path), start_time=int(candidate.start))
                    with right:
                        st.write(
                            f"Czas: {format_duration(candidate.start)}–{format_duration(candidate.end)}"
                        )
                        st.write(f"Wynik: {candidate.score:.2f}")
                        st.write(f"Mowa: {candidate.speech_ratio * 100:.0f}%")
                        st.write(f"Twarz: {candidate.face_ratio * 100:.0f}%")
                        st.write(f"Ruch: {candidate.motion_score * 100:.0f}%")
                        selected = st.checkbox(
                            "Renderuj ten klip",
                            value=True,
                            key=f"select-{item_index}-{candidate_index}",
                        )
                        if candidate_data.get("transcript"):
                            st.caption("Tekst w tym fragmencie:")
                            st.write(candidate_data["transcript"])
                        if selected:
                            st.caption("✓ Zaznaczony do renderowania")
                    st.divider()

                if st.button(
                    "Renderuj zaznaczone Smart Clips",
                    type="primary",
                    use_container_width=True,
                    key=f"render-{item_index}",
                ):
                    selected_candidates = []
                    for candidate_index, candidate_data in enumerate(candidates, start=1):
                        if st.session_state.get(f"select-{item_index}-{candidate_index}", True):
                            selected_candidates.append((candidate_index, candidate_data))

                    if not selected_candidates:
                        st.warning("Zaznacz przynajmniej jeden klip.")
                    else:
                        render_progress = st.progress(0.0)
                        render_status = st.empty()
                        rendered = []
                        transcript_objects = [
                            SpeechSegment(**segment)
                            for segment in item.get("transcript_segments", [])
                        ]

                        try:
                            for done, (candidate_index, candidate_data) in enumerate(selected_candidates):
                                candidate = CandidateClip(**{
                                    key: candidate_data[key]
                                    for key in [
                                        "start", "end", "score", "face_ratio", "motion_score",
                                        "scene_score", "focus_x", "speech_ratio"
                                    ]
                                })
                                render_status.write(
                                    f"Renderowanie {done + 1}/{len(selected_candidates)}..."
                                )

                                subtitles_path = None
                                if item.get("burn_subtitles") and transcript_objects:
                                    subtitles_path = Path(item["temp_dir"]) / (
                                        f"smartclip_{candidate_index:02d}_captions.srt"
                                    )
                                    write_clip_srt(
                                        transcript_objects,
                                        candidate.start,
                                        candidate.end,
                                        subtitles_path,
                                    )

                                output = render_smart_clip(
                                    primary_path,
                                    candidate,
                                    int(metadata.get("width", 1920)),
                                    int(metadata.get("height", 1080)),
                                    candidate_index,
                                    subtitles_path=subtitles_path,
                                )
                                rendered.append(str(output))
                                render_progress.progress((done + 1) / len(selected_candidates))

                            item["rendered_smart_clips"] = rendered
                            item["files"] = [
                                str(path) for path in list_output_files(item["temp_dir"])
                            ]
                            st.session_state.download_results[item_index] = item
                            render_status.write("Gotowe. Klipy są poniżej w sekcji plików.")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Błąd renderowania Smart Clips: {exc}")

            if item.get("rendered_smart_clips"):
                st.success(f"Wyrenderowano Smart Clips: {len(item['rendered_smart_clips'])}")

            files = [Path(path) for path in item.get("files", [])]
            files = [path for path in files if path.exists()]
            if files:
                st.markdown("### Pliki")
                for file_index, path in enumerate(files):
                    label = f"{file_kind(path)} • {path.name} • {human_size(path.stat().st_size)}"
                    with open(path, "rb") as file_handle:
                        st.download_button(
                            label,
                            data=file_handle.read(),
                            file_name=path.name,
                            mime=guess_mime(path),
                            key=f"download-{item_index}-{file_index}-{path.name}",
                            use_container_width=True,
                        )

st.divider()
st.caption(
    "Smart Clips 3.1 analizuje pliki lokalnie. Faster-Whisper może przy pierwszej transkrypcji "
    "pobrać model. Facebook i X częściej wymagają aktywnej sesji."
)
