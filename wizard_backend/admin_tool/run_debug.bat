@echo off
REM Wizard Admin Tool launcher with visible console (for debugging).
REM Uses regular python so you can see Python errors / tracebacks.

cd /d "%~dp0"
python main.py %*
pause
