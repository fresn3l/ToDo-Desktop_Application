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
            {
                "content": "Wrote about Spanish.",
                "date": "2026-09-02",
                "id": "j1",
                "kind": "evening_review",
                "tags": ["spanish"],
            }
        )
        self.assertIn("Wrote about Spanish.", payload["text"])
        self.assertIn("kind=evening_review", payload["text"])
        self.assertIn("tags=spanish", payload["text"])
        self.assertTrue(payload["catalog"])
        self.assertEqual(payload["source"], "kosistenz-journal")
        self.assertEqual(payload["collection"], "journal")
        self.assertEqual(payload["title"], "2026-09-02 evening_review")

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

    def test_checkin_hits_brain_ingest_without_custom_url(self) -> None:
        import cluny_client

        cluny_sync.save_cluny_settings(
            {
                "checklist_enabled": True,
                "sqlite_path": "",
                "ingest_url": "",
            }
        )
        with mock.patch.object(cluny_client, "ingest_text") as ingest:
            cluny_sync.sync_checklist_submission_safe(
                {
                    "id": 1,
                    "checklist_id": "morning",
                    "local_date": "2026-09-02",
                    "created_at": "2026-09-02T08:00:00",
                    "answers": {"intentions": "go"},
                }
            )
        ingest.assert_called_once()
        args, kwargs = ingest.call_args
        self.assertIn("kind=check-in", args[0])
        self.assertEqual(kwargs.get("collection"), "check-in")
        self.assertEqual(kwargs.get("source"), "kosistenz-checkin")

    def test_life_digest_ingests_when_brain_ready(self) -> None:
        import cluny_client
        import cluny_snapshot

        payload = {
            "date": "2026-09-09",
            "week_start": "2026-09-07",
            "week_end": "2026-09-13",
            "free_minutes": 120,
            "journal": [{"date": "2026-09-09", "kind": "journal", "content": "Full page about Spanish."}],
            "todos_today": [{"title": "Essay", "notes": "Need sources"}],
            "events_today": [{"title": "CHEM", "start": "09:30"}],
            "goals": [{"title": "Spanish", "spent_minutes": 0, "target_minutes": 180}],
            "workout_plan": {"lifts": {"0": "push"}},
            "workouts": [],
            "briefs": [],
            "work": {"backlog": [], "week": []},
        }
        digest = cluny_snapshot.snapshot_as_text(payload)
        self.assertIn("Full page about Spanish.", digest)
        self.assertIn("Need sources", digest)
        with mock.patch.object(cluny_client, "health", return_value={"brain_ready": True}), mock.patch.object(
            cluny_client, "ingest_text"
        ) as ingest:
            result = cluny_sync.sync_life_digest_safe(payload)
        self.assertTrue(result["ok"])
        ingest.assert_called_once()
        self.assertEqual(ingest.call_args.kwargs["collection"], "life")
        self.assertEqual(ingest.call_args.kwargs["title"], "kosistenz-life")

    def test_task_mirror_does_not_write_cluny_tasks(self) -> None:
        import cluny_client

        with mock.patch.object(cluny_client, "sync_task") as sync, mock.patch.object(
            cluny_client, "delete_synced_task"
        ) as delete:
            cluny_sync.sync_task_mirror_safe(
                {"id": "abc", "title": "Essay", "status": "open", "due_at": "2026-09-10T14:30:00"}
            )
            cluny_sync.delete_task_mirror_safe("abc")
        sync.assert_not_called()
        delete.assert_not_called()


if __name__ == "__main__":
    unittest.main()
