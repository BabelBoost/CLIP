"""Streamlit desktop UI for Babel Boost AutoClip No API."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import streamlit as st

from offline_studio import StudioError, create_video, make_plan, validate_plan

BASE = Path(__file__).resolve().parent
STOCK = BASE / "stock"
OUTPUTS = BASE / "exports"
STOCK.mkdir(parents=True, exist_ok=True)
OUTPUTS.mkdir(parents=True, exist_ok=True)

st.set_page_config(page_title="Babel Boost AutoClip No API", layout="wide", page_icon="🎬")
st.title("Babel Boost AutoClip | Bez API")
st.caption("Z promptu do MP4 bez kluczy. Lokalne media stock, autorskie grafiki, głos Windows.")
st.info("Program nie potrzebuje OpenAI, Pexels ani Pixabay API. "
        "Bez materiałów w folderze stock tworzy własne grafiki. "
        "Opcjonalne Wikimedia Commons wymaga internetu i może nie znaleźć zdjęć.")

with st.sidebar:
    st.subheader("Biblioteka stock")
    st.code(str(STOCK))
    st.caption("Skopiuj tutaj własne, legalnie pobrane zdjęcia i filmy. "
               "Nazywaj pliki po angielsku, np. iceland_winter_road.mp4.")
    st.write(f"Plików w bibliotece: {sum(1 for p in STOCK.rglob('*') if p.suffix.lower() in {'.jpg','.jpeg','.png','.webp','.mp4','.mov','.m4v'})}")
    st.markdown("[Pexels do ręcznego pobrania](https://www.pexels.com/)")
    st.markdown("[Pixabay do ręcznego pobrania](https://pixabay.com/)")
    st.markdown("[Wikimedia Commons](https://commons.wikimedia.org/)")
    st.caption("Nie pobieramy automatycznie materiałów z Pexels/Pixabay bez ich API.")

with st.form("brief"):
    a, b = st.columns([2,1])
    with a:
        prompt = st.text_area("Twój prompt / scenariusz", height=210, value=(
            "Create a short film about winter road trips in Iceland. "
            "Hook: Would you drive this road in winter? "
            "Tell viewers to check current road conditions and forecasts before departure. "
            "No invented alerts or fake footage."
        ))
        cta = st.text_input("Wezwanie do działania", value="Follow Babel Boost Iceland | BabelBoost.com")
        brand = st.text_input("Nazwa marki", value="BABEL BOOST ICELAND")
    with b:
        language = st.selectbox("Język scenariusza", ["English","Polski"])
        seconds = st.selectbox("Docelowy czas", [15,20,30,35,45,60,90], index=3)
        quality = st.selectbox("Rozdzielczość", ["720p","1080p","540p"], index=0)
        style = st.selectbox("Wygląd", ["Dokumentalny","Energetyczny","Minimalistyczny"])
        commons = st.checkbox("Szukaj zdjęć CC0 w Wikimedia Commons (bez API)", value=False,
                               help="Opcjonalne. Wymaga internetu, może nie znaleźć pasujących zdjęć. "
                               "Używamy tylko pozycji z wykrytym CC0 na stronie pliku.")
        use_local_ai = st.checkbox("AI lokalne przez Ollama, bez klucza API", value=False,
                                    help="Wymaga lokalnie zainstalowanego programu Ollama i pobranego modelu.")
        model = st.text_input("Model Ollama", value="llama3.2:3b") if use_local_ai else "llama3.2:3b"
        speech = st.checkbox("Lektor offline (głos zainstalowany w Windows)", value=True)
        voice_hint = st.text_input("Nazwa głosu Windows (opcjonalnie)", value="",
                                   help="Np. Zofia. Gdy brak, używany jest głos systemowy.")
        autopilot = st.checkbox("Od razu stwórz film po zatwierdzeniu promptu", value=True)
    started = st.form_submit_button("Stwórz klip z promptu", type="primary", use_container_width=True)

if started:
    try:
        new_plan = make_plan(prompt, language, seconds, cta, use_local_ai, model)
        st.session_state["plan"] = validate_plan(new_plan)
        st.session_state["trigger"] = autopilot
        st.session_state.pop("result",None)
        st.session_state.pop("editor",None)
    except StudioError as exc:
        st.error(str(exc))

if "plan" in st.session_state:
    st.subheader("Sceny i teksty. Możesz poprawić przed eksportem.")
    plan = st.session_state["plan"]
    title = st.text_input("Tytuł", plan["title"])
    rows = st.data_editor(plan["scenes"], hide_index=True, num_rows="dynamic",
                          use_container_width=True, key="editor",
                          column_config={
                              "voiceover": st.column_config.TextColumn("Lektor",width="large"),
                              "caption": st.column_config.TextColumn("Napisy",width="large"),
                              "search_query": st.column_config.TextColumn("Szukane zdjęcia",width="medium")
                          })
    music = st.file_uploader("Opcjonalna muzyka MP3/M4A/WAV. Użyj tylko pliku, do którego masz prawa.",
                             type=["mp3","m4a","wav"])
    if st.button("Eksportuj film MP4", type="primary") or st.session_state.pop("trigger",False):
        try:
            edited = validate_plan({"title":title,"scenes":rows.to_dict("records") if hasattr(rows,"to_dict") else rows})
            destination = OUTPUTS / (datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid4().hex[:4])
            destination.mkdir(parents=True,exist_ok=True)
            music_path = None
            if music:
                if music.size > 50*1024*1024:
                    raise StudioError("Plik muzyki nie może być większy niż 50 MB.")
                music_path = destination/("music"+Path(music.name).suffix.lower())
                music_path.write_bytes(music.getbuffer())
            message = st.empty()
            with st.spinner("Tworzę film na Twoim komputerze..."):
                out, source_list = create_video(
                    edited, stock_folder=STOCK, output_dir=destination, duration=seconds,
                    quality=quality, brand=brand, style=style, with_voice=speech,
                    voice_hint=voice_hint, music=music_path, search_commons=commons,
                    progress=lambda status: message.info(status),
                )
            st.session_state["result"]={"video":str(out), "credits":str(destination/"credits.txt"),
                                         "json":str(source_list)}
            message.success("Film MP4 gotowy.")
        except (OSError,StudioError,ValueError) as exc:
            st.error("Błąd montażu: " + str(exc))

if "result" in st.session_state:
    st.subheader("Gotowy klip")
    paths = st.session_state["result"]
    video = Path(paths["video"])
    if video.is_file():
        st.video(str(video))
        st.download_button("Pobierz MP4",video.read_bytes(),file_name="BabelBoost_AutoClip_No_API.mp4",
                           mime="video/mp4",use_container_width=True)
    credits = Path(paths["credits"])
    if credits.is_file():
        st.download_button("Pobierz opis autorów i licencji",credits.read_bytes(),
                           file_name="credits.txt",mime="text/plain")
    source_list = Path(paths["json"])
    if source_list.is_file():
        st.download_button("Pobierz listę źródeł JSON",source_list.read_bytes(),
                           file_name="sources.json",mime="application/json")
        with st.expander("Wykorzystane materiały"):
            for item in json.loads(source_list.read_text(encoding="utf-8"))["media"]:
                st.write(f"Scena {item['scene']}: {item['media']} • {item['file']} • {item['license']}")

st.caption("Scenariusz szablonowy bez Ollama wymaga korekty przed publikacją. "
           "Stock nie potwierdza faktów ani nie przedstawia automatycznie rzeczywistych zdarzeń.")
