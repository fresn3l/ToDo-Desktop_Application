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

from paths import data_directory

GRID_COLUMNS = 4
MAX_PAGES = 12
MAX_WIDGETS_PER_PAGE = 24
MAX_PAGE_NAME = 40
MAX_SCAN_ROWS = 32

# Allowed (width, height) in cells. macOS-style few sizes per kind.
WIDGET_CATALOG: Dict[str, Dict[str, Any]] = {
    "todo": {
        "label": "To Do",
        "sizes": ((2, 2), (2, 3), (4, 2), (4, 4)),
        "default": (2, 3),
    },
    "today_calendar": {
        "label": "Today",
        "sizes": ((2, 2), (2, 3), (4, 2)),
        "default": (2, 2),
    },
    "workout": {
        "label": "Workout",
        "sizes": ((2, 2), (2, 3), (4, 3), (4, 4)),
        "default": (2, 2),
    },
    "journal": {
        "label": "Journal",
        "sizes": ((2, 2), (4, 2), (4, 4)),
        "default": (2, 2),
    },
    "goals": {
        "label": "Goals",
        "sizes": ((2, 2), (4, 3), (4, 4)),
        "default": (4, 3),
    },
    "allwork": {
        "label": "All Work",
        "sizes": ((2, 2), (2, 3), (4, 2)),
        "default": (2, 2),
    },
    "analytics": {
        "label": "Analytics",
        "sizes": ((4, 3), (4, 4)),
        "default": (4, 3),
    },
    "timeline": {
        "label": "Timeline",
        "sizes": ((4, 2), (4, 3), (4, 4)),
        "default": (4, 3),
    },
    "countdown": {
        "label": "Countdown",
        "sizes": ((2, 2), (4, 2)),
        "default": (2, 2),
    },
    "heatmap": {
        "label": "Heatmap",
        "sizes": ((4, 2), (4, 3)),
        "default": (4, 2),
    },
    "day_brief": {
        "label": "Day",
        "sizes": ((2, 3), (4, 3), (4, 4)),
        "default": (2, 3),
    },
    "counters": {
        "label": "Counters",
        "sizes": ((2, 2), (2, 3), (4, 2), (4, 3)),
        "default": (2, 2),
    },
    "reading": {
        "label": "Reading",
        "sizes": ((2, 2), (2, 3), (4, 2)),
        "default": (2, 2),
    },
}

SOURCE_TAB = {
    "todo": "todoTab",
    "today_calendar": "todayCalendarSource",
    "workout": "workoutTab",
    "journal": "journalTab",
    "goals": "goalsTab",
    "allwork": "allWorkTab",
    "analytics": "analyticsTab",
    "timeline": "timelineTab",
    "countdown": "countdownSource",
    "heatmap": "heatmapSource",
    "day_brief": "dayBriefSource",
    "counters": "countersSource",
    "reading": "readingSource",
}


def _new_id() -> str:
    return str(uuid.uuid4())


def default_layout() -> Dict[str, Any]:
    page_id = _new_id()
    return {
        "columns": GRID_COLUMNS,
        "active_page_id": page_id,
        "pages": [
            {
                "id": page_id,
                "name": "Home",
                "widgets": [
                    {
                        "id": _new_id(),
                        "kind": "todo",
                        "x": 0,
                        "y": 0,
                        "w": 2,
                        "h": 3,
                    },
                    {
                        "id": _new_id(),
                        "kind": "today_calendar",
                        "x": 2,
                        "y": 0,
                        "w": 2,
                        "h": 2,
                    },
                ],
            }
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
        return (2, 2)
    try:
        want = (int(w), int(h))
    except (TypeError, ValueError):
        return spec_default(kind)
    if want in sizes:
        return want
    return spec_default(kind)


def spec_default(kind: str) -> Tuple[int, int]:
    spec = WIDGET_CATALOG.get(kind)
    if not spec:
        return (2, 2)
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


def _clip_name(raw: Any, fallback: str) -> str:
    text = str(raw or "").strip()
    if not text:
        return fallback
    return text[:MAX_PAGE_NAME]


def _as_int(raw: Any, default: int, lo: int, hi: int) -> int:
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, n))


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
        for item in incoming[:MAX_WIDGETS_PER_PAGE]:
            if not isinstance(item, dict):
                continue
            kind = str(item.get("kind") or "").strip()
            if kind not in WIDGET_CATALOG or kind in seen_kinds:
                continue
            w, h = coerce_size(kind, item.get("w"), item.get("h"))
            x = _as_int(item.get("x"), 0, 0, GRID_COLUMNS - w)
            y = _as_int(item.get("y"), 0, 0, MAX_SCAN_ROWS - 1)
            widget = {
                "id": str(item.get("id") or "").strip() or _new_id(),
                "kind": kind,
                "x": x,
                "y": y,
                "w": w,
                "h": h,
            }
            if any(boxes_overlap(widget, other) for other in widgets):
                spot = first_fit(widgets, w, h)
                if spot is None:
                    continue
                widget["x"], widget["y"] = spot
            seen_kinds.add(kind)
            widgets.append(widget)
        pages.append({"id": page_id, "name": name, "widgets": widgets})
    if not pages:
        return default_layout()
    active = str(raw.get("active_page_id") or "").strip()
    if not any(page["id"] == active for page in pages):
        active = pages[0]["id"]
    return {"columns": GRID_COLUMNS, "active_page_id": active, "pages": pages}


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


def add_widget(layout: Dict[str, Any], page_id: str, kind: str) -> Dict[str, Any]:
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
    w, h = spec_default(kind)
    spot = first_fit(page["widgets"], w, h)
    if spot is None:
        raise ValueError("No free space for that size")
    page["widgets"].append(
        {"id": _new_id(), "kind": kind, "x": spot[0], "y": spot[1], "w": w, "h": h}
    )
    return packed


def move_widget(
    layout: Dict[str, Any], page_id: str, widget_id: str, x: int, y: int
) -> Dict[str, Any]:
    packed = sanitize_layout(layout)
    page = _page(packed, page_id)
    if page is None:
        raise ValueError("Page not found")
    widget = next((item for item in page["widgets"] if item["id"] == widget_id), None)
    if widget is None:
        raise ValueError("Widget not found")
    nx = _as_int(x, widget["x"], 0, GRID_COLUMNS - widget["w"])
    ny = _as_int(y, widget["y"], 0, MAX_SCAN_ROWS - 1)
    trial = dict(widget, x=nx, y=ny)
    if any(
        other["id"] != widget_id and boxes_overlap(trial, other) for other in page["widgets"]
    ):
        raise ValueError("That cell is taken")
    widget["x"] = nx
    widget["y"] = ny
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
    else:
        nw, nh = coerce_size(widget["kind"], w, h)
    trial = dict(widget, w=nw, h=nh)
    trial["x"] = min(widget["x"], GRID_COLUMNS - nw)
    if any(
        other["id"] != widget_id and boxes_overlap(trial, other) for other in page["widgets"]
    ):
        spot = first_fit(page["widgets"], nw, nh, ignore_id=widget_id)
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
            return sanitize_layout(json.load(handle))
    except (OSError, json.JSONDecodeError):
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
def add_home_widget(page_id: str, kind: str) -> Dict[str, Any]:
    return _write(add_widget(get_home_layout(), page_id, kind))


@eel.expose
def move_home_widget(page_id: str, widget_id: str, x: int, y: int) -> Dict[str, Any]:
    return _write(move_widget(get_home_layout(), page_id, widget_id, x, y))


@eel.expose
def resize_home_widget(page_id: str, widget_id: str, w: Any = None, h: Any = None) -> Dict[str, Any]:
    return _write(resize_widget(get_home_layout(), page_id, widget_id, w, h))


@eel.expose
def remove_home_widget(page_id: str, widget_id: str) -> Dict[str, Any]:
    return _write(remove_widget(get_home_layout(), page_id, widget_id))
