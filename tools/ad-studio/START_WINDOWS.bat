@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
 echo Zainstaluj Python 3.11 lub 3.12 z python.org, wraz z Python Launcher.
 pause
 exit /b 1
)
where ffmpeg >nul 2>nul
if errorlevel 1 (
 echo Brak FFmpeg. W terminalu uruchom: winget install --id Gyan.FFmpeg -e
 echo Po instalacji zamknij i ponownie otworz ten plik.
 pause
 exit /b 1
)
where ffprobe >nul 2>nul
if errorlevel 1 (
 echo Brak ffprobe. Zainstaluj pelny pakiet FFmpeg.
 pause
 exit /b 1
)
if not exist .venv\Scripts\python.exe py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
 pause
 exit /b 1
)
.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.maxUploadSize 500 --browser.gatherUsageStats false
pause
