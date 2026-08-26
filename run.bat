@echo off
cd /d "%~dp0"
title Shorts Clipper
echo Shorts Clipper baslatiliyor...
start "" http://localhost:8000
python serve.py
pause
