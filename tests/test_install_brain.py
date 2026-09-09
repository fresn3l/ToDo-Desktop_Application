"""Mac Cluny + Ollama installer: present, Darwin-only, wired from install_app."""

from __future__ import annotations

import os
import platform
import stat
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BRAIN = ROOT / "macos" / "install_brain.sh"
APP = ROOT / "macos" / "install_app.sh"


class InstallBrainTests(unittest.TestCase):
    def test_script_exists_and_is_executable_intent(self) -> None:
        self.assertTrue(BRAIN.is_file(), "macos/install_brain.sh is missing")
        text = BRAIN.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("#!/usr/bin/env bash"))
        mode = BRAIN.stat().st_mode
        self.assertTrue(mode & stat.S_IXUSR, "install_brain.sh should be executable")
        syntax = subprocess.run(["bash", "-n", str(BRAIN)], capture_output=True, text=True)
        self.assertEqual(syntax.returncode, 0, syntax.stderr)
        app_syntax = subprocess.run(["bash", "-n", str(APP)], capture_output=True, text=True)
        self.assertEqual(app_syntax.returncode, 0, app_syntax.stderr)

    def test_mentions_ollama_cluny_repo_models_and_data_dir(self) -> None:
        text = BRAIN.read_text(encoding="utf-8")
        self.assertIn("Ollama", text)
        self.assertIn("https://github.com/fresn3l/Cluny_the_AI_Agent", text)
        self.assertIn("llama3.2", text)
        self.assertIn("nomic-embed-text", text)
        self.assertIn("Application Support/Cluny", text)
        self.assertIn('".[api]"', text)
        self.assertIn("cluny_binary_path", text)
        self.assertIn("cluny_data_dir", text)
        self.assertIn("CLUNY_DATA_DIR", text)
        self.assertIn("$CLUNY_BIN_DIR/cluny", text)
        self.assertIn("pip install -e", text)
        self.assertIn('uname -s', text)

    def test_exits_nonzero_on_non_darwin(self) -> None:
        if platform.system() == "Darwin":
            self.skipTest("non-Darwin exit is for Linux CI")
        result = subprocess.run(
            ["bash", str(BRAIN)],
            capture_output=True,
            text=True,
            env={**os.environ, "SKIP_MODELS": "1"},
        )
        self.assertEqual(result.returncode, 1)
        combined = (result.stderr or "") + (result.stdout or "")
        self.assertIn("macOS", combined)

    def test_install_app_calls_or_mentions_brain(self) -> None:
        text = APP.read_text(encoding="utf-8")
        self.assertIn("install_brain.sh", text)
        self.assertIn("SKIP_BRAIN", text)
        self.assertIn("--skip-brain", text)

    def test_settings_and_docs_name_the_installer(self) -> None:
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        docs = (ROOT / "docs" / "cluny-integration.md").read_text(encoding="utf-8")
        self.assertIn("install_brain.sh", html)
        self.assertIn("install_brain.sh", docs)
        self.assertIn("llama3.2", docs)
        self.assertIn("nomic-embed-text", docs)


if __name__ == "__main__":
    unittest.main()
