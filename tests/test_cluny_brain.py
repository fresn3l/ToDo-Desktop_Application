"""Tests for Kosistenz-managed Cluny serve lifecycle."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import cluny_brain
import cluny_sync


class ClunyBrainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"KOSISTENZ_DATA_DIR": self.tmp.name}, clear=False)
        self.env.start()
        cluny_sync._write_file_settings(dict(cluny_sync._FILE_DEFAULTS))

    def tearDown(self) -> None:
        cluny_brain.stop_supervisor()
        self.env.stop()
        self.tmp.cleanup()

    def test_auto_start_disabled_skips_spawn(self) -> None:
        cluny_sync._write_file_settings({"auto_start_brain": False})
        with mock.patch("cluny_brain.cluny_client.health", return_value={"brain_ready": False, "ok": False}):
            status = cluny_brain.ensure_running()
        self.assertFalse(status["auto_start"])
        self.assertFalse(status.get("started"))

    def test_spawn_uses_cluny_api_env(self) -> None:
        probes = iter(
            [
                {"brain_ready": False, "ok": False},
                {"brain_ready": True, "ok": True},
            ]
        )
        with mock.patch("cluny_brain._resolve_serve_command", return_value=["/tmp/cluny", "serve"]), mock.patch(
            "cluny_brain.subprocess.Popen", return_value=mock.Mock(poll=lambda: None)
        ) as popen, mock.patch("cluny_brain._wait_for_ready", return_value=True), mock.patch(
            "cluny_brain.cluny_client.health",
            side_effect=lambda: next(probes, {"brain_ready": True, "ok": True}),
        ):
            status = cluny_brain.ensure_running()
        self.assertTrue(status["started"])
        env = popen.call_args.kwargs["env"]
        self.assertEqual(env["CLUNY_API_BIND"], "127.0.0.1")
        self.assertEqual(env["CLUNY_API_PORT"], "8787")
        self.assertEqual(env["PATH"], cluny_brain.augmented_path())
        self.assertTrue(popen.call_args.kwargs["stdout"])
        self.assertIn("serve_log", status)

    def test_lookup_finds_candidate_binary_when_path_is_empty(self) -> None:
        os.environ.pop("CLUNY_BIN", None)
        fake = Path(self.tmp.name) / "cluny"
        fake.write_text("#!/bin/sh\n")
        fake.chmod(0o755)
        with mock.patch("cluny_brain.shutil.which", return_value=None), mock.patch.object(
            cluny_brain, "_candidate_binaries", return_value=[fake]
        ):
            command = cluny_brain._resolve_serve_command()
        self.assertEqual(command, [str(fake), "serve"])

    def test_frozen_app_does_not_reuse_kosistenz_as_python_m(self) -> None:
        os.environ.pop("CLUNY_BIN", None)
        with mock.patch.object(cluny_brain, "_frozen", return_value=True), mock.patch(
            "cluny_brain.shutil.which", return_value=None
        ), mock.patch.object(cluny_brain, "_candidate_binaries", return_value=[]):
            self.assertIsNone(cluny_brain._resolve_serve_command())
            lookup = cluny_brain._serve_lookup()
        self.assertIn("Homebrew", lookup.get("message") or "")
        self.assertIn("install_brain.sh", lookup.get("message") or "")

    def test_candidate_binaries_include_application_support_wrapper(self) -> None:
        names = cluny_brain._candidate_binaries()
        self.assertIn(cluny_brain.DEFAULT_DATA_DIR / "bin" / "cluny", names)
        self.assertIn(cluny_brain.DEFAULT_DATA_DIR / "src" / ".venv" / "bin" / "cluny", names)


if __name__ == "__main__":
    unittest.main()
