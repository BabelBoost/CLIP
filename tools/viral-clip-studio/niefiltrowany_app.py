from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from viralclip import analyze_segments, format_time, transcribe_video
from viralclip.evaluator import evaluate_candidates


st.set_page_config(page_title="Niefiltrowany | TikTok Clip Finder", layout="wide")
st.title("Niefiltrowany | TikTok Clip Finder")
st.caption("Znajdź mocne, samodzielne fragmenty 20–35 sekund z własnego filmu lub linku YouTube.")
st.info("Cytaty i timecode’y pochodzą z lokalnej transkrypcji Whisper. Hooki, komentarz i opis są propozycjami redakcyjnymi. Sprawdź transkrypcję przed publikacją.")


def exact_time(seconds: float) -> str:
    ms = max(0, round(float(seconds) * 1000))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, milli = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{milli:03d}"


def short_quote(text: str, words: int = 8) -> str:
    parts = text.split()
    return " ".join(parts[:words]) + ("…" if len(parts) > words else "")


def quote_start(clip, segments) -> float | None:
    target = " ".join(clip.quote.lower().split()).strip(" .,!?:;\"'„”")
    for seg in segments:
        if seg.end < clip.start or seg.start > clip.end:
            continue
        value = " ".join(seg.text.lower().split()).strip(" .,!?:;\"'„”")
        if target and target in value:
            return float(seg.start)
    return None


def download_youtube(url: str, folder: Path) -> Path:
    try:
        import yt_dlp
    except ImportError as exc:
        raise RuntimeError("Brakuje yt-dlp. Zainstaluj zależności z requirements.txt i uruchom aplikację ponownie.") from exc

    options = {
        "format": "best[ext=mp4]/best",
        "outtmpl": str(folder / "source.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "restrictfilenames": True,
    }
    with yt_dlp.YoutubeDL(options) as downloader:
        downloader.download([url])
    files = [p for p in folder.glob("source.*") if p.is_file() and not p.name.endswith(".part")]
    if not files:
        raise RuntimeError("YouTube nie zwrócił pliku wideo. Sprawdź link i dostępność filmu.")
    return max(files, key=lambda p: p.stat().st_size)


with st.sidebar:
    st.header("Ustawienia")
    source_mode = st.radio("Źródło", ["Plik wideo", "Link YouTube"])
    language = st.selectbox("Język wypowiedzi", ["pl", "en", "auto"], index=0)
    model = st.selectbox("Model transkrypcji", ["tiny", "base", "small", "medium"], index=2)
    result_count = st.slider("Liczba propozycji", 1, 5, 3)
    st.caption("Analiza działa lokalnie. Pierwsze uruchomienie może pobrać model Whisper.")

with st.form("source_form"):
    uploaded = None
    youtube_url = ""
    if source_mode == "Plik wideo":
        uploaded = st.file_uploader("Dodaj film", type=["mp4", "mov", "mkv", "webm", "m4v"])
    else:
        youtube_url = st.text_input("Wklej pełny link YouTube", placeholder="https://www.youtube.com/watch?v=...")
    submitted = st.form_submit_button("ANALIZUJ I ZNAJDŹ FRAGMENTY", type="primary", use_container_width=True)


def analyze(video_path: Path, workspace: Path) -> None:
    progress = st.progress(0)
    status = st.empty()

    def on_progress(value: float, message: str) -> None:
        progress.progress(min(55, int(value * 55)))
        status.write(message)

    segments, detected = transcribe_video(
        video_path,
        model_size=model,
        language=None if language == "auto" else language,
        progress_cb=on_progress,
    )
    progress.progress(62)
    status.write(f"Transkrypcja gotowa. Wykryty język: {detected or language}. Szukam fragmentów 20–35 s.")

    pool = analyze_segments(segments, top_n=120, content_mode="public_affairs", include_weak=True)
    eligible = [c for c in pool if 20 <= c.duration <= 35]
    if not eligible:
        st.warning("Nie znaleziono samodzielnego fragmentu o długości 20–35 sekund. Spróbuj większego pliku lub popraw transkrypcję źródłową.")
        return

    evaluated = evaluate_candidates(eligible, limit=result_count)
    rows = []
    for item in evaluated:
        c = item.clip
        rows.append({
            "#": item.rank,
            "Początek": exact_time(c.start),
            "Koniec": exact_time(c.end),
            "Długość": f"{c.duration:.1f} s",
            "Ocena montażowa": f"{item.overall_score:.0f}/100",
            "Najmocniejsza wypowiedź": c.quote,
        })

    st.session_state["niefiltrowany_results"] = [
        {"rank": item.rank, "score": item.overall_score, "clip": item.clip.to_dict(), "quote_start": quote_start(item.clip, segments)}
        for item in evaluated
    ]
    st.session_state["niefiltrowany_segments"] = [s.to_dict() for s in segments]
    st.session_state["niefiltrowany_source"] = str(video_path)
    st.session_state["niefiltrowany_duration"] = len(segments)
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    progress.progress(100)
    status.success(f"Gotowe. Wybrano {len(evaluated)} propozycji. Wynik ocenia konstrukcję klipu, nie prawdziwość wypowiedzi ani szansę na viral.")


if submitted:
    if source_mode == "Plik wideo" and uploaded is None:
        st.error("Dodaj plik wideo.")
    elif source_mode == "Link YouTube" and not youtube_url.strip():
        st.error("Wklej link YouTube.")
    else:
        workspace = Path(tempfile.mkdtemp(prefix="niefiltrowany_tiktok_"))
        try:
            if source_mode == "Plik wideo":
                suffix = Path(uploaded.name).suffix or ".mp4"
                video_path = workspace / f"source{suffix}"
                video_path.write_bytes(uploaded.getbuffer())
            else:
                video_path = download_youtube(youtube_url.strip(), workspace)
            st.video(str(video_path))
            analyze(video_path, workspace)
        except Exception as exc:
            st.error(f"Analiza nie powiodła się: {exc}")


results = st.session_state.get("niefiltrowany_results", [])
if results:
    st.header("Propozycje do @niefiltrowanypl")
    for result in results:
        clip = result["clip"]
        qstart = result.get("quote_start")
        with st.expander(f"Klip {result['rank']} | {exact_time(clip['start'])}–{exact_time(clip['end'])} | {clip['duration']:.1f} s", expanded=result["rank"] == 1):
            st.markdown(f"**Temat:** {clip['topic']}")
            st.markdown(f"**Najmocniejszy cytat ze źródła:** „{clip['quote']}”")
            if qstart is not None:
                st.caption(f"Początek cytatu według transkrypcji: {exact_time(qstart)}")
            st.markdown(f"**Ocena montażowa:** {result['score']:.0f}/100. To heurystyka, nie prognoza zasięgu.")
            if result["score"] < 55:
                st.warning("Materiał jest słaby według przyjętych kryteriów. Nie polecam publikacji bez ponownego odsłuchu i sprawdzenia kontekstu.")

            quote_hook = short_quote(clip["quote"])
            hooks = [
                ("Cytat źródłowy", quote_hook),
                ("Tekst redakcyjny", "Co wynika z tej odpowiedzi?"),
                ("Tekst redakcyjny", "Posłuchaj tej wypowiedzi do końca."),
            ]
            best_index = 0 if qstart is not None and qstart <= clip["start"] + 3 else 1
            st.markdown("**Trzy krótkie hooki na ekran:**")
            for idx, (kind, text) in enumerate(hooks):
                marker = " ← najlepszy" if idx == best_index else ""
                st.markdown(f"{idx + 1}. **{kind}:** {text}{marker}")
            if best_index == 0:
                st.caption("Cytat jest w pierwszych 3 sekundach wybranego fragmentu.")
            else:
                st.caption("Cytat pojawia się później. Na początku użyj tekstu redakcyjnego, aby nie sugerować, że rozmówca wypowiedział go wcześniej.")

            st.markdown("**Plan cięć:**")
            st.markdown(f"1. Start: **{exact_time(clip['start'])}**. Odetnij wszystko przed pierwszym słowem.")
            st.markdown("2. Zostaw wypowiedź w kolejności źródłowej. Nie wycinaj zdania, które zmienia jej sens.")
            st.markdown(f"3. Koniec: **{exact_time(clip['end'])}**. Zakończ po puencie, bez dalszego dopowiadania.")
            st.markdown("**Napisy:**")
            subtitle_lines = clip.get("subtitles", [])
            for line in subtitle_lines[:12]:
                st.write(f"{line['start']:.2f}–{line['end']:.2f} s  {line['text']}")
            if len(subtitle_lines) > 12:
                st.caption("Pozostałe linie napisów są w transkrypcji źródłowej.")

            comment = f"Moim zdaniem najmocniej wybrzmiewa tu zdanie: „{short_quote(clip['quote'], 12)}”."
            st.markdown(f"**Komentarz (propozycja, oddzielona od cytatu):** {comment}")
            st.markdown(f"**Opis:** Fragment wypowiedzi: „{short_quote(clip['quote'], 15)}”. Jak oceniasz tę argumentację po poznaniu pełnego kontekstu?")
            st.markdown("**Hashtagi:** #niefiltrowanypl #publicystyka #polityka #komentarz")

            report_lines = [
                f"Klip {result['rank']} | {exact_time(clip['start'])}–{exact_time(clip['end'])} | {clip['duration']:.1f} s",
                f"Temat: {clip['topic']}",
                f"Cytat źródłowy: {clip['quote']}",
                "Hooki: " + " | ".join(text for _, text in hooks),
                f"Komentarz: {comment}",
                f"Opis: Fragment wypowiedzi: {short_quote(clip['quote'], 15)}. Jak oceniasz tę argumentację po poznaniu pełnego kontekstu?",
                "Hashtagi: #niefiltrowanypl #publicystyka #polityka #komentarz",
                "Napisy:",
                *[f"{line['start']:.2f}-{line['end']:.2f}s {line['text']}" for line in subtitle_lines],
            ]
            st.download_button(
                "Pobierz plan tego klipu (.txt)",
                "\n".join(report_lines).encode("utf-8"),
                file_name=f"niefiltrowany_klip_{result['rank']}.txt",
                mime="text/plain",
                key=f"niefiltrowany-download-{result['rank']}",
            )
