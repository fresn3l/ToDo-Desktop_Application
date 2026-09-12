"""Home pages, snap-to-grid widgets, and first-install defaults."""

from __future__ import annotations

import ast
import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import home_layout

ROOT = Path(__file__).resolve().parents[1]
CLIENT_CATALOG = (ROOT / "web" / "js" / "home_layout.js").read_text(encoding="utf-8")


def _client_catalog() -> dict:
    """Read the browser copy of the widget catalog so the two cannot drift."""
    body = CLIENT_CATALOG.split("export const WIDGET_CATALOG = {", 1)[1].split("\n};", 1)[0]
    rows = {}
    for line in body.splitlines():
        match = re.match(
            r"\s*(\w+): \{ label: '([^']*)', sizes: (\[.*?\]), default: (\[\d+, \d+\]),", line
        )
        if not match:
            continue
        kind, label, sizes, default = match.groups()
        rows[kind] = {
            "label": label,
            "sizes": tuple(tuple(size) for size in ast.literal_eval(sizes)),
            "default": tuple(ast.literal_eval(default)),
        }
    return rows


def keys_on(page):
    """A tile is named by what it shows, so two Work slices read apart."""
    return [home_layout.widget_key(item["kind"], item.get("settings")) for item in page["widgets"]]


def by_key(page):
    return {home_layout.widget_key(item["kind"], item.get("settings")): item for item in page["widgets"]}


class HomeLayoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.env = mock.patch.dict(os.environ, {"KOSISTENZ_DATA_DIR": str(self.root)})
        self.env.start()

    def tearDown(self) -> None:
        self.env.stop()
        self.tmp.cleanup()

    def test_browser_catalog_matches_the_python_one(self) -> None:
        client = _client_catalog()
        self.assertEqual(set(client), set(home_layout.WIDGET_CATALOG))
        for kind, spec in home_layout.WIDGET_CATALOG.items():
            self.assertEqual(client[kind]["label"], spec["label"], kind)
            self.assertEqual(client[kind]["sizes"], tuple(spec["sizes"]), kind)
            self.assertEqual(client[kind]["default"], tuple(spec["default"]), kind)

    def test_anything_with_a_list_starts_tall_enough_to_show_one(self) -> None:
        # Half the board wide and six rows tall. At four rows the tile spends
        # its height on a headline and buttons and the list collapses.
        for kind in ("work", "goals", "habits"):
            self.assertEqual(home_layout.spec_default(kind), (4, 6), kind)

    def test_catalog_lists_folded_tabs_not_settings_or_calendar(self) -> None:
        kinds = {row["kind"] for row in home_layout.catalog()}
        self.assertIn("work", kinds)
        self.assertIn("today_calendar", kinds)
        self.assertIn("workout", kinds)
        self.assertNotIn("journal", kinds)
        self.assertIn("goals", kinds)
        self.assertIn("analytics", kinds)
        self.assertIn("weather", kinds)
        self.assertIn("countdown", kinds)
        self.assertIn("habits", kinds)
        self.assertIn("day_brief", kinds)
        self.assertIn("counters", kinds)
        self.assertIn("reading", kinds)
        self.assertIn("word", kinds)
        self.assertIn("cluny", kinds)
        self.assertNotIn("checklist", kinds)
        self.assertNotIn("settings", kinds)
        self.assertNotIn("calendar", kinds)
        # Retired tiles. Each of these still has a tab; none of them said
        # enough in a tile to earn a place on the board.
        for gone in ("now_next", "free_today", "heatmap", "focus", "timeline"):
            self.assertNotIn(gone, kinds)
        # To Do, All Work, Unplaced and Due are one Work tile with a setting.
        for folded in ("todo", "allwork", "unplaced", "dues"):
            self.assertNotIn(folded, kinds)
        work = next(row for row in home_layout.catalog() if row["kind"] == "work")
        self.assertEqual(
            [option["value"] for option in work["settings"]["slice"]["options"]],
            ["today", "backlog", "unplaced", "due"],
        )

    def test_default_home_is_a_bento_of_day_slices(self) -> None:
        layout = home_layout.default_layout()
        self.assertEqual(len(layout["pages"]), 2)
        self.assertEqual(layout["pages"][0]["name"], "Home")
        self.assertEqual(layout["pages"][1]["name"], "Week")
        kinds = keys_on(layout["pages"][0])
        # Today already carries now and next, so there is no second clock tile.
        self.assertEqual(
            kinds,
            [
                "work:slice=today",
                "today_calendar",
                "cluny",
                "weather",
                "word",
                "work:slice=unplaced",
                "day_brief",
            ],
        )
        todo = layout["pages"][0]["widgets"][0]
        today = layout["pages"][0]["widgets"][1]
        cluny = layout["pages"][0]["widgets"][2]
        weather = layout["pages"][0]["widgets"][3]
        word = layout["pages"][0]["widgets"][4]
        unplaced = layout["pages"][0]["widgets"][5]
        day = layout["pages"][0]["widgets"][6]
        self.assertEqual((todo["x"], todo["y"], todo["w"], todo["h"]), (0, 0, 4, 6))
        self.assertEqual(todo.get("region"), "above")
        self.assertEqual((today["x"], today["y"], today["w"], today["h"]), (4, 0, 4, 6))
        self.assertEqual(today.get("region"), "above")
        self.assertEqual((cluny["x"], cluny["y"], cluny["w"], cluny["h"]), (0, 0, 8, 4))
        self.assertNotEqual(cluny.get("region"), "above")
        self.assertEqual((weather["x"], weather["y"], weather["w"], weather["h"]), (0, 4, 4, 2))
        self.assertEqual((word["x"], word["y"], word["w"], word["h"]), (4, 4, 4, 2))
        self.assertEqual((unplaced["x"], unplaced["y"], unplaced["w"], unplaced["h"]), (0, 6, 4, 6))
        self.assertEqual((day["x"], day["y"], day["w"], day["h"]), (4, 6, 4, 6))
        self.assertFalse(home_layout.boxes_overlap(todo, today))
        self.assertFalse(home_layout.boxes_overlap(cluny, weather))
        self.assertFalse(home_layout.boxes_overlap(weather, word))
        self.assertFalse(home_layout.boxes_overlap(unplaced, day))
        week_kinds = keys_on(layout["pages"][1])
        self.assertEqual(
            week_kinds,
            [
                "goals",
                "work:slice=backlog",
                "habits",
                "work:slice=due",
                "workout",
                "reading",
            ],
        )

    def test_fresh_file_writes_the_default(self) -> None:
        layout = home_layout.get_home_layout()
        self.assertTrue((self.root / "home_layout.json").exists())
        self.assertEqual(
            keys_on(layout["pages"][0]),
            [
                "work:slice=today",
                "today_calendar",
                "cluny",
                "weather",
                "word",
                "work:slice=unplaced",
                "day_brief",
            ],
        )

    def test_each_kind_has_a_few_allowed_sizes(self) -> None:
        for kind, spec in home_layout.WIDGET_CATALOG.items():
            sizes = spec["sizes"]
            self.assertGreaterEqual(len(sizes), 4, kind)
            self.assertLessEqual(len(sizes), 8, kind)
            self.assertIn(spec["default"], sizes)
            self.assertEqual(home_layout.coerce_size(kind, 99, 99), spec["default"])

    def test_glance_widgets_can_shrink_to_a_single_chip(self) -> None:
        # A chip is a quarter of the board wide and one old row tall, which on
        # the eight column grid is two cells each way.
        for kind in ("weather", "word", "countdown"):
            self.assertIn((2, 2), home_layout.allowed_sizes(kind), kind)
        self.assertEqual(home_layout.spec_default("weather"), (4, 2))
        self.assertEqual(home_layout.spec_default("word"), (4, 2))
        self.assertEqual(home_layout.spec_default("cluny"), (8, 4))
        self.assertIn((4, 4), home_layout.allowed_sizes("analytics"))
        self.assertEqual(home_layout.coerce_size("analytics", 4, 4), (4, 4))

    def test_first_fit_skips_occupied_cells(self) -> None:
        occupied = [{"id": "a", "x": 0, "y": 0, "w": 4, "h": 4}]
        # Room to the right of it, so the next tile goes there.
        self.assertEqual(home_layout.first_fit(occupied, 4, 4), (4, 0))
        # Too wide to sit beside it, so the next row down.
        self.assertEqual(home_layout.first_fit(occupied, 8, 4), (0, 4))

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
        kinds = keys_on(packed["pages"][0])
        self.assertEqual(kinds, ["work:slice=today"])

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
        self.assertEqual(len(layout["pages"]), 3)
        self.assertEqual(layout["pages"][2]["name"], "Lift")
        self.assertEqual(layout["pages"][2]["widgets"], [])
        self.assertEqual(layout["active_page_id"], layout["pages"][2]["id"])
        lift_id = layout["pages"][2]["id"]
        layout = home_layout.rename_home_page(lift_id, "  Strength week  ")
        self.assertEqual(layout["pages"][2]["name"], "Strength week")
        layout = home_layout.delete_home_page(lift_id)
        self.assertEqual(len(layout["pages"]), 2)
        self.assertEqual(layout["active_page_id"], home_id)

    def test_cannot_delete_the_last_page(self) -> None:
        layout = home_layout.get_home_layout()
        layout = home_layout.delete_page(layout, layout["pages"][1]["id"])
        with self.assertRaises(ValueError):
            home_layout.delete_page(layout, layout["pages"][0]["id"])

    def test_add_widget_first_fit_and_unique_per_page(self) -> None:
        layout = home_layout.get_home_layout()
        page_id = layout["pages"][0]["id"]
        layout = home_layout.add_home_widget(page_id, "workout")
        kinds = keys_on(layout["pages"][0])
        self.assertIn("workout", kinds)
        with self.assertRaises(ValueError):
            home_layout.add_widget(layout, page_id, "workout")
        with self.assertRaises(ValueError):
            home_layout.add_widget(layout, page_id, "calendar")
        layout = home_layout.add_home_widget(page_id, "countdown")
        self.assertIn("countdown", keys_on(layout["pages"][0]))

    def test_two_work_slices_share_a_page_but_one_slice_cannot_repeat(self) -> None:
        """A tile is the same tile only when it shows the same thing, so Work
        can sit on a page twice as long as the two slices differ."""
        layout = home_layout.get_home_layout()
        page_id = layout["pages"][0]["id"]
        layout = home_layout.add_home_widget(page_id, "work", "below", {"slice": "backlog"})
        keys = keys_on(layout["pages"][0])
        self.assertIn("work:slice=today", keys)
        self.assertIn("work:slice=backlog", keys)
        with self.assertRaises(ValueError):
            home_layout.add_widget(layout, page_id, "work", "below", {"slice": "backlog"})

    def test_a_slice_nobody_offers_falls_back_to_the_default(self) -> None:
        layout = home_layout.get_home_layout()
        page_id = layout["pages"][1]["id"]
        layout = home_layout.add_home_widget(page_id, "work", "below", {"slice": "yesterday"})
        self.assertIn("work:slice=today", keys_on(layout["pages"][1]))

    def test_a_board_from_before_the_fold_comes_back_as_work_slices(self) -> None:
        """To Do, All Work, Unplaced and Due were four widgets. A board saved
        while they still were reads back as four slices of one."""
        raw = {
            "version": home_layout.LAYOUT_VERSION,
            "pages": [
                {
                    "id": "p1",
                    "name": "Home",
                    "widgets": [
                        {"id": "a", "kind": "todo", "x": 0, "y": 0, "w": 4, "h": 6},
                        {"id": "b", "kind": "allwork", "x": 4, "y": 0, "w": 4, "h": 6},
                        {"id": "c", "kind": "unplaced", "x": 0, "y": 6, "w": 4, "h": 6},
                        {"id": "d", "kind": "dues", "x": 4, "y": 6, "w": 4, "h": 6},
                    ],
                }
            ],
        }
        packed = home_layout.sanitize_layout(raw)
        self.assertEqual(
            keys_on(packed["pages"][0]),
            [
                "work:slice=today",
                "work:slice=backlog",
                "work:slice=unplaced",
                "work:slice=due",
            ],
        )

    def test_a_work_slice_opens_the_list_it_was_cut_from(self) -> None:
        self.assertEqual(home_layout.widget_source("work", {"slice": "today"}), "todoTab")
        self.assertEqual(home_layout.widget_source("work", {"slice": "backlog"}), "allWorkTab")
        self.assertEqual(home_layout.widget_source("work", {"slice": "unplaced"}), "allWorkTab")
        self.assertEqual(home_layout.widget_source("work", {"slice": "due"}), "todoTab")
        self.assertEqual(home_layout.widget_source("weather"), "weatherSource")

    def test_move_rejects_overlap_resize_cycles(self) -> None:
        layout = home_layout.get_home_layout()
        page_id = layout["pages"][0]["id"]
        todo = by_key(layout["pages"][0])["work:slice=today"]
        with self.assertRaises(ValueError):
            home_layout.move_widget(layout, page_id, todo["id"], 2, 0)
        layout = home_layout.resize_home_widget(page_id, todo["id"])
        todo = by_key(layout["pages"][0])["work:slice=today"]
        self.assertIn((todo["w"], todo["h"]), home_layout.allowed_sizes("work"))
        self.assertNotEqual((todo["w"], todo["h"]), (2, 2))

    def test_resize_snaps_to_nearest_allowed_size(self) -> None:
        self.assertEqual(home_layout.nearest_size("work", 4, 4), (4, 4))
        self.assertEqual(home_layout.nearest_size("work", 8, 6), (6, 6))
        self.assertEqual(home_layout.nearest_size("analytics", 10, 10), (6, 6))
        self.assertEqual(home_layout.nearest_size("weather", 2, 2), (2, 2))
        layout = home_layout.get_home_layout()
        page_id = layout["pages"][0]["id"]
        todo = by_key(layout["pages"][0])["work:slice=today"]
        with self.assertRaises(ValueError):
            home_layout.resize_widget(layout, page_id, todo["id"], 8, 4)
        today = by_key(layout["pages"][0])["today_calendar"]
        layout = home_layout.remove_home_widget(page_id, today["id"])
        weather = by_key(layout["pages"][0])["weather"]
        layout = home_layout.remove_home_widget(page_id, weather["id"])
        word = by_key(layout["pages"][0])["word"]
        layout = home_layout.remove_home_widget(page_id, word["id"])
        todo = by_key(layout["pages"][0])["work:slice=today"]
        layout = home_layout.resize_home_widget(page_id, todo["id"], 8, 6)
        todo = by_key(layout["pages"][0])["work:slice=today"]
        self.assertEqual((todo["w"], todo["h"], todo["x"], todo["y"]), (6, 6, 0, 0))

    def test_remove_widget(self) -> None:
        layout = home_layout.get_home_layout()
        page_id = layout["pages"][0]["id"]
        today = by_key(layout["pages"][0])["today_calendar"]
        layout = home_layout.remove_home_widget(page_id, today["id"])
        kinds = keys_on(layout["pages"][0])
        self.assertEqual(
            kinds,
            [
                "work:slice=today",
                "cluny",
                "weather",
                "word",
                "work:slice=unplaced",
                "day_brief",
            ],
        )

    def test_today_can_move_down_without_hitting_todo(self) -> None:
        layout = home_layout.get_home_layout()
        page_id = layout["pages"][0]["id"]
        today = by_key(layout["pages"][0])["today_calendar"]
        moved = home_layout.move_home_widget(page_id, today["id"], 4, 6)
        row = next(item for item in moved["pages"][0]["widgets"] if item["id"] == today["id"])
        self.assertEqual((row["x"], row["y"]), (4, 6))
        todo = by_key(moved["pages"][0])["work:slice=today"]
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
        extra_id = extra["pages"][-1]["id"]
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
        layout = home_layout.add_home_widget(page_id, "countdown")
        layout = home_layout.add_home_widget(page_id, "habits")
        layout = home_layout.add_home_widget(page_id, "analytics")
        layout = home_layout.add_home_widget(page_id, "counters")
        layout = home_layout.add_home_widget(page_id, "reading")
        kinds = keys_on(layout["pages"][0])
        self.assertIn("weather", kinds)
        self.assertIn("countdown", kinds)
        self.assertIn("habits", kinds)
        self.assertIn("analytics", kinds)
        self.assertIn("day_brief", kinds)
        self.assertIn("counters", kinds)
        self.assertIn("reading", kinds)
        self.assertIn("word", kinds)
        self.assertIn("cluny", kinds)
        self.assertNotIn("checklist", kinds)
        self.assertEqual(home_layout.coerce_size("countdown", 8, 4), (4, 2))
        self.assertEqual(home_layout.coerce_size("analytics", 4, 4), (4, 4))
        self.assertEqual(home_layout.coerce_size("analytics", 6, 6), (6, 6))
        self.assertEqual(home_layout.coerce_size("day_brief", 4, 6), (4, 6))

    def test_reset_restores_first_install(self) -> None:
        layout = home_layout.get_home_layout()
        home_layout.add_home_page("Extra")
        layout = home_layout.reset_home_layout()
        self.assertEqual(len(layout["pages"]), 2)
        self.assertEqual(
            keys_on(layout["pages"][0]),
            [
                "work:slice=today",
                "today_calendar",
                "cluny",
                "weather",
                "word",
                "work:slice=unplaced",
                "day_brief",
            ],
        )
        self.assertEqual(layout["pages"][1]["name"], "Week")

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
        kinds = keys_on(packed["pages"][0])
        self.assertEqual(kinds, ["work:slice=today"])

    def test_first_page_keeps_above_and_below_regions(self) -> None:
        layout = home_layout.get_home_layout()
        page_id = layout["pages"][0]["id"]
        weather = by_key(layout["pages"][0])["weather"]
        layout = home_layout.move_home_widget(page_id, weather["id"], 0, 6, "above")
        weather = by_key(layout["pages"][0])["weather"]
        self.assertEqual(weather.get("region"), "above")
        self.assertEqual((weather["x"], weather["y"]), (0, 6))
        extra = home_layout.add_home_page("Studio")
        extra_id = extra["pages"][-1]["id"]
        extra = home_layout.add_home_widget(extra_id, "countdown", "above")
        focus = extra["pages"][-1]["widgets"][0]
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
        kinds = keys_on(packed["pages"][0])
        self.assertIn("cluny", kinds)
        again, added_again = home_layout.seed_ask_cluny(packed)
        self.assertFalse(added_again)
        self.assertEqual(len(again["pages"][0]["widgets"]), len(packed["pages"][0]["widgets"]))

    def test_stock_home_restacks_to_the_roomier_template(self) -> None:
        raw = {
            "pages": [
                {
                    "id": "p1",
                    "name": "Home",
                    "widgets": [
                        {"id": "a", "kind": "todo", "x": 0, "y": 0, "w": 2, "h": 2, "region": "above"},
                        {"id": "b", "kind": "today_calendar", "x": 2, "y": 0, "w": 2, "h": 2, "region": "above"},
                        {"id": "c", "kind": "weather", "x": 0, "y": 0, "w": 2, "h": 1},
                        {"id": "d", "kind": "word", "x": 2, "y": 0, "w": 2, "h": 2},
                        {"id": "e", "kind": "day_brief", "x": 0, "y": 2, "w": 2, "h": 1},
                        {"id": "f", "kind": "cluny", "x": 0, "y": 1, "w": 2, "h": 2},
                    ],
                }
            ]
        }
        packed, changed = home_layout.restack_stock_home(raw)
        self.assertTrue(changed)
        tiles = by_key(packed["pages"][0])
        self.assertEqual((tiles["work:slice=today"]["w"], tiles["work:slice=today"]["h"]), (4, 6))
        self.assertEqual((tiles["today_calendar"]["w"], tiles["today_calendar"]["h"]), (4, 6))
        self.assertEqual((tiles["word"]["w"], tiles["word"]["h"]), (4, 2))
        self.assertEqual((tiles["day_brief"]["w"], tiles["day_brief"]["h"]), (4, 6))
        self.assertEqual((tiles["cluny"]["w"], tiles["cluny"]["h"]), (8, 4))
        again, changed_again = home_layout.restack_stock_home(packed)
        self.assertFalse(changed_again)

    def test_old_layout_version_resets_the_board(self) -> None:
        path = self.root / "home_layout.json"
        path.write_text(
            '{"version": 1, "pages": [{"id": "p1", "name": "Home", "widgets": []}]}',
            encoding="utf-8",
        )
        layout = home_layout.get_home_layout()
        self.assertEqual(layout["version"], home_layout.LAYOUT_VERSION)
        kinds = keys_on(layout["pages"][0])
        self.assertEqual(
            kinds,
            [
                "work:slice=today",
                "today_calendar",
                "cluny",
                "weather",
                "word",
                "work:slice=unplaced",
                "day_brief",
            ],
        )
        word = by_key(layout["pages"][0])["word"]
        self.assertEqual((word["w"], word["h"]), (4, 2))
        todo = by_key(layout["pages"][0])["work:slice=today"]
        self.assertEqual((todo["w"], todo["h"]), (4, 6))
        self.assertEqual(len(layout["pages"]), 2)

    def test_an_up_to_date_board_is_read_rather_than_migrated_again(self) -> None:
        """Catching a board up used to happen on every load, which meant eight
        passes over it each time the Home tab opened. It happens once now, on
        the load that finds an old file."""
        home_layout.get_home_layout()
        path = self.root / "home_layout.json"
        before = path.read_bytes()
        writes = []
        real = home_layout._write
        home_layout._write = lambda layout: writes.append(layout) or real(layout)
        try:
            home_layout.get_home_layout()
        finally:
            home_layout._write = real
        self.assertEqual(writes, [])
        self.assertEqual(path.read_bytes(), before)

    def test_a_board_saved_before_the_week_page_shipped_still_gains_it(self) -> None:
        """The catch-up steps moved behind the version gate, so they have to
        still fire for someone whose board predates them."""
        path = self.root / "home_layout.json"
        page = {
            "id": "p1",
            "name": "Home",
            "widgets": [
                {"id": "a", "kind": "todo", "x": 0, "y": 0, "w": 4, "h": 6, "region": "above"},
                {"id": "b", "kind": "today_calendar", "x": 4, "y": 0, "w": 4, "h": 6, "region": "above"},
                {"id": "c", "kind": "cluny", "x": 0, "y": 0, "w": 8, "h": 4},
                {"id": "d", "kind": "weather", "x": 0, "y": 4, "w": 4, "h": 2},
                {"id": "e", "kind": "word", "x": 4, "y": 4, "w": 4, "h": 2},
            ],
        }
        path.write_text(json.dumps({"version": 3, "columns": 8, "pages": [page]}), encoding="utf-8")
        layout = home_layout.get_home_layout()
        self.assertEqual(layout["version"], home_layout.LAYOUT_VERSION)
        self.assertEqual([item["name"] for item in layout["pages"]], ["Home", "Week"])
        kinds = set(keys_on(layout["pages"][0]))
        self.assertIn("day_brief", kinds)
        self.assertIn("work:slice=unplaced", kinds)

    def test_a_four_column_board_is_widened_rather_than_thrown_away(self) -> None:
        """Someone who arranged their board by hand keeps that arrangement.
        Each cell split in two, so doubling every box lands on the same
        pixels; the sizes in between are what the finer grid buys."""
        path = self.root / "home_layout.json"
        path.write_text(
            json.dumps(
                {
                    "version": 2,
                    "columns": 4,
                    "active_page_id": "p1",
                    "pages": [
                        {
                            "id": "p1",
                            "name": "Home",
                            "widgets": [
                                {"id": "a", "kind": "todo", "x": 0, "y": 0, "w": 2, "h": 3},
                                {"id": "b", "kind": "weather", "x": 2, "y": 1, "w": 1, "h": 1},
                            ],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        layout = home_layout.get_home_layout()
        self.assertEqual(layout["version"], home_layout.LAYOUT_VERSION)
        self.assertEqual(layout["columns"], 8)
        tiles = by_key(layout["pages"][0])
        work = tiles["work:slice=today"]
        self.assertEqual((work["x"], work["y"], work["w"], work["h"]), (0, 0, 4, 6))
        weather = tiles["weather"]
        self.assertEqual(
            (weather["x"], weather["y"], weather["w"], weather["h"]), (4, 2, 2, 2)
        )
        # The page was kept, not replaced with the first-install board.
        self.assertEqual(len(layout["pages"]), 1)

    def test_stock_one_page_home_gains_the_week_board(self) -> None:
        raw = {
            "version": 2,
            "pages": [
                {
                    "id": "p1",
                    "name": "Home",
                    "widgets": [
                        {"id": "a", "kind": "todo", "x": 0, "y": 0, "w": 2, "h": 2, "region": "above"},
                        {"id": "b", "kind": "today_calendar", "x": 2, "y": 0, "w": 2, "h": 2, "region": "above"},
                        {"id": "c", "kind": "weather", "x": 0, "y": 0, "w": 2, "h": 1},
                        {"id": "d", "kind": "word", "x": 2, "y": 0, "w": 2, "h": 1},
                        {"id": "e", "kind": "cluny", "x": 0, "y": 1, "w": 4, "h": 2},
                    ],
                }
            ],
        }
        packed, added = home_layout.seed_week_page(raw)
        self.assertTrue(added)
        self.assertEqual(packed["pages"][1]["name"], "Week")
        self.assertEqual(
            keys_on(packed["pages"][1]),
            [
                "goals",
                "work:slice=backlog",
                "habits",
                "work:slice=due",
                "workout",
                "reading",
            ],
        )
        again, added_again = home_layout.seed_week_page(packed)
        self.assertFalse(added_again)

    def test_stock_home_gains_the_day_tile(self) -> None:
        raw = {
            "pages": [
                {
                    "id": "p1",
                    "name": "Home",
                    "widgets": [
                        {"id": "a", "kind": "todo", "x": 0, "y": 0, "w": 2, "h": 2, "region": "above"},
                        {"id": "b", "kind": "today_calendar", "x": 2, "y": 0, "w": 2, "h": 2, "region": "above"},
                        {"id": "c", "kind": "weather", "x": 0, "y": 0, "w": 2, "h": 1},
                        {"id": "d", "kind": "word", "x": 2, "y": 0, "w": 2, "h": 1},
                        {"id": "e", "kind": "cluny", "x": 0, "y": 1, "w": 4, "h": 2},
                    ],
                }
            ]
        }
        packed, added = home_layout.seed_day_brief(raw)
        self.assertTrue(added)
        kinds = keys_on(packed["pages"][0])
        self.assertIn("day_brief", kinds)
        again, added_again = home_layout.seed_day_brief(packed)
        self.assertFalse(added_again)

    def test_old_week_page_gains_plan_tiles(self) -> None:
        raw = {
            "pages": [
                {
                    "id": "p1",
                    "name": "Home",
                    "widgets": [
                        {"id": "a", "kind": "todo", "x": 0, "y": 0, "w": 2, "h": 2, "region": "above"},
                    ],
                },
                home_layout.default_week_page(),
            ]
        }
        # Strip the new tiles so we look like a pre-plan Week board.
        raw["pages"][1]["widgets"] = [
            item
            for item in raw["pages"][1]["widgets"]
            if home_layout.widget_key(item["kind"], item.get("settings")) in home_layout.WEEK_STOCK_KINDS
        ]
        packed, added = home_layout.seed_week_plan_tiles(raw)
        self.assertTrue(added)
        kinds = keys_on(packed["pages"][1])
        self.assertNotIn("work:slice=unplaced", kinds)
        self.assertIn("work:slice=due", kinds)
        again, added_again = home_layout.seed_week_plan_tiles(packed)
        self.assertFalse(added_again)

    def test_stock_home_gains_unplaced(self) -> None:
        raw = {
            "pages": [
                {
                    "id": "p1",
                    "name": "Home",
                    "widgets": [
                        {"id": "a", "kind": "todo", "x": 0, "y": 0, "w": 2, "h": 2, "region": "above"},
                        {"id": "b", "kind": "today_calendar", "x": 2, "y": 0, "w": 2, "h": 2, "region": "above"},
                        {"id": "c", "kind": "weather", "x": 0, "y": 0, "w": 2, "h": 1},
                        {"id": "d", "kind": "word", "x": 2, "y": 0, "w": 2, "h": 1},
                        {"id": "e", "kind": "day_brief", "x": 0, "y": 1, "w": 2, "h": 2},
                        {"id": "f", "kind": "cluny", "x": 2, "y": 1, "w": 2, "h": 2},
                    ],
                }
            ]
        }
        packed, added = home_layout.seed_home_plan_tiles(raw)
        self.assertTrue(added)
        kinds = set(keys_on(packed["pages"][0]))
        self.assertIn("work:slice=unplaced", kinds)
        restacked, changed = home_layout.restack_stock_home(packed)
        self.assertTrue(changed)
        tiles = by_key(restacked["pages"][0])
        self.assertEqual((tiles["work:slice=unplaced"]["x"], tiles["work:slice=unplaced"]["y"]), (0, 6))
        self.assertEqual((tiles["work:slice=unplaced"]["w"], tiles["work:slice=unplaced"]["h"]), (4, 6))
        again, added_again = home_layout.seed_home_plan_tiles(restacked)
        self.assertFalse(added_again)

    def test_a_board_carrying_a_retired_tile_loses_it_and_keeps_the_rest(self) -> None:
        """Five tiles left the catalog. A board holding one comes back without
        it rather than refusing to load."""
        raw = {
            "version": home_layout.LAYOUT_VERSION,
            "pages": [
                {
                    "id": "p1",
                    "name": "Home",
                    "widgets": [
                        {"id": "a", "kind": "now_next", "x": 0, "y": 0, "w": 4, "h": 2},
                        {"id": "b", "kind": "heatmap", "x": 4, "y": 0, "w": 4, "h": 2},
                        {"id": "c", "kind": "focus", "x": 0, "y": 2, "w": 4, "h": 2},
                        {"id": "d", "kind": "timeline", "x": 4, "y": 2, "w": 4, "h": 4},
                        {"id": "e", "kind": "free_today", "x": 0, "y": 6, "w": 4, "h": 2},
                        {"id": "f", "kind": "habits", "x": 4, "y": 6, "w": 4, "h": 6},
                    ],
                }
            ],
        }
        packed = home_layout.sanitize_layout(raw)
        kinds = keys_on(packed["pages"][0])
        self.assertEqual(kinds, ["habits"])
