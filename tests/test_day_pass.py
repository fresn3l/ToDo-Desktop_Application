"""Day-first calendar: one appointment shape, one to-do shape, no daily Push."""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

import calclock
import icloud_sync
import schedule
import work


ROOT = Path(__file__).resolve().parents[1]


class DayPassTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.env = mock.patch.dict(os.environ, {"KOSISTENZ_DATA_DIR": str(self.root)})
        self.env.start()
        icloud_sync._last_written_stamp = ""
        icloud_sync._exporting = False
        work.invalidate_work_board_cache()
        calclock.reset_purge_cache()
        self.addCleanup(self.env.stop)
        self.addCleanup(work.cancel_heavy_snapshot_side_effects)
        self.addCleanup(self.tmp.cleanup)

    def test_blank_appointment_is_not_saved(self) -> None:
        with self.assertRaises(ValueError):
            calclock.create_calendar_event("  ", "2026-10-26T09:30:00", "2026-10-26T10:00:00")
        self.assertEqual(calclock.list_owned_hard_events(), [])

    def test_dated_todo_stays_a_list_item(self) -> None:
        result = schedule.add_todo_to_calendar("Read the chapter", on_date="2026-10-26")
        self.assertEqual(result["item"]["scheduled_date"], "2026-10-26")
        self.assertIsNone(result["start_at"])
        self.assertEqual(calclock.list_owned_hard_events(), [])
        parked = schedule.add_todo_to_calendar("A thought", on_date="park")
        self.assertIsNone(parked["item"]["scheduled_date"])

    def test_mac_appointment_reaches_the_pack_without_a_manual_push(self) -> None:
        icloud_sync.ensure_automatic_sync()
        calclock.create_calendar_event(
            "Lab meeting",
            "2026-10-26T09:30:00",
            "2026-10-26T10:30:00",
        )
        folder = Path(icloud_sync.load_settings()["folder"])
        payload = icloud_sync._read_json(folder / "calendar.json", {})
        titles = [row.get("title") for row in payload.get("hard_events") or []]
        self.assertIn("Lab meeting", titles)
        self.assertEqual(payload["hard_events"][0]["source"], "kosistenz")

    def test_phone_appointment_and_checkoff_come_back(self) -> None:
        item = work.create_work_item("Call the lab", scheduled_date="2026-10-26")
        icloud_sync.ensure_automatic_sync()
        icloud_sync.write_pack()
        folder = Path(icloud_sync.load_settings()["folder"])
        now = datetime.now().replace(microsecond=0)
        calendar = icloud_sync._read_json(folder / "calendar.json", {})
        calendar.setdefault("hard_events", []).append(
            {
                "id": "phone-lab",
                "title": "Office hours",
                "start_at": "2026-10-26T14:00:00",
                "end_at": "2026-10-26T15:00:00",
                "weekdays": [],
                "source": "iphone",
                "created_at": now.isoformat(timespec="seconds"),
                "updated_at": now.isoformat(timespec="seconds"),
            }
        )
        icloud_sync._write_json(folder / "calendar.json", calendar)
        packed = icloud_sync._read_json(folder / "work.json", {"items": []})
        row = next(entry for entry in packed["items"] if entry["id"] == item["id"])
        row["status"] = "done"
        row["updated_at"] = (now + timedelta(minutes=2)).isoformat(timespec="seconds")
        icloud_sync._write_json(folder / "work.json", packed)
        manifest = icloud_sync._read_json(folder / "manifest.json", {})
        manifest["exported_at"] = (now + timedelta(minutes=2)).isoformat(timespec="seconds")
        icloud_sync._write_json(folder / "manifest.json", manifest)
        icloud_sync._last_written_stamp = ""
        pulled = icloud_sync.pull_if_remote_changed()
        self.assertTrue(pulled.get("pulled_remote"))
        owned = {row["id"]: row for row in calclock.list_owned_hard_events()}
        self.assertEqual(owned["phone-lab"]["title"], "Office hours")
        stored = {row["id"]: row for row in work.list_all_work_items()}
        self.assertEqual(stored[item["id"]]["status"], "done")

    def test_next_appointment_is_on_the_glance(self) -> None:
        frozen = datetime(2026, 10, 25, 8, 0, 0)
        with mock.patch.object(calclock, "_now", return_value=frozen):
            calclock.create_calendar_event(
                "Lab",
                "2026-10-25T09:30:00",
                "2026-10-25T10:30:00",
            )
            snap = work.refresh_widget_snapshot()
        self.assertEqual(snap["next_title"], "Lab")
        self.assertEqual(snap["next_when"], "09:30–10:30")
        self.assertIn("09:30–10:30 Lab", snap["summary"])

    def test_automatic_sync_turns_on_once(self) -> None:
        self.assertEqual(icloud_sync.load_settings()["sync_pass"], 0)
        turned = icloud_sync.ensure_automatic_sync()
        self.assertTrue(turned["auto"])
        self.assertTrue(turned["auto_pull"])
        self.assertEqual(turned["sync_pass"], 1)
        icloud_sync.save_settings({"auto": False, "auto_pull": False})
        again = icloud_sync.ensure_automatic_sync()
        self.assertFalse(again["auto"])
        self.assertFalse(again["auto_pull"])
        self.assertEqual(again["sync_pass"], 1)

    def test_pull_skips_our_own_export(self) -> None:
        icloud_sync.ensure_automatic_sync()
        icloud_sync.write_pack()
        skipped = icloud_sync.pull_if_remote_changed()
        self.assertTrue(skipped.get("skipped"))
        self.assertEqual(skipped.get("reason"), "own_export")

    def test_day_surfaces_stay_quiet(self) -> None:
        index = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        calendar = (ROOT / "web" / "js" / "calendar.js").read_text(encoding="utf-8")
        chrome = (ROOT / "macos" / "KosistenzChrome.swift").read_text(encoding="utf-8")
        mac_widget = (ROOT / "macos" / "KosistenzWidget.swift").read_text(encoding="utf-8")
        phone = (ROOT / "ios" / "Kosistenz" / "TodayScreen.swift").read_text(encoding="utf-8")
        phone_widget = (ROOT / "ios" / "KosistenzWidget" / "KosistenzWidget.swift").read_text(encoding="utf-8")
        listing = (ROOT / "ios" / "Kosistenz" / "TodayList.swift").read_text(encoding="utf-8")
        span = calendar.split("async function onSpanPointerUp", 1)[1].split("function onBlockPointerDown", 1)[0]
        event_draw = span.split("drawKind === 'event'", 1)[1].split("} else {", 1)[0]
        menu = chrome.split("func rebuildStatusMenu", 1)[1].split("func openKosistenz", 1)[0]
        self.assertIn("startNewEvent()", event_draw)
        self.assertNotIn("create_calendar_event", event_draw)
        self.assertNotIn('placeholder="2026-09-08 0930"', index)
        self.assertIn('id="calEventDate"', index)
        self.assertIn("next_title", menu)
        self.assertNotIn("Log session", menu)
        self.assertNotIn("New journal", menu)
        self.assertIn("nextTitle", mac_widget)
        self.assertNotIn("Workout logged", mac_widget)
        self.assertNotIn("journalStreak", mac_widget.split("var body: some View", 1)[1])
        self.assertIn('Section("On the clock")', phone)
        self.assertIn('Section("Today")', phone)
        self.assertIn('Section("Park")', phone)
        self.assertIn("PackActions.park", phone)
        self.assertIn("nextBlock", phone_widget)
        self.assertNotIn("expectedLabel", phone_widget)
        self.assertNotIn("item.itemId ?? item.id", listing)
        self.assertIn("item.markKey", listing)
