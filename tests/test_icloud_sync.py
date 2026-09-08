"""JSON pack export/import between two isolated data dirs."""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timedelta
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
        self.assertTrue((self.pack / "calendar.json").is_file())

    def test_calendar_pack_includes_awake_window(self):
        import calclock

        self._use(self.src)
        calclock.save_calendar_settings({"day_start": "0530", "day_end": "2130"})
        icloud_sync.write_pack(self.pack)
        payload = icloud_sync._read_json(self.pack / "calendar.json", {})
        self.assertEqual(payload.get("day_start"), "05:30")
        self.assertEqual(payload.get("day_end"), "21:30")

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
        incoming["updated_at"] = (datetime.now() + timedelta(minutes=2)).isoformat(timespec="seconds")
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

    def test_journal_import_rejects_path_traversal(self):
        self._use(self.src)
        outside = self.root / "escaped.json"
        journal.import_journal_entry(
            {
                "id": "entry_../../../escaped",
                "content": "should not land outside Journal",
                "date": datetime.now().isoformat(),
            }
        )
        self.assertFalse(outside.exists())
        root = journal.get_journal_directory().resolve()
        for path in root.rglob("*.json"):
            self.assertTrue(path.resolve().is_relative_to(root))
            self.assertNotIn("..", path.name)

    def test_future_timestamp_does_not_overwrite(self):
        self._use(self.src)
        item = work.create_work_item("Keep", scheduled_date=work._today().isoformat())
        icloud_sync.write_pack(self.pack)
        self._use(self.dst)
        icloud_sync.apply_pack(self.pack)
        pack = icloud_sync.read_pack(self.pack)
        incoming = next(row for row in pack["work"]["items"] if row["id"] == item["id"])
        incoming["title"] = "Poisoned"
        incoming["updated_at"] = "2099-01-01T00:00:00"
        icloud_sync._write_json(self.pack / "work.json", pack["work"])
        icloud_sync.apply_pack(self.pack)
        titles = {row["id"]: row["title"] for row in work.list_all_work_items()}
        self.assertEqual(titles[item["id"]], "Keep")

    def test_settings_rpc_ignores_folder(self):
        self._use(self.src)
        before = icloud_sync.load_settings()["folder"]
        icloud_sync.save_icloud_sync_settings({"folder": "/tmp/kosistenz-evil", "auto": True})
        after = icloud_sync.load_settings()
        self.assertTrue(after["auto"])
        self.assertEqual(after["folder"], before)
        self.assertNotIn("kosistenz-evil", after["folder"])

    def test_pack_includes_resolved_appearance_colors(self):
        import appearance

        self._use(self.src)
        appearance.save_appearance_settings(
            {
                "theme": "paper",
                "colorOverrides": {"accent": "#c45c6a", "pageBg": "#f4e8c8"},
                "widgetBorderWidth": 2,
            }
        )
        pack = icloud_sync.build_pack()
        resolved = pack["appearance"]["resolved"]
        self.assertEqual(set(resolved["colors"]), set(appearance.COLOR_SLOTS))
        self.assertEqual(resolved["colors"]["accent"], "#c45c6a")
        self.assertEqual(resolved["colors"]["pageBg"], "#f4e8c8")
        self.assertIn("ink", resolved)
        self.assertEqual(resolved["widgetBorderWidth"], 2)
        exported = icloud_sync.write_pack(self.pack)
        self.assertTrue(exported["ok"])
        on_disk = icloud_sync._read_json(self.pack / "appearance.json", {})
        self.assertEqual(on_disk["resolved"]["colors"]["accent"], "#c45c6a")

    def test_open_pull_imports_phone_todo_when_auto_pull_on(self):
        self._use(self.src)
        dest = icloud_sync.default_sync_dir()
        icloud_sync.save_settings({"auto": True, "auto_pull": True})
        icloud_sync.write_pack(dest)
        pack = icloud_sync.read_pack(dest)
        pack["work"]["items"].append(
            {
                "id": "phone-1",
                "title": "From the train",
                "scheduled_date": work._today().isoformat(),
                "status": "open",
                "updated_at": datetime.now().isoformat(timespec="seconds"),
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "duration_seconds": 0,
                "sort_order": 0,
                "source": "iphone",
            }
        )
        icloud_sync._write_json(dest / "work.json", pack["work"])
        icloud_sync._last_open_pull = 0.0
        result = icloud_sync.maybe_pull_icloud_on_open()
        self.assertTrue(result.get("ok"))
        self.assertFalse(result.get("skipped"))
        titles = [row["title"] for row in work.list_all_work_items()]
        self.assertIn("From the train", titles)

    def test_running_zero_miles_is_not_imported(self):
        self._use(self.src)
        icloud_sync.write_pack(self.pack)
        pack = icloud_sync.read_pack(self.pack)
        pack["workouts"]["sessions"].append(
            {
                "id": "bad-run",
                "local_date": work._today().isoformat(),
                "kind": "running",
                "miles": 0,
                "other_label": "",
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
        )
        icloud_sync._write_json(self.pack / "workouts.json", pack["workouts"])
        icloud_sync.apply_pack(self.pack)
        day = workouts.get_workout_day(work._today().isoformat())
        ids = [row.get("id") for row in day.get("sessions") or []]
        self.assertNotIn("bad-run", ids)

    def test_journal_newer_edit_overwrites(self):
        self._use(self.src)
        saved = journal.save_journal_entry("First pass.")
        icloud_sync.write_pack(self.pack)
        pack = icloud_sync.read_pack(self.pack)
        row = next(entry for entry in pack["journal"] if entry["id"] == saved["id"])
        row["content"] = "Edited on the phone."
        row["updated_at"] = (datetime.now() + timedelta(minutes=1)).isoformat(timespec="seconds")
        icloud_sync._write_json(self.pack / "journal.json", pack["journal"])
        icloud_sync.apply_pack(self.pack)
        texts = [entry.get("content") for entry in journal.get_all_entries()]
        self.assertIn("Edited on the phone.", texts)


if __name__ == "__main__":
    unittest.main()

