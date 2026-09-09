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
_SERVE_LOG: Any = None
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
NOT_FOUND_COPY = (
    "Cluny not found. On a Mac run ./macos/install_brain.sh, or set Settings → Cluny binary path. "
    "The Mac app does not see Homebrew PATH, so Kosistenz also looks in "
    "/opt/homebrew/bin, /usr/local/bin, and ~/Library/Application Support/Cluny/bin."
)


def _log(message: str) -> None:
    print(f"[Cluny brain] {message}", flush=True)


def _brain_host_port() -> tuple[str, int]:
    cfg = cluny_sync.effective_cluny_config()
    parsed = urlparse(str(cfg.get("brain_url") or cluny_client.DEFAULT_BRAIN_URL))
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 8787
    return host, port


def _data_dir() -> str:
    env = os.environ.get("CLUNY_DATA_DIR", "").strip()
    if env:
        return env
    stored = cluny_sync._read_file_settings()
    configured = str(stored.get("cluny_data_dir") or "").strip()
    if configured:
        return str(Path(configured).expanduser())
    return str(DEFAULT_DATA_DIR)


def _auto_start_enabled() -> bool:
    stored = cluny_sync._read_file_settings()
    if stored.get("auto_start_brain") is False:
        return False
    if os.environ.get("CLUNY_AUTO_START", "").strip().lower() in ("0", "false", "no"):
        return False
    return True


def _macos_bin_dirs() -> list[str]:
    home = Path.home()
    return [
        "/opt/homebrew/bin",
        "/opt/homebrew/sbin",
        "/usr/local/bin",
        "/usr/local/sbin",
        str(home / ".local" / "bin"),
        str(home / "bin"),
        str(home / ".cargo" / "bin"),
        "/Applications/Ollama.app/Contents/Resources",
    ]


def augmented_path() -> str:
    """GUI apps get a tiny PATH. Cluny and Ollama usually live on Homebrew."""
    current = os.environ.get("PATH") or "/usr/bin:/bin:/usr/sbin:/sbin"
    seen = set(current.split(":"))
    extra = [path for path in _macos_bin_dirs() if path not in seen and Path(path).is_dir()]
    return ":".join(extra + [current]) if extra else current


def serve_log_path() -> Path:
    logs = Path.home() / "Library" / "Logs"
    try:
        logs.mkdir(parents=True, exist_ok=True)
    except OSError:
        logs = Path(_data_dir())
        logs.mkdir(parents=True, exist_ok=True)
    return logs / "Kosistenz-cluny-serve.log"


def _is_executable(path: Path) -> bool:
    try:
        return path.is_file() and os.access(path, os.X_OK)
    except OSError:
        return False


def _candidate_binaries() -> list[Path]:
    home = Path.home()
    names = [
        Path("/opt/homebrew/bin/cluny"),
        Path("/usr/local/bin/cluny"),
        home / ".local" / "bin" / "cluny",
        home / "bin" / "cluny",
        home / ".local" / "share" / "pipx" / "venvs" / "cluny" / "bin" / "cluny",
        Path("/Applications/Cluny.app/Contents/MacOS/cluny"),
        home / "Applications" / "Cluny.app" / "Contents" / "MacOS" / "cluny",
        DEFAULT_DATA_DIR / "bin" / "cluny",
        DEFAULT_DATA_DIR / "src" / ".venv" / "bin" / "cluny",
    ]
    out: list[Path] = []
    for path in names:
        if path not in out:
            out.append(path)
    return out


def _serve_env() -> dict[str, str]:
    host, port = _brain_host_port()
    env = os.environ.copy()
    env.setdefault("CLUNY_DATA_DIR", _data_dir())
    env["CLUNY_API_BIND"] = host
    env["CLUNY_API_PORT"] = str(port)
    env["PATH"] = augmented_path()
    return env


def _frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _serve_lookup() -> dict[str, Any]:
    env_bin = (os.environ.get("CLUNY_BIN") or "").strip()
    if env_bin:
        return {"command": [env_bin, "serve"], "found_via": "CLUNY_BIN"}
    stored = cluny_sync._read_file_settings()
    configured = str(stored.get("cluny_binary_path") or "").strip()
    if configured:
        path = Path(configured).expanduser()
        if _is_executable(path):
            return {"command": [str(path), "serve"], "found_via": "settings"}
        return {
            "command": None,
            "found_via": "",
            "message": f"Settings binary is not executable: {path}",
        }
    which = shutil.which("cluny", path=augmented_path())
    if which:
        return {"command": [which, "serve"], "found_via": "PATH"}
    for path in _candidate_binaries():
        if _is_executable(path):
            return {"command": [str(path), "serve"], "found_via": str(path)}
    if not _frozen():
        try:
            import cluny  # noqa: F401

            return {
                "command": [sys.executable, "-m", "cluny.cli", "serve"],
                "found_via": "python -m cluny.cli",
            }
        except ImportError:
            pass
    return {"command": None, "found_via": "", "message": NOT_FOUND_COPY}


def _resolve_serve_command() -> list[str] | None:
    command = _serve_lookup().get("command")
    return command if isinstance(command, list) else None


def _wait_for_ready(timeout: float = STARTUP_WAIT_SEC, proc: subprocess.Popen | None = None) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline and not _STOP.is_set():
        if proc is not None and proc.poll() is not None:
            return False
        probe = cluny_client.health()
        if probe.get("brain_ready"):
            return True
        time.sleep(0.5)
    return False


def _read_log_tail(limit: int = 1200) -> str:
    path = serve_log_path()
    try:
        data = path.read_bytes()
    except OSError:
        return ""
    text = data[-limit:].decode("utf-8", errors="replace").strip()
    return text[-800:] if text else ""


def _close_serve_log() -> None:
    global _SERVE_LOG  # noqa: PLW0603
    handle = _SERVE_LOG
    _SERVE_LOG = None
    if handle is not None:
        try:
            handle.close()
        except OSError:
            pass


def _spawn_serve() -> dict[str, Any]:
    global _SERVE_PROC, _SPAWNED_BY_KOSISTENZ, _SERVE_LOG  # noqa: PLW0603

    lookup = _serve_lookup()
    cmd = _resolve_serve_command()
    if not cmd:
        return {
            "started": False,
            "ready": False,
            "managed": False,
            "serve_command": "",
            "serve_log": str(serve_log_path()),
            "message": str(lookup.get("message") or NOT_FOUND_COPY),
        }

    data_dir = _data_dir()
    Path(data_dir).mkdir(parents=True, exist_ok=True)
    log_path = serve_log_path()
    try:
        _close_serve_log()
        _SERVE_LOG = open(log_path, "ab")  # noqa: SIM115
        _SERVE_LOG.write(f"\n--- {time.strftime('%Y-%m-%d %H:%M:%S')} {' '.join(cmd)}\n".encode("utf-8"))
        _SERVE_LOG.flush()
        _SERVE_PROC = subprocess.Popen(
            cmd,
            stdout=_SERVE_LOG,
            stderr=subprocess.STDOUT,
            env=_serve_env(),
            start_new_session=True,
        )
        _SPAWNED_BY_KOSISTENZ = True
    except OSError as exc:
        _SERVE_PROC = None
        _SPAWNED_BY_KOSISTENZ = False
        _close_serve_log()
        return {
            "started": False,
            "ready": False,
            "managed": False,
            "serve_command": " ".join(cmd),
            "serve_log": str(log_path),
            "message": str(exc),
        }

    _log(f"Started {' '.join(cmd)} (data_dir={data_dir})")
    ready = _wait_for_ready(proc=_SERVE_PROC)
    probe = cluny_client.health()
    if _SERVE_PROC is not None and _SERVE_PROC.poll() is not None:
        tail = _read_log_tail()
        code = _SERVE_PROC.returncode
        message = f"Cluny serve exited ({code}). See {log_path}"
        if tail:
            message = f"{message}\n{tail}"
        return {
            "started": True,
            "ready": False,
            "managed": False,
            "serve_command": " ".join(cmd),
            "serve_log": str(log_path),
            "message": message,
            "ollama_ok": False,
        }
    if ready and probe.get("brain_ready"):
        message = probe.get("message") or "Brain ready"
    elif probe.get("ok") and not probe.get("ollama_ok"):
        message = (
            probe.get("message")
            or "Cluny is up; Ollama is not ready. Open Ollama and pull a chat model."
        )
    else:
        message = probe.get("message") or "Cluny started; waiting for Ollama"
    return {
        "started": True,
        "ready": ready and bool(probe.get("brain_ready")),
        "managed": True,
        "serve_command": " ".join(cmd),
        "serve_log": str(log_path),
        "found_via": lookup.get("found_via") or "",
        "message": message,
        "ollama_ok": probe.get("ollama_ok"),
    }


def _our_process_running() -> bool:
    return _SERVE_PROC is not None and _SERVE_PROC.poll() is None


def ensure_running(*, wait: bool = False) -> dict[str, Any]:
    """Start Cluny serve if auto-start is on and nothing is listening."""
    global _SERVE_PROC  # noqa: PLW0603

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
        _close_serve_log()


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
            "serve_command": _LAST_STATUS.get("serve_command") or " ".join(_resolve_serve_command() or []),
            "serve_log": str(serve_log_path()),
            "found_via": _LAST_STATUS.get("found_via") or "",
            **probe,
        }


def _supervisor_loop() -> None:
    _LAST_STATUS["supervisor"] = "running"
    ensure_running(wait=False)
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
