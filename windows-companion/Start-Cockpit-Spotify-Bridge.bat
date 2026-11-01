@echo off
setlocal
cd /d "%~dp0"
py -3 -c "import sys; assert sys.version_info >= (3,11)" >nul 2>&1
if errorlevel 1 (
  echo Cockpit Spotify Bridge requires Python 3.11 or later.
  echo Download the official Windows installer: https://www.python.org/downloads/windows/
  echo During setup, enable "Add python.exe to PATH".
  pause
  exit /b 1
)
if not exist .venv\Scripts\python.exe (
  py -3 -m venv .venv || (echo Could not create the local Python environment.& pause & exit /b 1)
)
.venv\Scripts\python.exe -m pip install --disable-pip-version-check -r requirements.txt || (echo Dependency installation failed.& pause & exit /b 1)
.venv\Scripts\python.exe companion.py
pause
