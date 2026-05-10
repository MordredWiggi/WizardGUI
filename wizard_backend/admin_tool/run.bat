@echo off
REM Wizard Admin Tool launcher (Windows).
REM Uses pythonw so no console window stays open in the background.
REM "start" detaches the process and lets the cmd shell exit immediately.

cd /d "%~dp0"
start "" pythonw main.py %*
exit /b
