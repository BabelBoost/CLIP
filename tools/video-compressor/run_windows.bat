@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo.
  echo BLAD: Nie znaleziono Pythona.
  echo Zainstaluj Python 3.10 lub nowszy i zaznacz "Add Python to PATH".
  echo.
  pause
  exit /b 1
)

where ffmpeg >nul 2>nul
if errorlevel 1 (
  echo.
  echo BLAD: Nie znaleziono FFmpeg.
  echo.
  echo Otworz PowerShell i uruchom:
  echo winget install Gyan.FFmpeg
  echo.
  echo Po instalacji uruchom komputer lub terminal ponownie.
  echo.
  pause
  exit /b 1
)

python "%~dp0app.py"

if errorlevel 1 (
  echo.
  echo Program zakonczyl sie bledem.
  pause
)

endlocal
