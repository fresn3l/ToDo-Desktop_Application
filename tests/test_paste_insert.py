"""Execute paste_insert.js sanitizer with Node when available."""

from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PASTE_JS = ROOT / "web" / "js" / "paste_insert.js"


@unittest.skipUnless(shutil.which("node"), "node is required to execute paste_insert.js")
class PasteInsertJsTests(unittest.TestCase):
    def test_sanitize_pasted_calendar_urls(self) -> None:
        cases = [
            ["<webcal://cal.example.edu/x.ics>", "https://cal.example.edu/x.ics"],
            ["# comment\nhttps://cal.example.edu/x.ics?token=1\n", "https://cal.example.edu/x.ics?token=1"],
            ["Copy this: https://cal.example.edu/feed.ics", "https://cal.example.edu/feed.ics"],
            ["http://cal.example.edu/feed.ics", "http://cal.example.edu/feed.ics"],
            ["not a link", "not a link"],
            ["", ""],
        ]
        script = f"""
const fs = require('fs');
const vm = require('vm');
const ctx = {{
    window: {{}},
    document: {{ getElementById() {{ return null; }}, activeElement: null }}
}};
ctx.window = ctx;
vm.createContext(ctx);
vm.runInContext(fs.readFileSync({json.dumps(str(PASTE_JS))}, 'utf8'), ctx);
const sanitize = ctx.window.kosistenzSanitizePastedUrl;
const cases = {json.dumps(cases)};
const out = cases.map(([raw, expect]) => [raw, sanitize(raw), expect]);
process.stdout.write(JSON.stringify(out));
"""
        proc = subprocess.run(
            ["node", "-e", script],
            check=True,
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        rows = json.loads(proc.stdout)
        for raw, got, expect in rows:
            self.assertEqual(got, expect, msg=raw)
