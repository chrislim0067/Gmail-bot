@echo off
setlocal EnableExtensions
title Gmail Outreach - Stop

cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\scripts\stop-all.ps1"
exit
