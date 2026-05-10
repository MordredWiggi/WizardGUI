@echo off
REM Wizard Admin Tool launcher (Windows)
REM Switches to the script directory and starts the tool.

cd /d "%~dp0"
python main.py %*
