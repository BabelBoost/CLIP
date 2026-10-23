"""Streamlit desktop-style UI for Babel Boost AutoClip Studio."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import streamlit as st

from studio import StudioError, ai_plan, create_video, validate_plan


BASE = Path(__file__).resolve().parent
EXPORTS = BASE / "exports"
EXAMPLE_EN = (
    "Create a 35-second short about safe winter road trips in Iceland. "
    "Use practical advice, a compelling opening question, authentic-looking "
    "winter road stock as illustration and a final CTA to BabelBoost.com. "
    "Do not invent weather warnings or report current conditions."
)
EXAMPLE_PL = (
    "Stwórz film o podróżowaniu po Islandii zimą. Mocny hook, "
    "praktyczne wskazówki, czytelne napisy i wezwanie do obserwowania. "
    "Nie wymyślaj aktualnych ostrzeżeń pogodowych."
)


st.set_page_config(page_title="Babel Boost AutoClip Studio", page_icon="🎬", layout="wide")
st.title("Babel Boost AutoClip Studio")
st.caption("Prompt → scenariusz AI → stock Pexels / Pixabay → lektor PL/EN → MP4")
st.markdown("Biblioteki: [Pexels](https://www.pexels.com) i [Pixabay](https://pixabay.com). Każdy projekt zapisuje listę autorów i źródeł.")

with st.sidebar:
    st.header("Połączenia")
    pexels_key = st.text_input("Pexels API key", type="password", help="Darmowy klucz: https://www.pexels.com/api/")
    pixabay_key = st.text_input("Pixabay API key (opcjonalnie)", type="password",
                                help="Alternatywna biblioteka zdjęć, wideo, grafik i ilustracji.")
    openai_key = st.text_input("OpenAI API key (opcjonalnie)", type="password",
                               help="Bez klucza AI powstaje prosty, edytowalny szkic scenariusza.")
    model = st.text_input("Model do scenariusza", value="gpt-4.1-mini")
    st.caption("Klucze są używane podczas działania aplikacji. Nie zapisujemy ich w projekcie.")
    st.divider()
    st.markdown("[Uzyskaj klucz Pexels](https://www.pexels.com/api/)")
    st.markdown("[Uzyskaj klucz Pixabay](https://pixabay.com/api/docs/)")
    st.markdown("[Warunki Pexels](https://www.pexels.com/license/)")
    st.markdown("[Warunki Pixabay](https://pixabay.com/service/license-summary/)")

with st.form("settings"):
    left, right = st.columns([2, 1])
    with left:
        language = st.selectbox("Język", ["English", "Polski"])
        example = EXAMPLE_EN if language == "English" else EXAMPLE_PL
        prompt = st.text_area("Prompt lub temat filmu", value=example, height=180,
                              help="Dodaj fakty, narrację, zakaz wymyślania cytatów i preferowane ujęcia.")
    with right:
        seconds = st.selectbox("Docelowa długość", [15, 30, 35, 45, 60, 90], index=2)
        format_name = st.selectbox("Proporcje", ["9:16", "16:9", "1:1"])
        preference = st.selectbox("Materiały", ["Mix wideo i zdjęć", "Tylko wideo", "Tylko zdjęcia", "Grafiki i ilustracje"])
        stock_source = st.selectbox("Biblioteka stock", ["Auto", "Pexels", "Pixabay"],
                                    help="Auto wybiera Pexels, a gdy brak materiałów przechodzi do Pixabay.")
        brand = st.text_input("Marka na ekranie", "BABEL BOOST ICELAND")
        cta = st.text_input("Wezwanie na końcu", "Follow Babel Boost | BabelBoost.com")
        voice = st.selectbox("Lektor",
                             ["en-US-GuyNeural", "en-US-JennyNeural", "pl-PL-MarekNeural", "pl-PL-ZofiaNeural"],
                             index=0 if language == "English" else 2)
    autopilot = st.checkbox("Autopilot: wygeneruj od razu MP4 z promptu", value=True)
    create_story = st.form_submit_button("Stwórz klip z promptu", type="primary", use_container_width=True)

if create_story:
    try:
        result = ai_plan(prompt, language, seconds, cta, openai_key, model)
        st.session_state["plan"] = validate_plan(result)
        st.session_state["autopilot"] = bool(autopilot)
        if "scene_editor" in st.session_state:
            del st.session_state["scene_editor"]
        st.session_state.pop("last_output", None)
    except StudioError as exc:
        st.error(str(exc))

if "plan" in st.session_state:
    plan = st.session_state["plan"]
    st.divider()
    st.subheader("Scenariusz i zapytania do zdjęć (edytowalne)")
    if plan.get("planning") != "AI":
        st.warning("To jest szkic bez generowania AI. Popraw lektora i wyszukiwane frazy przed montażem.")
    st.text_input("Tytuł klipu", value=plan["title"], key="edited_title")
    edited = st.data_editor(plan["scenes"], use_container_width=True, num_rows="fixed",
                            key="scene_editor", hide_index=False,
                            column_config={
                                "voiceover": st.column_config.TextColumn("Tekst lektora", width="large", required=True),
                                "caption": st.column_config.TextColumn("Napis na ekranie", width="medium", required=True),
                                "search_query": st.column_config.TextColumn("Fraza Pexels (EN)", width="medium", required=True),
                            })
    st.caption("Każdy wiersz odpowiada jednej scenie. Materiał Pexels jest ilustracją, nie nagraniem opisanego zdarzenia.")
    personal = st.file_uploader("Twoje zdjęcia lub filmy (opcjonalnie, po jednym na scenę, w kolejności)",
                                type=["jpg", "jpeg", "png", "webp", "mp4", "mov", "m4v"],
                                accept_multiple_files=True)
    soundtrack = st.file_uploader("Muzyka MP3/M4A/WAV (opcjonalnie, tylko z prawem do użycia)",
                                  type=["mp3", "m4a", "wav"])
    if st.button("Wygeneruj / ponów eksport MP4", type="primary", use_container_width=True) or st.session_state.pop("autopilot", False):
        try:
            rows = edited.to_dict("records") if hasattr(edited, "to_dict") else list(edited)
            edit_plan = validate_plan({"title": st.session_state.get("edited_title") or plan["title"], "scenes": rows})
            if not (pexels_key or pixabay_key) and len(personal or []) < len(rows):
                raise StudioError("Podaj klucz Pexels lub Pixabay albo dodaj tyle własnych plików, ile jest scen.")
            output_dir = EXPORTS / (datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid4().hex[:6])
            output_dir.mkdir(parents=True, exist_ok=True)
            upload_paths = []
            for index, entry in enumerate(personal or []):
                if entry.size > 150 * 1024 * 1024:
                    raise StudioError("Własny plik jest za duży (limit 150 MB).")
                upload_path = output_dir / ("upload_" + str(index) + Path(entry.name).suffix.lower())
                upload_path.write_bytes(entry.getbuffer())
                upload_paths.append(upload_path)
            music_path = None
            if soundtrack:
                music_path = output_dir / ("user_music" + Path(soundtrack.name).suffix.lower())
                music_path.write_bytes(soundtrack.getbuffer())
            message = st.empty()
            with st.spinner("Montuję film. Duże wideo może wymagać czasu."):
                video, manifest = create_video(
                    edit_plan, pexels_key=pexels_key, seconds=seconds, format_name=format_name,
                    preference=preference, voice=voice, brand=brand, cta=cta,
                    destination=output_dir, user_media=upload_paths, music=music_path,
                    pixabay_key=pixabay_key, stock_source=stock_source,
                    progress=lambda msg: message.info(msg),
                )
            st.session_state["last_output"] = {"video": str(video), "manifest": str(manifest)}
            message.success("Gotowe. Pliki zapisano także w katalogu exports.")
        except (StudioError, OSError, ValueError) as exc:
            st.error("Błąd: " + str(exc))
        except Exception as exc:
            st.error("Nie udało się dokończyć montażu: " + str(exc))

if "last_output" in st.session_state:
    saved = st.session_state["last_output"]
    video_path = Path(saved["video"])
    manifest_path = Path(saved["manifest"])
    if video_path.exists():
        st.divider()
        st.subheader("Twój film")
        st.video(str(video_path))
        st.download_button("Pobierz MP4", video_path.read_bytes(), file_name="BabelBoost_AutoClip.mp4",
                           mime="video/mp4", use_container_width=True)
    if manifest_path.exists():
        st.download_button("Pobierz listę źródeł", manifest_path.read_bytes(), file_name="sources.json",
                           mime="application/json", use_container_width=True)
        with st.expander("Źródła użytych materiałów"):
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            for item in data["media"]:
                st.write("Scena " + str(item["scene"]) + ": " + item["provider"] + " · " + item["credit"] + " | " + item["source_page"])

st.info("Przed publikacją sprawdź poprawność faktów, licencje, kontekst i czy grafiki nie sugerują fałszywego nagrania prawdziwych wydarzeń.")
