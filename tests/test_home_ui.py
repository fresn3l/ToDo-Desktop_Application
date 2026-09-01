"""Home shell markup: two main tabs, widget sources, first-install catalog."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
TABS = (ROOT / "web" / "js" / "tabs.js").read_text(encoding="utf-8")
HOME_JS = (ROOT / "web" / "js" / "home_layout.js").read_text(encoding="utf-8")


class HomeUiTests(unittest.TestCase):
    def test_sidebar_is_home_and_calendar(self) -> None:
        self.assertIn('data-tab="home"', INDEX)
        self.assertIn('data-tab="calendar"', INDEX)
        self.assertIn('data-tab="settings"', INDEX)
        self.assertNotIn('data-tab="today"', INDEX)
        self.assertNotIn('data-tab="workout"', INDEX)
        self.assertNotIn('data-tab="todo"', INDEX)
        self.assertNotIn('data-tab="journal"', INDEX)

    def test_old_pages_are_widget_sources(self) -> None:
        for source_id in (
            "todoTab",
            "todayCalendarSource",
            "workoutTab",
            "journalTab",
            "goalsTab",
            "allWorkTab",
            "analyticsTab",
            "timelineTab",
        ):
            self.assertIn(f'id="{source_id}"', INDEX)
            self.assertIn("widget-source", INDEX)

    def test_edit_home_controls_exist(self) -> None:
        for needle in (
            "homeEditBtn",
            "homeGrid",
            "homePages",
            "homeAddPageBtn",
            "homeRenamePageBtn",
            "homeCatalog",
            "homeBorderWidth",
            "homeBorderColor",
        ):
            self.assertIn(f'id="{needle}"', INDEX)

    def test_appearance_color_slots_exist(self) -> None:
        self.assertIn('id="colorSlotList"', INDEX)
        self.assertIn('id="userPresetChips"', INDEX)
        self.assertIn("Saved palettes", INDEX)
        self.assertEqual(INDEX.count('id="inkAutoToggle"'), 1)
        self.assertIn('id="savePresetBtn"', INDEX)
        self.assertIn('id="newPresetBtn"', INDEX)
        self.assertIn('id="inkAutoToggle"', INDEX)
        self.assertIn('id="inkColorInput"', INDEX)
        self.assertNotIn('id="inkCustomWrap"', INDEX)
        self.assertIn('id="accentGrid"', INDEX)
        self.assertIn('data-preset-id', Path(__file__).resolve().parents[1].joinpath("web", "js", "settings.js").read_text(encoding="utf-8"))

    def test_tabs_alias_old_names_to_home(self) -> None:
        self.assertIn("canonicalTab", TABS)
        self.assertIn("today: 'homeTab'", TABS)
        self.assertIn("1: 'home'", TABS)
        self.assertIn("2: 'calendar'", TABS)

    def test_js_catalog_matches_folded_tabs(self) -> None:
        for kind in (
            "todo",
            "today_calendar",
            "workout",
            "journal",
            "goals",
            "allwork",
            "analytics",
            "timeline",
        ):
            self.assertIn(f"{kind}:", HOME_JS)
        self.assertNotIn("settings:", HOME_JS)
