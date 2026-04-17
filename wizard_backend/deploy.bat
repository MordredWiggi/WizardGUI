@echo off
REM deploy.bat – Doppelklick-Wrapper fuer deploy.ps1
REM Laedt das Backend hoch und startet den Wizard-Leaderboard-Dienst auf der Oracle VM neu.
REM
REM Einstellungen (SSH-Key, Host, User) entweder:
REM   1) per Kommandozeile:   deploy.bat -SshKey "C:\Pfad\zum\key"
REM   2) oder dauerhaft in    deploy.config.json  (siehe deploy.config.example.json)

setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0deploy.ps1" %*
set RC=%ERRORLEVEL%
echo.
if %RC% NEQ 0 (
    echo [Deploy fehlgeschlagen – Exit %RC%]
) else (
    echo [Deploy erfolgreich]
)
pause
exit /b %RC%
