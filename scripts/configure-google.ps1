# Configure Google OAuth credentials for real Gmail connection
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$EnvFile = Join-Path $ProjectRoot ".env"

function Open-BrowserUrl {
    param([string]$Url)
    $chromePaths = @(
        "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe",
        "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
        "$env:LocalAppData\Google\Chrome\Application\chrome.exe"
    )
    foreach ($path in $chromePaths) {
        if (Test-Path $path) {
            Start-Process -FilePath $path -ArgumentList $Url | Out-Null
            return $true
        }
    }
    try {
        Start-Process "cmd.exe" -ArgumentList "/c", "start", "", $Url -ErrorAction Stop | Out-Null
        return $true
    } catch {
        Write-Host "Could not open browser automatically. Open this URL manually:" -ForegroundColor Yellow
        Write-Host "  $Url"
        return $false
    }
}

Write-Host ""
Write-Host "=== Connect REAL Gmail accounts ===" -ForegroundColor Cyan
Write-Host ""
Write-Host 'You need a Google OAuth Client ID + Secret (one-time setup).'
Write-Host ""

function Set-EnvLine {
    param([string]$Key, [string]$Value)
    $lines = Get-Content $EnvFile
    $found = $false
    $out = foreach ($line in $lines) {
        if ($line -match "^\s*$([regex]::Escape($Key))=") {
            $found = $true
            "$Key=$Value"
        } else {
            $line
        }
    }
    if (-not $found) { $out += "$Key=$Value" }
    $out | Set-Content $EnvFile -Encoding UTF8
}

if (-not (Test-Path $EnvFile)) {
    Copy-Item (Join-Path $ProjectRoot ".env.example") $EnvFile
}

Write-Host "Step 1 - Open Google Cloud Console" -ForegroundColor Yellow
Write-Host "  https://console.cloud.google.com/apis/credentials"
Write-Host ""
Write-Host '  a. Create or select a project'
Write-Host '  b. Enable Gmail API: https://console.cloud.google.com/apis/library/gmail.googleapis.com'
Write-Host '  c. OAuth consent screen -> External -> Testing -> add your Gmail as Test user'
Write-Host '  d. Credentials -> Create OAuth client ID -> Web application'
Write-Host '  e. Authorized redirect URI - copy exactly:'
Write-Host "     http://localhost:8000/api/v1/gmail/callback" -ForegroundColor Green
Write-Host ""

$open = Read-Host 'Open Google Cloud Console in browser now? [Y/n]'
if ($open -ne "n" -and $open -ne "N") {
    Open-BrowserUrl "https://console.cloud.google.com/apis/credentials" | Out-Null
    Start-Sleep -Seconds 1
    Open-BrowserUrl "https://console.cloud.google.com/apis/library/gmail.googleapis.com" | Out-Null
}

Write-Host ""
Write-Host "Step 2 - Paste your OAuth credentials" -ForegroundColor Yellow
Write-Host ""

do {
    $clientId = Read-Host 'Google Client ID (ends with .apps.googleusercontent.com)'
} while ([string]::IsNullOrWhiteSpace($clientId))

do {
    $clientSecret = Read-Host 'Google Client Secret'
} while ([string]::IsNullOrWhiteSpace($clientSecret))

if ($clientId -eq "TODO.apps.googleusercontent.com" -or $clientSecret -eq "TODO") {
    Write-Host "ERROR: Please use real credentials from Google Console." -ForegroundColor Red
    exit 1
}

Set-EnvLine "GOOGLE_CLIENT_ID" $clientId.Trim()
Set-EnvLine "GOOGLE_CLIENT_SECRET" $clientSecret.Trim()
Set-EnvLine "GOOGLE_REDIRECT_URI" "http://localhost:8000/api/v1/gmail/callback"
Set-EnvLine "GOOGLE_OAUTH_PUBLISHING_STATUS" "testing"
Set-EnvLine "USE_MOCK_GMAIL" "false"

Write-Host ""
Write-Host "Saved to .env:" -ForegroundColor Green
Write-Host "  USE_MOCK_GMAIL=false"
Write-Host "  GOOGLE_CLIENT_ID=$($clientId.Trim())"
Write-Host "  GOOGLE_CLIENT_SECRET=********"
Write-Host ""
Write-Host "Step 3 - Restart the app" -ForegroundColor Yellow
Write-Host '  1. Run bin\GmailOutreach-Stop.bat'
Write-Host '  2. Run bin\GmailOutreach-Start.bat'
Write-Host '  3. Go to Accounts -> Connect Gmail -> Connect with Google'
Write-Host ""
Write-Host 'Remember: each Gmail you connect must be listed as a Test user in Google Console.'
Write-Host ""
