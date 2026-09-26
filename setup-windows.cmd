@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup-windows.ps1"
if errorlevel 1 (
    echo.
    echo Setup failed. Review the error above.
    pause
    exit /b 1
)
exit /b 0
