@echo off
setlocal EnableExtensions
title Gmail Outreach - Reset Send History

cd /d "%~dp0.."

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\scripts\reset-send-history.ps1"
echo.
pause
