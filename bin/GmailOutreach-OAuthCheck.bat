@echo off
setlocal EnableExtensions
title Gmail Outreach - OAuth Check

cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\scripts\oauth-check.ps1"
pause
