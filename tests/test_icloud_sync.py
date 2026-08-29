"""JSON pack export/import between two isolated data dirs."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import icloud_sync
import journal
import work
import workouts


class IcloudSyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.src = self.root / "mac"
        self.dst = self.root / "phone"
        self.pack = self.root / "pack"
        self.src.mkdir()
        self.dst.mkdir()
        self.env = patch.dict(os.environ, {"KOSISTENZ_DATA_DIR": str(self.src)})
        self.env.start()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(self.env.stop)

    def _use(self, folder: Path):
        os.environ["KOSISTENZ_DATA_DIR"] = str(folder)

    def test_round_trip_todo_workout_and_journal(self):
        self._use(self.src)
        item = work.create_work_item("Write on the train", scheduled_date=work._today().isoformat())
        workouts.add_workout_session(work._today().isoformat(), "push", "", None, None)
        journal.save_journal_entry("Rode north.", 60, False, ["health"])

        exported = icloud_sync.write_pack(self.pack)
        self.assertTrue(exported["ok"])
        self.assertTrue((self.pack / "work.json").is_file())
        self.assertTrue((self.pack / "journal.json").is_file())

        self._use(self.dst)
        pulled = icloud_sync.apply_pack(self.pack)
        self.assertTrue(pulled["ok"])
        titles = [row["title"] for row in work.list_all_work_items()]
        self.assertIn("Write on the train", titles)
        day = workouts.get_workout_day(work._today().isoformat())
        self.assertTrue(day.get("done") or day.get("session_count"))
        texts = [entry.get("content") for entry in journal.get_all_entries()]
        self.assertIn("Rode north.", texts)
        self.assertEqual(item["id"], work.list_all_work_items()[0]["id"])

    def test_newer_updated_at_wins(self):
        self._use(self.src)
        item = work.create_work_item("Keep", scheduled_date=work._today().isoformat())
        icloud_sync.write_pack(self.pack)

        self._use(self.dst)
        icloud_sync.apply_pack(self.pack)
        work.create_work_item("Local only", scheduled_date=None)

        pack = icloud_sync.read_pack(self.pack)
        incoming = next(row for row in pack["work"]["items"] if row["id"] == item["id"])
        incoming["title"] = "Keep from phone"
        incoming["updated_at"] = "2099-01-01T00:00:00"
        icloud_sync._write_json(self.pack / "work.json", pack["work"])
        icloud_sync.apply_pack(self.pack)
        titles = {row["id"]: row["title"] for row in work.list_all_work_items()}
        self.assertEqual(titles[item["id"]], "Keep from phone")
        self.assertIn("Local only", titles.values())

    def test_auto_export_stays_off_until_first_push(self):
        self._use(self.src)
        self.assertFalse(icloud_sync.load_settings()["auto"])
        work.create_work_item("Quiet", scheduled_date=None)
        self.assertFalse((icloud_sync.default_sync_dir() / "work.json").exists())
