"""URL paste sanitizing: Safari copies HTML/href, Canvas copies webcal."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PASTE_JS = (ROOT / "web" / "js" / "paste_insert.js").read_text(encoding="utf-8")
CAL_JS = (ROOT / "web" / "js" / "calendar.js").read_text(encoding="utf-8")

URL_RE = re.compile(r"(?:https?|webcal)://[^\s<>\"']+", re.I)
HREF_RE = re.compile(r"href=[\"']((?:https?|webcal)://[^\"']+)", re.I)


def sanitize_pasted_url(raw: str) -> str:
    s = (raw or "").replace("\ufeff", "").strip()
    if not s:
        return ""
    for line in s.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            s = line
            break
    s = s.strip("<>").strip().strip("\"'")
    href = HREF_RE.search(s)
    if href:
        s = href.group(1)
    match = URL_RE.search(s)
    if match:
        s = match.group(0)
    if s.lower().startswith("webcal://"):
        s = "https://" + s[len("webcal://") :]
    return s


def looks_like_calendar_url(text: str) -> bool:
    u = (text or "").lower()
    if not re.match(r"^(https?|webcal)://", u):
        return False
    return (
        u.startswith("webcal://")
        or bool(re.search(r"\.ics(\?|#|$)", u))
        or "/calendar" in u
        or "feeds/calendars" in u
        or "webcal" in u
    )


def from_local_input(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    match = re.match(r"^(\d{4}-\d{2}-\d{2})(?:[T ](\d{1,2}):?(\d{2}))?", raw)
    if not match:
        return f"{raw}:00" if len(raw) == 16 and "T" in raw else raw
    hour = (match.group(2) or "00").zfill(2)
    minute = match.group(3) or "00"
    return f"{match.group(1)}T{hour}:{minute}:00"


class PasteUrlTests(unittest.TestCase):
    def test_js_exposes_insert_and_calendar_page(self) -> None:
        self.assertIn("window.kosistenzInsertText", PASTE_JS)
        self.assertIn("isCalendarPage", PASTE_JS)
        self.assertIn("data-page", PASTE_JS)
        self.assertIn("text/html", PASTE_JS)

    def test_canvas_webcal_becomes_https(self) -> None:
        url = "webcal://canvas.example.edu/feeds/calendars/user_abc.ics"
        cleaned = sanitize_pasted_url(url)
        self.assertEqual(cleaned, "https://canvas.example.edu/feeds/calendars/user_abc.ics")
        self.assertTrue(looks_like_calendar_url(url))
        self.assertTrue(looks_like_calendar_url(cleaned))

    def test_safari_html_href_is_extracted(self) -> None:
        html = '<meta charset="utf-8"><a href="https://canvas.example.edu/feeds/calendars/user.ics">Calendar Feed</a>'
        self.assertEqual(
            sanitize_pasted_url(html),
            "https://canvas.example.edu/feeds/calendars/user.ics",
        )

    def test_angle_bracket_url(self) -> None:
        self.assertEqual(
            sanitize_pasted_url("<https://school.edu/calendar.ics>"),
            "https://school.edu/calendar.ics",
        )

    def test_lecture_times_are_24_hour_not_datetime_local(self) -> None:
        self.assertIn("pad(d.getHours())}${pad(d.getMinutes())}", CAL_JS)
        self.assertNotIn("datetime-local", (ROOT / "web" / "index.html").read_text(encoding="utf-8"))
        self.assertEqual(from_local_input("2026-09-08 0930"), "2026-09-08T09:30:00")
        self.assertEqual(from_local_input("2026-09-08T09:30"), "2026-09-08T09:30:00")
        self.assertEqual(from_local_input("2026-09-08 9:30"), "2026-09-08T09:30:00")
