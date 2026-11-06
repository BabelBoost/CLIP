#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
command -v ffmpeg >/dev/null || { echo 'Zainstaluj ffmpeg.'; exit 1; }
command -v ffprobe >/dev/null || { echo 'Zainstaluj ffprobe.'; exit 1; }
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1 --server.maxUploadSize 500 --browser.gatherUsageStats false
