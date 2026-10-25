@echo off
setlocal EnableExtensions
cd /d "%~dp0"

title Babel Boost Social Shorts Maker

echo ================================================
echo    Babel Boost Social Shorts Maker
echo ================================================
echo.

py -3.12 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3.12"
    goto python_selected
)
py -3.11 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3.11"
    goto python_selected
)
python --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    goto python_selected
)
goto no_python

:python_selected
echo Wybrany Python:
%PYTHON_CMD% --version
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info[:2] in ((3,11),(3,12)) else 1)"
    if errorlevel 1 (
        echo Usuwam srodowisko z nieobslugiwana wersja Pythona...
        rmdir /s /q ".venv"
    )
)

if not exist ".venv\Scripts\python.exe" (
    echo Tworze srodowisko aplikacji...
    %PYTHON_CMD% -m venv ".venv"
    if errorlevel 1 goto setup_error
)

echo Instalacja wymaganych bibliotek. Przy pierwszym uruchomieniu moze to potrwac kilka minut.
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto setup_error
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto setup_error

where ffmpeg >nul 2>&1
if errorlevel 1 (
    echo.
    echo UWAGA: Nie znaleziono FFmpeg.
    echo Aplikacja sie otworzy, ale montaz klipow wymaga FFmpeg.
    echo Zainstaluj go poleceniem: winget install Gyan.FFmpeg
    echo Potem uruchom ponownie ten plik.
    echo.
)

echo Uruchamiam aplikacje. Nie zamykaj tego okna podczas pracy.
echo.
".venv\Scripts\python.exe" -m streamlit run app.py
if errorlevel 1 goto run_error
goto end

:no_python
echo Nie znaleziono Pythona 3.11 ani 3.12.
echo Zainstaluj Python 3.12 z https://www.python.org/downloads/
echo Podczas instalacji zaznacz "Add Python to PATH".
goto failed

:setup_error
echo.
echo Instalacja srodowiska lub bibliotek nie powiodla sie.
echo Sprawdz polaczenie z internetem i komunikat bledu powyzej.
goto failed

:run_error
echo.
echo Aplikacja zakonczyla prace z bledem. Szczegoly sa powyzej.
goto failed

:failed
echo.
pause
exit /b 1

:end
pause
