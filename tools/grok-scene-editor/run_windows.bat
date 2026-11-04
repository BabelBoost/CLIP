@echo off
cd /d "%~dp0"
py -3 scene_editor.py
if errorlevel 1 pause
