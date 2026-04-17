@echo off
REM setup_domain.bat – Doppelklick-Wrapper fuer setup_domain.ps1
REM 
REM Fuehrt alle SSH-Schritte aus (Port-Freigaben auf der VM, Nginx Proxy, Let's Encrypt SSL Certbot).
REM
REM Einstellungen koennen Sie ueber die deploy.config.json anpassen,
REM in der Sie zusaetzlich "Domain": "ihrecoolenamen.com" (ohne www.) eintragen muessen.

setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_domain.ps1" %*
set RC=%ERRORLEVEL%
echo.
if %RC% NEQ 0 (
    echo [Domain-Setup fehlgeschlagen – Exit %RC%]
) else (
    echo [Domain-Setup erfolgreich]
)
pause
exit /b %RC%
