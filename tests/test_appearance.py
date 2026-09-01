"""Appearance palettes, color overrides, ink, and user presets."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import appearance


class AppearancePaletteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.env = patch.dict(os.environ, {"KOSISTENZ_DATA_DIR": str(self.root)})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_every_builtin_theme_has_every_slot(self):
        self.assertEqual(set(appearance.THEME_PALETTES), appearance.ALLOWED["theme"])
        for theme, palette in appearance.THEME_PALETTES.items():
            with self.subTest(theme=theme):
                self.assertEqual(tuple(palette.keys()), appearance.COLOR_SLOTS)
                for hex_color in palette.values():
                    self.assertEqual(appearance._as_hex(hex_color, ""), hex_color)

    def test_hex_sanitize_accepts_short_and_rejects_junk(self):
        self.assertEqual(appearance._as_hex("#abc", ""), "#aabbcc")
        self.assertEqual(appearance._as_hex("4F8FCF", ""), "#4f8fcf")
        self.assertEqual(appearance._as_hex("not-a-color", "#121c26"), "#121c26")
        self.assertEqual(appearance._as_hex("#zzzzzz", "#121c26"), "#121c26")

    def test_overrides_and_border_width_sanitize(self):
        cleaned = appearance._sanitize(
            {
                "theme": "paper",
                "colorOverrides": {
                    "pageBg": "#112233",
                    "widgetBorder": "not-a-color",
                    "nope": "#ffffff",
                    "titles": "#abc",
                },
                "widgetBorderWidth": 99,
            }
        )
        self.assertEqual(cleaned["theme"], "paper")
        self.assertEqual(cleaned["colorOverrides"]["pageBg"], "#112233")
        self.assertEqual(cleaned["colorOverrides"]["titles"], "#aabbcc")
        self.assertNotIn("widgetBorder", cleaned["colorOverrides"])
        self.assertNotIn("nope", cleaned["colorOverrides"])
        self.assertEqual(cleaned["widgetBorderWidth"], 8)

    def test_resolve_uses_palette_then_override(self):
        ocean = appearance.resolve_colors({"theme": "ocean", "colorOverrides": {}})
        self.assertEqual(ocean["pageBg"], appearance.THEME_PALETTES["ocean"]["pageBg"])
        paper = appearance.resolve_colors(
            {"theme": "paper", "colorOverrides": {"pageBg": "#ffeedd"}, "accent": "sky"}
        )
        self.assertEqual(paper["pageBg"], "#ffeedd")
        self.assertEqual(paper["sidebar"], appearance.THEME_PALETTES["paper"]["sidebar"])

    def test_ink_auto_picks_from_accent_luminance(self):
        self.assertEqual(appearance.ink_for_hex("#111111"), appearance.INK_LIGHT)
        self.assertEqual(appearance.ink_for_hex("#f4e8c8"), appearance.INK_DARK)
        auto = appearance.resolve_ink({"theme": "ocean", "accent": "sky", "inkAuto": True})
        self.assertEqual(auto, appearance.INK_LIGHT)
        manual = appearance.resolve_ink(
            {"theme": "ocean", "accent": "sky", "inkAuto": False, "ink": "#123456"}
        )
        self.assertEqual(manual, "#123456")

    def test_user_presets_round_trip_and_drop_unknown_ids(self):
        saved = appearance.save_appearance_settings(
            {
                "theme": "ocean",
                "activePresetId": "up-studio",
                "userPresets": [
                    {
                        "id": "up-studio",
                        "name": "Studio",
                        "baseTheme": "ocean",
                        "colors": {"pageBg": "#102030", "accent": "#c45c6a"},
                        "widgetBorderWidth": 3,
                        "inkAuto": False,
                        "ink": "#ffffff",
                    },
                    {"id": "no", "name": "x"},
                    {"id": "up-studio", "name": "dup"},
                ],
            }
        )
        self.assertEqual(saved["activePresetId"], "up-studio")
        self.assertEqual(len(saved["userPresets"]), 1)
        preset = saved["userPresets"][0]
        self.assertEqual(preset["name"], "Studio")
        self.assertEqual(preset["colors"]["pageBg"], "#102030")
        self.assertEqual(preset["colors"]["widgetBg"], appearance.THEME_PALETTES["ocean"]["widgetBg"])
        self.assertEqual(preset["widgetBorderWidth"], 3)
        self.assertFalse(preset["inkAuto"])
        dropped = appearance._sanitize({**saved, "activePresetId": "up-missing"})
        self.assertEqual(dropped["activePresetId"], "")

    def test_reset_keeps_saved_palettes(self):
        appearance.save_appearance_settings(
            {
                "theme": "dusk",
                "colorOverrides": {"pageBg": "#000000"},
                "userPresets": [
                    {
                        "id": "up-keep",
                        "name": "Keep me",
                        "baseTheme": "paper",
                        "colors": {},
                    }
                ],
            }
        )
        reset = appearance.reset_appearance_settings()
        self.assertEqual(reset["theme"], "ocean")
        self.assertEqual(reset["colorOverrides"], {})
        self.assertEqual(len(reset["userPresets"]), 1)
        self.assertEqual(reset["userPresets"][0]["id"], "up-keep")

    def test_js_palettes_and_slots_match_python(self):
        js = Path(__file__).resolve().parents[1].joinpath("web", "js", "appearance.js").read_text(encoding="utf-8")
        for slot in appearance.COLOR_SLOTS:
            self.assertIn(f"id: '{slot}'", js)
        for theme, palette in appearance.THEME_PALETTES.items():
            self.assertIn(f"{theme}:", js)
            for hex_color in palette.values():
                self.assertIn(hex_color, js)

    def test_futuresprints_notes_iphone_appearance(self):
        text = Path(__file__).resolve().parents[1].joinpath("docs", "futuresprints.md").read_text(encoding="utf-8")
        self.assertIn("iPhone appearance", text)
        self.assertIn("appearance.json", text)
