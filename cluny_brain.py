"""Keep Cluny serve alive while Kosistenz is open."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import cluny_client
import cluny_sync

_SERVE_PROC: subprocess.Popen | None = None
_SPAWNED_BY_KOSISTENZ = False
_SUPERVISOR_THREAD: threading.Thread | None = None
_STOP = threading.Event()
_LOCK = threading.Lock()
_LAST_STATUS: dict[str, Any] = {
    "supervisor": "stopped",
    "managed": False,
    "ready": False,
    "message": "Supervisor not started",
}

DEFAULT_DATA_DIR = Path.home() / "Library" / "Application Support" / "Cluny"
POLL_INTERVAL_SEC = 8.0
STARTUP_WAIT_SEC = 45.0


def _log(message: str) -> None:
    print(f"[Cluny brain] {message}", flush=True)


def _brain_host_port() -> tuple[str, int]:
    cfg = cluny_sync.effective_cluny_config()
    parsed = urlparse(str(cfg.get("brain_url") or cluny_client.DEFAULT_BRAIN_URL))
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 8787
    return host, port


def _data_dir() -> str:
    return os.environ.get("CLUNY_DATA_DIR") or str(DEFAULT_DATA_DIR)


def _auto_start_enabled() -> bool:
    stored = cluny_sync._read_file_settings()
    if stored.get("auto_start_brain") is False:
        return False
    if os.environ.get("CLUNY_AUTO_START", "").strip().lower() in ("0", "false", "no"):
        return False
    return True


def _serve_env() -> dict[str, str]:
    host, port = _brain_host_port()
    env = os.environ.copy()
    env.setdefault("CLUNY_DATA_DIR", _data_dir())
    env["CLUNY_API_BIND"] = host
    env["CLUNY_API_PORT"] = str(port)
    return env


def _resolve_serve_command() -> list[str] | None:
    env_bin = (os.environ.get("CLUNY_BIN") or "").strip()
    if env_bin:
        return [env_bin, "serve"]
    stored = cluny_sync._read_file_settings()
    configured = str(stored.get("cluny_binary_path") or "").strip()
    if configured:
        path = Path(configured).expanduser()
        if path.is_file() and os.access(path, os.X_OK):
            return [str(path), "serve"]
    found = shutil.which("cluny")
    if found:
        return [found, "serve"]
    try:
        import cluny  # noqa: F401

        return [sys.executable, "-m", "cluny.cli", "serve"]
    except ImportError:
        return None


def _wait_for_ready(timeout: float = STARTUP_WAIT_SEC) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline and not _STOP.is_set():
        probe = cluny_client.health()
        if probe.get("brain_ready"):
            return True
        time.sleep(0.5)
    return False


def _spawn_serve() -> dict[str, Any]:
    global _SERVE_PROC, _SPAWNED_BY_KOSISTENZ  # noqa: PLW0603

    cmd = _resolve_serve_command()
    if not cmd:
        return {
            "started": False,
            "ready": False,
            "managed": False,
            "message": "Cluny not found. Install Cluny or set CLUNY_BIN / Settings → Cluny binary path.",
        }

    data_dir = _data_dir()
    Path(data_dir).mkdir(parents=True, exist_ok=True)

    try:
        _SERVE_PROC = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=_serve_env(),
            start_new_session=True,
        )
        _SPAWNED_BY_KOSISTENZ = True
    except OSError as exc:
        _SERVE_PROC = None
        _SPAWNED_BY_KOSISTENZ = False
        return {"started": False, "ready": False, "managed": False, "message": str(exc)}

    _log(f"Started {' '.join(cmd)} (data_dir={data_dir})")
    ready = _wait_for_ready()
    probe = cluny_client.health()
    return {
        "started": True,
        "ready": ready and bool(probe.get("brain_ready")),
        "managed": True,
        "message": probe.get("message") or ("Brain ready" if ready else "Cluny started; waiting for Ollama"),
        "ollama_ok": probe.get("ollama_ok"),
    }


def _our_process_running() -> bool:
    return _SERVE_PROC is not None and _SERVE_PROC.poll() is None


def ensure_running(*, wait: bool = False) -> dict[str, Any]:
    """Start Cluny serve if auto-start is on and nothing is listening."""
    with _LOCK:
        if not _auto_start_enabled():
            probe = cluny_client.health()
            status = {
                "started": False,
                "ready": bool(probe.get("brain_ready")),
                "managed": False,
                "auto_start": False,
                "message": "Auto-start is off in Settings → Cluny",
                **probe,
            }
            _LAST_STATUS.update(status)
            return status

        probe = cluny_client.health()
        if probe.get("brain_ready"):
            status = {
                "started": False,
                "ready": True,
                "managed": _SPAWNED_BY_KOSISTENZ and _our_process_running(),
                "auto_start": True,
                "message": probe.get("message") or "Brain ready",
                **probe,
            }
            _LAST_STATUS.update(status)
            return status

        if _our_process_running():
            if wait:
                ready = _wait_for_ready(timeout=10.0)
                probe = cluny_client.health()
                status = {
                    "started": False,
                    "ready": ready and bool(probe.get("brain_ready")),
                    "managed": True,
                    "auto_start": True,
                    "message": probe.get("message") or "Starting…",
                    **probe,
                }
            else:
                status = {
                    "started": False,
                    "ready": False,
                    "managed": True,
                    "auto_start": True,
                    "message": "Cluny is starting…",
                    **probe,
                }
            _LAST_STATUS.update(status)
            return status

        if _SERVE_PROC is not None and _SERVE_PROC.poll() is not None:
            _log(f"Cluny serve exited (code {_SERVE_PROC.returncode}); restarting")
            _SERVE_PROC = None

        status = {**_spawn_serve(), "auto_start": True}
        _LAST_STATUS.update(status)
        return status


def stop_managed_serve() -> None:
    """Stop Cluny only if Kosistenz started it."""
    global _SERVE_PROC, _SPAWNED_BY_KOSISTENZ  # noqa: PLW0603

    with _LOCK:
        if not _SPAWNED_BY_KOSISTENZ or _SERVE_PROC is None:
            return
        if _SERVE_PROC.poll() is None:
            _log("Stopping managed Cluny serve")
            _SERVE_PROC.terminate()
            try:
                _SERVE_PROC.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                _SERVE_PROC.kill()
        _SERVE_PROC = None
        _SPAWNED_BY_KOSISTENZ = False


def supervisor_status() -> dict[str, Any]:
    probe = cluny_client.health()
    with _LOCK:
        return {
            "supervisor": "running" if _SUPERVISOR_THREAD and _SUPERVISOR_THREAD.is_alive() else "stopped",
            "auto_start": _auto_start_enabled(),
            "managed": _SPAWNED_BY_KOSISTENZ and _our_process_running(),
            "ready": bool(probe.get("brain_ready")),
            "ollama_ok": probe.get("ollama_ok"),
            "brain_ready": probe.get("brain_ready"),
            "message": _LAST_STATUS.get("message") or probe.get("message"),
            "data_dir": _data_dir(),
            **probe,
        }


def _supervisor_loop() -> None:
    _LAST_STATUS["supervisor"] = "running"
    ensure_running(wait=True)
    while not _STOP.wait(POLL_INTERVAL_SEC):
        try:
            if not _auto_start_enabled():
                continue
            probe = cluny_client.health()
            if probe.get("brain_ready"):
                continue
            if _our_process_running():
                continue
            ensure_running()
        except Exception as exc:  # noqa: BLE001
            _log(f"Supervisor tick failed: {exc}")


def start_supervisor() -> None:
    """Start background thread that keeps Cluny serve up while Kosistenz runs."""
    global _SUPERVISOR_THREAD  # noqa: PLW0603

    if _SUPERVISOR_THREAD is not None and _SUPERVISOR_THREAD.is_alive():
        return
    _STOP.clear()
    _SUPERVISOR_THREAD = threading.Thread(target=_supervisor_loop, name="cluny-brain-supervisor", daemon=True)
    _SUPERVISOR_THREAD.start()
    _log("Supervisor started")


def stop_supervisor() -> None:
    _STOP.set()
    stop_managed_serve()
    thread = _SUPERVISOR_THREAD
    if thread is not None and thread.is_alive() and thread is not threading.current_thread():
        thread.join(timeout=2.0)
    _LAST_STATUS["supervisor"] = "stopped"


import eel


@eel.expose
def get_cluny_brain_supervisor() -> dict[str, Any]:
    return supervisor_status()


@eel.expose
def restart_cluny_brain() -> dict[str, Any]:
    stop_managed_serve()
    return ensure_running(wait=True)
