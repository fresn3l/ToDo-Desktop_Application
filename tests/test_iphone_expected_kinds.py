"""Expected workout kinds — lockstep with ios/Kosistenz/WorkoutPlan.swift."""

from __future__ import annotations

import unittest
from datetime import date

import workouts


class IphoneExpectedKindsTests(unittest.TestCase):
    def test_default_monday_is_push(self) -> None:
        monday = date(2026, 8, 24)
        kinds = workouts.expected_kinds_for_date(monday, workouts.DEFAULT_WEEK_TEMPLATE)
        self.assertIn("push", kinds)

    def test_default_wednesday_is_pull(self) -> None:
        kinds = workouts.expected_kinds_for_date(date(2026, 8, 26), workouts.DEFAULT_WEEK_TEMPLATE)
        self.assertIn("pull", kinds)

    def test_default_friday_is_legs(self) -> None:
        kinds = workouts.expected_kinds_for_date(date(2026, 8, 28), workouts.DEFAULT_WEEK_TEMPLATE)
        self.assertIn("legs", kinds)

    def test_swift_comment_points_at_this_module(self) -> None:
        text = (
            __import__("pathlib")
            .Path(__file__)
            .resolve()
            .parents[1]
            .joinpath("ios", "Kosistenz", "WorkoutPlan.swift")
            .read_text(encoding="utf-8")
        )
        self.assertIn("tests/test_iphone_expected_kinds.py", text)
        self.assertIn("2026-08-24", text)


if __name__ == "__main__":
    unittest.main()
