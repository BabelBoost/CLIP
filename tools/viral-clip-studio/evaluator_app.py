from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from viralclip import analyze_segments, format_time, transcribe_video
from viralclip.evaluator import CRITERIA_LABELS, evaluate_candidates, render_evaluation_markdown


st.set_page_config(page_title="Viral Video Evaluator 1.0", layout="wide")
st.title("Viral Video Evaluator 1.0")
st.caption(
    "Analizuje cały film, wyszukuje najmocniejsze fragmenty i ocenia je według 10 kryteriów "
    "pod TikTok, Reels i YouTube Shorts."
)

with st.sidebar:
    st.header("Ustawienia")
    whisper_model = st.selectbox("Model transkrypcji", ["tiny", "base", "small", "medium"], index=2)
    language = st.selectbox("Język", ["pl", "en", "auto"], index=0)
    content_label = st.selectbox(
        "Rodzaj materiału",
        ["Auto", "Ogólny", "Polityka / publicystyka"],
        help="Tryb publicystyczny zachowuje sens źródłowej wypowiedzi i nie dopisuje ocen politycznych.",
    )
    content_mode = {"Auto": "auto", "Ogólny": "general", "Polityka / publicystyka": "public_affairs"}[content_label]
    result_count = st.slider("Liczba wyników", min_value=5, max_value=20, value=10, step=1)

uploaded = st.file_uploader("Wybierz plik wideo", type=["mp4", "mov", "mkv", "webm", "m4v"])

if uploaded:
    workspace = Path(tempfile.mkdtemp(prefix="viral_video_evaluator_"))
    video_path = workspace / uploaded.name
    video_path.write_bytes(uploaded.getbuffer())
    st.video(str(video_path))

    if st.button("ANALIZUJ CAŁE WIDEO", type="primary", use_container_width=True):
        progress = st.progress(0)
        status = st.empty()

        def cb(value: float, message: str) -> None:
            progress.progress(min(58, int(value * 58)))
            status.write(message)

        try:
            segments, detected = transcribe_video(
                video_path,
                model_size=whisper_model,
                language=None if language == "auto" else language,
                progress_cb=cb,
            )
            progress.progress(64)
            status.write(f"Transkrypcja gotowa. Wykryty język: {detected or language}. Szukam fragmentów 15, 30 i 60 s.")

            candidates = analyze_segments(
                segments,
                top_n=max(60, result_count * 4),
                content_mode=content_mode,
            )
            progress.progress(82)
            status.write("Oceniam fragmenty według 10 kryteriów.")

            evaluations = evaluate_candidates(candidates, limit=result_count)
            st.session_state["evaluator_results"] = [item.to_dict() for item in evaluations]
            st.session_state["evaluator_report"] = render_evaluation_markdown(evaluations)

            progress.progress(100)
            status.success("Analiza gotowa.")
        except Exception as exc:
            st.exception(exc)

if st.session_state.get("evaluator_results"):
    results = st.session_state["evaluator_results"]
    st.subheader("Ranking fragmentów")

    table_rows = []
    for item in results:
        clip = item["clip"]
        criteria = item["criteria"]
        table_rows.append({
            "#": item["rank"],
            "Start": format_time(clip["start"]),
            "Koniec": format_time(clip["end"]),
            "Długość": f"{clip['duration']:.1f}s",
            "Wersja": f"{clip['suggested_length']}s",
            "Viral": round(item["overall_score"]),
            "Hook": round(criteria["hook_sentence"]),
            "Emocje": round(criteria["emotion"]),
            "Komentarze": round(criteria["comment_potential"]),
            "Bez kontekstu": round(criteria["standalone_context"]),
            "Tekst na ekran": clip["screen_text"],
        })

    st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

    for item in results:
        clip = item["clip"]
        criteria = item["criteria"]
        with st.expander(
            f"Klip {item['rank']} | {format_time(clip['start'])}–{format_time(clip['end'])} | Viral {item['overall_score']:.0f}/100",
            expanded=item["rank"] == 1,
        ):
            st.markdown(f"**TIMECODE START:** {format_time(clip['start'])}")
            st.markdown(f"**TIMECODE KONIEC:** {format_time(clip['end'])}")
            st.markdown(f"**DŁUGOŚĆ:** {clip['duration']:.1f} sekundy")
            st.markdown(f"**REKOMENDOWANA WERSJA:** {clip['suggested_length']} sekund")
            st.markdown(f"**CYTAT / NAJMOCNIEJSZE ZDANIE:** {clip['quote']}")
            st.markdown(f"**HOOK NA PIERWSZE 3 SEKUNDY:** {clip['hook']}")
            st.markdown(f"**TEKST NA EKRAN:** {clip['screen_text']}")
            st.markdown(f"**OCENA VIRAL:** {item['overall_score']:.0f}/100")

            st.markdown("### 10 kryteriów")
            score_rows = [
                {"Kryterium": CRITERIA_LABELS[key], "Wynik": f"{criteria[key]:.0f}/100"}
                for key in CRITERIA_LABELS
            ]
            st.dataframe(pd.DataFrame(score_rows), use_container_width=True, hide_index=True)

            st.markdown(f"**DLACZEGO TEN FRAGMENT:** {clip['reason']}")
            st.markdown(f"**SUGEROWANE CIĘCIE:** {clip['cut_before']} {clip['cut_after']}")

    report = st.session_state.get("evaluator_report", "")
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "Pobierz raport Markdown",
            report.encode("utf-8"),
            file_name="viral_video_evaluation.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with col2:
        st.download_button(
            "Pobierz dane JSON",
            json.dumps(results, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name="viral_video_evaluation.json",
            mime="application/json",
            use_container_width=True,
        )
