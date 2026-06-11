@echo off
setlocal EnableExtensions
title Gmail Outreach - Start

cd /d "%~dp0.."
set "PROJECT_ROOT=%CD%"
set "PYTHONPATH=%PROJECT_ROOT%;%PROJECT_ROOT%\backend"

echo Running health check before start...
call "%~dp0GmailOutreach-Check.bat" nopause
if errorlevel 1 (
    echo.
    echo Start cancelled. Fix the issues above, then try again.
    pause
    exit /b 1
)

echo.
echo Starting Gmail Outreach...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\scripts\start-services.ps1"
if errorlevel 1 (
    echo.
    echo Start failed.
    pause
    exit /b 1
)

echo To stop everything, run GmailOutreach-Stop.bat
echo.
echo Waiting 15 seconds for frontend to start...
timeout /t 15 /nobreak >nul

echo Opening dashboard in Google Chrome...
call "%~dp0_open-browser.bat" "http://localhost:3000"
if errorlevel 1 (
    echo.
    echo Chrome is required. Install it, then open:
    echo   http://localhost:3000
    goto :done
)

echo.
echo If Chrome did not open, copy this URL into Chrome:
echo   http://localhost:3000
echo.
:done
echo Keep the 4 "Gmail Outreach" windows open while using the app.
echo.
pause
