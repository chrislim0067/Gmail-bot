@echo off
setlocal EnableExtensions
set "URL=%~1"
if "%URL%"=="" set "URL=http://localhost:3000"

set "CHROME="

if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" (
    set "CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
)
if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" (
    set "CHROME=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
)
if exist "%LocalAppData%\Google\Chrome\Application\chrome.exe" (
    set "CHROME=%LocalAppData%\Google\Chrome\Application\chrome.exe"
)

if not defined CHROME (
    echo ERROR: Google Chrome not found.
    echo Install Chrome from https://www.google.com/chrome/
    echo Then open manually: %URL%
    exit /b 1
)

start "" "%CHROME%" "%URL%"
exit /b 0
