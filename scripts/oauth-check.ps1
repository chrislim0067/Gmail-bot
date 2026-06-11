# Print exact OAuth settings and open Google client editor
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host ""
Write-Host "=== Gmail OAuth diagnostic ===" -ForegroundColor Cyan
Write-Host ""

try {
    $info = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/gmail/connect-info" -TimeoutSec 5
} catch {
    Write-Host "ERROR: API is not running on http://localhost:8000" -ForegroundColor Red
    Write-Host "Run GmailOutreach-Start.bat first, then run this check again."
    exit 1
}

Write-Host "App configuration (what Google receives):" -ForegroundColor Yellow
Write-Host "  Client ID:    $($info.google_client_id)"
Write-Host "  Redirect URI: $($info.redirect_uri)"
Write-Host "  Mock mode:    $($info.use_mock_gmail)"
Write-Host ""
Write-Host "Add BOTH of these under Authorized redirect URIs in Google Console:" -ForegroundColor Yellow
foreach ($uri in $info.redirect_uris_for_google_console) {
    Write-Host "  $uri" -ForegroundColor Green
}
Write-Host ""
Write-Host "IMPORTANT:" -ForegroundColor Red
Write-Host "  - Use Authorized redirect URIs (NOT JavaScript origins)"
Write-Host "  - Click Save at the bottom of the client page"
Write-Host "  - Wait 2 minutes before trying Connect with Google again"
Write-Host ""

$open = Read-Host "Open your OAuth client in Chrome now? [Y/n]"
if ($open -ne "n" -and $open -ne "N") {
    $url = $info.google_client_edit_url
    $chromePaths = @(
        "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe",
        "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
        "$env:LocalAppData\Google\Chrome\Application\chrome.exe"
    )
    $opened = $false
    foreach ($path in $chromePaths) {
        if (Test-Path $path) {
            Start-Process -FilePath $path -ArgumentList $url | Out-Null
            $opened = $true
            break
        }
    }
    if (-not $opened) {
        Write-Host "Open manually: $url"
    }
}

Write-Host ""
