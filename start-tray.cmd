@echo off
setlocal
cd /d "%~dp0"

set "PYTHONW=%~dp0.venv\Scripts\pythonw.exe"
if exist "%PYTHONW%" (
    start "" "%PYTHONW%" "%~dp0tray.py"
    exit /b 0
)

where pythonw >nul 2>nul
if errorlevel 1 (
    echo pythonw.exe was not found.
    echo Run setup-windows.cmd first, or install Python 3.10+ and make pythonw available.
    pause
    exit /b 1
)

start "" pythonw "%~dp0tray.py"
exit /b 0
