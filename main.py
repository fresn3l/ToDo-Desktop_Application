"""
Kosistenz — native desktop window (macOS WebKit / WKWebView).

Chrome is not used. On a Mac this is a regular Cocoa window with traffic
lights, Dock presence, and Cmd+Q. The HTML UI is served locally and shown
in Apple’s WebKit engine.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from paths import resource_path


WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 840
MIN_WIDTH = 960
MIN_HEIGHT = 680
PREFERRED_PORT = 17653


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
    raise RuntimeError(f"Kosistenz UI server did not start on port {port}: {last_error}")


def _storage_path() -> str:
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "ToDo" / "webview"
    elif sys.platform == "win32":
        base = Path.home() / "AppData" / "Local" / "ToDo" / "webview"
    else:
        base = Path.home() / ".local" / "share" / "ToDo" / "webview"
    base.mkdir(parents=True, exist_ok=True)
    return str(base)


def _gui_backend() -> str | None:
    if sys.platform == "darwin":
        return "cocoa"
    if sys.platform == "win32":
        return "edgechromium"
    return None


def _polish_cocoa(window) -> None:
    if sys.platform != "darwin":
        return
    try:
        from AppKit import NSApp, NSApplicationActivationPolicyRegular

        NSApp.setActivationPolicy_(NSApplicationActivationPolicyRegular)
        NSApp.activateIgnoringOtherApps_(True)
        native = getattr(window, "native", None)
        if native is None:
            return
        if hasattr(native, "setTabbingMode_"):
            native.setTabbingMode_(2)
        if hasattr(native, "center"):
            native.center()
    except Exception:
        pass


def _start_bridge(port: int) -> subprocess.Popen:
    web_dir = str(resource_path("web"))
    cmd = [sys.executable]
    if not getattr(sys, "frozen", False):
        cmd.append(str(Path(__file__).resolve()))
    cmd.extend(["--bridge", str(port), web_dir])
    return subprocess.Popen(cmd)


def _stop_bridge(proc: subprocess.Popen | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill()


def main() -> None:
    if len(sys.argv) >= 4 and sys.argv[1] == "--bridge":
        from bridge import run_bridge

        run_bridge(int(sys.argv[2]), sys.argv[3])
        return

    try:
        import webview
    except ImportError as exc:
        raise SystemExit(
            "pywebview is required for the native window. Run ./setup_venv.sh"
        ) from exc

    port = _pick_port()
    bridge = _start_bridge(port)
    try:
        _wait_for_server(port)
    except Exception:
        _stop_bridge(bridge)
        raise

    try:
        webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True
        webview.settings["ALLOW_DOWNLOADS"] = False
    except Exception:
        pass

    window = webview.create_window(
        "Kosistenz",
        f"http://127.0.0.1:{port}/index.html",
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        min_size=(MIN_WIDTH, MIN_HEIGHT),
        background_color="#0B1218",
        text_select=True,
        confirm_close=False,
        easy_drag=False,
    )

    def on_shown() -> None:
        _polish_cocoa(window)
        try:
            window.evaluate_js(
                "document.documentElement.classList.add('native-shell');"
            )
        except Exception:
            pass

    def on_closed() -> None:
        _stop_bridge(bridge)
        os._exit(0)

    window.events.shown += on_shown
    window.events.closed += on_closed

    try:
        webview.start(
            gui=_gui_backend(),
            debug=False,
            private_mode=False,
            storage_path=_storage_path(),
        )
    finally:
        _stop_bridge(bridge)


if __name__ == "__main__":
    main()
