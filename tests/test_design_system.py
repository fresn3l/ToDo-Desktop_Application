"""The stylesheet has to stay a system: one scale per idea, no stray values.

These are deliberately property tests rather than string pins. A pin breaks
every time the design moves and stops meaning anything; these keep holding.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STYLE = (ROOT / "web" / "style.css").read_text(encoding="utf-8")
TOKENS = (ROOT / "web" / "tokens.css").read_text(encoding="utf-8")
FONTS = ROOT / "web" / "fonts"

# The scale itself is defined here; everything after it has to reference it.
SCALE_MARK = "--fs-nano:"


def _body_after_scale(text: str) -> str:
    """Everything below the :root definitions, where literals are not allowed."""
    return text.split("--letter-wide:", 1)[1]


def _declarations(text: str, prop: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(rf"{prop}: ([^;]+);", text)]


class TypeScaleTests(unittest.TestCase):
    def test_one_type_scale_and_nothing_outside_it(self) -> None:
        body = _body_after_scale(STYLE)
        stray = []
        for value in _declarations(body, "font-size"):
            if value.startswith("var(--fs-"):
                continue
            # Responsive display type and the reader's own journal size are
            # the only sanctioned exceptions.
            if value.startswith("clamp(") or value == "var(--journal-font-size)":
                continue
            if value.endswith("em") and not value.endswith("rem"):
                continue
            stray.append(value)
        self.assertEqual(stray, [], f"font sizes outside the scale: {stray}")

    def test_the_retired_type_tokens_are_gone(self) -> None:
        both = STYLE + TOKENS
        for dead in ("--t-label", "--t-body", "--t-metric", "--t-hero", "--t-lead",
                     "--text-h1", "--text-h2", "--text-h3", "--text-caption",
                     "--tab-title", "--tab-heading", "--tab-subheading", "--tab-label",
                     "--glance-list-size"):
            self.assertNotIn(dead, both, f"{dead} should have been retired")


class FontWeightTests(unittest.TestCase):
    def test_every_weight_asked_for_has_a_face_behind_it(self) -> None:
        """The static faces could not answer 550/650/670, so those rounded to a
        neighbour and headings rendered at the same weight as bold text."""
        body = _body_after_scale(STYLE)
        stray = [v for v in _declarations(body, "font-weight") if not v.startswith("var(--fw-")]
        self.assertEqual(stray, [], f"weights outside the scale: {stray}")

    def test_inter_is_one_variable_file(self) -> None:
        self.assertTrue((FONTS / "inter-variable-latin.woff2").is_file())
        for gone in ("inter-latin-400.woff2", "inter-latin-600.woff2", "inter-latin-700.woff2"):
            self.assertFalse((FONTS / gone).is_file(), f"{gone} is superseded")
        face = STYLE.split("@font-face {", 1)[1].split("}", 1)[0]
        self.assertIn("inter-variable-latin.woff2", face)
        self.assertIn("font-weight: 100 900", face)

    def test_the_weight_scale_covers_regular_through_bold(self) -> None:
        for token, value in (("--fw-regular", "400"), ("--fw-medium", "500"),
                             ("--fw-semibold", "600"), ("--fw-bold", "700")):
            self.assertIn(f"{token}: {value}", STYLE)


class NumeralTests(unittest.TestCase):
    def test_figures_line_up_where_the_app_shows_numbers(self) -> None:
        """Proportional digits shuffle sideways as a clock or a count ticks."""
        self.assertIn("font-variant-numeric: tabular-nums", STYLE)
        block = STYLE.split("font-variant-numeric: tabular-nums")[0]
        selectors = block.rsplit("}", 1)[-1]
        for needed in (".glance-primary", ".cal-block-time"):
            self.assertIn(needed, selectors)

    def test_optical_sizing_is_on(self) -> None:
        # Inter carries an opsz axis; large type tightens on its own.
        self.assertIn("font-optical-sizing: auto", STYLE)


if __name__ == "__main__":
    unittest.main()
