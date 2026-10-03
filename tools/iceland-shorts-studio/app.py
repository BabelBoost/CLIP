from __future__ import annotations

import json
import tempfile
from pathlib import Path

import streamlit as st

from iceland_studio import (
    StudioError,
    fallback_plan,
    make_plan_with_xai,
    render_project,
)
from prompt import TOPICS


st.set_page_config(page_title="Iceland Shorts Studio", page_icon="🇮🇸", layout="wide")

st.title("Iceland Shorts Studio")
st.caption("Faceless English shorts about Iceland for TikTok, Reels and YouTube Shorts.")

if "plan" not in st.session_state:
    st.session_state.plan = None

with st.sidebar:
    st.header("1. Ustawienia")
    duration = st.slider("Docelowa długość", 15, 30, 20, 1)
    topic_choice = st.selectbox("Temat", TOPICS + ["Custom topic"])
    if topic_choice == "Custom topic":
        topic = st.text_input("Własny temat", "A surprising Iceland travel mistake")
    else:
        topic = topic_choice

    st.subheader("AI")
    use_xai = st.checkbox("Generuj skrypt przez Grok/xAI", value=False)
    xai_api_key = st.text_input("xAI API key", type="password")
    xai_model = st.text_input("Model xAI", value="grok-4-fast")

    st.subheader("Stock")
    pexels_key = st.text_input("Pexels API key", type="password")

    st.subheader("Voice")
    voice_name = st.selectbox(
        "English voice",
        ["en-US-GuyNeural", "en-US-AriaNeural", "en-GB-RyanNeural"],
    )
    voice_rate = st.select_slider(
        "Tempo",
        options=["-10%", "-5%", "+0%", "+5%", "+10%", "+15%"],
        value="+5%",
    )

st.header("2. Skrypt i storyboard")
col1, col2 = st.columns([1, 1])

with col1:
    if st.button("GENERUJ PROJEKT", type="primary", use_container_width=True):
        try:
            if use_xai:
                st.session_state.plan = make_plan_with_xai(
                    topic, duration, xai_api_key, xai_model
                )
            else:
                st.session_state.plan = fallback_plan(topic, duration)
        except Exception as exc:
            st.error(str(exc))

with col2:
    if st.session_state.plan:
        st.download_button(
            "Pobierz plan JSON",
            json.dumps(st.session_state.plan, ensure_ascii=False, indent=2),
            file_name="iceland_short_plan.json",
            mime="application/json",
            use_container_width=True,
        )

plan = st.session_state.plan

if plan:
    left, right = st.columns([1.1, 0.9])
    with left:
        st.text_input("Title", value=plan["title"], key="title_edit")
        hook = st.text_area("Hook", value=plan["hook"], height=80)
        voiceover = st.text_area("Voice-over", value=plan["voiceover"], height=220)
        ending = st.text_input("Ending", value=plan["ending"])
        caption = st.text_area("Caption", value=plan["caption"], height=90)

    with right:
        st.markdown("**Storyboard**")
        scenes = []
        for i, scene in enumerate(plan["scenes"], start=1):
            with st.expander(f"Scene {i}: {scene['query']}", expanded=i <= 3):
                query = st.text_input(
                    "Search query",
                    value=scene["query"],
                    key=f"scene_query_{i}",
                )
                visual = st.text_area(
                    "Visual",
                    value=scene["visual"],
                    key=f"scene_visual_{i}",
                    height=80,
                )
                scenes.append({"query": query, "visual": visual})

    plan = {
        **plan,
        "title": st.session_state.get("title_edit", plan["title"]),
        "hook": hook,
        "voiceover": voiceover,
        "ending": ending,
        "caption": caption,
        "scenes": scenes,
    }
    st.session_state.plan = plan

    st.header("3. Materiały")
    st.write(
        "Wgraj własne autentyczne ujęcia Islandii. Jeśli nic nie wgrasz, program może pobrać "
        "stocki automatycznie z Pexels po podaniu API key."
    )
    uploads = st.file_uploader(
        "Wideo źródłowe",
        type=["mp4", "mov", "m4v", "webm"],
        accept_multiple_files=True,
    )
    music_upload = st.file_uploader(
        "Muzyka opcjonalna",
        type=["mp3", "wav", "m4a"],
        accept_multiple_files=False,
    )

    st.header("4. Render")
    st.write("Final: 1080 × 1920, H.264, voice-over, duże napisy, opcjonalna muzyka.")

    if st.button("STWÓRZ GOTOWY MP4", type="primary", use_container_width=True):
        try:
            with st.spinner("Produkcja klipu..."):
                temp_root = Path(tempfile.mkdtemp(prefix="iceland-shorts-"))
                sources_dir = temp_root / "sources"
                sources_dir.mkdir(parents=True, exist_ok=True)

                source_paths = []
                for i, upload in enumerate(uploads or []):
                    suffix = Path(upload.name).suffix or ".mp4"
                    p = sources_dir / f"source_{i:02d}{suffix}"
                    p.write_bytes(upload.getbuffer())
                    source_paths.append(p)

                music_path = None
                if music_upload is not None:
                    suffix = Path(music_upload.name).suffix or ".mp3"
                    music_path = temp_root / f"music{suffix}"
                    music_path.write_bytes(music_upload.getbuffer())

                output = render_project(
                    plan=plan,
                    source_videos=source_paths,
                    workdir=temp_root / "render",
                    voice_name=voice_name,
                    voice_rate=voice_rate,
                    music=music_path,
                    pexels_api_key=pexels_key,
                )

                data = output.read_bytes()
                st.success("Gotowe.")
                st.video(data)
                st.download_button(
                    "POBIERZ MP4",
                    data=data,
                    file_name="iceland_short.mp4",
                    mime="video/mp4",
                    use_container_width=True,
                )
        except StudioError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.exception(exc)

st.divider()
st.caption(
    "Najlepszy efekt daje prawdziwe islandzkie footage. AI ma tworzyć skrypt i montaż, "
    "a nie udawać znaki drogowe lub szczegóły, których nie potrafi wygenerować wiarygodnie."
)
