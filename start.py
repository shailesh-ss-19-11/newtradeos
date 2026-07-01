#!/usr/bin/env python3
"""
Start all trading system services:
  - Flask API      (port 8000)
  - Scanner        (signal generation)
  - React Frontend (port 3001)

Usage:
    python start.py
    python start.py --no-frontend   # skip React dev server
"""

import subprocess
import threading
import sys
import os
import signal
import argparse
import time

BASE = os.path.dirname(os.path.abspath(__file__))
_win = sys.platform == 'win32'
VENV_PYTHON = os.path.join(BASE, 'venv', 'Scripts' if _win else 'bin', 'python' + ('.exe' if _win else ''))
FRONTEND_DIR = os.path.join(BASE, 'frontend')

# ANSI colors
COLORS = {
    'api':      '\033[36m',   # cyan
    'scanner':  '\033[35m',   # magenta
    'frontend': '\033[33m',   # yellow
    'system':   '\033[32m',   # green
    'reset':    '\033[0m',
}

processes = []


def log(service, line):
    color = COLORS.get(service, '')
    reset = COLORS['reset']
    print(f"{color}[{service.upper():8s}]{reset} {line}", flush=True)


def stream(proc, service):
    for line in proc.stdout:
        log(service, line.rstrip())


def start(name, cmd, cwd=BASE):
    log('system', f"Starting {name}...")
    kwargs = dict(
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        encoding='utf-8',
        errors='replace',
        bufsize=1,
    )
    # On Windows, give each child its own process group so a Ctrl+C in the
    # parent console doesn't kill children mid-import (e.g. numpy DLL load).
    if _win:
        kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
    proc = subprocess.Popen(cmd, **kwargs)
    processes.append(proc)
    t = threading.Thread(target=stream, args=(proc, name), daemon=True)
    t.start()
    return proc


def shutdown(sig=None, frame=None):
    print(f"\n{COLORS['system']}[SYSTEM  ] Shutting down all services...{COLORS['reset']}")
    for p in processes:
        try:
            if _win:
                p.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                p.terminate()
        except Exception:
            pass
    for p in processes:
        try:
            p.wait(timeout=5)
        except Exception:
            p.kill()
    print(f"{COLORS['system']}[SYSTEM  ] All services stopped.{COLORS['reset']}")
    sys.exit(0)


def main():
    # Ensure the orchestrator's own stdout handles UTF-8 (subprocess logs may
    # contain Unicode arrows / dashes that CP1252 can't encode).
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    parser = argparse.ArgumentParser()
    parser.add_argument('--no-frontend', action='store_true', help='Skip React dev server')
    args = parser.parse_args()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    print(f"{COLORS['system']}")
    print("╔══════════════════════════════════════╗")
    print("║      Trading System — Starting       ║")
    print("║  API: http://localhost:8001/api      ║")
    print("║  UI:  http://localhost:3001          ║")
    print("╚══════════════════════════════════════╝")
    print(f"{COLORS['reset']}")

    # Flask API
    start('api', [VENV_PYTHON, '-u', 'app.py'])

    # Scanner (-u = unbuffered stdout so logs appear immediately)
    start('scanner', [VENV_PYTHON, '-u', 'scanner.py'])

    # React frontend
    if not args.no_frontend:
        npm = 'npm.cmd' if sys.platform == 'win32' else 'npm'
        start('frontend', [npm, 'run', 'dev'], cwd=FRONTEND_DIR)

    print(f"{COLORS['system']}[SYSTEM  ] All services started. Press Ctrl+C to stop.{COLORS['reset']}\n")

    # Keep main thread alive with a short-sleep loop so Python's signal
    # handler can fire on Windows (p.wait() blocks in a C call and never
    # returns control to the interpreter to deliver SIGINT).
    try:
        while True:
            if all(p.poll() is not None for p in processes):
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        shutdown()


if __name__ == '__main__':
    main()
