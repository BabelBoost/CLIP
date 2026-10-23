@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel% == 0 (
  set PY=py -3
) else (
  set PY=python
)
if not exist ".venv\Scripts\python.exe" (
  echo Tworzenie srodowiska Python...
  %PY% -m venv .venv
  if errorlevel 1 goto error
)
echo Instalacja bibliotek. Tylko przy pierwszym uruchomieniu potrzebny jest internet.
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto error
echo Uruchamiam Babel Boost AutoClip BEZ API.
".venv\Scripts\python.exe" -m streamlit run app.py --server.address 127.0.0.1
if errorlevel 1 goto error
exit /b 0
:error
echo Nie udalo sie uruchomic. Sprawdz Python 3.10+ i polaczenie podczas instalacji.
pause
exit /b 1
