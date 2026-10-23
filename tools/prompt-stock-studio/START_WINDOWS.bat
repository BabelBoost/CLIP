@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  set "PY=py -3"
) else (
  set "PY=python"
)
if not exist ".venv\Scripts\python.exe" (
  echo Tworzenie srodowiska Python...
  %PY% -m venv .venv
  if errorlevel 1 goto failed
)
echo Instalacja / aktualizacja bibliotek...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo Otwieram aplikacje w przegladarce...
".venv\Scripts\python.exe" -m streamlit run app.py --server.address 127.0.0.1
if errorlevel 1 goto failed
exit /b 0
:failed
echo.
echo Nie udalo sie uruchomic. Upewnij sie, ze masz Python 3.10+ i internet.
pause
exit /b 1
