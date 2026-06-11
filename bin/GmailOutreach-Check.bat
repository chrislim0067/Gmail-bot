@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Gmail Outreach - Health Check

cd /d "%~dp0"

set "OK=1"
set "PSQL=C:\Program Files\PostgreSQL\16\bin\psql.exe"
set "REDIS_CLI=C:\Program Files\Redis\redis-cli.exe"

if not exist "%PSQL%" set "PSQL=C:\Program Files\PostgreSQL\17\bin\psql.exe"
if not exist "%REDIS_CLI%" set "REDIS_CLI=redis-cli"

echo ========================================
echo   Gmail Outreach - Service Health Check
echo ========================================
echo.

echo [1/4] Windows services
set "ANY_PG=0"
for %%S in (Redis postgresql-x64-16 postgresql-x64-17) do (
    sc query "%%S" >nul 2>&1
    if not errorlevel 1 (
        sc query "%%S" | findstr /I "RUNNING" >nul
        if not errorlevel 1 (
            echo   OK   - %%S is RUNNING
            echo %%S | findstr /I "postgres" >nul && set "ANY_PG=1"
        ) else (
            echo   FAIL - %%S is NOT running
            set "OK=0"
        )
    )
)
if "!ANY_PG!"=="0" (
    echo   FAIL - No PostgreSQL service found running
    set "OK=0"
)
echo.

echo [2/4] Redis connection
"%REDIS_CLI%" ping 2>nul | findstr /I "PONG" >nul
if errorlevel 1 (
    echo   FAIL - Redis did not respond to PING
    set "OK=0"
) else (
    echo   OK   - Redis responded PONG
)
echo.

echo [3/4] PostgreSQL connection
if exist "%PSQL%" (
    if not defined PGPASSWORD set "PGPASSWORD=postgres"
    "%PSQL%" -U postgres -h localhost -tAc "SELECT 1" 2>nul | findstr "^1$" >nul
    if errorlevel 1 (
        echo   FAIL - Cannot connect as postgres@localhost
        echo         Tip: set PGPASSWORD if your password is not "postgres"
        set "OK=0"
    ) else (
        echo   OK   - PostgreSQL is reachable
    )
) else (
    echo   FAIL - psql.exe not found under Program Files\PostgreSQL
    set "OK=0"
)
echo.

echo [4/4] Outreach database
if exist "%PSQL%" (
    set "PGPASSWORD=outreach"
    "%PSQL%" -U outreach -h localhost -d outreach -tAc "SELECT 1" 2>nul | findstr "^1$" >nul
    if errorlevel 1 (
        echo   WARN - Database "outreach" not ready
        echo         Run GmailOutreach-Setup.bat first
        set "OK=0"
    ) else (
        echo   OK   - Database "outreach" is ready
    )
)
echo.

if "!OK!"=="1" (
    echo ========================================
    echo   All checks passed. Ready to start.
    echo ========================================
    echo.
    echo Next: double-click GmailOutreach-Start.bat
) else (
    echo ========================================
    echo   Some checks failed. Fix issues above.
    echo ========================================
    echo.
    echo Tips:
    echo   1. Press Win+R, type services.msc, press Enter
    echo   2. Start "Redis" and "postgresql-x64-16" if stopped
    echo   3. First time? Run GmailOutreach-Setup.bat
    echo   4. Run this check again
)

echo.
if /I not "%~1"=="nopause" (
    echo Press any key to close this window...
    pause >nul
)

if "!OK!"=="1" (
    endlocal
    exit /b 0
)
endlocal
exit /b 1
