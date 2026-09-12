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


class OneSystemPerIdeaTests(unittest.TestCase):
    """Spacing and radius each get one set of names, the way type now does."""

    def test_there_is_no_second_spacing_or_radius_ladder(self) -> None:
        both = STYLE + TOKENS
        for dead in ("--s-1", "--s-2", "--s-3", "--s-4", "--s-5", "--r-sm", "--r-md"):
            self.assertNotIn(f"{dead}:", both, f"{dead} duplicates the real ladder")
            self.assertNotIn(f"var({dead})", both, f"{dead} still has readers")

    def test_density_reaches_every_rung_of_the_spacing_ladder(self) -> None:
        """A rung the compact block never remaps stays put while its
        neighbours tighten, which is what left compact half applied."""
        compact = STYLE.split("html[data-density='compact'] {")[1].split("}")[0]
        rungs = set(re.findall(r"(--space-[a-z0-9]+):", STYLE))
        missing = sorted(r for r in rungs if f"{r}:" not in compact)
        self.assertEqual(missing, [], f"compact density skips {missing}")

    def test_no_token_is_declared_and_never_read(self) -> None:
        """A token nothing reads is a promise the stylesheet does not keep.
        --lift-hover was declared for hover states that were never built, and
        the widget border controls wrote two of these from the settings pane
        while the board went on drawing its own border.
        """
        readers = STYLE + TOKENS
        for path in (ROOT / "web").rglob("*"):
            if path.suffix in (".js", ".html"):
                readers += path.read_text(encoding="utf-8")
        declared = set(re.findall(r"^\s*(--[a-z0-9-]+):", STYLE + TOKENS, re.M))
        dead = sorted(t for t in declared if f"var({t}" not in readers)
        self.assertEqual(dead, [], f"declared but never read: {dead}")


class InteractionStateTests(unittest.TestCase):
    def test_a_tile_answers_the_pointer(self) -> None:
        """The hover rule used to set the border and shadow back to the values
        they already had, so the whole board was inert under the pointer."""
        hover = STYLE.split(".home-shell:not(.is-editing) .home-widget:hover {")[1].split("}")[0]
        self.assertIn("var(--tint-hover)", hover)
        self.assertIn("var(--lift-hover)", hover)
        self.assertNotIn("box-shadow: none", hover)

    def test_reduced_motion_takes_the_lift_away_once(self) -> None:
        block = STYLE.split("html[data-motion='reduce'] {")[1].split("}")[0]
        self.assertIn("--lift-hover: none", block)

    def test_buttons_move_under_a_press(self) -> None:
        self.assertIn(".btn-primary:active:not(:disabled)", STYLE)
        buttons = STYLE.split(".btn-primary:active:not(:disabled),")[1].split("}")[0]
        self.assertIn("transform: translateY(1px)", buttons)


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
