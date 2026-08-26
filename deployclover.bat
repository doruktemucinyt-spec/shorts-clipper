@echo off
cd /d "%~dp0"
echo Site yeniden uretiliyor...
python build_site.py || goto :hata
echo.
echo Vercel'e yayinlaniyor...
npx --yes vercel deploy shorts-clipper --prod --yes
echo.
pause
exit /b

:hata
echo Site uretilemedi.
pause
