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
        self.assertNotIn("journal", kinds)
        self.assertIn("goals", kinds)
        self.assertIn("allwork", kinds)
        self.assertIn("analytics", kinds)
        self.assertIn("timeline", kinds)
        self.assertIn("weather", kinds)
        self.assertIn("focus", kinds)
        self.assertIn("countdown", kinds)
        self.assertIn("habits", kinds)
        self.assertIn("heatmap", kinds)
        self.assertIn("day_brief", kinds)
        self.assertIn("counters", kinds)
        self.assertIn("reading", kinds)
        self.assertIn("word", kinds)
        self.assertIn("cluny", kinds)
        self.assertNotIn("checklist", kinds)
        self.assertNotIn("settings", kinds)
        self.assertNotIn("calendar", kinds)

    def test_default_home_is_a_bento_of_day_slices(self) -> None:
        layout = home_layout.default_layout()
        self.assertEqual(len(layout["pages"]), 1)
        self.assertEqual(layout["pages"][0]["name"], "Home")
        kinds = [item["kind"] for item in layout["pages"][0]["widgets"]]
        self.assertEqual(kinds, ["todo", "today_calendar", "weather", "word", "cluny"])
        todo = layout["pages"][0]["widgets"][0]
        today = layout["pages"][0]["widgets"][1]
        weather = layout["pages"][0]["widgets"][2]
        word = layout["pages"][0]["widgets"][3]
        cluny = layout["pages"][0]["widgets"][4]
        self.assertEqual((todo["x"], todo["y"], todo["w"], todo["h"]), (0, 0, 2, 2))
        self.assertEqual(todo.get("region"), "above")
        self.assertEqual((today["x"], today["y"], today["w"], today["h"]), (2, 0, 2, 2))
        self.assertEqual(today.get("region"), "above")
        self.assertEqual((weather["x"], weather["y"], weather["w"], weather["h"]), (0, 0, 1, 1))
        self.assertNotEqual(weather.get("region"), "above")
        self.assertEqual((word["x"], word["y"], word["w"], word["h"]), (1, 0, 1, 1))
        self.assertEqual((cluny["x"], cluny["y"], cluny["w"], cluny["h"]), (2, 0, 2, 2))
        self.assertEqual(cluny["kind"], "cluny")
        self.assertFalse(home_layout.boxes_overlap(todo, today))
        self.assertFalse(home_layout.boxes_overlap(weather, word))
        self.assertFalse(home_layout.boxes_overlap(weather, cluny))
        self.assertFalse(home_layout.boxes_overlap(word, cluny))

    def test_fresh_file_writes_the_default(self) -> None:
        layout = home_layout.get_home_layout()
        self.assertTrue((self.root / "home_layout.json").exists())
        self.assertEqual(
            [item["kind"] for item in layout["pages"][0]["widgets"]],
            ["todo", "today_calendar", "weather", "word", "cluny"],
        )

    def test_each_kind_has_a_few_allowed_sizes(self) -> None:
        for kind, spec in home_layout.WIDGET_CATALOG.items():
            sizes = spec["sizes"]
            self.assertGreaterEqual(len(sizes), 4, kind)
            self.assertLessEqual(len(sizes), 8, kind)
            self.assertIn(spec["default"], sizes)
            self.assertEqual(home_layout.coerce_size(kind, 99, 99), spec["default"])

    def test_glance_widgets_can_be_one_by_one(self) -> None:
        self.assertIn((1, 1), home_layout.allowed_sizes("weather"))
        self.assertIn((1, 1), home_layout.allowed_sizes("word"))
        self.assertIn((1, 1), home_layout.allowed_sizes("focus"))
        self.assertEqual(home_layout.spec_default("weather"), (2, 1))
        self.assertEqual(home_layout.spec_default("word"), (1, 1))
        self.assertIn((2, 2), home_layout.allowed_sizes("analytics"))
        self.assertEqual(home_layout.coerce_size("analytics", 2, 2), (2, 2))

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
                        {"id": "b", "kind": "workout", "x": 0, "y": 0, "w": 2, "h": 2},
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
        layout = home_layout.add_home_widget(page_id, "focus")
        self.assertIn("focus", [item["kind"] for item in layout["pages"][0]["widgets"]])

    def test_move_rejects_overlap_resize_cycles(self) -> None:
        layout = home_layout.get_home_layout()
        page_id = layout["pages"][0]["id"]
        todo = next(item for item in layout["pages"][0]["widgets"] if item["kind"] == "todo")
        with self.assertRaises(ValueError):
            home_layout.move_widget(layout, page_id, todo["id"], 2, 0)
        layout = home_layout.resize_home_widget(page_id, todo["id"])
        todo = next(item for item in layout["pages"][0]["widgets"] if item["kind"] == "todo")
        self.assertIn((todo["w"], todo["h"]), home_layout.allowed_sizes("todo"))
        self.assertNotEqual((todo["w"], todo["h"]), (2, 2))

    def test_resize_snaps_to_nearest_allowed_size(self) -> None:
        self.assertEqual(home_layout.nearest_size("todo", 2, 2), (2, 2))
        self.assertEqual(home_layout.nearest_size("todo", 4, 3), (4, 3))
        self.assertEqual(home_layout.nearest_size("analytics", 5, 5), (4, 4))
        self.assertEqual(home_layout.nearest_size("weather", 1, 1), (1, 1))
        layout = home_layout.get_home_layout()
        page_id = layout["pages"][0]["id"]
        todo = next(item for item in layout["pages"][0]["widgets"] if item["kind"] == "todo")
        with self.assertRaises(ValueError):
            home_layout.resize_widget(layout, page_id, todo["id"], 4, 2)
        today = next(item for item in layout["pages"][0]["widgets"] if item["kind"] == "today_calendar")
        layout = home_layout.remove_home_widget(page_id, today["id"])
        weather = next(item for item in layout["pages"][0]["widgets"] if item["kind"] == "weather")
        layout = home_layout.remove_home_widget(page_id, weather["id"])
        word = next(item for item in layout["pages"][0]["widgets"] if item["kind"] == "word")
        layout = home_layout.remove_home_widget(page_id, word["id"])
        todo = next(item for item in layout["pages"][0]["widgets"] if item["kind"] == "todo")
        layout = home_layout.resize_home_widget(page_id, todo["id"], 4, 3)
        todo = next(item for item in layout["pages"][0]["widgets"] if item["kind"] == "todo")
        self.assertEqual((todo["w"], todo["h"], todo["x"], todo["y"]), (4, 3, 0, 0))

    def test_remove_widget(self) -> None:
        layout = home_layout.get_home_layout()
        page_id = layout["pages"][0]["id"]
        today = next(item for item in layout["pages"][0]["widgets"] if item["kind"] == "today_calendar")
        layout = home_layout.remove_home_widget(page_id, today["id"])
        kinds = [item["kind"] for item in layout["pages"][0]["widgets"]]
        self.assertEqual(kinds, ["todo", "weather", "word", "cluny"])

    def test_today_can_move_down_without_hitting_todo(self) -> None:
        layout = home_layout.get_home_layout()
        page_id = layout["pages"][0]["id"]
        today = next(item for item in layout["pages"][0]["widgets"] if item["kind"] == "today_calendar")
        moved = home_layout.move_home_widget(page_id, today["id"], 2, 3)
        row = next(item for item in moved["pages"][0]["widgets"] if item["id"] == today["id"])
        self.assertEqual((row["x"], row["y"]), (2, 3))
        todo = next(item for item in moved["pages"][0]["widgets"] if item["kind"] == "todo")
        self.assertEqual((todo["x"], todo["y"]), (0, 0))

    def test_page_name_is_clipped(self) -> None:
        layout = home_layout.get_home_layout()
        page_id = layout["pages"][0]["id"]
        layout = home_layout.rename_home_page(page_id, "x" * 80)
        self.assertEqual(len(layout["pages"][0]["name"]), 40)

    def test_page_colors_are_optional_and_sanitized(self) -> None:
        layout = home_layout.get_home_layout()
        page_id = layout["pages"][0]["id"]
        self.assertNotIn("colors", layout["pages"][0])
        layout = home_layout.set_home_page_colors(
            page_id,
            {
                "pageBg": "#112233",
                "titles": "abc",
                "nope": "#ffffff",
                "widgetBorder": "not-a-color",
            },
        )
        self.assertEqual(layout["pages"][0]["colors"]["pageBg"], "#112233")
        self.assertEqual(layout["pages"][0]["colors"]["titles"], "#aabbcc")
        self.assertNotIn("nope", layout["pages"][0]["colors"])
        self.assertNotIn("widgetBorder", layout["pages"][0]["colors"])
        extra = home_layout.add_home_page("Studio")
        extra_id = extra["pages"][1]["id"]
        extra = home_layout.set_home_page_colors(extra_id, {"accent": "#4f8fcf"})
        home_colors = next(page["colors"] for page in extra["pages"] if page["id"] == page_id)
        self.assertEqual(home_colors["pageBg"], "#112233")
        studio = next(page for page in extra["pages"] if page["id"] == extra_id)
        self.assertEqual(studio["colors"]["accent"], "#4f8fcf")
        cleared = home_layout.set_home_page_colors(page_id, {})
        home = next(page for page in cleared["pages"] if page["id"] == page_id)
        self.assertNotIn("colors", home)

    def test_new_home_widgets_can_be_added(self) -> None:
        layout = home_layout.get_home_layout()
        page_id = layout["pages"][0]["id"]
        layout = home_layout.add_home_widget(page_id, "focus")
        layout = home_layout.add_home_widget(page_id, "countdown")
        layout = home_layout.add_home_widget(page_id, "habits")
        layout = home_layout.add_home_widget(page_id, "heatmap")
        layout = home_layout.add_home_widget(page_id, "day_brief")
        layout = home_layout.add_home_widget(page_id, "counters")
        layout = home_layout.add_home_widget(page_id, "reading")
        kinds = [item["kind"] for item in layout["pages"][0]["widgets"]]
        self.assertIn("weather", kinds)
        self.assertIn("focus", kinds)
        self.assertIn("countdown", kinds)
        self.assertIn("habits", kinds)
        self.assertIn("heatmap", kinds)
        self.assertIn("day_brief", kinds)
        self.assertIn("counters", kinds)
        self.assertIn("reading", kinds)
        self.assertIn("word", kinds)
        self.assertIn("cluny", kinds)
        self.assertNotIn("checklist", kinds)
        self.assertEqual(home_layout.coerce_size("countdown", 4, 2), (4, 2))
        self.assertEqual(home_layout.coerce_size("heatmap", 2, 2), (2, 2))
        self.assertEqual(home_layout.coerce_size("heatmap", 3, 1), (4, 1))
        self.assertEqual(home_layout.coerce_size("day_brief", 2, 3), (2, 3))

    def test_reset_restores_first_install(self) -> None:
        layout = home_layout.get_home_layout()
        home_layout.add_home_page("Extra")
        layout = home_layout.reset_home_layout()
        self.assertEqual(len(layout["pages"]), 1)
        self.assertEqual(
            [item["kind"] for item in layout["pages"][0]["widgets"]],
            ["todo", "today_calendar", "weather", "word", "cluny"],
        )

    def test_sanitize_drops_journal_and_checklist_widgets(self) -> None:
        packed = home_layout.sanitize_layout(
            {
                "pages": [
                    {
                        "id": "p1",
                        "name": "Home",
                        "widgets": [
                            {"id": "a", "kind": "todo", "x": 0, "y": 0, "w": 2, "h": 2, "region": "above"},
                            {"id": "b", "kind": "journal", "x": 2, "y": 0, "w": 2, "h": 2},
                            {"id": "c", "kind": "checklist", "x": 0, "y": 2, "w": 2, "h": 2},
                        ],
                    }
                ]
            }
        )
        kinds = [item["kind"] for item in packed["pages"][0]["widgets"]]
        self.assertEqual(kinds, ["todo"])

    def test_first_page_keeps_above_and_below_regions(self) -> None:
        layout = home_layout.get_home_layout()
        page_id = layout["pages"][0]["id"]
        weather = next(item for item in layout["pages"][0]["widgets"] if item["kind"] == "weather")
        layout = home_layout.move_home_widget(page_id, weather["id"], 0, 2, "above")
        weather = next(item for item in layout["pages"][0]["widgets"] if item["kind"] == "weather")
        self.assertEqual(weather.get("region"), "above")
        self.assertEqual((weather["x"], weather["y"]), (0, 2))
        extra = home_layout.add_home_page("Studio")
        extra_id = extra["pages"][1]["id"]
        extra = home_layout.add_home_widget(extra_id, "focus", "above")
        focus = extra["pages"][1]["widgets"][0]
        self.assertNotEqual(focus.get("region"), "above")
        with self.assertRaises(ValueError):
            home_layout.add_widget(layout, page_id, "journal")
        with self.assertRaises(ValueError):
            home_layout.add_widget(layout, page_id, "checklist")

    def test_stock_home_seeds_ask_cluny(self) -> None:
        raw = {
            "pages": [
                {
                    "id": "p1",
                    "name": "Home",
                    "widgets": [
                        {"id": "a", "kind": "todo", "x": 0, "y": 0, "w": 2, "h": 2, "region": "above"},
                        {"id": "b", "kind": "today_calendar", "x": 2, "y": 0, "w": 2, "h": 2, "region": "above"},
                        {"id": "c", "kind": "weather", "x": 0, "y": 0, "w": 1, "h": 1},
                        {"id": "d", "kind": "word", "x": 1, "y": 0, "w": 1, "h": 1},
                    ],
                }
            ]
        }
        packed, added = home_layout.seed_ask_cluny(raw)
        self.assertTrue(added)
        kinds = [item["kind"] for item in packed["pages"][0]["widgets"]]
        self.assertIn("cluny", kinds)
        again, added_again = home_layout.seed_ask_cluny(packed)
        self.assertFalse(added_again)
        self.assertEqual(len(again["pages"][0]["widgets"]), len(packed["pages"][0]["widgets"]))
