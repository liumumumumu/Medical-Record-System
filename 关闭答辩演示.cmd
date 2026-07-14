@echo off
setlocal
chcp 65001 >nul
title Medical Record System - Stop Demo
cd /d "%~dp0"

echo Stopping the medical record system...
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop-all.ps1"
set "RESULT=%ERRORLEVEL%"

echo.
if not "%RESULT%"=="0" (
    echo Stop reported a problem and refused to kill any unverified process.
    echo.
    pause
    exit /b %RESULT%
)

echo Shutdown complete.
timeout /t 3 /nobreak >nul
exit /b 0
