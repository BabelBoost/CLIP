@echo off
cd /d "%~dp0"
where py >nul 2>&1
if errorlevel 1 (
 echo Zainstaluj Python 3.11 lub 3.12 i dodaj do PATH.
 pause
 exit /b 1
)
py -m pip install -r requirements.txt
py app.py
pause
