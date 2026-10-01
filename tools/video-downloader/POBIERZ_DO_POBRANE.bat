@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Babel Boost - Pobierz do Pobrane
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0local_download.ps1"
