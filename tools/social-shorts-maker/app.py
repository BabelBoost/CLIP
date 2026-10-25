from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

import streamlit as st

APP_DIR = Path(__file__).resolve().parent
JOB_ROOT = Path(tempfile.gettempdir()) / "babel_social_shorts_jobs"
JOB_ROOT.mkdir(parents=True, exist_ok=True)
WORKER = APP_DIR / "worker.py"

for old_job in JOB_ROOT.iterdir():
    try:
        if old_job.is_dir() and time.time() - old_job.stat().st_mtime > 7 * 24 * 60 * 60:
            shutil.rmtree(old_job, ignore_errors=True)
    except OSError:
        pass

st.set_page_config(page_title="Babel Boost Social Shorts Maker", page_icon="✂️", layout="wide")
st.title("Babel Boost Social Shorts Maker")
st.caption("Z długiego filmu do krótkich klipów na TikTok, X, Facebook Reels i YouTube Shorts.")
st.info(
    "Przetwarzaj materiały, które należą do Ciebie albo do których masz zgodę. "
    "Aplikacja nie omija zabezpieczeń ani DRM. Wynik rankingu jest wskazówką, nie obietnicą zasięgu."
)


def read_job(job_id: str) -> tuple[Path, dict] | tuple[None, None]:
    if not job_id or not all(char in "0123456789abcdef" for char in job_id) or len(job_id) != 32:
        return None, None
    folder = JOB_ROOT / job_id
    state_file = folder / "job.json"
    if not state_file.is_file():
        return None, None
    try:
        return folder, json.loads(state_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return folder, None


def write_job(path: Path, value: dict) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


with st.sidebar:
    st.header("Ustawienia klipów")
    editorial_format = st.selectbox(
        "Format analizy",
        ["TikTok @niefiltrowanypl · 20–35 s", "Uniwersalny short"],
    )
    niefiltrowany_mode = editorial_format.startswith("TikTok")
    language_label = st.selectbox("Język filmu", ["Automatycznie", "Polski", "English", "Íslenska"])
    language = {"Automatycznie": None, "Polski": "pl", "English": "en", "Íslenska": "is"}[language_label]
    whisper_model = st.selectbox("Model transkrypcji", ["tiny", "base", "small"], index=1)
    content_label = st.selectbox("Rodzaj materiału", ["Ogólny", "Polityka / publicystyka"])
    content_mode = "public_affairs" if niefiltrowany_mode or content_label.startswith("Polityka") else "general"
    clip_count = st.slider("Maksymalna liczba klipów", 1, 5, 5)
    min_score = st.slider("Minimalny Viral Score", 40, 85, 55)
    targets = st.multiselect(
        "Platformy do przygotowania",
        ["TikTok", "X", "Facebook Reels", "YouTube Shorts"],
        default=["TikTok", "X", "Facebook Reels", "YouTube Shorts"],
    )
    burn_subtitles = st.checkbox("Wypal napisy w klipach", value=True)
    show_hook = st.checkbox("Pokaż hook na początku", value=True)
    dynamic_subtitles = st.checkbox("Dynamiczne napisy", value=True)
    auto_zoom = st.checkbox("Kadruj na mówcę", value=True)
    trim_silence = st.checkbox("Wycinaj dłuższe cisze", value=True)

if niefiltrowany_mode:
    st.caption("Tryb @niefiltrowanypl szuka fragmentów 20–35 s, w których główne zdanie pada na początku.")

source_kind_label = st.radio("Źródło filmu", ["Link YouTube", "Prześlij plik"], horizontal=True)
youtube_url = ""
uploaded = None
if source_kind_label == "Link YouTube":
    youtube_url = st.text_input("Link do filmu", placeholder="https://www.youtube.com/watch?v=...")
    st.caption("Obsługiwane są publiczne linki YouTube dostępne bez omijania zabezpieczeń.")
else:
    uploaded = st.file_uploader(
        "Wybierz długi film",
        type=["mp4", "mov", "mkv", "webm", "m4v"],
        help="Maksymalny rozmiar pliku: 1 GB. Film jest obrabiany lokalnie.",
    )

has_source = bool(youtube_url.strip()) if source_kind_label == "Link YouTube" else uploaded is not None

if st.button(
    "URUCHOM ANALIZĘ I TWORZENIE KLIPÓW",
    type="primary",
    use_container_width=True,
    disabled=(not targets or not has_source),
):
    job_id = uuid.uuid4().hex
    job_dir = JOB_ROOT / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    state = {
        "job_id": job_id,
        "status": "queued",
        "message": "Zadanie czeka na uruchomienie…",
        "progress": 0,
        "created_at": __import__("time").time(),
        "source_kind": "youtube" if source_kind_label == "Link YouTube" else "upload",
        "youtube_url": youtube_url.strip() if source_kind_label == "Link YouTube" else "",
        "upload_path": "",
        "niefiltrowany_mode": niefiltrowany_mode,
        "language": language,
        "whisper_model": whisper_model,
        "content_mode": content_mode,
        "clip_count": clip_count,
        "min_score": min_score,
        "targets": targets,
        "burn_subtitles": burn_subtitles,
        "show_hook": show_hook,
        "dynamic_subtitles": dynamic_subtitles,
        "auto_zoom": auto_zoom,
        "trim_silence": trim_silence,
    }
    try:
        if uploaded is not None and source_kind_label == "Prześlij plik":
            input_path = job_dir / Path(uploaded.name).name
            uploaded.seek(0)
            with input_path.open("wb") as destination:
                shutil.copyfileobj(uploaded, destination, length=8 * 1024 * 1024)
            state["upload_path"] = str(input_path)

        state_path = job_dir / "job.json"
        write_job(state_path, state)
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        with (job_dir / "worker.log").open("ab") as log_file:
            subprocess.Popen(
                [sys.executable, str(WORKER), "--job-dir", str(job_dir)],
                cwd=APP_DIR,
                stdin=subprocess.DEVNULL,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                creationflags=flags,
                close_fds=(os.name != "nt"),
            )
        st.query_params["job"] = job_id
        st.rerun()
    except Exception as exc:
        state.update(status="error", message=f"Nie udało się uruchomić zadania: {exc}", progress=100)
        write_job(job_dir / "job.json", state)

job_id = st.query_params.get("job", "")
job_dir, initial_state = read_job(job_id) if job_id else (None, None)
if job_id and job_dir is None:
    st.warning("Nie znaleziono zadania. Uruchom analizę ponownie.")

def show_completed(job_id: str, job_dir: Path, state: dict) -> None:
    st.success("Gotowe. Wynik został zapisany.")
    rows = state.get("candidates", [])
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    report_path = Path(state["report_path"]) if state.get("report_path") else None
    if report_path and report_path.is_file():
        report = report_path.read_text(encoding="utf-8")
        st.markdown(report)
        st.download_button(
            "Pobierz plan TikToka @niefiltrowanypl",
            report.encode("utf-8"),
            file_name=report_path.name,
            mime="text/markdown",
            key=f"report-{job_id}",
        )
    for index, value in enumerate(state.get("rendered_files", []), start=1):
        video_path = Path(value)
        if video_path.is_file():
            st.markdown(f"**Klip {index}**")
            st.video(str(video_path))
            st.download_button(
                f"Pobierz klip {index}",
                video_path.read_bytes(),
                file_name=video_path.name,
                mime="video/mp4",
                key=f"clip-{job_id}-{index}",
                use_container_width=True,
            )
    zip_path = Path(state["zip_path"]) if state.get("zip_path") else None
    if zip_path and zip_path.is_file():
        st.download_button(
            "POBIERZ PACZKĘ KLIPÓW",
            zip_path.read_bytes(),
            file_name=zip_path.name,
            mime="application/zip",
            type="primary",
            key=f"zip-{job_id}",
            use_container_width=True,
        )


if job_dir is not None and initial_state:
    st.divider()
    st.subheader("Postęp zadania")
    job_status = initial_state.get("status")
    if job_status in {"queued", "running"}:
        @st.fragment(run_every="2s")
        def show_job_progress():
            _, current = read_job(job_id)
            if not current:
                st.error("Nie można odczytać stanu zadania.")
                return
            if current.get("status") not in {"queued", "running"}:
                st.rerun(scope="app")
                return
            st.write(current.get("message", "Przetwarzanie…"))
            st.progress(int(current.get("progress", 0)) / 100)
            st.caption("Zadanie działa osobno. Możesz odświeżyć stronę lub wrócić później.")

        show_job_progress()
    elif job_status == "no_clips":
        st.warning(initial_state.get("message", "Nie znaleziono odpowiedniego fragmentu."))
    elif job_status == "error":
        st.error(f"Przetwarzanie przerwane: {initial_state.get('message', 'Nieznany błąd')}")
        log_path = job_dir / "worker.log"
        if log_path.exists():
            try:
                tail = log_path.read_text(encoding="utf-8", errors="replace")[-4000:]
                if tail.strip():
                    with st.expander("Szczegóły błędu"):
                        st.code(tail)
            except OSError:
                pass
    elif job_status == "complete":
        show_completed(job_id, job_dir, initial_state)

st.caption("Przetwarzanie działa osobno. Postęp i gotowe pliki są zachowywane, gdy strona zostanie odświeżona.")
