"""Windows launcher for Gmail Outreach — build to .exe with PyInstaller."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


APP_NAME = "GmailOutreach"
PID_FILE_NAME = "pids.json"


def project_root() -> Path:
    if getattr(sys, "frozen", False):
        # bin/GmailOutreach-Start.exe -> project root
        return Path(sys.executable).resolve().parent.parent
    return Path(__file__).resolve().parents[2]


def runtime_dir(root: Path) -> Path:
    path = root / ".runtime"
    path.mkdir(exist_ok=True)
    return path


def pid_file(root: Path) -> Path:
    return runtime_dir(root) / PID_FILE_NAME


def find_python() -> str:
    for candidate in ("py", "python", "python3"):
        found = shutil.which(candidate)
        if found:
            return candidate
    raise RuntimeError("Python not found. Install Python 3.12+ and ensure 'py' is on PATH.")


def find_npm() -> str:
    found = shutil.which("npm")
    if not found:
        raise RuntimeError("Node.js/npm not found. Install Node.js 20+.")
    return found


def find_psql() -> Path | None:
    for version in ("16", "17", "15", "14"):
        path = Path(rf"C:\Program Files\PostgreSQL\{version}\bin\psql.exe")
        if path.exists():
            return path
    return shutil.which("psql") and Path(shutil.which("psql"))  # type: ignore[arg-type]


def run_cmd(
    args: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    print(f">>> {' '.join(args)}")
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        env=env,
        check=check,
        text=True,
    )


def find_chrome() -> Path | None:
    candidates = (
        Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
        / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
        / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("LocalAppData", "")) / "Google/Chrome/Application/chrome.exe",
    )
    for path in candidates:
        if path.exists():
            return path
    return None


def open_chrome(url: str) -> bool:
    chrome = find_chrome()
    if chrome is None:
        print("ERROR: Google Chrome not found. Open manually:", url)
        return False
    subprocess.Popen([str(chrome), url])
    return True


def spawn_console(title: str, command: str, cwd: Path, env: dict[str, str]) -> subprocess.Popen[bytes]:
    # Start each service in its own console window (Windows).
    full_cmd = f'title {title} & {command}'
    return subprocess.Popen(
        ["cmd.exe", "/k", full_cmd],
        cwd=str(cwd),
        env=env,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )


def pythonpath_env(root: Path) -> dict[str, str]:
    env = os.environ.copy()
    backend = root / "backend"
    env["PYTHONPATH"] = f"{root};{backend}"
    return env


def check_redis() -> bool:
    try:
        result = subprocess.run(
            ["redis-cli", "ping"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0 and "PONG" in (result.stdout or "").upper()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_postgres(psql: Path | None) -> bool:
    if psql is None:
        return False
    env = os.environ.copy()
    env.setdefault("PGPASSWORD", "postgres")
    try:
        result = subprocess.run(
            [str(psql), "-U", "postgres", "-h", "localhost", "-tAc", "SELECT 1"],
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        return result.returncode == 0 and result.stdout.strip() == "1"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def cmd_setup(root: Path) -> int:
    print(f"=== {APP_NAME} Setup ===")
    print(f"Project: {root}")

    env_file = root / ".env"
    if not env_file.exists():
        example = root / ".env.example"
        if example.exists():
            shutil.copy(example, env_file)
            print("Created .env from .env.example")

    psql = find_psql()
    if psql:
        env = os.environ.copy()
        env.setdefault("PGPASSWORD", "postgres")
        role_sql = (
            "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'outreach') "
            "THEN CREATE ROLE outreach LOGIN PASSWORD 'outreach'; END IF; END $$;"
        )
        subprocess.run(
            [str(psql), "-U", "postgres", "-h", "localhost", "-c", role_sql],
            env=env,
            check=False,
        )
        for db in ("outreach", "outreach_test"):
            exists = subprocess.run(
                [str(psql), "-U", "postgres", "-h", "localhost", "-tAc",
                 f"SELECT 1 FROM pg_database WHERE datname='{db}'"],
                env=env,
                capture_output=True,
                text=True,
            )
            if exists.stdout.strip() != "1":
                subprocess.run(
                    [str(psql), "-U", "postgres", "-h", "localhost", "-c",
                     f"CREATE DATABASE {db} OWNER outreach;"],
                    env=env,
                    check=False,
                )
                print(f"Created database: {db}")
        print("PostgreSQL: outreach user and databases ready.")
    else:
        print("WARNING: PostgreSQL psql not found. Install PostgreSQL or use Docker.")

    py = find_python()
    backend = root / "backend"
    frontend = root / "frontend"

    print("Installing Python packages...")
    run_cmd([py, "-m", "pip", "install", "-e", ".[dev]"], cwd=backend)

    print("Installing Node packages...")
    if not (frontend / "node_modules").exists():
        run_cmd([find_npm(), "install"], cwd=frontend)

    print("Initializing database schema...")
    env = pythonpath_env(root)
    run_cmd(
        [py, "-c", "import asyncio; from app.init_db import init_db; asyncio.run(init_db()); print('OK')"],
        cwd=backend,
        env=env,
    )

    print("\nSetup complete. Double-click GmailOutreach-Start.exe to run the platform.")
    input("\nPress Enter to close...")
    return 0


def cmd_start(root: Path, open_browser: bool = True) -> int:
    print(f"=== {APP_NAME} Start ===")

    if not check_redis():
        print("ERROR: Redis is not running. Start the Redis Windows service first.")
        input("\nPress Enter to close...")
        return 1

    psql = find_psql()
    if not check_postgres(psql):
        print("ERROR: PostgreSQL is not reachable. Run GmailOutreach-Setup.exe first.")
        input("\nPress Enter to close...")
        return 1

    py = find_python()
    npm = find_npm()
    backend = root / "backend"
    frontend = root / "frontend"
    env = pythonpath_env(root)

    processes: list[dict[str, object]] = []

    api_cmd = f'"{py}" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000'
    worker_cmd = (
        f'"{py}" -m celery -A workers.celery_app worker '
        f'-Q send,sync,import,health,default --loglevel=info --pool=solo'
    )
    beat_cmd = f'"{py}" -m celery -A workers.celery_app beat --loglevel=info'
    front_cmd = f'"{npm}" run dev'

    print("Starting API (port 8000)...")
    processes.append({"name": "api", "pid": spawn_console("Gmail Outreach API", api_cmd, backend, env).pid})

    time.sleep(2)

    print("Starting Celery worker...")
    processes.append(
        {"name": "worker", "pid": spawn_console("Gmail Outreach Worker", worker_cmd, root, env).pid}
    )

    print("Starting Celery beat...")
    processes.append(
        {"name": "beat", "pid": spawn_console("Gmail Outreach Beat", beat_cmd, root, env).pid}
    )

    time.sleep(1)

    print("Starting frontend (port 3000)...")
    processes.append(
        {"name": "frontend", "pid": spawn_console("Gmail Outreach Frontend", front_cmd, frontend, env).pid}
    )

    pid_file(root).write_text(json.dumps(processes, indent=2), encoding="utf-8")

    print("\nAll services started in separate windows.")
    print("  API:       http://localhost:8000/api/docs")
    print("  Dashboard: http://localhost:3000")
    print("\nTo stop everything, run GmailOutreach-Stop.exe")

    if open_browser:
        time.sleep(15)
        open_chrome("http://localhost:3000")

    input("\nPress Enter to close this launcher (services keep running)...")
    return 0


def cmd_stop(root: Path) -> int:
    print(f"=== {APP_NAME} Stop ===")
    pf = pid_file(root)
    stopped = 0

    if pf.exists():
        try:
            entries = json.loads(pf.read_text(encoding="utf-8"))
            for entry in entries:
                pid = int(entry["pid"])
                name = entry.get("name", "service")
                try:
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], check=False)
                    print(f"Stopped {name} (PID {pid})")
                    stopped += 1
                except Exception as exc:
                    print(f"Could not stop {name}: {exc}")
        except json.JSONDecodeError:
            pass
        pf.unlink(missing_ok=True)

    # Fallback: free common ports used by the stack.
    for port in (8000, 3000):
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
        )
        for line in result.stdout.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                parts = line.split()
                if parts:
                    pid = parts[-1]
                    if pid.isdigit() and int(pid) > 0:
                        subprocess.run(["taskkill", "/F", "/T", "/PID", pid], check=False)
                        print(f"Freed port {port} (PID {pid})")
                        stopped += 1

    if stopped == 0:
        print("No running services found.")
    else:
        print(f"\nStopped {stopped} process(es).")

    input("\nPress Enter to close...")
    return 0


def command_from_invocation() -> str:
    if getattr(sys, "frozen", False):
        stem = Path(sys.executable).stem.lower()
        if "setup" in stem:
            return "setup"
        if "stop" in stem:
            return "stop"
        return "start"
    if len(sys.argv) > 1 and sys.argv[1] in ("setup", "start", "stop"):
        return sys.argv[1]
    return "start"


def main() -> int:
    command = command_from_invocation()
    open_browser = "--no-browser" not in sys.argv

    root = project_root()
    if not (root / "backend").is_dir() or not (root / "frontend").is_dir():
        print(f"ERROR: Invalid project root: {root}")
        print("Place the .exe files in the bin\\ folder at the project root.")
        input("\nPress Enter to close...")
        return 1

    if command == "setup":
        return cmd_setup(root)
    if command == "start":
        return cmd_start(root, open_browser=open_browser)
    return cmd_stop(root)


if __name__ == "__main__":
    raise SystemExit(main())
