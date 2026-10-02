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
    package_clips,
    render_markdown,
    render_top_clips,
    save_reports,
    transcribe_video,
    write_top5_copy,
)

st.set_page_config(page_title="Viral Clip Studio 3.2", layout="wide")
st.title("Viral Clip Studio 3.2")
st.caption(
    "Wrzucasz film. Program ocenia hook, retencję, emocję, komentarze i potencjał udostępnień, "
    "odrzuca słabe fragmenty i tworzy TOP 5 gotowe do montażu."
)


def score_label(score: float, inverse: bool = False) -> str:
    value = 100 - score if inverse else score
    if value >= 80:
        return "bardzo mocny"
    if value >= 65:
        return "mocny"
    if value >= 50:
        return "średni"
    return "słaby"


with st.sidebar:
    st.header("Ustawienia")
    whisper_model = st.selectbox("Model transkrypcji", ["tiny", "base", "small", "medium"], index=2)
    language = st.selectbox("Język", ["pl", "en", "auto"], index=0)
    content_label = st.selectbox(
        "Rodzaj materiału",
        ["Auto", "Ogólny", "Polityka / publicystyka"],
        help="Tryb publicystyczny zachowuje sens wypowiedzi i nie dopisuje ocen politycznych.",
    )
    content_mode = {"Auto": "auto", "Ogólny": "general", "Polityka / publicystyka": "public_affairs"}[content_label]

    st.subheader("Scoring TikTok 3.2")
    reject_weak = st.checkbox("Odrzucaj słabe fragmenty przed TOP 5", value=True)
    min_viral_score = st.slider(
        "Minimalny Viral Score",
        min_value=40,
        max_value=85,
        value=55,
        step=1,
        disabled=not reject_weak,
        help="85+: publikuj najpierw, 70–84: dobry materiał, 55–69: popraw hook lub skróć, poniżej 55: odrzuć / przemontuj.",
    )

    st.subheader("Montaż 3.2")
    show_hook = st.checkbox("Hook przez pierwsze 3 sekundy", value=True)
    dynamic_subtitles = st.checkbox("Dynamiczne napisy", value=True)
    highlight_words = st.checkbox("Wyróżniaj aktualnie wypowiadane słowo", value=True, disabled=not dynamic_subtitles)
    auto_zoom = st.checkbox("Auto-zoom na twarz / mówcę", value=True)
    trim_silence = st.checkbox("Automatycznie usuwaj dłuższe cisze", value=True)
    silence_threshold = st.slider(
        "Cisza do wycięcia od",
        min_value=0.5,
        max_value=1.5,
        value=0.8,
        step=0.1,
        format="%.1f s",
        disabled=not trim_silence,
        help="Krótsze pauzy pozostają, żeby mowa nie brzmiała nienaturalnie.",
    )
    burn_subtitles = st.checkbox("Wypal napisy w MP4", value=True)

    st.subheader("Opcjonalne AI")
    use_ollama = st.checkbox("Ulepsz copy lokalnym Ollama", value=False)
    ollama_model = st.text_input("Model Ollama", value="qwen3:8b", disabled=not use_ollama)

uploaded = st.file_uploader("Wybierz plik wideo", type=["mp4", "mov", "mkv", "webm", "m4v"])

if uploaded:
    workspace = Path(tempfile.mkdtemp(prefix="viral_clip_studio_3_1_"))
    video_path = workspace / uploaded.name
    video_path.write_bytes(uploaded.getbuffer())
    st.video(str(video_path))

    if st.button("ANALIZUJ I STWÓRZ TOP 5 KLIPÓW", type="primary", use_container_width=True):
        progress = st.progress(0)
        status = st.empty()

        def cb(value: float, message: str) -> None:
            progress.progress(min(52, int(value * 52)))
            status.write(message)

        try:
            segments, detected = transcribe_video(
                video_path,
                model_size=whisper_model,
                language=None if language == "auto" else language,
                progress_cb=cb,
            )
            progress.progress(57)
            status.write(f"Ocena viralowa. Wykryty język: {detected or language}")

            candidates = analyze_segments(
                segments,
                top_n=10,
                content_mode=content_mode,
                min_viral_score=float(min_viral_score),
                include_weak=not reject_weak,
            )
            if not candidates:
                progress.progress(100)
                status.warning("Brak fragmentów spełniających ustawiony próg. Obniż Minimalny Viral Score albo wyłącz odrzucanie słabych fragmentów.")
                st.stop()

            if use_ollama:
                status.write("Ulepszanie hooków i opisów przez lokalny Ollama")
                candidates = enrich_with_ollama(candidates, model=ollama_model, content_mode=content_mode)

            output_root = workspace / "output"
            save_reports(candidates, output_root)
            progress.progress(64)

            rendered = []
            top5 = candidates[:5]
            for idx, clip in enumerate(top5, start=1):
                status.write(f"Montaż 3.2: klip {idx}/{len(top5)}")
                rendered.extend(
                    render_top_clips(
                        video_path,
                        [clip],
                        output_root / "clips",
                        count=1,
                        burn_subtitles=burn_subtitles,
                        show_hook=show_hook,
                        dynamic_subtitles=dynamic_subtitles,
                        segments=segments,
                        highlight_words=highlight_words,
                        auto_zoom=auto_zoom,
                        trim_silence=trim_silence,
                        silence_threshold=silence_threshold,
                    )
                )
                progress.progress(64 + int(idx / max(1, len(top5)) * 30))

            copy_files = write_top5_copy(top5, output_root / "copy", count=5)
            zip_path = package_clips(
                rendered,
                output_root / "viral_top5_tiktok_3_2.zip",
                extra_files=copy_files,
            )

            st.session_state["workspace"] = str(workspace)
            st.session_state["video_path"] = str(video_path)
            st.session_state["candidates"] = [c.to_dict() for c in candidates]
            st.session_state["rendered"] = [str(p) for p in rendered]
            st.session_state["copy_files"] = [str(p) for p in copy_files]
            st.session_state["zip_path"] = str(zip_path)
            progress.progress(100)
            status.success("Gotowe. TOP 5 przeszło scoring 3.2 i ma napisy, copy oraz paczkę ZIP.")
        except Exception as exc:
            st.exception(exc)

if st.session_state.get("candidates"):
    from viralclip.models import ClipCandidate

    candidates = [ClipCandidate(**item) for item in st.session_state["candidates"]]
    st.subheader("TOP 5")

    table = pd.DataFrame([
        {
            "#": c.rank,
            "Timecode": f"{format_time(c.start)}-{format_time(c.end)}",
            "Długość źródła": f"{c.duration:.1f}s",
            "Viral": round(c.viral_score),
            "Hook": round(c.hook_score),
            "Emocja": round(c.emotion_score),
            "Komentarze": round(c.comment_potential),
            "Retencja": round(c.retention_score),
            "Udostępnienia": round(c.share_potential),
            "Kontekst": round(c.context_dependency),
            "Status": c.quality_label,
            "Tekst na ekran": c.screen_text,
        }
        for c in candidates[:5]
    ])
    st.dataframe(table, use_container_width=True, hide_index=True)
    st.caption("Progi: 85+ publikuj najpierw, 70–84 dobry materiał, 55–69 popraw hook lub skróć. Kontekst: niższy wynik jest lepszy.")

    for c in candidates[:5]:
        with st.expander(
            f"#{c.rank}  {format_time(c.start)}-{format_time(c.end)} | Viral {c.viral_score:.0f}/100",
            expanded=c.rank == 1,
        ):
            m1, m2, m3, m4, m5, m6, m7 = st.columns(7)
            m1.metric("Viral", f"{c.viral_score:.0f}/100")
            m2.metric("Hook", f"{c.hook_score:.0f}/100")
            m3.metric("Emocja", f"{c.emotion_score:.0f}/100")
            m4.metric("Komentarze", f"{c.comment_potential:.0f}/100")
            m5.metric("Retencja", f"{c.retention_score:.0f}/100")
            m6.metric("Udostępnienia", f"{c.share_potential:.0f}/100")
            m7.metric("Kontekst", f"{c.context_dependency:.0f}/100")
            st.markdown(f"**Status:** {c.quality_label}")
            st.markdown(f"**Hook 0–3 s:** {c.hook}")
            st.markdown(f"**Tekst na ekran:** {c.screen_text}")
            st.markdown(f"**Najmocniejszy cytat:** {c.quote}")
            st.markdown(f"**Emocja:** {c.emotion}")
            st.markdown(f"**Dlaczego:** {c.reason}")
            st.markdown(f"**Opis TikTok:** {c.tiktok_description}")
            st.markdown(f"**Hashtagi:** {' '.join(c.hashtags)}")
            st.markdown(f"**CTA:** {c.cta}")

    report = render_markdown(candidates)
    st.download_button(
        "Pobierz raport Markdown",
        report.encode("utf-8"),
        "viral_report.md",
        "text/markdown",
        use_container_width=True,
    )
    st.download_button(
        "Pobierz dane JSON",
        json.dumps([c.to_dict() for c in candidates], ensure_ascii=False, indent=2).encode("utf-8"),
        "viral_report.json",
        "application/json",
        use_container_width=True,
    )

if st.session_state.get("rendered"):
    st.subheader("Gotowe MP4 do TikToka")
    copy_files = st.session_state.get("copy_files", [])
    for idx, value in enumerate(st.session_state["rendered"], start=1):
        path = Path(value)
        if path.exists():
            st.markdown(f"**Klip {idx}**")
            st.video(str(path))
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    f"Pobierz klip {idx}",
                    path.read_bytes(),
                    file_name=path.name,
                    mime="video/mp4",
                    key=f"clip-download-{idx}-{path.name}",
                    use_container_width=True,
                )
            if idx <= len(copy_files):
                copy_path = Path(copy_files[idx - 1])
                if copy_path.exists():
                    with col2:
                        st.download_button(
                            f"Pobierz opis + hashtagi {idx}",
                            copy_path.read_bytes(),
                            file_name=copy_path.name,
                            mime="text/plain",
                            key=f"copy-download-{idx}-{copy_path.name}",
                            use_container_width=True,
                        )

if st.session_state.get("zip_path"):
    zip_path = Path(st.session_state["zip_path"])
    if zip_path.exists():
        st.download_button(
            "POBIERZ TOP 5 + OPISY I HASHTAGI JAKO ZIP",
            zip_path.read_bytes(),
            file_name="viral_top5_tiktok_3_2.zip",
            mime="application/zip",
            type="primary",
            use_container_width=True,
        )
