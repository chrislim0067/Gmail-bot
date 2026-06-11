# Start API, Celery worker, beat, and frontend (opens separate windows)
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $ProjectRoot "backend"
$Frontend = Join-Path $ProjectRoot "frontend"
$PythonPath = "$ProjectRoot;$Backend"

Write-Host "Starting Gmail Outreach stack..." -ForegroundColor Cyan

Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "`$host.UI.RawUI.WindowTitle='Gmail Outreach API'; `$env:PYTHONPATH='$PythonPath'; Set-Location '$Backend'; py -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
) -WindowStyle Normal

Start-Sleep -Seconds 2

Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "`$host.UI.RawUI.WindowTitle='Gmail Outreach Worker'; `$env:PYTHONPATH='$PythonPath'; Set-Location '$ProjectRoot'; py -m celery -A workers.celery_app worker -Q send,sync,import,health,default --loglevel=info --pool=solo"
) -WindowStyle Normal

Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "`$host.UI.RawUI.WindowTitle='Gmail Outreach Beat'; `$env:PYTHONPATH='$PythonPath'; Set-Location '$ProjectRoot'; py -m celery -A workers.celery_app beat --loglevel=info"
) -WindowStyle Normal

Start-Sleep -Seconds 1

Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "`$host.UI.RawUI.WindowTitle='Gmail Outreach Frontend'; Set-Location '$Frontend'; npm run dev"
) -WindowStyle Normal

Write-Host ""
Write-Host "  API:       http://localhost:8000/api/docs" -ForegroundColor Green
Write-Host "  Dashboard: http://localhost:3000" -ForegroundColor Green
