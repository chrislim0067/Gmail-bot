# Start Gmail Outreach services in separate console windows and record PIDs
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $ProjectRoot "backend"
$Frontend = Join-Path $ProjectRoot "frontend"
$PythonPath = "$ProjectRoot;$Backend"
$RunDir = Join-Path $ProjectRoot ".run"
$PidFile = Join-Path $RunDir "service-pids.txt"

New-Item -ItemType Directory -Force -Path $RunDir | Out-Null

function Start-ServiceConsole {
    param(
        [string]$Title,
        [string]$WorkDir,
        [string]$Command
    )
    $cmdLine = "title $Title && cd /d `"$WorkDir`" && $Command"
    $proc = Start-Process -FilePath "cmd.exe" -ArgumentList "/k", $cmdLine -PassThru -WindowStyle Normal
    Start-Sleep -Milliseconds 800

    $console = Get-Process cmd -ErrorAction SilentlyContinue | Where-Object {
        $_.MainWindowTitle -like "$Title*"
    } | Select-Object -First 1

    if ($console) { return $console.Id }
    return $proc.Id
}

Write-Host "Starting Gmail Outreach stack..." -ForegroundColor Cyan

$pids = @()
$pids += Start-ServiceConsole -Title "Gmail Outreach API" -WorkDir $Backend -Command "set PYTHONPATH=$PythonPath&& py -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
Start-Sleep -Seconds 1
$pids += Start-ServiceConsole -Title "Gmail Outreach Worker" -WorkDir $ProjectRoot -Command "set PYTHONPATH=$PythonPath&& py -m celery -A workers.celery_app worker -Q send,sync,import,health,default --loglevel=info --pool=solo"
$pids += Start-ServiceConsole -Title "Gmail Outreach Beat" -WorkDir $ProjectRoot -Command "set PYTHONPATH=$PythonPath&& py -m celery -A workers.celery_app beat --loglevel=info"
Start-Sleep -Seconds 1
$pids += Start-ServiceConsole -Title "Gmail Outreach Frontend" -WorkDir $Frontend -Command "npm run dev"

$pids | Where-Object { $_ -gt 0 } | Set-Content $PidFile -Encoding ASCII

Write-Host ""
Write-Host "  API:       http://localhost:8000/api/docs" -ForegroundColor Green
Write-Host "  Dashboard: http://localhost:3000" -ForegroundColor Green
Write-Host ""
