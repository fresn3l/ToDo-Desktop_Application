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
        self.assertEqual(item["estimate_minutes"], 30)
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


if __name__ == "__main__":
    unittest.main()
