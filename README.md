# Gmail Cold-Email Outreach Platform

Self-hosted outreach platform: Next.js + FastAPI + PostgreSQL + Redis + Celery + Gmail API (OAuth).

See [docs/TECHNICAL_REQUIREMENTS.md](docs/TECHNICAL_REQUIREMENTS.md) for full specifications.

## Quick start (.bat files — easiest)

Three launchers are in the **`bin\`** folder:

| File | When to use |
|------|-------------|
| **`GmailOutreach-Check.bat`** | Verify PostgreSQL, Redis, and database are ready |
| **`GmailOutreach-Setup.bat`** | **Once** — installs deps, creates DB, initializes schema |
| **`GmailOutreach-Start.bat`** | **Every time** — checks services, then starts everything |
| **`GmailOutreach-Stop.bat`** | Stops all services |

**Steps:**
1. Double-click **`bin\GmailOutreach-Check.bat`** to verify services (optional — Start runs this too)
2. Double-click **`bin\GmailOutreach-Setup.bat`** (first time only)
3. Double-click **`bin\GmailOutreach-Start.bat`**
4. Use the dashboard at http://localhost:3000
5. When done, double-click **`bin\GmailOutreach-Stop.bat`**

## Quick start (.exe launchers)

Same as above, but use `GmailOutreach-Setup.exe`, `GmailOutreach-Start.exe`, and `GmailOutreach-Stop.exe` in `bin\`.

To rebuild the `.exe` files:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\launcher\build.ps1
```

## Quick start (PowerShell scripts)

```powershell
cd "C:\Users\Blue Moon\Desktop\Google gmail bot"
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\start-all.ps1
```

`setup.ps1` creates PostgreSQL databases, installs Python/Node deps, and initializes schema.  
`start-all.ps1` opens four windows: API, Celery worker, Celery beat, and frontend.

### 1. Prerequisites

- **PostgreSQL 16+** (running locally) or Docker Desktop
- **Redis** (running locally) or Docker
- Python 3.12+ (3.14 supported)
- Node.js 20+

### 2. Environment

```powershell
cd "C:\Users\Blue Moon\Desktop\Google gmail bot"
copy .env.example .env
```

Generate secrets:

```powershell
py -c "import os,base64; print('TOKEN_ENCRYPTION_KEY=' + base64.b64encode(os.urandom(32)).decode())"
```

Set `JWT_SECRET`, `TOKEN_ENCRYPTION_KEY`, and `UNSUBSCRIBE_SECRET` in `.env`.

### 3. Start database & Redis

```powershell
docker compose -f docker/docker-compose.yml up -d db redis
```

### 4. Backend API

```powershell
cd backend
py -m pip install fastapi uvicorn "sqlalchemy[asyncio]" asyncpg pydantic-settings "python-jose[cryptography]" "passlib[bcrypt]" httpx redis cryptography jinja2 email-validator python-multipart aiofiles celery bcrypt pytest pytest-asyncio
py -m uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/api/docs

### 5. Celery workers

```powershell
$env:PYTHONPATH="C:\Users\Blue Moon\Desktop\Google gmail bot;C:\Users\Blue Moon\Desktop\Google gmail bot\backend"
celery -A workers.celery_app worker -Q send,sync,import,health,default --loglevel=info
celery -A workers.celery_app beat --loglevel=info
```

### 6. Frontend

```powershell
cd frontend
npm install
npm run dev
```

Dashboard: http://localhost:3000

### 7. Full stack (Docker)

```powershell
docker compose -f docker/docker-compose.yml up --build
```

## Mock Gmail (default)

`USE_MOCK_GMAIL=true` in `.env` — no Google credentials needed for development.

Connect a mock account:

1. Register / login at http://localhost:3000/login
2. Go to Accounts → Connect Gmail
3. Use mock OAuth flow (redirects automatically in dev)

## Tests

```powershell
docker exec -it $(docker ps -qf name=db) psql -U outreach -c "CREATE DATABASE outreach_test;"
cd backend
py -m pytest tests/ -v
```

## Project structure

```
backend/     FastAPI API + models + services
workers/     Celery tasks (sender, scheduler, bounce, etc.)
frontend/    Next.js dashboard
docker/      Docker Compose + Dockerfiles
docs/        Requirements, compliance, runbook
```
