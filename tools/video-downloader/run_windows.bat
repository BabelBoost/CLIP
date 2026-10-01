@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Babel Boost Video Downloader

echo ==========================================
echo  Babel Boost Video Downloader
echo ==========================================
echo.
echo 1. Pobierz film bezpośrednio do folderu Pobrane
echo 2. Uruchom Video Downloader 3.2 z analizą klipów
echo.
choice /c 12 /n /m "Wybierz 1 albo 2: "

if errorlevel 2 goto advanced

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0local_download.ps1"
goto end

:advanced
where python >nul 2>nul
if errorlevel 1 (
    echo.
    echo Python nie jest zainstalowany. Wybierz opcję 1, która nie wymaga Pythona.
    echo.
    pause
    goto end
)

python -m pip install -r requirements.txt
python -m streamlit run app.py

:end
