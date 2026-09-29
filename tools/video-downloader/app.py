import mimetypes
import shutil
import tempfile
from pathlib import Path

import streamlit as st
import yt_dlp

from downloader import (
    QUALITY_FORMATS,
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
)

st.set_page_config(
    page_title="Babel Boost Video Downloader 2.0",
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
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def file_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if "_tiktok_9x16" in path.stem.lower():
        return "TikTok 9:16"
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


st.title("Babel Boost Video Downloader 2.0")
st.caption("YouTube • X/Twitter • Facebook • kolejka • napisy • miniatury • TikTok 9:16")

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

settings_left, settings_mid, settings_right = st.columns(3)
with settings_left:
    mode = st.selectbox("Format", ["Wideo MP4", "MP3"])
    quality = st.selectbox(
        "Jakość",
        list(QUALITY_FORMATS),
        disabled=(mode == "MP3"),
    )

with settings_mid:
    download_thumbnail = st.checkbox("Pobierz miniaturę", value=True)
    download_subtitles = st.checkbox("Pobierz napisy", value=False)
    subtitle_languages_text = st.text_input(
        "Języki napisów",
        value="pl,en",
        disabled=not download_subtitles,
        help="Kody języków oddzielone przecinkami, np. pl,en,is.",
    )

with settings_right:
    make_tiktok = st.checkbox(
        "Przygotuj TikTok 9:16",
        value=False,
        disabled=(mode == "MP3"),
        help="Tworzy MP4 1080×1920 z rozmytym tłem i zachowaniem pełnego kadru.",
    )
    browser = st.selectbox(
        "Cookies przeglądarki",
        ["Bez logowania", "Chrome", "Edge", "Firefox"],
        help="Używaj tylko do treści, do których masz legalny dostęp.",
    )

ffmpeg_found = shutil.which("ffmpeg") is not None
if not ffmpeg_found:
    st.warning(
        "FFmpeg nie jest wykryty. Łączenie wideo z audio, MP3 i TikTok 9:16 "
        "mogą nie działać. Instrukcja instalacji jest w README."
    )

preview_button, download_button, clear_button = st.columns([1, 1, 1])

with preview_button:
    check_links = st.button("Sprawdź linki", use_container_width=True)
with download_button:
    start_download = st.button("Pobierz kolejkę", type="primary", use_container_width=True)
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
    elif (mode == "MP3" or make_tiktok) and not ffmpeg_found:
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
                    overall = (job_index + min(max(local_progress, 0.0), 0.9)) / total_jobs
                    progress.progress(min(max(overall, 0.0), 0.99))
                    status.write(f"{job_index + 1}/{total_jobs}: pobieranie {job_url}")
                elif data.get("status") == "finished":
                    overall = (job_index + 0.92) / total_jobs
                    progress.progress(min(overall, 0.99))
                    status.write(f"{job_index + 1}/{total_jobs}: obróbka pliku")

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
                    status.write(f"{index + 1}/{total_jobs}: tworzenie wersji TikTok 9:16")
                    prepare_tiktok_9x16(primary_file)

                files = list_output_files(temp_dir)
                results.append({
                    "url": url,
                    "title": info.get("title") or primary_file.stem,
                    "thumbnail": info.get("thumbnail"),
                    "temp_dir": temp_dir,
                    "files": [str(path) for path in files],
                    "error": None,
                })
            except Exception as exc:
                results.append({
                    "url": url,
                    "title": url,
                    "thumbnail": None,
                    "temp_dir": temp_dir,
                    "files": [],
                    "error": str(exc),
                })

            progress.progress((index + 1) / total_jobs)

        st.session_state.download_results = results
        status.write("Kolejka zakończona.")

if st.session_state.download_results:
    st.subheader("Gotowe pliki")
    for item_index, item in enumerate(st.session_state.download_results):
        title = item.get("title") or item.get("url")
        with st.expander(title, expanded=True):
            if item.get("error"):
                st.error(item["error"])
                continue

            if item.get("thumbnail"):
                st.image(item["thumbnail"], width=240)

            for file_index, path_string in enumerate(item.get("files", [])):
                path = Path(path_string)
                if not path.exists():
                    continue
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
    "Facebook i X częściej wymagają aktywnej sesji. Wtedy wybierz przeglądarkę, "
    "w której jesteś zalogowany. Wersja TikTok 9:16 wymaga FFmpeg."
)
