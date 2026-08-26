@echo off
cd /d "%~dp0"
title Shorts Clipper
echo Shorts Clipper baslatiliyor...
start "" http://localhost:8000
if exist ".venv\Scripts\python.exe" (
  .venv\Scripts\python.exe serve.py
) else (
  python serve.py
)
pause
