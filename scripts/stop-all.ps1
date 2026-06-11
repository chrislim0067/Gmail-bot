# Stop Gmail Outreach services and close ALL related desktop console windows
$ErrorActionPreference = "SilentlyContinue"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PidFile = Join-Path $ProjectRoot ".run\service-pids.txt"

Write-Host ""
Write-Host "Stopping Gmail Outreach services..." -ForegroundColor Cyan
Write-Host ""

function Stop-ProcessTree {
    param([int]$ProcessId, [string]$Label)
    if ($ProcessId -le 0) { return }
    $null = & taskkill.exe /F /T /PID $ProcessId 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Closed: $Label (PID $ProcessId)"
    }
}

function Close-GmailOutreachConsoles {
    param([int[]]$ExcludePids = @())
    Get-Process cmd, powershell, pwsh -ErrorAction SilentlyContinue | Where-Object {
        $_.MainWindowTitle -like "Gmail Outreach*" -and ($ExcludePids -notcontains $_.Id)
    } | ForEach-Object {
        Stop-ProcessTree -ProcessId $_.Id -Label $_.MainWindowTitle
    }
}

# 1) Close every visible Gmail Outreach console (API, Worker, Beat, Frontend, Start, Health Check, etc.)
Close-GmailOutreachConsoles -ExcludePids @($PID)

# 2) PIDs saved when Start.bat runs
if (Test-Path $PidFile) {
    Get-Content $PidFile | ForEach-Object {
        if ($_ -match '^\d+$') {
            Stop-ProcessTree -ProcessId ([int]$_) -Label "saved PID $_"
        }
    }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}

# 3) Kill service processes by command line
$commandPatterns = @(
    'uvicorn\s+app\.main:app',
    'celery\s+-A\s+workers\.celery_app\s+worker',
    'celery\s+-A\s+workers\.celery_app\s+beat',
    'workers\.celery_app',
    'next(\.cmd)?\s+dev',
    'npm(\.cmd)?\s+run\s+dev'
)

Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and (
        ($_.CommandLine -like "*$ProjectRoot*") -or
        ($_.CommandLine -match ($commandPatterns -join '|'))
    )
} | Where-Object {
    $_.Name -match '^(python|py|pythonw|node|celery)\.exe$'
} | ForEach-Object {
    Stop-ProcessTree -ProcessId $_.ProcessId -Label "$($_.Name) service"
}

# 4) Free ports 8000 and 3000
foreach ($port in @(8000, 3000)) {
    $connections = netstat -ano | Select-String ":$port\s+.*LISTENING"
    foreach ($line in $connections) {
        $parts = ($line -split '\s+') | Where-Object { $_ -ne '' }
        $listenerPid = $parts[-1]
        if ($listenerPid -match '^\d+$' -and [int]$listenerPid -gt 0) {
            Stop-ProcessTree -ProcessId ([int]$listenerPid) -Label "port $port listener"
        }
    }
}

# 5) Second pass on consoles
Start-Sleep -Milliseconds 400
Close-GmailOutreachConsoles -ExcludePids @($PID)

Write-Host ""
Write-Host "All Gmail Outreach consoles closed." -ForegroundColor Green
Write-Host ""

# 6) Final sweep after this script exits — closes Stop / Start / Health Check windows too
$sweepFile = Join-Path $env:TEMP "gmail-outreach-stop-sweep.ps1"
@'
Start-Sleep -Milliseconds 800
Get-Process cmd, powershell, pwsh -ErrorAction SilentlyContinue |
  Where-Object { $_.MainWindowTitle -like "Gmail Outreach*" } |
  ForEach-Object { taskkill /F /T /PID $_.Id 2>$null | Out-Null }
'@ | Set-Content -Path $sweepFile -Encoding UTF8

Start-Process -FilePath "powershell.exe" -WindowStyle Hidden -ArgumentList @(
    "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $sweepFile
) | Out-Null
