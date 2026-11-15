"""Tests for the shared data dir and the page lockdown."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import paths
import work


class DataDirectoryTests(unittest.TestCase):
    def test_override_applies_to_work(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"KOSISTENZ_DATA_DIR": tmp}):
                root = paths.data_directory()
                self.assertEqual(root, Path(tmp))
                self.assertEqual(work._data_dir(), Path(tmp))


class PageLockdownTests(unittest.TestCase):
    def test_index_has_csp_and_no_inline_script(self) -> None:
        html = Path(__file__).resolve().parents[1] / "web" / "index.html"
        text = html.read_text(encoding="utf-8")
        self.assertIn('http-equiv="Content-Security-Policy"', text)
        self.assertIn("frame-src 'none'", text)
        self.assertIn("object-src 'none'", text)
        self.assertIn("script-src 'self'", text)
        self.assertNotIn("<script>", text)
        self.assertIn("js/boot-appearance.js", text)

    def test_local_api_does_not_send_wildcard_cors(self) -> None:
        source = Path(__file__).resolve().parents[1] / "local_api.py"
        text = source.read_text(encoding="utf-8")
        self.assertNotIn("Access-Control-Allow-Origin", text)
        self.assertIn("X-Content-Type-Options", text)


if __name__ == "__main__":
    unittest.main()
