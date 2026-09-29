import shutil
import tempfile

import streamlit as st
import yt_dlp

from downloader import (
    QUALITY_FORMATS,
    build_ydl_options,
    find_output_file,
    human_size,
    is_supported_url,
)

st.set_page_config(
    page_title="Babel Boost Video Downloader",
    page_icon="🎬",
    layout="centered",
)

st.title("Babel Boost Video Downloader")
st.caption("YouTube • X/Twitter • Facebook")

st.info(
    "Pobieraj tylko materiały, do których masz prawa lub zgodę. "
    "Narzędzie nie omija DRM ani zabezpieczeń prywatnych treści."
)

url = st.text_input(
    "Wklej link do filmu",
    placeholder="https://www.youtube.com/watch?v=...",
)

col1, col2 = st.columns(2)
with col1:
    mode = st.selectbox("Format", ["Wideo MP4", "MP3"])
with col2:
    quality = st.selectbox(
        "Jakość",
        list(QUALITY_FORMATS),
        disabled=(mode == "MP3"),
    )

browser = st.selectbox(
    "Logowanie przez cookies przeglądarki (opcjonalnie)",
    ["Bez logowania", "Chrome", "Edge", "Firefox"],
    help=(
        "Przydatne dla własnych treści dostępnych tylko po zalogowaniu. "
        "Działa najlepiej przy uruchomieniu lokalnym na tym samym komputerze."
    ),
)

ffmpeg_found = shutil.which("ffmpeg") is not None
if not ffmpeg_found:
    st.warning(
        "FFmpeg nie jest wykryty. Łączenie wideo z audio oraz MP3 może nie działać. "
        "Instrukcja instalacji jest w README."
    )

if st.button("Pobierz", type="primary", use_container_width=True):
    if not is_supported_url(url):
        st.error("Podaj poprawny link z YouTube, X/Twitter lub Facebooka.")
    elif mode == "MP3" and not ffmpeg_found:
        st.error("Do MP3 potrzebny jest FFmpeg.")
    else:
        temp_dir = tempfile.mkdtemp(prefix="babelboost_video_")
        try:
            opts = build_ydl_options(temp_dir, mode, quality, browser)
            with st.spinner("Pobieranie i przygotowanie pliku..."):
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url.strip(), download=True)

            output_file = find_output_file(temp_dir)
            if not output_file:
                st.error("Nie udało się znaleźć pobranego pliku.")
            else:
                title = info.get("title") or output_file.stem
                st.success(f"Gotowe: {title}")
                st.write(f"Rozmiar: {human_size(output_file.stat().st_size)}")

                mime = (
                    "audio/mpeg"
                    if output_file.suffix.lower() == ".mp3"
                    else "video/mp4"
                )
                with open(output_file, "rb") as file_handle:
                    data = file_handle.read()

                st.download_button(
                    "Zapisz plik na komputerze",
                    data=data,
                    file_name=output_file.name,
                    mime=mime,
                    use_container_width=True,
                )
        except yt_dlp.utils.DownloadError as exc:
            st.error(f"Błąd pobierania: {exc}")
        except Exception as exc:
            st.error(f"Wystąpił błąd: {exc}")

st.divider()
st.caption(
    "Facebook i X częściej wymagają aktywnej sesji. "
    "Wtedy wybierz przeglądarkę, w której jesteś zalogowany."
)
