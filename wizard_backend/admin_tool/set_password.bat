@echo off
REM MAINTAINER ONLY: update the shared developer password.
REM After running this, commit & push admin_password.json.

cd /d "%~dp0"
python set_shared_password.py %*
