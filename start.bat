@echo off
cd /d "%~dp0"
title ClipClover
echo.
echo   ClipClover calisiyor.
echo.
echo   Site:     https://shorts-clipper-seven.vercel.app
echo   ya da:    http://localhost:8000
echo.
echo   Bu pencereyi kapatinca durur.
echo.
if exist ".venv\Scripts\python.exe" (
  .venv\Scripts\python.exe serve.py
) else (
  python serve.py
)
echo.
echo   Sunucu durdu.
pause
