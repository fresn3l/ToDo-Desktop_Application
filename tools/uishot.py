#!/usr/bin/env python3
"""Screenshot the running UI over the devtools protocol.

Chrome's --screenshot fires on the load event, which lands before the bridge
has answered, so every capture showed empty tiles. This drives the browser
instead: navigate, let the board settle, optionally click through to a tab,
then capture.

    python3 tools/uishot.py out.png --tab calendar --width 1440 --height 1000

Expects the UI server already running:

    KOSISTENZ_DATA_DIR=/tmp/kdata python3 main.py --bridge 8099 web
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

import websocket

CHROME = os.environ.get("CHROME_BIN", "google-chrome")


class Devtools:
    def __init__(self, port: int) -> None:
        self.port = port
        self.seq = 0
        self.ws: websocket.WebSocket | None = None

    def _targets(self) -> list:
        raw = urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json", timeout=5).read()
        return json.loads(raw)

    def connect(self, tries: int = 60) -> None:
        for _ in range(tries):
            try:
                pages = [t for t in self._targets() if t.get("type") == "page"]
                if pages:
                    self.ws = websocket.create_connection(
                        pages[0]["webSocketDebuggerUrl"], timeout=30, max_size=64 * 1024 * 1024
                    )
                    return
            except (urllib.error.URLError, OSError, ValueError):
                pass
            time.sleep(0.5)
        raise RuntimeError("devtools never came up")

    def call(self, method: str, **params):
        assert self.ws is not None
        self.seq += 1
        self.ws.send(json.dumps({"id": self.seq, "method": method, "params": params}))
        while True:
            message = json.loads(self.ws.recv())
            if message.get("id") == self.seq:
                if "error" in message:
                    raise RuntimeError(f"{method}: {message['error']}")
                return message.get("result", {})

    def evaluate(self, expression: str):
        result = self.call(
            "Runtime.evaluate", expression=expression, awaitPromise=True, returnByValue=True
        )
        return (result.get("result") or {}).get("value")

    def close(self) -> None:
        if self.ws is not None:
            self.ws.close()


def capture(out: str, url: str, width: int, height: int, settle: float,
            tab: str | None, full: bool, before: str | None,
            hover: str | None) -> None:
    profile = tempfile.mkdtemp(prefix="uishot-")
    port = 9222
    proc = subprocess.Popen(
        [
            CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
            f"--remote-debugging-port={port}", "--remote-allow-origins=*",
            f"--user-data-dir={profile}",
            f"--window-size={width},{height}", "--force-device-scale-factor=2",
            "--force-color-profile=srgb", "--font-render-hinting=none",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    dev = Devtools(port)
    try:
        dev.connect()
        dev.call("Page.enable")
        dev.call("Runtime.enable")
        dev.call("Emulation.setDeviceMetricsOverride",
                 width=width, height=height, deviceScaleFactor=2, mobile=False)
        dev.call("Page.navigate", url=url)
        time.sleep(settle)
        if tab:
            dev.evaluate(
                "(() => { const b = document.querySelector(`.nav-item[data-tab=\"%s\"]`);"
                " if (b) b.click(); return !!b; })()" % tab
            )
            time.sleep(2.5)
        if before:
            dev.evaluate(before)
            time.sleep(1.5)
        if hover:
            # A real pointer move, because :hover cannot be set from script and
            # the interaction states are most of what there is to look at.
            box = dev.evaluate(
                "(() => { const el = document.querySelector(`%s`); if (!el) return null;"
                " const r = el.getBoundingClientRect();"
                " return {x: r.left + r.width / 2, y: r.top + r.height / 2}; })()" % hover
            )
            if not box:
                raise RuntimeError(f"nothing matched {hover}")
            dev.call("Input.dispatchMouseEvent", type="mouseMoved", x=box["x"], y=box["y"])
            time.sleep(0.6)
        # Let fonts and any entrance animation finish before the frame is taken.
        dev.evaluate("document.fonts ? document.fonts.ready.then(() => true) : true")
        time.sleep(0.4)
        params = {"format": "png", "captureBeyondViewport": True}
        if full:
            metrics = dev.call("Page.getLayoutMetrics")
            css = metrics.get("cssContentSize") or metrics.get("contentSize")
            params["clip"] = {
                "x": 0, "y": 0,
                "width": css["width"], "height": css["height"], "scale": 1,
            }
        shot = dev.call("Page.captureScreenshot", **params)
        import base64
        with open(out, "wb") as handle:
            handle.write(base64.b64decode(shot["data"]))
        print(f"wrote {out} ({os.path.getsize(out)} bytes)")
    finally:
        dev.close()
        proc.send_signal(signal.SIGKILL)
        proc.wait(timeout=10)
        shutil.rmtree(profile, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--url", default="http://127.0.0.1:8099/index.html")
    ap.add_argument("--width", type=int, default=1440)
    ap.add_argument("--height", type=int, default=1000)
    ap.add_argument("--settle", type=float, default=6.0)
    ap.add_argument("--tab", default=None, help="sidebar tab to click first")
    ap.add_argument("--full", action="store_true", help="capture the whole scroll height")
    ap.add_argument("--before", default=None, help="JS to run just before capture")
    ap.add_argument("--hover", default=None, help="selector to park the pointer on")
    args = ap.parse_args()
    capture(args.out, args.url, args.width, args.height, args.settle,
            args.tab, args.full, args.before, args.hover)
    return 0


if __name__ == "__main__":
    sys.exit(main())
