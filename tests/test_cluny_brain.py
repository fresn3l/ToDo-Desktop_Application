"""Tests for Kosistenz-managed Cluny serve lifecycle."""

from __future__ import annotations

import os
import tempfile
import unittest
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
        with mock.patch("cluny_brain._resolve_serve_command", return_value=["/tmp/cluny", "serve"]), mock.patch(
            "cluny_brain.subprocess.Popen", return_value=mock.Mock(poll=lambda: None)
        ) as popen, mock.patch("cluny_brain._wait_for_ready", return_value=True), mock.patch(
            "cluny_brain.cluny_client.health", return_value={"brain_ready": True, "ok": True}
        ):
            status = cluny_brain.ensure_running()
        self.assertTrue(status["started"])
        env = popen.call_args.kwargs["env"]
        self.assertEqual(env["CLUNY_API_BIND"], "127.0.0.1")
        self.assertEqual(env["CLUNY_API_PORT"], "8787")


if __name__ == "__main__":
    unittest.main()
