@echo off
setlocal
chcp 65001 >nul
title Medical Record System - Start Demo
cd /d "%~dp0"

echo Starting the medical record system. Please wait...
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-all.ps1" -EnableDemoUser -OpenBrowser
set "RESULT=%ERRORLEVEL%"

echo.
if not "%RESULT%"=="0" (
    echo Startup failed. See the error above and logs in .runtime\logs.
    echo.
    pause
    exit /b %RESULT%
)

echo Demo username: demo
echo Demo password: demo123456
echo URL: http://127.0.0.1:5173/
echo.
echo This window will close automatically. The services will keep running.
timeout /t 8 /nobreak >nul
exit /b 0
