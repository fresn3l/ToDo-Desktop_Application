"""Cluny Settings persist independently of environment variables."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import cluny_sync


class ClunySettingsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.home = Path(self.tmp.name) / "home"
        self.home.mkdir()
        self.env = mock.patch.dict(
            os.environ,
            {"KOSISTENZ_DATA_DIR": str(self.root)},
            clear=False,
        )
        self.env.start()
        for key in (
            "CLUNY_SQLITE_PATH",
            "CLUNY_DATABASE_PATH",
            "CLUNY_INGEST_URL",
            "CLUNY_BRAIN_URL",
            "CLUNY_CHECKLIST_INGEST_URL",
            "CLUNY_API_KEY",
        ):
            os.environ.pop(key, None)
        self.home_patch = mock.patch.object(Path, "home", return_value=self.home)
        self.home_patch.start()

    def tearDown(self) -> None:
        self.home_patch.stop()
        self.env.stop()
        self.tmp.cleanup()

    def test_settings_round_trip_and_status(self) -> None:
        db = self.home / "cluny.sqlite"
        saved = cluny_sync.save_cluny_settings(
            {
                "sqlite_path": str(db),
                "ingest_url": "http://127.0.0.1:8765/ingest",
                "journal_enabled": True,
                "checklist_enabled": False,
            }
        )
        self.assertTrue(saved["configured"])
        self.assertEqual(saved["sqlite_path"], str(db.resolve()))
        self.assertEqual(saved["ingest_url"], "http://127.0.0.1:8765/ingest")
        self.assertFalse(saved["checklist_enabled"])
        self.assertIn("Check-in push is off", saved["status_note"])
        again = cluny_sync.get_cluny_settings()
        self.assertEqual(again["sqlite_path"], saved["sqlite_path"])

    def test_env_overrides_file(self) -> None:
        db = self.home / "from-file.sqlite"
        cluny_sync.save_cluny_settings({"sqlite_path": str(db), "ingest_url": ""})
        os.environ["CLUNY_SQLITE_PATH"] = str(self.home / "from-env.sqlite")
        cfg = cluny_sync.effective_cluny_config()
        self.assertTrue(cfg["env_overrides"]["sqlite_path"])
        self.assertTrue(str(cfg["sqlite_path"]).endswith("from-env.sqlite"))

    def test_journal_disabled_skips_sync(self) -> None:
        cluny_sync.save_cluny_settings(
            {
                "sqlite_path": str(self.home / "cluny.sqlite"),
                "journal_enabled": False,
                "checklist_enabled": True,
            }
        )
        with mock.patch.object(cluny_sync, "_sync_sqlite") as sqlite_sync:
            with mock.patch.object(cluny_sync, "_sync_http") as http_sync:
                cluny_sync.sync_journal_entry_safe({"id": "j1", "content": "hi"})
                sqlite_sync.assert_not_called()
                http_sync.assert_not_called()

    def test_ingest_url_rejects_plain_http_remote(self) -> None:
        with self.assertRaises(ValueError):
            cluny_sync._validate_ingest_url("http://example.com/ingest")
        self.assertEqual(
            cluny_sync._validate_ingest_url("https://example.com/ingest"),
            "https://example.com/ingest",
        )
        self.assertEqual(
            cluny_sync._validate_ingest_url("http://localhost:9/ingest"),
            "http://localhost:9/ingest",
        )

    def test_brain_url_allows_loopback_http_not_remote(self) -> None:
        import cluny_client

        self.assertEqual(cluny_client.validate_brain_url("http://127.0.0.1:8787"), "http://127.0.0.1:8787")
        self.assertEqual(cluny_client.validate_brain_url("http://localhost:8787"), "http://localhost:8787")
        self.assertEqual(
            cluny_client.validate_brain_url("https://example.com"),
            "https://example.com",
        )
        with self.assertRaises(ValueError):
            cluny_client.validate_brain_url("http://example.com")

    def test_journal_ingest_payload_is_text_catalog(self) -> None:
        import cluny_client

        payload = cluny_client.journal_ingest_payload(
            {"content": "Wrote about Spanish.", "date": "2026-09-02", "id": "j1"}
        )
        self.assertEqual(payload["text"], "Wrote about Spanish.")
        self.assertTrue(payload["catalog"])
        self.assertEqual(payload["source"], "kosistenz-journal")
        self.assertEqual(payload["collection"], "journal")
        self.assertEqual(payload["title"], "2026-09-02 journal")

    def test_journal_http_runs_without_sqlite_or_ingest_url(self) -> None:
        cluny_sync.save_cluny_settings({"journal_enabled": True, "sqlite_path": "", "ingest_url": ""})
        with mock.patch.object(cluny_sync, "_sync_http") as http_sync:
            with mock.patch.object(cluny_sync, "_sync_sqlite") as sqlite_sync:
                cluny_sync.sync_journal_entry_safe(
                    {"id": "j1", "content": "hi", "date": "2026-09-02"}
                )
                http_sync.assert_called_once()
                sqlite_sync.assert_not_called()

    def test_journal_save_swallows_cluny_down(self) -> None:
        cluny_sync.save_cluny_settings({"journal_enabled": True})
        with mock.patch("cluny_client.ingest_text", side_effect=ValueError("Cluny is off")):
            cluny_sync.sync_journal_entry_safe(
                {"id": "j1", "content": "still saved", "date": "2026-09-02"}
            )


if __name__ == "__main__":
    unittest.main()
