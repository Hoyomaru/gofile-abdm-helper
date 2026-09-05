@echo off
cd /d "%~dp0"
where pythonw >nul 2>nul
if errorlevel 1 (
    echo pythonw.exe was not found in PATH.
    echo Install Python and make sure Python is available from the command line.
    pause
    exit /b 1
)
start "" pythonw "%~dp0tray.py"
exit /b 0
