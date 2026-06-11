# One-time environment setup for Windows (local Postgres + Redis)
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $ProjectRoot "backend"
$Frontend = Join-Path $ProjectRoot "frontend"
$Psql = "C:\Program Files\PostgreSQL\16\bin\psql.exe"

Write-Host "=== Gmail Outreach environment setup ===" -ForegroundColor Cyan

if (-not (Test-Path (Join-Path $ProjectRoot ".env"))) {
    Copy-Item (Join-Path $ProjectRoot ".env.example") (Join-Path $ProjectRoot ".env")
    Write-Host "Created .env from .env.example"
}

if (Test-Path $Psql) {
    if (-not $env:PGPASSWORD) { $env:PGPASSWORD = "postgres" }
    $roleSql = "DO `$`$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'outreach') THEN CREATE ROLE outreach LOGIN PASSWORD 'outreach'; END IF; END `$`$;"
    & $Psql -U postgres -h localhost -c $roleSql | Out-Null
    foreach ($db in @("outreach", "outreach_test")) {
        $exists = (& $Psql -U postgres -h localhost -tAc "SELECT 1 FROM pg_database WHERE datname='$db'").Trim()
        if ($exists -ne "1") {
            & $Psql -U postgres -h localhost -c "CREATE DATABASE $db OWNER outreach;" | Out-Null
            Write-Host "Created database: $db"
        }
    }
    Write-Host "PostgreSQL ready (user: outreach)"
} else {
    Write-Host "WARNING: psql not found. Install PostgreSQL or use Docker." -ForegroundColor Yellow
}

Write-Host "Installing Python dependencies..."
Push-Location $Backend
py -m pip install -e ".[dev]" --quiet
Pop-Location

Write-Host "Installing Node dependencies..."
Push-Location $Frontend
if (-not (Test-Path "node_modules")) { npm install }
Pop-Location

Write-Host "Initializing database schema..."
Push-Location $Backend
$env:PYTHONPATH = "$ProjectRoot;$Backend"
py -c "import asyncio; from app.init_db import init_db; asyncio.run(init_db()); print('Database schema initialized.')"
Pop-Location

Write-Host ""
Write-Host "Setup complete. Start the stack with:" -ForegroundColor Green
Write-Host "  .\scripts\start-all.ps1"
