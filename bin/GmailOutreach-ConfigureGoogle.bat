@echo off
setlocal EnableExtensions
title Gmail Outreach - Configure Google OAuth

cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\scripts\configure-google.ps1"

if errorlevel 1 (
    echo.
    echo Configuration failed.
    pause
    exit /b 1
)

echo.
pause
