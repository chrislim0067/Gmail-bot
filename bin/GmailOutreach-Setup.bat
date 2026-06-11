@echo off
setlocal EnableExtensions
title Gmail Outreach - Setup

cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\scripts\setup.ps1"

if errorlevel 1 (
    echo.
    echo Setup failed.
    pause
    exit /b 1
)

echo.
pause
