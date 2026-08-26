@echo off
cd /d "%~dp0"
title Shorts Clipper kurulumu
where python >nul 2>&1
if errorlevel 1 (
  echo.
  echo   Once Python kurman gerekiyor: https://www.python.org/downloads/
  echo   Kurarken "Add python.exe to PATH" kutusunu isaretle.
  echo.
  pause
  exit /b
)
python install.py
