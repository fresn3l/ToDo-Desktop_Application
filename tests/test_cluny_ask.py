"""Ask Cluny inbox: accept into All Work, never a calendar block, dedup."""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest import mock

import cluny_ask
import cluny_client
import work


class ClunyAskTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"KOSISTENZ_DATA_DIR": self.tmp.name}, clear=False)
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

    def tearDown(self) -> None:
        self.env.stop()
        self.tmp.cleanup()

    def test_health_down_is_offline_copy_not_an_exception(self) -> None:
        with mock.patch.object(
            cluny_client, "_request", side_effect=ValueError("Cluny is off or unreachable")
        ):
            probe = cluny_client.health()
        self.assertFalse(probe["ok"])
        self.assertFalse(probe["brain_ready"])
        self.assertEqual(probe["status"], "offline")

    def test_proposal_uid_hashes_title_due_keywords(self) -> None:
        uid = cluny_ask.proposal_uid(
            {"title": "Spanish vocab", "due": "2026-09-10", "keywords": ["spanish"]}
        )
        again = cluny_ask.proposal_uid(
            {"title": "Spanish vocab", "due": "2026-09-10", "keywords": ["spanish"]}
        )
        other = cluny_ask.proposal_uid(
            {"title": "Spanish vocab", "due": "2026-09-11", "keywords": ["spanish"]}
        )
        self.assertEqual(uid, again)
        self.assertNotEqual(uid, other)
        self.assertTrue(uid.startswith("cluny-"))

    def _seed_pending(self, **row: object) -> str:
        packed = {
            "id": row.get("id") or "abc",
            "title": row.get("title") or "Spanish vocab",
            "estimate_minutes": row.get("estimate_minutes", 30),
            "due": row.get("due", "2026-09-10"),
            "keywords": row.get("keywords") or ["spanish"],
            "status": "pending",
        }
        cluny_ask._save_inbox({"pending": [packed], "closed": []})
        return str(packed["id"])

    def test_accept_creates_backlog_item_not_a_calendar_block(self) -> None:
        uid = self._seed_pending()
        result = cluny_ask.accept_cluny_proposal(uid)
        item = result["item"]
        self.assertFalse(result["duplicate"])
        self.assertEqual(item["source"], "cluny_proposal")
        self.assertEqual(item["source_calendar"], "cluny")
        self.assertEqual(item["source_uid"], uid)
        self.assertIsNone(item["scheduled_date"])
        self.assertTrue(item["is_backlog"])
        self.assertEqual(item["due_at"][:10], "2026-09-10")
        self.assertEqual(item["due_at"], "2026-09-10T23:59:00")
        self.assertEqual(item["estimate_minutes"], 30)
        self.assertIsNone(item.get("start_at"))
        self.assertNotIn("14:", item["due_at"])
        today = work._today().isoformat()
        board = work.get_work_board(today)
        dated = [row["id"] for row in board["today"] + board["upcoming"]]
        self.assertNotIn(item["id"], dated)
        backlog_ids = [row["id"] for row in work.list_backlog()]
        self.assertIn(item["id"], backlog_ids)

    def test_second_accept_of_same_uid_does_not_duplicate(self) -> None:
        uid = self._seed_pending()
        first = cluny_ask.accept_cluny_proposal(uid)
        second = cluny_ask.accept_cluny_proposal(uid)
        self.assertTrue(second["duplicate"])
        matches = [
            row
            for row in work.list_all_work_items()
            if row.get("source_uid") == uid
        ]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["id"], first["item"]["id"])
        cluny_ask._save_inbox(
            {
                "pending": [
                    {
                        "id": uid,
                        "title": "Spanish vocab",
                        "due": "2026-09-10",
                        "keywords": ["spanish"],
                    }
                ],
                "closed": [],
            }
        )
        third = cluny_ask.accept_cluny_proposal(uid)
        self.assertEqual(third["item"]["id"], first["item"]["id"])
        matches = [
            row
            for row in work.list_all_work_items()
            if row.get("source_uid") == uid
        ]
        self.assertEqual(len(matches), 1)

    def test_dismiss_keeps_the_same_row_out_of_pending(self) -> None:
        uid = self._seed_pending()
        inbox = cluny_ask.dismiss_cluny_proposal(uid)
        self.assertEqual(inbox["pending_count"], 0)
        with mock.patch.object(
            cluny_client,
            "propose",
            return_value=[
                {
                    "id": uid,
                    "title": "Spanish vocab",
                    "due": "2026-09-10",
                    "keywords": ["spanish"],
                }
            ],
        ):
            with mock.patch.object(cluny_ask, "build_context", return_value={"date": "2026-09-02"}):
                again = cluny_ask.suggest_cluny_work()
        self.assertEqual(again["added"], 0)
        self.assertEqual(again["pending_count"], 0)

    def test_suggest_hashes_id_when_cluny_omits_one(self) -> None:
        with mock.patch.object(
            cluny_client,
            "propose",
            return_value=[
                {
                    "title": "Essay outline",
                    "due": "2026-09-12",
                    "keywords": ["essay"],
                    "estimate_minutes": 45,
                }
            ],
        ):
            with mock.patch.object(cluny_ask, "build_context", return_value={"date": "2026-09-02"}):
                inbox = cluny_ask.suggest_cluny_work()
        self.assertEqual(inbox["added"], 1)
        row = inbox["pending"][0]
        expected = cluny_ask.proposal_uid(
            {"title": "Essay outline", "due": "2026-09-12", "keywords": ["essay"]}
        )
        self.assertEqual(row["id"], expected)

    def test_free_minutes_subtracts_busy_blocks(self) -> None:
        minutes = cluny_ask.free_minutes(
            [{"start": "09:00", "end": "10:00"}, {"start": "09:30", "end": "11:00"}],
            "07:00",
            "12:00",
        )
        self.assertEqual(minutes, 180)

    def test_context_lists_today_work_and_forbids_clock_times(self) -> None:
        today = work._today().isoformat()
        work.create_work_item("Essay", scheduled_date=today)
        work.create_work_item("Spanish backlog")
        ctx = cluny_ask.build_context()
        self.assertEqual(ctx["date"], today)
        self.assertIn("Essay", [row["title"] for row in ctx["todos_today"]])
        self.assertIn("Spanish backlog", [row["title"] for row in ctx["backlog"]])
        self.assertIn("Never pick a clock time", ctx["instruction"])
        self.assertIn("live list", ctx["instruction"])
        self.assertIn("free_minutes", ctx)
        self.assertIsInstance(ctx["free_minutes"], int)
        self.assertIn("analytics", ctx)
        self.assertIn("period", ctx["analytics"])
        self.assertIn("journal", ctx)
        self.assertIn("work", ctx)
        self.assertIn("calendar", ctx)

    def test_accept_stores_kosistenz_handshake(self) -> None:
        uid = self._seed_pending()
        with mock.patch.object(cluny_client, "mark_proposal_accepted") as posted:
            posted.return_value = {"ok": True}
            result = cluny_ask.accept_cluny_proposal(uid)
        item_id = result["item"]["id"]
        kid = f"kosistenz:{item_id}"
        self.assertEqual(result["kosistenz_id"], kid)
        closed = result["inbox"]["closed"][0]
        self.assertEqual(closed["kosistenz_id"], kid)
        posted.assert_called_once_with(uid, kid)

    def test_accept_succeeds_when_accepted_pointer_fails(self) -> None:
        uid = self._seed_pending()
        with mock.patch.object(
            cluny_client,
            "mark_proposal_accepted",
            return_value={"ok": False, "error": "Cluny HTTP 404"},
        ):
            result = cluny_ask.accept_cluny_proposal(uid)
        self.assertTrue(result["ok"])
        self.assertFalse(result["duplicate"])
        self.assertTrue(str(result["kosistenz_id"]).startswith("kosistenz:"))

    def test_parse_citations_keeps_known_fields_and_drops_junk(self) -> None:
        parsed = cluny_client.parse_citations(
            [
                {"title": "Syllabus.pdf", "locator": "p.4", "score": 0.9, "unknown": True},
                {"label": "Lecture notes"},
                "Reading list",
                None,
                12,
                {},
            ]
        )
        self.assertEqual(
            parsed,
            [
                {"title": "Syllabus.pdf", "locator": "p.4", "label": "Syllabus.pdf"},
                {"title": "Lecture notes", "locator": "", "label": "Lecture notes"},
                {"title": "Reading list", "locator": "", "label": "Reading list"},
            ],
        )
        self.assertEqual(cluny_client.parse_citations(None), [])
        self.assertEqual(cluny_client.parse_citations({"title": "nope"}), [])

    def test_propose_keeps_citations_and_day_due(self) -> None:
        payload = {
            "proposals": [
                {
                    "id": "syl-1",
                    "title": "Read week 3",
                    "due": "2026-09-12T14:30:00",
                    "estimate_minutes": 25,
                    "keywords": ["spanish"],
                    "unknown": "drop-me",
                    "citations": [
                        {"title": "Syllabus.pdf", "locator": "p.4", "score": 0.9},
                        "Lecture notes",
                    ],
                }
            ],
            "sources": [{"title": "Library dump"}],
        }
        with mock.patch.object(cluny_client, "_request", return_value=payload):
            result = cluny_client.propose("next")
        row = result["proposals"][0]
        self.assertEqual(row["id"], "syl-1")
        self.assertEqual(row["due"], "2026-09-12")
        self.assertNotIn("unknown", row)
        self.assertEqual(row["citations"][0]["title"], "Syllabus.pdf")
        self.assertEqual(row["citations"][0]["locator"], "p.4")
        self.assertEqual(row["citations"][1]["label"], "Lecture notes")
        self.assertEqual(result["sources"][0]["title"], "Library dump")

    def test_mark_proposal_accepted_posts_pointer(self) -> None:
        with mock.patch.object(cluny_client, "_request", return_value={"ok": True}) as req:
            result = cluny_client.mark_proposal_accepted("syl-1", "kosistenz:abc")
        self.assertTrue(result["ok"])
        self.assertEqual(req.call_args.args[0], "POST")
        self.assertIn("/propose/accepted", req.call_args.args[1])
        self.assertEqual(
            req.call_args.args[2],
            {"proposal_id": "syl-1", "kosistenz_id": "kosistenz:abc"},
        )

    def test_mark_proposal_accepted_does_not_raise_when_cluny_is_off(self) -> None:
        with mock.patch.object(
            cluny_client, "_request", side_effect=ValueError("Cluny is off or unreachable")
        ):
            result = cluny_client.mark_proposal_accepted("syl-1", "kosistenz:abc")
        self.assertFalse(result["ok"])
        self.assertIn("Cluny is off", result["error"])

    def test_suggest_stores_per_proposal_citations(self) -> None:
        with mock.patch.object(
            cluny_client,
            "propose",
            return_value={
                "proposals": [
                    {
                        "id": "syl-1",
                        "title": "Read week 3",
                        "due": "2026-09-12",
                        "keywords": ["spanish"],
                        "citations": [
                            {"title": "Syllabus.pdf", "locator": "p.4", "extra": "ignore"}
                        ],
                    }
                ],
                "sources": [{"title": "Old top-level"}],
            },
        ):
            with mock.patch.object(cluny_ask, "build_context", return_value={"date": "2026-09-02"}):
                inbox = cluny_ask.suggest_cluny_work()
        row = inbox["pending"][0]
        self.assertEqual(row["id"], "syl-1")
        self.assertEqual(row["citations"], [{"title": "Syllabus.pdf", "locator": "p.4", "label": "Syllabus.pdf"}])

    def test_suggest_falls_back_to_top_level_sources(self) -> None:
        with mock.patch.object(
            cluny_client,
            "propose",
            return_value={
                "proposals": [
                    {
                        "id": "syl-2",
                        "title": "Outline essay",
                        "due": "2026-09-14",
                    }
                ],
                "sources": [{"title": "Essay prompt.pdf", "locator": "p.1"}],
            },
        ):
            with mock.patch.object(cluny_ask, "build_context", return_value={"date": "2026-09-02"}):
                inbox = cluny_ask.suggest_cluny_work()
        self.assertEqual(
            inbox["pending"][0]["citations"],
            [{"title": "Essay prompt.pdf", "locator": "p.1", "label": "Essay prompt.pdf"}],
        )

    def test_due_date_only_drops_clock_times(self) -> None:
        self.assertEqual(cluny_ask.due_date_only("2026-09-10T14:30:00"), "2026-09-10")
        self.assertEqual(cluny_ask.due_date_only("2026-09-10 14:30"), "2026-09-10")
        self.assertEqual(cluny_ask.due_date_only("2026-09-10"), "2026-09-10")
        self.assertIsNone(cluny_ask.due_date_only("14:30"))
        self.assertIsNone(cluny_ask.due_date_only(""))

    def test_accept_strips_hhmm_from_proposal_due(self) -> None:
        uid = self._seed_pending(due="2026-09-10T14:30:00")
        result = cluny_ask.accept_cluny_proposal(uid)
        item = result["item"]
        self.assertEqual(item["due_at"], "2026-09-10T23:59:00")
        self.assertIsNone(item["scheduled_date"])
        self.assertTrue(item["is_backlog"])


if __name__ == "__main__":
    unittest.main()
