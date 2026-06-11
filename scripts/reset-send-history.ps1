# Reset send history so campaigns can be retested from scratch.
param(
    [string]$CampaignName = "Test Campaign",
    [switch]$AllCampaigns,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

$psql = "C:\Program Files\PostgreSQL\16\bin\psql.exe"
if (-not (Test-Path $psql)) {
    $psql = "C:\Program Files\PostgreSQL\17\bin\psql.exe"
}
if (-not (Test-Path $psql)) {
    Write-Host "ERROR: psql.exe not found." -ForegroundColor Red
    exit 1
}

$redisCli = "C:\Program Files\Redis\redis-cli.exe"
if (-not (Test-Path $redisCli)) {
    $redisCli = "redis-cli"
}

$env:PGPASSWORD = "outreach"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Gmail Outreach - Reset Send History" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Current send history:" -ForegroundColor Yellow
$historySql = @"
SELECT se.sent_at, ga.email AS from_account, se.recipient_email, l.status
FROM sent_emails se
JOIN gmail_accounts ga ON ga.id = se.gmail_account_id
JOIN leads l ON l.id = se.lead_id
JOIN campaigns c ON c.id = se.campaign_id
WHERE c.deleted_at IS NULL
ORDER BY se.sent_at DESC
LIMIT 30;
"@
& $psql -U outreach -h localhost -d outreach -c $historySql

if ($AllCampaigns) {
    $campaignFilter = "c.deleted_at IS NULL"
    $scopeLabel = "ALL campaigns"
} else {
    $escaped = $CampaignName.Replace("'", "''")
    $campaignFilter = "c.deleted_at IS NULL AND c.name = '$escaped'"
    $scopeLabel = "campaign '$CampaignName'"
}

Write-Host ""
Write-Host "Will reset: $scopeLabel" -ForegroundColor Yellow
Write-Host "  - sent_emails, send_jobs, reply_events for those campaigns" -ForegroundColor DarkGray
Write-Host "  - leads back to pending (except unsubscribed/skipped)" -ForegroundColor DarkGray
Write-Host "  - campaign sent/replied counts" -ForegroundColor DarkGray
Write-Host "  - gmail account last_send_at and Redis rate-limit counters" -ForegroundColor DarkGray
Write-Host ""

if (-not $Force) {
    $answer = Read-Host "Type RESET to continue"
    if ($answer -ne "RESET") {
        Write-Host "Cancelled." -ForegroundColor Yellow
        exit 0
    }
}

$resetSql = @"
BEGIN;

CREATE TEMP TABLE _reset_campaigns ON COMMIT DROP AS
SELECT c.id, c.user_id
FROM campaigns c
WHERE $campaignFilter;

DELETE FROM reply_events
WHERE sent_email_id IN (
    SELECT se.id FROM sent_emails se
    WHERE se.campaign_id IN (SELECT id FROM _reset_campaigns)
);

DELETE FROM sent_emails
WHERE campaign_id IN (SELECT id FROM _reset_campaigns);

DELETE FROM send_job_dlq
WHERE send_job_id IN (
    SELECT sj.id FROM send_jobs sj
    WHERE sj.campaign_id IN (SELECT id FROM _reset_campaigns)
);

DELETE FROM send_jobs
WHERE campaign_id IN (SELECT id FROM _reset_campaigns);

UPDATE leads
SET status = 'pending',
    last_contacted_at = NULL
WHERE campaign_id IN (SELECT id FROM _reset_campaigns)
  AND deleted_at IS NULL
  AND status NOT IN ('unsubscribed', 'skipped');

UPDATE campaigns
SET sent_count = 0,
    replied_count = 0,
    status = 'paused'
WHERE id IN (SELECT id FROM _reset_campaigns);

UPDATE gmail_accounts
SET last_send_at = NULL,
    lifetime_send_count = 0
WHERE user_id IN (SELECT DISTINCT user_id FROM _reset_campaigns)
  AND deleted_at IS NULL;

COMMIT;
"@

& $psql -U outreach -h localhost -d outreach -c $resetSql
if ($LASTEXITCODE -ne 0) {
    Write-Host "Database reset failed." -ForegroundColor Red
    exit 1
}

Write-Host "Database reset complete." -ForegroundColor Green

try {
    foreach ($db in @(1, 0)) {
        $keys = & $redisCli -n $db KEYS "rate:*" 2>$null
        if ($keys) {
            foreach ($key in $keys) {
                if ($key) { & $redisCli -n $db DEL $key | Out-Null }
            }
        }
        $lockKeys = & $redisCli -n $db KEYS "lock:*" 2>$null
        if ($lockKeys) {
            foreach ($key in $lockKeys) {
                if ($key) { & $redisCli -n $db DEL $key | Out-Null }
            }
        }
    }
    Write-Host "Cleared Redis rate limits and locks (db 0 and 1)." -ForegroundColor Green
} catch {
    Write-Host "WARN: Could not clear Redis keys: $_" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Ready to retest. Suggested steps:" -ForegroundColor Cyan
Write-Host "  1. Campaign was auto-paused — open it and click Resume" -ForegroundColor White
Write-Host "  2. Watch Send Queue — first account should show Available now" -ForegroundColor White
Write-Host "  3. Next accounts send 2-3 min apart by pool priority" -ForegroundColor White
Write-Host ""
