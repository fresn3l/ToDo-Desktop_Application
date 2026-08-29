"""
Kosistenz — native desktop window (macOS WebKit / WKWebView).

Chrome is not used. The installed .app’s main executable is a Swift Cocoa
host; this Python program serves the UI over localhost (--bridge) or opens
a PyObjC window when run from source.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from paths import resource_path


WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 840
MIN_WIDTH = 960
MIN_HEIGHT = 680
PREFERRED_PORT = 17653


def _log_path() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Logs" / "Kosistenz.log"
    return Path.home() / ".local" / "share" / "ToDo" / "Kosistenz.log"


def _log(message: str) -> None:
    path = _log_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"{stamp} {message}\n")
            handle.flush()
            os.fsync(handle.fileno())
    except OSError:
        pass


def _show_alert(message: str) -> None:
    _log(message)
    if sys.platform != "darwin":
        return
    text = message.replace("\\", "\\\\").replace('"', '\\"')[:900]
    log = str(_log_path())
    script = (
        f'display dialog "{text}\\n\\nDetails: {log}" '
        f'with title "Kosistenz" buttons {{"OK"}} default button 1'
    )
    try:
        subprocess.run(["osascript", "-e", script], check=False, capture_output=True)
    except OSError:
        pass


def _pick_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", PREFERRED_PORT))
            return PREFERRED_PORT
        except OSError:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])


def _wait_for_server(port: int, timeout: float = 20.0) -> None:
    url = f"http://127.0.0.1:{port}/index.html"
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=0.5) as response:
                if 200 <= response.status < 500:
                    return
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            last_error = exc
            time.sleep(0.1)
    raise RuntimeError(f"UI server did not start on port {port}: {last_error}")


def _start_bridge(port: int) -> subprocess.Popen:
    web_dir = str(resource_path("web"))
    if not Path(web_dir).is_dir():
        raise FileNotFoundError(f"UI folder missing: {web_dir}")

    cmd = [sys.executable]
    if not getattr(sys, "frozen", False):
        cmd.append(str(Path(__file__).resolve()))
    cmd.extend(["--bridge", str(port), web_dir])

    env = os.environ.copy()
    if getattr(sys, "frozen", False):
        # Without this, PyInstaller 6.9+ treats the child as a worker and it dies.
        env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"

    log_handle = _log_path().open("a", encoding="utf-8")
    _log(f"Starting bridge: {cmd!r}")
    proc = subprocess.Popen(
        cmd,
        env=env,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    proc._kosistenz_log = log_handle  # keep file open for the child's lifetime
    return proc


def _stop_bridge(proc: subprocess.Popen | None) -> None:
    if proc is None or proc.poll() is not None:
        log_handle = getattr(proc, "_kosistenz_log", None)
        if log_handle:
            try:
                log_handle.close()
            except OSError:
                pass
        return
    proc.terminate()
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill()
    log_handle = getattr(proc, "_kosistenz_log", None)
    if log_handle:
        try:
            log_handle.close()
        except OSError:
            pass


def _run_window(port: int, bridge: subprocess.Popen) -> None:
    url = f"http://127.0.0.1:{port}/index.html"
    _log(f"Opening window {url}")

    def on_close() -> None:
        _stop_bridge(bridge)

    from native_mac import available, run_mac_window

    if not available():
        raise RuntimeError(
            "macOS WebKit bindings (PyObjC AppKit/WebKit) are missing. "
            "On a Mac run: pip install pyobjc-framework-Cocoa pyobjc-framework-WebKit"
        )

    _log("Starting Cocoa WKWebView")
    run_mac_window(url, WINDOW_WIDTH, WINDOW_HEIGHT, MIN_WIDTH, MIN_HEIGHT, on_close)


def main() -> None:
    import faulthandler

    try:
        faulthandler.enable(open(_log_path(), "a", encoding="utf-8"), all_threads=True)
    except Exception:
        pass

    _log(f"argv={sys.argv!r} frozen={getattr(sys, 'frozen', False)}")
    if len(sys.argv) >= 4 and sys.argv[1] == "--bridge":
        from bridge import run_bridge

        _log(f"Bridge listening on {sys.argv[2]} serving {sys.argv[3]}")
        run_bridge(int(sys.argv[2]), sys.argv[3])
        return

    port = _pick_port()
    bridge = _start_bridge(port)
    try:
        if bridge.poll() is not None:
            raise RuntimeError(f"UI server exited immediately (code {bridge.returncode}).")
        _wait_for_server(port)
        _log(f"UI server ready on {port}")
        _run_window(port, bridge)
    finally:
        _stop_bridge(bridge)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        tb = traceback.format_exc()
        _log(tb)
        _show_alert(f"Kosistenz could not start.\n\n{tb.splitlines()[-1]}")
        sys.exit(1)
