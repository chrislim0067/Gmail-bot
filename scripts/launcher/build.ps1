# Build GmailOutreach-Setup.exe, GmailOutreach-Start.exe, GmailOutreach-Stop.exe
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$LauncherDir = $PSScriptRoot
$BinDir = Join-Path $ProjectRoot "bin"
$LauncherPy = Join-Path $LauncherDir "launcher.py"

Write-Host "=== Building Gmail Outreach launchers ===" -ForegroundColor Cyan

if (-not (Test-Path $BinDir)) {
    New-Item -ItemType Directory -Path $BinDir | Out-Null
}

py -m pip install pyinstaller --quiet

$commonArgs = @(
    "--onefile",
    "--console",
    "--clean",
    "--noconfirm",
    "--distpath", $BinDir,
    "--workpath", (Join-Path $ProjectRoot ".runtime\pyinstaller-work"),
    "--specpath", (Join-Path $ProjectRoot ".runtime\pyinstaller-spec")
)

function Build-Launcher($Name) {
    Write-Host "Building $Name.exe ..."
    py -m PyInstaller @commonArgs `
        --name $Name `
        $LauncherPy
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed for $Name" }
}

Build-Launcher "GmailOutreach-Setup"
Build-Launcher "GmailOutreach-Start"
Build-Launcher "GmailOutreach-Stop"

Write-Host ""
Write-Host "Done. Executables are in:" -ForegroundColor Green
Write-Host "  $BinDir"
Write-Host ""
Write-Host "  GmailOutreach-Setup.exe  - run once (install deps + database)"
Write-Host "  GmailOutreach-Start.exe  - start API, workers, and dashboard"
Write-Host "  GmailOutreach-Stop.exe   - stop all services"
