@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Viral Clip Studio 3.1

cls
echo ==========================================
echo        VIRAL CLIP STUDIO 3.1
echo ==========================================
echo.
echo Sprawdzam wymagania...

where ffmpeg >nul 2>nul
if errorlevel 1 goto :no_ffmpeg

set "PY_CMD="
py -3.12 --version >nul 2>nul
if not errorlevel 1 set "PY_CMD=py -3.12"

if not defined PY_CMD (
  py -3.11 --version >nul 2>nul
  if not errorlevel 1 set "PY_CMD=py -3.11"
)

if not defined PY_CMD (
  python -c "import sys; raise SystemExit(0 if (3,11) <= sys.version_info[:2] < (3,13) else 1)" >nul 2>nul
  if not errorlevel 1 set "PY_CMD=python"
)

if not defined PY_CMD goto :no_python

echo [OK] FFmpeg znaleziony.
echo [OK] Python 3.11 lub 3.12 znaleziony.
echo.

if not exist ".venv\Scripts\python.exe" (
  echo Pierwsze uruchomienie. Tworze srodowisko programu...
  %PY_CMD% -m venv .venv
  if errorlevel 1 goto :failed
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 goto :failed

echo Aktualizuje instalator pakietow...
python -m pip install --upgrade pip
if errorlevel 1 goto :failed

echo Sprawdzam i instaluje wymagane biblioteki...
python -m pip install -r requirements.txt
if errorlevel 1 goto :failed

echo.
echo ==========================================
echo Program jest gotowy.
echo Za chwile otworzy sie w przegladarce.
echo Nie zamykaj tego okna podczas pracy.
echo ==========================================
echo.

python -m streamlit run app.py
if errorlevel 1 goto :failed

goto :end

:no_python
cls
echo ==========================================
echo BRAK PYTHONA 3.11 LUB 3.12
echo ==========================================
echo.
echo Zainstaluj Python 3.12 z python.org.
echo Podczas instalacji zaznacz opcje "Add Python to PATH".
echo Potem uruchom ten plik ponownie.
echo.
pause
goto :end

:no_ffmpeg
cls
echo ==========================================
echo BRAK FFMPEG
echo ==========================================
echo.
echo Viral Clip Studio potrzebuje FFmpeg do ciecia i renderowania wideo.
echo Najprosciej zainstalowac go w Terminalu Windows poleceniem:
echo.
echo winget install Gyan.FFmpeg

echo Po instalacji zamknij i otworz ponownie Terminal lub komputer,
echo a potem uruchom run_windows.bat jeszcze raz.
echo.
pause
goto :end

:failed
echo.
echo ==========================================
echo WYSTAPIL BLAD PODCZAS URUCHAMIANIA
echo ==========================================
echo.
echo Zrob zrzut ekranu tego okna i wyslij mi go.
echo Nie musisz sam szukac przyczyny.
echo.
pause

:end
endlocal
