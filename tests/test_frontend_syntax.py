"""Frontend modules must parse — a duplicate const once killed every tab."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"


class FrontendSyntaxTests(unittest.TestCase):
    def test_web_javascript_parses(self) -> None:
        files = sorted(WEB.glob("*.js")) + sorted((WEB / "js").glob("*.js"))
        self.assertTrue(files)
        for path in files:
            with self.subTest(file=path.name):
                result = subprocess.run(
                    ["node", "--check", str(path)],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
