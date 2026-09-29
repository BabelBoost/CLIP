from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from viralclip import (
    analyze_segments,
    enrich_with_ollama,
    format_time,
    render_clip,
    render_markdown,
    save_reports,
    transcribe_video,
)

st.set_page_config(page_title="Viral Clip Studio", page_icon="🎬", layout="wide")
st.title("Viral Clip Studio")
st.caption("MP4 → transkrypcja → TOP 5 → hooki → napisy → pionowe klipy 9:16")

with st.sidebar:
    st.header("Ustawienia")
    whisper_model = st.selectbox("Model transkrypcji", ["tiny", "base", "small", "medium"], index=2)
    language = st.selectbox("Język", ["pl", "en", "auto"], index=0)
    content_label = st.selectbox(
        "Rodzaj materiału",
        ["Auto", "Ogólny", "Polityka / publicystyka"],
        help="Tryb publicystyczny używa neutralnych, kontekstowych hooków i nie zmienia sensu wypowiedzi.",
    )
    content_mode = {"Auto": "auto", "Ogólny": "general", "Polityka / publicystyka": "public_affairs"}[content_label]
    use_ollama = st.checkbox("Ulepsz hooki lokalnym Ollama", value=False)
    ollama_model = st.text_input("Model Ollama", value="qwen3:8b", disabled=not use_ollama)
    burn_subtitles = st.checkbox("Wypal napisy w gotowych klipach", value=True)

uploaded = st.file_uploader("Wybierz pobrany plik wideo", type=["mp4", "mov", "mkv", "webm", "m4v"])

if uploaded:
    workspace = Path(tempfile.mkdtemp(prefix="viral_clip_studio_"))
    video_path = workspace / uploaded.name
    video_path.write_bytes(uploaded.getbuffer())
    st.video(str(video_path))

    if st.button("1. Przeanalizuj cały film", type="primary", use_container_width=True):
        progress = st.progress(0)
        status = st.empty()

        def cb(value: float, message: str) -> None:
            progress.progress(min(100, int(value * 100)))
            status.write(message)

        try:
            segments, detected = transcribe_video(
                video_path,
                model_size=whisper_model,
                language=None if language == "auto" else language,
                progress_cb=cb,
            )
            status.write(f"Analiza treści. Wykryty język: {detected or language}")
            candidates = analyze_segments(segments, top_n=10, content_mode=content_mode)
            if use_ollama:
                status.write("Ulepszanie opisów przez lokalny model Ollama…")
                candidates = enrich_with_ollama(candidates, model=ollama_model, content_mode=content_mode)

            st.session_state["workspace"] = str(workspace)
            st.session_state["video_path"] = str(video_path)
            st.session_state["candidates"] = [c.to_dict() for c in candidates]
            st.session_state["segments"] = [s.to_dict() for s in segments]
            save_reports(candidates, workspace / "output")
            progress.progress(100)
            status.success("Analiza zakończona")
        except Exception as exc:
            st.exception(exc)

if st.session_state.get("candidates"):
    from viralclip.models import ClipCandidate

    candidates = [ClipCandidate(**item) for item in st.session_state["candidates"]]
    st.subheader("TOP 5")
    table = pd.DataFrame([
        {
            "Ranking": c.rank,
            "Timecode": f"{format_time(c.start)}–{format_time(c.end)}",
            "Długość": f"{c.duration:.1f}s",
            "Temat": c.topic,
            "Hook": c.hook,
            "Viral Score": c.viral_score,
        }
        for c in candidates[:5]
    ])
    st.dataframe(table, use_container_width=True, hide_index=True)

    for c in candidates[:5]:
        with st.expander(f"#{c.rank}  {format_time(c.start)}–{format_time(c.end)}  |  {c.viral_score}/10", expanded=c.rank == 1):
            st.markdown(f"**Cytat:** {c.quote}")
            st.markdown(f"**Hook:** {c.hook}")
            st.markdown(f"**Tekst na ekran:** {c.screen_text}")
            st.markdown(f"**Emocja:** {c.emotion}")
            st.markdown(f"**Dlaczego:** {c.reason}")
            st.markdown(f"**Cięcie:** {c.cut_before} {c.cut_after}")
            st.markdown(f"**Opis:** {c.tiktok_description}")
            st.markdown(f"**Hashtagi:** {' '.join(c.hashtags)}")
            st.markdown(f"**CTA:** {c.cta}")

    report = render_markdown(candidates)
    st.download_button("Pobierz raport Markdown", report.encode("utf-8"), "viral_report.md", "text/markdown", use_container_width=True)
    st.download_button(
        "Pobierz dane JSON",
        json.dumps([c.to_dict() for c in candidates], ensure_ascii=False, indent=2).encode("utf-8"),
        "viral_report.json",
        "application/json",
        use_container_width=True,
    )

    st.subheader("Renderowanie")
    render_count = st.selectbox("Ile najlepszych klipów wyrenderować?", [1, 3, 5], index=0)
    if st.button("2. Wyrenderuj pionowe klipy 9:16", use_container_width=True):
        output = Path(st.session_state["workspace"]) / "output" / "clips"
        video = Path(st.session_state["video_path"])
        rendered = []
        try:
            for c in candidates[:render_count]:
                with st.spinner(f"Renderowanie klipu #{c.rank}…"):
                    rendered.append(render_clip(video, c, output, burn_subtitles=burn_subtitles))
            st.success(f"Gotowe: {len(rendered)} klipów")
            for path in rendered:
                st.video(str(path))
                st.download_button(
                    f"Pobierz {path.name}",
                    path.read_bytes(),
                    file_name=path.name,
                    mime="video/mp4",
                    key=f"download-{path.name}",
                )
        except Exception as exc:
            st.exception(exc)
