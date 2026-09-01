"""Home pages, snap-to-grid widgets, and first-install defaults."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import home_layout


class HomeLayoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.env = mock.patch.dict(os.environ, {"KOSISTENZ_DATA_DIR": str(self.root)})
        self.env.start()

    def tearDown(self) -> None:
        self.env.stop()
        self.tmp.cleanup()

    def test_catalog_lists_folded_tabs_not_settings_or_calendar(self) -> None:
        kinds = {row["kind"] for row in home_layout.catalog()}
        self.assertIn("todo", kinds)
        self.assertIn("today_calendar", kinds)
        self.assertIn("workout", kinds)
        self.assertIn("journal", kinds)
        self.assertIn("goals", kinds)
        self.assertIn("allwork", kinds)
        self.assertIn("analytics", kinds)
        self.assertIn("timeline", kinds)
        self.assertIn("countdown", kinds)
        self.assertIn("heatmap", kinds)
        self.assertIn("day_brief", kinds)
        self.assertNotIn("settings", kinds)
        self.assertNotIn("calendar", kinds)

    def test_default_home_is_todo_and_today_calendar(self) -> None:
        layout = home_layout.default_layout()
        self.assertEqual(len(layout["pages"]), 1)
        self.assertEqual(layout["pages"][0]["name"], "Home")
        kinds = [item["kind"] for item in layout["pages"][0]["widgets"]]
        self.assertEqual(kinds, ["todo", "today_calendar"])
        todo = layout["pages"][0]["widgets"][0]
        today = layout["pages"][0]["widgets"][1]
        self.assertEqual((todo["x"], todo["y"], todo["w"], todo["h"]), (0, 0, 2, 3))
        self.assertEqual((today["x"], today["y"], today["w"], today["h"]), (2, 0, 2, 2))
        self.assertFalse(home_layout.boxes_overlap(todo, today))

    def test_fresh_file_writes_the_default(self) -> None:
        layout = home_layout.get_home_layout()
        self.assertTrue((self.root / "home_layout.json").exists())
        self.assertEqual([item["kind"] for item in layout["pages"][0]["widgets"]], ["todo", "today_calendar"])

    def test_each_kind_has_a_few_allowed_sizes(self) -> None:
        for kind, spec in home_layout.WIDGET_CATALOG.items():
            sizes = spec["sizes"]
            self.assertGreaterEqual(len(sizes), 2, kind)
            self.assertLessEqual(len(sizes), 4, kind)
            self.assertIn(spec["default"], sizes)
            self.assertEqual(home_layout.coerce_size(kind, 99, 99), spec["default"])

    def test_analytics_cannot_be_tiny(self) -> None:
        self.assertNotIn((2, 2), home_layout.allowed_sizes("analytics"))
        self.assertEqual(home_layout.coerce_size("analytics", 2, 2), (4, 3))

    def test_first_fit_skips_occupied_cells(self) -> None:
        occupied = [{"id": "a", "x": 0, "y": 0, "w": 2, "h": 2}]
        self.assertEqual(home_layout.first_fit(occupied, 2, 2), (2, 0))
        self.assertEqual(home_layout.first_fit(occupied, 4, 2), (0, 2))

    def test_sanitize_drops_unknown_and_duplicate_kinds(self) -> None:
        raw = {
            "pages": [
                {
                    "id": "p1",
                    "name": "Home",
                    "widgets": [
                        {"id": "a", "kind": "todo", "x": 0, "y": 0, "w": 2, "h": 3},
                        {"id": "b", "kind": "todo", "x": 2, "y": 0, "w": 2, "h": 2},
                        {"id": "c", "kind": "settings", "x": 0, "y": 3, "w": 2, "h": 2},
                    ],
                }
            ]
        }
        packed = home_layout.sanitize_layout(raw)
        kinds = [item["kind"] for item in packed["pages"][0]["widgets"]]
        self.assertEqual(kinds, ["todo"])

    def test_sanitize_restacks_overlaps(self) -> None:
        raw = {
            "pages": [
                {
                    "id": "p1",
                    "name": "Home",
                    "widgets": [
                        {"id": "a", "kind": "todo", "x": 0, "y": 0, "w": 2, "h": 2},
                        {"id": "b", "kind": "journal", "x": 0, "y": 0, "w": 2, "h": 2},
                    ],
                }
            ]
        }
        packed = home_layout.sanitize_layout(raw)
        a, b = packed["pages"][0]["widgets"]
        self.assertFalse(home_layout.boxes_overlap(a, b))

    def test_add_and_rename_pages(self) -> None:
        layout = home_layout.get_home_layout()
        home_id = layout["pages"][0]["id"]
        layout = home_layout.add_home_page("Lift")
        self.assertEqual(len(layout["pages"]), 2)
        self.assertEqual(layout["pages"][1]["name"], "Lift")
        self.assertEqual(layout["pages"][1]["widgets"], [])
        self.assertEqual(layout["active_page_id"], layout["pages"][1]["id"])
        lift_id = layout["pages"][1]["id"]
        layout = home_layout.rename_home_page(lift_id, "  Strength week  ")
        self.assertEqual(layout["pages"][1]["name"], "Strength week")
        layout = home_layout.delete_home_page(lift_id)
        self.assertEqual(len(layout["pages"]), 1)
        self.assertEqual(layout["active_page_id"], home_id)

    def test_cannot_delete_the_last_page(self) -> None:
        layout = home_layout.get_home_layout()
        with self.assertRaises(ValueError):
            home_layout.delete_page(layout, layout["pages"][0]["id"])

    def test_add_widget_first_fit_and_unique_per_page(self) -> None:
        layout = home_layout.get_home_layout()
        page_id = layout["pages"][0]["id"]
        layout = home_layout.add_home_widget(page_id, "workout")
        kinds = [item["kind"] for item in layout["pages"][0]["widgets"]]
        self.assertIn("workout", kinds)
        with self.assertRaises(ValueError):
            home_layout.add_widget(layout, page_id, "workout")
        with self.assertRaises(ValueError):
            home_layout.add_widget(layout, page_id, "calendar")

    def test_move_rejects_overlap_resize_cycles(self) -> None:
        layout = home_layout.get_home_layout()
        page_id = layout["pages"][0]["id"]
        todo = next(item for item in layout["pages"][0]["widgets"] if item["kind"] == "todo")
        with self.assertRaises(ValueError):
            home_layout.move_widget(layout, page_id, todo["id"], 2, 0)
        layout = home_layout.resize_home_widget(page_id, todo["id"])
        todo = next(item for item in layout["pages"][0]["widgets"] if item["kind"] == "todo")
        self.assertIn((todo["w"], todo["h"]), home_layout.allowed_sizes("todo"))
        self.assertNotEqual((todo["w"], todo["h"]), (2, 3))

    def test_remove_widget(self) -> None:
        layout = home_layout.get_home_layout()
        page_id = layout["pages"][0]["id"]
        today = next(item for item in layout["pages"][0]["widgets"] if item["kind"] == "today_calendar")
        layout = home_layout.remove_home_widget(page_id, today["id"])
        kinds = [item["kind"] for item in layout["pages"][0]["widgets"]]
        self.assertEqual(kinds, ["todo"])

    def test_page_name_is_clipped(self) -> None:
        layout = home_layout.get_home_layout()
        page_id = layout["pages"][0]["id"]
        layout = home_layout.rename_home_page(page_id, "x" * 80)
        self.assertEqual(len(layout["pages"][0]["name"]), 40)

    def test_new_home_widgets_can_be_added(self) -> None:
        layout = home_layout.get_home_layout()
        page_id = layout["pages"][0]["id"]
        layout = home_layout.add_home_widget(page_id, "countdown")
        layout = home_layout.add_home_widget(page_id, "heatmap")
        layout = home_layout.add_home_widget(page_id, "day_brief")
        kinds = [item["kind"] for item in layout["pages"][0]["widgets"]]
        self.assertIn("countdown", kinds)
        self.assertIn("heatmap", kinds)
        self.assertIn("day_brief", kinds)
        self.assertEqual(home_layout.coerce_size("countdown", 4, 2), (4, 2))
        self.assertEqual(home_layout.coerce_size("heatmap", 2, 2), (4, 2))
        self.assertEqual(home_layout.coerce_size("day_brief", 2, 3), (2, 3))

    def test_reset_restores_first_install(self) -> None:
        layout = home_layout.get_home_layout()
        home_layout.add_home_page("Extra")
        layout = home_layout.reset_home_layout()
        self.assertEqual(len(layout["pages"]), 1)
        self.assertEqual([item["kind"] for item in layout["pages"][0]["widgets"]], ["todo", "today_calendar"])
