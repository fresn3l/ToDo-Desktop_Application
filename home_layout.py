"""
Home layout — pages of snap-to-grid widgets.

Stored as JSON next to other Kosistenz data. The first page is Home with
To Do and a mini Today calendar. Extra pages are optional.
"""

from __future__ import annotations

import json
import os
import uuid
from typing import Any, Dict, List, Optional, Tuple

import eel

from appearance import COLOR_SLOTS, _as_hex
from paths import data_directory

GRID_COLUMNS = 8
LAYOUT_VERSION = 4
MAX_PAGES = 12
MAX_WIDGETS_PER_PAGE = 32
MAX_PAGE_NAME = 40
MAX_SCAN_ROWS = 64

# Allowed (width, height) in cells. 2-wide tiles are glance chips; 8-wide is the full board.
# Anything that renders a list defaults six rows tall: at four rows the tile
# has to spend its height on a headline and buttons and the list collapses.
WIDGET_CATALOG: Dict[str, Dict[str, Any]] = {
    "todo": {
        "label": "To Do",
        "sizes": ((4, 2), (4, 4), (4, 6), (6, 4), (6, 6)),
        "default": (4, 6),
    },
    "today_calendar": {
        "label": "Today",
        "sizes": ((2, 2), (4, 2), (4, 4), (4, 6), (6, 4)),
        "default": (4, 4),
    },
    "workout": {
        "label": "Workout",
        "sizes": ((4, 2), (4, 4), (4, 6), (6, 4), (6, 6)),
        "default": (4, 4),
    },
    "goals": {
        "label": "Goals",
        "sizes": ((4, 2), (4, 4), (4, 6), (6, 4), (6, 6)),
        "default": (4, 6),
    },
    "allwork": {
        "label": "All Work",
        "sizes": ((4, 2), (4, 4), (4, 6), (6, 4), (6, 6)),
        "default": (4, 6),
    },
    "analytics": {
        "label": "Analytics",
        "sizes": ((4, 4), (4, 6), (6, 4), (6, 6)),
        "default": (4, 4),
    },
    "weather": {
        "label": "Weather",
        "sizes": ((2, 2), (4, 2), (2, 4), (4, 4), (4, 6), (6, 4)),
        "default": (4, 2),
    },
    "countdown": {
        "label": "Countdown",
        "sizes": ((2, 2), (4, 2), (2, 4), (4, 4), (4, 6), (6, 4)),
        "default": (4, 2),
    },
    "habits": {
        "label": "Habits",
        "sizes": ((2, 2), (4, 2), (2, 4), (4, 4), (4, 6), (6, 4)),
        "default": (4, 6),
    },
    "day_brief": {
        "label": "Day",
        "sizes": ((4, 2), (4, 4), (4, 6), (6, 4), (6, 6)),
        "default": (4, 4),
    },
    "counters": {
        "label": "Counters",
        "sizes": ((2, 2), (4, 2), (4, 4), (6, 4), (6, 6)),
        "default": (4, 2),
    },
    "reading": {
        "label": "Reading",
        "sizes": ((2, 2), (4, 2), (4, 4), (4, 6), (6, 4)),
        "default": (4, 2),
    },
    "word": {
        "label": "Word",
        "sizes": ((2, 2), (4, 2), (2, 4), (4, 4), (4, 6), (6, 4)),
        "default": (4, 2),
    },
    "cluny": {
        "label": "Ask Cluny",
        "sizes": ((4, 4), (4, 6), (6, 4), (6, 6), (8, 4)),
        "default": (8, 4),
    },
    "unplaced": {
        "label": "Unplaced",
        "sizes": ((4, 2), (4, 4), (4, 6), (6, 4), (6, 6)),
        "default": (4, 6),
    },
    "dues": {
        "label": "Due",
        "sizes": ((4, 2), (4, 4), (4, 6), (6, 4), (6, 6)),
        "default": (4, 6),
    },
}

SOURCE_TAB = {
    "todo": "todoTab",
    "today_calendar": "todayCalendarSource",
    "workout": "workoutTab",
    "goals": "goalsTab",
    "allwork": "allWorkTab",
    "analytics": "analyticsTab",
    "weather": "weatherSource",
    "countdown": "countdownSource",
    "habits": "habitsSource",
    "day_brief": "dayBriefSource",
    "counters": "countersSource",
    "reading": "readingSource",
    "word": "wordTab",
    "cluny": "clunySource",
    "unplaced": "allWorkTab",
    "dues": "todoTab",
}


def _new_id() -> str:
    return str(uuid.uuid4())


def _stock_home_widgets() -> List[Dict[str, Any]]:
    # Today already shows what is running and what is next, so the board does
    # not carry a second clock tile saying the same thing one row down.
    return [
        {"id": _new_id(), "kind": "todo", "x": 0, "y": 0, "w": 4, "h": 6, "region": "above"},
        {"id": _new_id(), "kind": "today_calendar", "x": 4, "y": 0, "w": 4, "h": 6, "region": "above"},
        {"id": _new_id(), "kind": "cluny", "x": 0, "y": 0, "w": 8, "h": 4},
        {"id": _new_id(), "kind": "weather", "x": 0, "y": 4, "w": 4, "h": 2},
        {"id": _new_id(), "kind": "word", "x": 4, "y": 4, "w": 4, "h": 2},
        {"id": _new_id(), "kind": "unplaced", "x": 0, "y": 6, "w": 4, "h": 6},
        {"id": _new_id(), "kind": "day_brief", "x": 4, "y": 6, "w": 4, "h": 6},
    ]


def default_week_page(name: str = "Week") -> Dict[str, Any]:
    """Second-page template: goals, backlog, habits, dues, workout, reading."""
    return {
        "id": _new_id(),
        "name": _clip_name(name, "Week"),
        "widgets": [
            {"id": _new_id(), "kind": "goals", "x": 0, "y": 0, "w": 4, "h": 6},
            {"id": _new_id(), "kind": "allwork", "x": 4, "y": 0, "w": 4, "h": 6},
            {"id": _new_id(), "kind": "habits", "x": 0, "y": 6, "w": 4, "h": 6},
            {"id": _new_id(), "kind": "dues", "x": 4, "y": 6, "w": 4, "h": 6},
            {"id": _new_id(), "kind": "workout", "x": 0, "y": 12, "w": 4, "h": 4},
            {"id": _new_id(), "kind": "reading", "x": 4, "y": 12, "w": 4, "h": 2},
        ],
    }


def default_layout() -> Dict[str, Any]:
    page_id = _new_id()
    return {
        "version": LAYOUT_VERSION,
        "columns": GRID_COLUMNS,
        "active_page_id": page_id,
        "pages": [
            {
                "id": page_id,
                "name": "Home",
                "widgets": _stock_home_widgets(),
            },
            default_week_page(),
        ],
    }


def catalog() -> List[Dict[str, Any]]:
    rows = []
    for kind, spec in WIDGET_CATALOG.items():
        rows.append(
            {
                "kind": kind,
                "label": spec["label"],
                "sizes": [list(size) for size in spec["sizes"]],
                "default": list(spec["default"]),
                "source": SOURCE_TAB[kind],
            }
        )
    return rows


def allowed_sizes(kind: str) -> Tuple[Tuple[int, int], ...]:
    spec = WIDGET_CATALOG.get(kind)
    if not spec:
        return ()
    return spec["sizes"]


def coerce_size(kind: str, w: Any, h: Any) -> Tuple[int, int]:
    sizes = allowed_sizes(kind)
    if not sizes:
        return (4, 4)
    try:
        want = (int(w), int(h))
    except (TypeError, ValueError):
        return spec_default(kind)
    if want in sizes:
        return want
    return spec_default(kind)


def nearest_size(kind: str, w: Any, h: Any) -> Tuple[int, int]:
    """Closest catalog size to a dragged width/height, not a cycle."""
    sizes = allowed_sizes(kind)
    if not sizes:
        return (4, 4)
    try:
        want = (int(w), int(h))
    except (TypeError, ValueError):
        return spec_default(kind)
    if want in sizes:
        return want
    return min(
        sizes,
        key=lambda size: (
            abs(size[0] - want[0]) + abs(size[1] - want[1]),
            abs(size[0] - want[0]),
            abs(size[1] - want[1]),
            size[0] * size[1],
        ),
    )


def spec_default(kind: str) -> Tuple[int, int]:
    spec = WIDGET_CATALOG.get(kind)
    if not spec:
        return (4, 4)
    return spec["default"]


def next_size(kind: str, w: int, h: int) -> Tuple[int, int]:
    sizes = allowed_sizes(kind)
    if not sizes:
        return (w, h)
    current = coerce_size(kind, w, h)
    try:
        i = sizes.index(current)
    except ValueError:
        return sizes[0]
    return sizes[(i + 1) % len(sizes)]


def boxes_overlap(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    return not (
        a["x"] + a["w"] <= b["x"]
        or b["x"] + b["w"] <= a["x"]
        or a["y"] + a["h"] <= b["y"]
        or b["y"] + b["h"] <= a["y"]
    )


def first_fit(
    occupied: List[Dict[str, Any]],
    w: int,
    h: int,
    columns: int = GRID_COLUMNS,
    ignore_id: Optional[str] = None,
) -> Optional[Tuple[int, int]]:
    others = [box for box in occupied if box.get("id") != ignore_id]
    for y in range(0, MAX_SCAN_ROWS):
        for x in range(0, columns - w + 1):
            trial = {"id": "_", "x": x, "y": y, "w": w, "h": h}
            if all(not boxes_overlap(trial, other) for other in others):
                return (x, y)
    return None


def widen_to_eight_columns(raw: Any) -> Dict[str, Any]:
    """Carry a four-column board onto the eight-column grid.

    Every cell split in two, and the row height halved with it, so doubling
    each box leaves the board looking exactly as it did. Sizes between the
    old ones are what the finer grid buys; nothing has to move to get them.
    """
    if not isinstance(raw, dict):
        return raw
    for page in raw.get("pages") or []:
        if not isinstance(page, dict):
            continue
        for item in page.get("widgets") or []:
            if not isinstance(item, dict):
                continue
            for axis in ("x", "y", "w", "h"):
                try:
                    item[axis] = int(item[axis]) * 2
                except (KeyError, TypeError, ValueError):
                    continue
    return raw


def _clip_name(raw: Any, fallback: str) -> str:
    text = str(raw or "").strip()
    if not text:
        return fallback
    return text[:MAX_PAGE_NAME]


def sanitize_colors(raw: Any) -> Dict[str, str]:
    """Keep only known color slots with valid hex values."""
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, str] = {}
    for slot in COLOR_SLOTS:
        hx = _as_hex(str(raw.get(slot) or ""), "")
        if hx:
            out[slot] = hx
    return out


def _as_int(raw: Any, default: int, lo: int, hi: int) -> int:
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, n))


def _is_first_page(layout: Dict[str, Any], page_id: str) -> bool:
    pages = layout.get("pages") or []
    return bool(pages) and pages[0].get("id") == page_id


def coerce_region(raw: Any, first_page: bool) -> str:
    if not first_page:
        return "below"
    return "above" if str(raw or "").strip() == "above" else "below"


def widget_region(widget: Dict[str, Any], first_page: bool) -> str:
    return coerce_region(widget.get("region"), first_page)


def region_widgets(
    widgets: List[Dict[str, Any]], region: str, first_page: bool, ignore_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for item in widgets:
        if ignore_id and item.get("id") == ignore_id:
            continue
        if widget_region(item, first_page) == region:
            out.append(item)
    return out


def _pack_widget(item: Dict[str, Any], region: str) -> Dict[str, Any]:
    widget = {
        "id": str(item.get("id") or "").strip() or _new_id(),
        "kind": item["kind"],
        "x": item["x"],
        "y": item["y"],
        "w": item["w"],
        "h": item["h"],
    }
    if region == "above":
        widget["region"] = "above"
    return widget


def sanitize_layout(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        return default_layout()
    pages_in = raw.get("pages")
    if not isinstance(pages_in, list) or not pages_in:
        return default_layout()
    pages: List[Dict[str, Any]] = []
    for index, page in enumerate(pages_in[:MAX_PAGES]):
        if not isinstance(page, dict):
            continue
        page_id = str(page.get("id") or "").strip() or _new_id()
        name = _clip_name(page.get("name"), f"Page {index + 1}")
        widgets: List[Dict[str, Any]] = []
        seen_kinds = set()
        incoming = page.get("widgets")
        if not isinstance(incoming, list):
            incoming = []
        first_page = index == 0
        for item in incoming[:MAX_WIDGETS_PER_PAGE]:
            if not isinstance(item, dict):
                continue
            kind = str(item.get("kind") or "").strip()
            if kind not in WIDGET_CATALOG or kind in seen_kinds:
                continue
            w, h = coerce_size(kind, item.get("w"), item.get("h"))
            x = _as_int(item.get("x"), 0, 0, GRID_COLUMNS - w)
            y = _as_int(item.get("y"), 0, 0, MAX_SCAN_ROWS - 1)
            region = coerce_region(item.get("region"), first_page)
            widget = _pack_widget(
                {"id": item.get("id"), "kind": kind, "x": x, "y": y, "w": w, "h": h},
                region,
            )
            occupied = region_widgets(widgets, region, first_page)
            if any(boxes_overlap(widget, other) for other in occupied):
                spot = first_fit(occupied, w, h)
                if spot is None:
                    continue
                widget["x"], widget["y"] = spot
            seen_kinds.add(kind)
            widgets.append(widget)
        packed_page: Dict[str, Any] = {"id": page_id, "name": name, "widgets": widgets}
        colors = sanitize_colors(page.get("colors") or page.get("colorOverrides"))
        if colors:
            packed_page["colors"] = colors
        pages.append(packed_page)
    if not pages:
        return default_layout()
    active = str(raw.get("active_page_id") or "").strip()
    if not any(page["id"] == active for page in pages):
        active = pages[0]["id"]
    return {
        "version": LAYOUT_VERSION,
        "columns": GRID_COLUMNS,
        "active_page_id": active,
        "pages": pages,
    }


STOCK_HOME_KINDS = frozenset({"todo", "today_calendar", "weather", "word"})
STOCK_HOME_WITH_CLUNY = STOCK_HOME_KINDS | {"cluny"}
STOCK_HOME_WITH_DAY = STOCK_HOME_KINDS | {"day_brief"}
STOCK_HOME_FULL = STOCK_HOME_KINDS | {"cluny", "day_brief"}
STOCK_HOME_PLANNED = STOCK_HOME_FULL | {"unplaced"}
STOCK_HOME_CORE_SLOTS = {
    "todo": {"x": 0, "y": 0, "w": 4, "h": 6, "region": "above"},
    "today_calendar": {"x": 4, "y": 0, "w": 4, "h": 6, "region": "above"},
    "cluny": {"x": 0, "y": 0, "w": 8, "h": 4, "region": "below"},
    "weather": {"x": 0, "y": 4, "w": 4, "h": 2, "region": "below"},
    "word": {"x": 4, "y": 4, "w": 4, "h": 2, "region": "below"},
    "day_brief": {"x": 0, "y": 6, "w": 4, "h": 6, "region": "below"},
}
STOCK_HOME_SLOTS = {
    "todo": {"x": 0, "y": 0, "w": 4, "h": 6, "region": "above"},
    "today_calendar": {"x": 4, "y": 0, "w": 4, "h": 6, "region": "above"},
    "cluny": {"x": 0, "y": 0, "w": 8, "h": 4, "region": "below"},
    "weather": {"x": 0, "y": 4, "w": 4, "h": 2, "region": "below"},
    "word": {"x": 4, "y": 4, "w": 4, "h": 2, "region": "below"},
    "unplaced": {"x": 0, "y": 6, "w": 4, "h": 6, "region": "below"},
    "day_brief": {"x": 4, "y": 6, "w": 4, "h": 6, "region": "below"},
}
WEEK_STOCK_KINDS = frozenset({"workout", "goals", "allwork", "habits", "reading"})
WEEK_PLAN_KINDS = ("dues",)


def seed_ask_cluny(layout: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """Put Ask Cluny on a stock first Home page that does not have it yet."""
    packed = sanitize_layout(layout)
    page = packed["pages"][0]
    kinds = {item["kind"] for item in page["widgets"]}
    if "cluny" in kinds:
        return packed, False
    if kinds not in (STOCK_HOME_KINDS, STOCK_HOME_WITH_DAY):
        return packed, False
    occupied = region_widgets(page["widgets"], "below", True)
    slot = STOCK_HOME_SLOTS["cluny"]
    w, h = coerce_size("cluny", slot["w"], slot["h"])
    trial = {"id": "_", "x": slot["x"], "y": slot["y"], "w": w, "h": h}
    if all(not boxes_overlap(trial, other) for other in occupied):
        spot = (slot["x"], slot["y"])
    else:
        spot = first_fit(occupied, w, h)
    if spot is None:
        return packed, False
    page["widgets"].append(
        {"id": _new_id(), "kind": "cluny", "x": spot[0], "y": spot[1], "w": w, "h": h}
    )
    return packed, True


def seed_week_page(layout: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """Give an uncustomized one-page Home the Week board."""
    packed = sanitize_layout(layout)
    if len(packed["pages"]) != 1:
        return packed, False
    kinds = {item["kind"] for item in packed["pages"][0]["widgets"]}
    if kinds not in (STOCK_HOME_WITH_CLUNY, STOCK_HOME_FULL, STOCK_HOME_PLANNED):
        return packed, False
    packed["pages"].append(default_week_page())
    return packed, True


def restack_stock_home(layout: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """Give the first-install Home board room to breathe if it was never customized."""
    packed = sanitize_layout(layout)
    page = packed["pages"][0]
    kinds = {item["kind"] for item in page["widgets"]}
    if kinds == STOCK_HOME_PLANNED:
        slots = STOCK_HOME_SLOTS
    elif kinds == STOCK_HOME_FULL:
        slots = STOCK_HOME_CORE_SLOTS
    else:
        return packed, False
    by_kind = {item["kind"]: item for item in page["widgets"]}
    widgets: List[Dict[str, Any]] = []
    changed = False
    for kind, slot in slots.items():
        item = by_kind.get(kind)
        if item is None:
            continue
        w, h = coerce_size(kind, slot["w"], slot["h"])
        nxt = {"id": item["id"], "kind": kind, "x": slot["x"], "y": slot["y"], "w": w, "h": h}
        if slot["region"] == "above":
            nxt["region"] = "above"
        if (
            int(item.get("x") or 0) != nxt["x"]
            or int(item.get("y") or 0) != nxt["y"]
            or int(item.get("w") or 0) != nxt["w"]
            or int(item.get("h") or 0) != nxt["h"]
            or bool(item.get("region") == "above") != bool(nxt.get("region") == "above")
        ):
            changed = True
        widgets.append(nxt)
    if not changed:
        return packed, False
    page["widgets"] = widgets
    return packed, True


def seed_day_brief(layout: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """Put Morning/Evening on a stock Home that only had To Do / Today / chips / Cluny."""
    packed = sanitize_layout(layout)
    page = packed["pages"][0]
    kinds = {item["kind"] for item in page["widgets"]}
    if "day_brief" in kinds:
        return packed, False
    if kinds not in (STOCK_HOME_KINDS, STOCK_HOME_WITH_CLUNY):
        return packed, False
    occupied = region_widgets(page["widgets"], "below", True)
    slot = STOCK_HOME_SLOTS["day_brief"]
    w, h = coerce_size("day_brief", slot["w"], slot["h"])
    trial = {"id": "_", "x": slot["x"], "y": slot["y"], "w": w, "h": h}
    if all(not boxes_overlap(trial, other) for other in occupied):
        spot = (slot["x"], slot["y"])
    else:
        spot = first_fit(occupied, w, h)
    if spot is None:
        return packed, False
    page["widgets"].append(
        {"id": _new_id(), "kind": "day_brief", "x": spot[0], "y": spot[1], "w": w, "h": h}
    )
    return packed, True


def seed_week_plan_tiles(layout: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """Add dues / free to an uncustomized Week page."""
    packed = sanitize_layout(layout)
    if len(packed["pages"]) < 2:
        return packed, False
    page = packed["pages"][1]
    kinds = [item["kind"] for item in page["widgets"]]
    if set(kinds) != WEEK_STOCK_KINDS:
        return packed, False
    occupied = list(page["widgets"])
    added = False
    for kind in WEEK_PLAN_KINDS:
        if any(item["kind"] == kind for item in occupied):
            continue
        w, h = spec_default(kind)
        spot = first_fit(occupied, w, h)
        if spot is None:
            continue
        widget = {"id": _new_id(), "kind": kind, "x": spot[0], "y": spot[1], "w": w, "h": h}
        occupied.append(widget)
        page["widgets"].append(widget)
        added = True
    return packed, added


def seed_home_plan_tiles(layout: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """Put Unplaced on a stock first Home page."""
    packed = sanitize_layout(layout)
    page = packed["pages"][0]
    kinds = {item["kind"] for item in page["widgets"]}
    if "unplaced" in kinds:
        return packed, False
    if kinds != STOCK_HOME_FULL:
        return packed, False
    occupied = region_widgets(page["widgets"], "below", True)
    slot = STOCK_HOME_SLOTS["unplaced"]
    w, h = coerce_size("unplaced", slot["w"], slot["h"])
    trial = {"id": "_", "x": slot["x"], "y": slot["y"], "w": w, "h": h}
    if all(not boxes_overlap(trial, other) for other in occupied):
        spot = (slot["x"], slot["y"])
    else:
        spot = first_fit(occupied, w, h)
    if spot is None:
        return packed, False
    page["widgets"].append(
        {"id": _new_id(), "kind": "unplaced", "x": spot[0], "y": spot[1], "w": w, "h": h}
    )
    return packed, True


def catch_up_stock_board(layout: Dict[str, Any]) -> Dict[str, Any]:
    """Hand a board nobody rearranged the tiles that shipped after it was saved.

    Each step checks the board against an exact stock arrangement and does
    nothing unless it matches, so a board someone touched comes through
    untouched.
    """
    packed = sanitize_layout(layout)
    for step in (
        seed_ask_cluny,
        seed_day_brief,
        restack_stock_home,
        seed_week_page,
        seed_week_plan_tiles,
        seed_home_plan_tiles,
        restack_stock_home,
    ):
        packed, _ = step(packed)
    return packed


def migrate(raw: Any) -> Dict[str, Any]:
    """Bring a saved board up to the current version.

    This runs once, on the load that finds an old file, and the result is
    written straight back. It used to run on every load instead, which meant
    eight passes over the board each time the Home tab opened.
    """
    stored = int((raw or {}).get("version") or 0)
    if stored < 2:
        # Before version 2 the record had a different shape, and there is no
        # honest way to read it. A clean board beats a mangled one.
        return default_layout()
    if stored < 3:
        raw = widen_to_eight_columns(raw)
    return catch_up_stock_board(raw)


def _page(layout: Dict[str, Any], page_id: str) -> Optional[Dict[str, Any]]:
    for page in layout["pages"]:
        if page["id"] == page_id:
            return page
    return None


def add_page(layout: Dict[str, Any], name: str = "") -> Dict[str, Any]:
    packed = sanitize_layout(layout)
    if len(packed["pages"]) >= MAX_PAGES:
        raise ValueError("Too many Home pages")
    page_id = _new_id()
    packed["pages"].append(
        {
            "id": page_id,
            "name": _clip_name(name, f"Page {len(packed['pages']) + 1}"),
            "widgets": [],
        }
    )
    packed["active_page_id"] = page_id
    return packed


def rename_page(layout: Dict[str, Any], page_id: str, name: str) -> Dict[str, Any]:
    packed = sanitize_layout(layout)
    page = _page(packed, page_id)
    if page is None:
        raise ValueError("Page not found")
    page["name"] = _clip_name(name, page["name"])
    return packed


def delete_page(layout: Dict[str, Any], page_id: str) -> Dict[str, Any]:
    packed = sanitize_layout(layout)
    if len(packed["pages"]) <= 1:
        raise ValueError("Keep at least one Home page")
    packed["pages"] = [page for page in packed["pages"] if page["id"] != page_id]
    if packed["active_page_id"] == page_id:
        packed["active_page_id"] = packed["pages"][0]["id"]
    return packed


def set_active_page(layout: Dict[str, Any], page_id: str) -> Dict[str, Any]:
    packed = sanitize_layout(layout)
    if _page(packed, page_id) is None:
        raise ValueError("Page not found")
    packed["active_page_id"] = page_id
    return packed


def set_page_colors(layout: Dict[str, Any], page_id: str, colors: Any) -> Dict[str, Any]:
    packed = sanitize_layout(layout)
    page = _page(packed, page_id)
    if page is None:
        raise ValueError("Page not found")
    cleaned = sanitize_colors(colors)
    if cleaned:
        page["colors"] = cleaned
    else:
        page.pop("colors", None)
    return packed


def add_widget(
    layout: Dict[str, Any], page_id: str, kind: str, region: str = "below"
) -> Dict[str, Any]:
    packed = sanitize_layout(layout)
    page = _page(packed, page_id)
    if page is None:
        raise ValueError("Page not found")
    if kind not in WIDGET_CATALOG:
        raise ValueError("Unknown widget")
    if any(item["kind"] == kind for item in page["widgets"]):
        raise ValueError("That widget is already on this page")
    if len(page["widgets"]) >= MAX_WIDGETS_PER_PAGE:
        raise ValueError("This page is full")
    first_page = _is_first_page(packed, page_id)
    region = coerce_region(region, first_page)
    w, h = spec_default(kind)
    occupied = region_widgets(page["widgets"], region, first_page)
    spot = first_fit(occupied, w, h)
    if spot is None:
        raise ValueError("No free space for that size")
    widget = {"id": _new_id(), "kind": kind, "x": spot[0], "y": spot[1], "w": w, "h": h}
    if region == "above":
        widget["region"] = "above"
    page["widgets"].append(widget)
    return packed


def move_widget(
    layout: Dict[str, Any],
    page_id: str,
    widget_id: str,
    x: int,
    y: int,
    region: Optional[str] = None,
) -> Dict[str, Any]:
    packed = sanitize_layout(layout)
    page = _page(packed, page_id)
    if page is None:
        raise ValueError("Page not found")
    widget = next((item for item in page["widgets"] if item["id"] == widget_id), None)
    if widget is None:
        raise ValueError("Widget not found")
    first_page = _is_first_page(packed, page_id)
    dest = coerce_region(region if region is not None else widget.get("region"), first_page)
    nx = _as_int(x, widget["x"], 0, GRID_COLUMNS - widget["w"])
    ny = _as_int(y, widget["y"], 0, MAX_SCAN_ROWS - 1)
    trial = dict(widget, x=nx, y=ny)
    if dest == "above":
        trial["region"] = "above"
    else:
        trial.pop("region", None)
    occupied = region_widgets(page["widgets"], dest, first_page, ignore_id=widget_id)
    if any(boxes_overlap(trial, other) for other in occupied):
        raise ValueError("That cell is taken")
    widget["x"] = nx
    widget["y"] = ny
    if dest == "above":
        widget["region"] = "above"
    else:
        widget.pop("region", None)
    return packed


def resize_widget(
    layout: Dict[str, Any], page_id: str, widget_id: str, w: Any = None, h: Any = None
) -> Dict[str, Any]:
    packed = sanitize_layout(layout)
    page = _page(packed, page_id)
    if page is None:
        raise ValueError("Page not found")
    widget = next((item for item in page["widgets"] if item["id"] == widget_id), None)
    if widget is None:
        raise ValueError("Widget not found")
    if w is None or h is None:
        nw, nh = next_size(widget["kind"], widget["w"], widget["h"])
        may_relocate = True
    else:
        nw, nh = nearest_size(widget["kind"], w, h)
        may_relocate = False
    trial = dict(widget, w=nw, h=nh)
    if may_relocate:
        trial["x"] = min(widget["x"], GRID_COLUMNS - nw)
    elif widget["x"] + nw > GRID_COLUMNS:
        raise ValueError("That size does not fit here")
    first_page = _is_first_page(packed, page_id)
    region = widget_region(widget, first_page)
    occupied = region_widgets(page["widgets"], region, first_page, ignore_id=widget_id)
    if any(boxes_overlap(trial, other) for other in occupied):
        if not may_relocate:
            raise ValueError("That size does not fit here")
        spot = first_fit(occupied, nw, nh)
        if spot is None:
            raise ValueError("No room for that size")
        trial["x"], trial["y"] = spot
    widget.update(trial)
    return packed


def remove_widget(layout: Dict[str, Any], page_id: str, widget_id: str) -> Dict[str, Any]:
    packed = sanitize_layout(layout)
    page = _page(packed, page_id)
    if page is None:
        raise ValueError("Page not found")
    page["widgets"] = [item for item in page["widgets"] if item["id"] != widget_id]
    return packed


def _path() -> Any:
    return data_directory() / "home_layout.json"


def _write(layout: Dict[str, Any]) -> Dict[str, Any]:
    packed = sanitize_layout(layout)
    path = _path()
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(packed, handle, indent=2)
    os.replace(tmp, path)
    return packed


@eel.expose
def get_home_catalog() -> List[Dict[str, Any]]:
    return catalog()


@eel.expose
def get_home_layout() -> Dict[str, Any]:
    path = _path()
    if not path.exists():
        return _write(default_layout())
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
        if int((raw or {}).get("version") or 0) < LAYOUT_VERSION:
            return _write(migrate(raw))
        return sanitize_layout(raw)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return _write(default_layout())


@eel.expose
def save_home_layout(layout: Dict[str, Any]) -> Dict[str, Any]:
    return _write(layout)


@eel.expose
def reset_home_layout() -> Dict[str, Any]:
    return _write(default_layout())


@eel.expose
def add_home_page(name: str = "") -> Dict[str, Any]:
    return _write(add_page(get_home_layout(), name))


@eel.expose
def rename_home_page(page_id: str, name: str) -> Dict[str, Any]:
    return _write(rename_page(get_home_layout(), page_id, name))


@eel.expose
def delete_home_page(page_id: str) -> Dict[str, Any]:
    return _write(delete_page(get_home_layout(), page_id))


@eel.expose
def set_active_home_page(page_id: str) -> Dict[str, Any]:
    return _write(set_active_page(get_home_layout(), page_id))


@eel.expose
def set_home_page_colors(page_id: str, colors: Any) -> Dict[str, Any]:
    return _write(set_page_colors(get_home_layout(), page_id, colors))


@eel.expose
def add_home_widget(page_id: str, kind: str, region: str = "below") -> Dict[str, Any]:
    return _write(add_widget(get_home_layout(), page_id, kind, region))


@eel.expose
def move_home_widget(
    page_id: str, widget_id: str, x: int, y: int, region: str = ""
) -> Dict[str, Any]:
    dest = region if str(region or "").strip() else None
    return _write(move_widget(get_home_layout(), page_id, widget_id, x, y, dest))


@eel.expose
def resize_home_widget(page_id: str, widget_id: str, w: Any = None, h: Any = None) -> Dict[str, Any]:
    return _write(resize_widget(get_home_layout(), page_id, widget_id, w, h))


@eel.expose
def remove_home_widget(page_id: str, widget_id: str) -> Dict[str, Any]:
    return _write(remove_widget(get_home_layout(), page_id, widget_id))
