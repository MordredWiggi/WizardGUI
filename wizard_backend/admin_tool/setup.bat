@echo off
REM Wizard Admin Tool setup (Windows)
REM Creates / updates the developer password and DB connections.

cd /d "%~dp0"
python setup_admin.py %*
