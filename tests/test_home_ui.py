"""Home shell markup: two main tabs, widget sources, first-install catalog."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
TABS = (ROOT / "web" / "js" / "tabs.js").read_text(encoding="utf-8")
HOME_JS = (ROOT / "web" / "js" / "home_layout.js").read_text(encoding="utf-8")
HOME_RUNTIME = (ROOT / "web" / "js" / "home.js").read_text(encoding="utf-8")
GLANCE_TILES = (ROOT / "web" / "js" / "glance_tiles.js").read_text(encoding="utf-8")
TODAY_JS = (ROOT / "web" / "js" / "today.js").read_text(encoding="utf-8")
GLANCE_JS = (ROOT / "web" / "js" / "glance.js").read_text(encoding="utf-8")
CAL_JS = (ROOT / "web" / "js" / "calendar.js").read_text(encoding="utf-8")
UTILS = (ROOT / "web" / "js" / "utils.js").read_text(encoding="utf-8")
SETTINGS_JS = (ROOT / "web" / "js" / "settings.js").read_text(encoding="utf-8")
GOALS_JS = (ROOT / "web" / "js" / "goals.js").read_text(encoding="utf-8")
STYLE = (ROOT / "web" / "style.css").read_text(encoding="utf-8")
TOKENS = (ROOT / "web" / "tokens.css").read_text(encoding="utf-8")
SWIFT = (ROOT / "macos" / "KosistenzWindow.swift").read_text(encoding="utf-8")
NATIVE_MAC = (ROOT / "native_mac.py").read_text(encoding="utf-8")
PASTE_JS = (ROOT / "web" / "js" / "paste_insert.js").read_text(encoding="utf-8")


def container_rules(condition: str) -> str:
    """Every rule the tile applies when its box matches `condition`.

    Tiles are styled by the room they have rather than the cells they span,
    so the tests ask the same question the stylesheet does.
    """
    out = []
    for chunk in STYLE.split("@container tile ")[1:]:
        head, _, rest = chunk.partition("{")
        if condition not in head:
            continue
        depth, end = 1, 0
        for i, ch in enumerate(rest):
            depth += (ch == "{") - (ch == "}")
            if depth == 0:
                end = i
                break
        out.append(rest[:end])
    return "\n".join(out)


class HomeUiTests(unittest.TestCase):
    def test_the_widget_border_settings_reach_the_board(self) -> None:
        """Appearance writes a width and a colour for the widget border. The
        board drew its own border and ignored both, so those controls moved
        nothing."""
        appearance = (ROOT / "web" / "js" / "appearance.js").read_text(encoding="utf-8")
        for token in ("--home-widget-border-width", "--home-widget-border-color"):
            self.assertIn(token, appearance, f"{token} should still be written")
            self.assertIn(f"var({token}", STYLE, f"{token} has no reader")
        rule = STYLE.split(".home-widget {")[1].split("}")[0]
        self.assertIn("var(--home-widget-border-width", rule)
        self.assertIn("var(--home-widget-border-color", rule)

    def test_sidebar_is_home_journal_and_calendar(self) -> None:
        self.assertIn('data-tab="home"', INDEX)
        self.assertIn('data-tab="journal"', INDEX)
        self.assertIn('data-tab="calendar"', INDEX)
        self.assertIn('data-tab="analytics"', INDEX)
        self.assertIn('data-tab="settings"', INDEX)
        self.assertNotIn('data-tab="today"', INDEX)
        self.assertNotIn('data-tab="workout"', INDEX)
        self.assertNotIn('data-tab="todo"', INDEX)

    def test_old_pages_are_widget_sources(self) -> None:
        for source_id in (
            "todoTab",
            "todayCalendarSource",
            "workoutTab",
            "goalsTab",
            "allWorkTab",
            "analyticsTab",
            "timelineTab",
            "weatherSource",
            "focusSource",
            "countdownSource",
            "habitsSource",
            "heatmapSource",
            "dayBriefSource",
            "countersSource",
            "readingSource",
            "wordTab",
            "clunySource",
            "checklistTab",
        ):
            self.assertIn(f'id="{source_id}"', INDEX)
            self.assertIn("widget-source", INDEX)
        self.assertIn('id="wordCard"', INDEX)
        self.assertIn('id="checklistWizard"', INDEX)
        self.assertIn('id="journalTab"', INDEX)
        self.assertIn('id="journalTab" class="tab-content"', INDEX)
        self.assertIn('id="analyticsTab" class="tab-content widget-source"', INDEX)
        self.assertIn('data-value="28"', INDEX)
        self.assertIn("4 weeks", INDEX)
        self.assertIn('id="calBarOutcome"', INDEX)
        self.assertIn("Did not complete", INDEX)
        self.assertIn("create_rate_goal", GOALS_JS)
        self.assertIn("set_bar_outcome", CAL_JS)
        self.assertIn("is-missed", CAL_JS)
        self.assertIn("weekChart", (ROOT / "web" / "js" / "analytics.js").read_text(encoding="utf-8"))

    def test_edit_home_controls_exist(self) -> None:
        for needle in (
            "homeEditBtn",
            "homeGrid",
            "homeGridAbove",
            "homeCheckinBand",
            "homeCheckinBody",
            "homeEditBar",
            "homeAddPageBtn",
            "homeRenamePageBtn",
            "homeCatalog",
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
        self.assertIn("journal: 'journalTab'", TABS)
        self.assertIn("1: 'home'", TABS)
        self.assertIn("2: 'journal'", TABS)
        self.assertIn("3: 'calendar'", TABS)
        self.assertIn("analytics: 'analyticsTab'", TABS)
        self.assertIn("analytics: 'Analytics'", TABS)
        self.assertNotIn("name === 'analytics'", TABS)
        self.assertIn("key === 'analytics'", TABS)

    def test_js_catalog_matches_folded_tabs(self) -> None:
        body = HOME_JS.split("export const WIDGET_CATALOG = {", 1)[1].split("\n};", 1)[0]
        kinds = set(re.findall(r"^ {4}(\w+): \{", body, re.M))
        # Journal, Checklist and Settings are tabs, not tiles. To Do, All Work,
        # Unplaced and Due are one Work tile with a setting.
        self.assertEqual(
            kinds,
            {
                "work",
                "today_calendar",
                "workout",
                "goals",
                "analytics",
                "weather",
                "countdown",
                "habits",
                "day_brief",
                "counters",
                "reading",
                "word",
                "cluny",
            },
        )
        for slice_name in ("'today'", "'backlog'", "'unplaced'", "'due'"):
            self.assertIn(f"value: {slice_name}", HOME_JS)

    def test_calendar_month_year_markup(self) -> None:
        for needle in ("calViewGroup", "calMonthGrid", "calYearGrid", "calFillWeek", "calPrevWeek"):
            self.assertIn(f'id="{needle}"', INDEX)
        self.assertIn('data-cal-view="week"', INDEX)
        self.assertIn('data-cal-view="month"', INDEX)
        self.assertIn('data-cal-view="year"', INDEX)
        self.assertIn('id="calFillWeek" class="btn-primary"', INDEX)
        self.assertNotIn('id="calFillWeek" class="btn-primary is-hidden"', INDEX)
        self.assertIn('id="calAskCluny"', INDEX)
        self.assertIn("cal-month-legend", STYLE)
        self.assertIn("cal-clock-hint", STYLE)
        self.assertIn("calView = 'week'", CAL_JS)
        self.assertIn("openWeekForDate", CAL_JS)
        self.assertIn("callEel('get_month'", CAL_JS)
        self.assertIn("callEel('get_year'", CAL_JS)
        self.assertIn("callEel('get_week'", CAL_JS)
        self.assertIn("callEel('create_calendar_event'", CAL_JS)
        self.assertIn("callEel('update_calendar_event'", CAL_JS)
        self.assertNotIn("eel.create_calendar_event", CAL_JS)
        lazy_js = (ROOT / "web" / "js" / "lazy.js").read_text(encoding="utf-8")
        self.assertIn("invoke_exposed", lazy_js)
        self.assertIn("eelErrorMessage", lazy_js)
        self.assertIn("errorText", lazy_js)
        self.assertIn("await loadLayout()", HOME_RUNTIME)
        self.assertIn("data.ok === false", GLANCE_TILES)
        self.assertNotIn("Nothing is written to Apple Calendar", INDEX)
        self.assertNotIn("Month and year for the long view", INDEX)
        self.assertNotIn("Class meeting times live here", INDEX)
        self.assertIn("Nothing to place.", CAL_JS)
        self.assertIn("html[data-page='calendar'] .app-content", STYLE)
        self.assertIn(".cal-month-cell.is-today", STYLE)
        self.assertIn(".cal-month-cell.is-out", STYLE)

    def test_work_layer_markup_and_dismiss_controls(self) -> None:
        for needle in ("homeWorkLayer", "homeWorkBackdrop", "homeWorkPanel", "homeWorkTitle", "homeWorkClose", "homeWorkBody"):
            self.assertIn(f'id="{needle}"', INDEX)
        self.assertIn("home-work-layer", STYLE)
        self.assertIn("home-work-backdrop", STYLE)
        self.assertIn("applyPanelBox", HOME_RUNTIME)
        self.assertIn("is-source", HOME_RUNTIME)
        self.assertIn("tileBox", HOME_RUNTIME)
        self.assertIn("openHomeWork", HOME_RUNTIME)
        self.assertIn("closeHomeWork", HOME_RUNTIME)
        self.assertIn("homeWorkClose", HOME_RUNTIME)
        self.assertIn("homeWorkBackdrop", HOME_RUNTIME)
        begin = HOME_RUNTIME.split("const beginDrag")[1].split("const beginResize")[0]
        self.assertIn("if (!editing) return", begin)
        self.assertIn("openHomeWork(card.getAttribute('data-key')", HOME_RUNTIME)
        self.assertIn("Escape", HOME_RUNTIME)
        self.assertIn("w-weather", HOME_RUNTIME)
        self.assertIn("w-word", HOME_RUNTIME)
        self.assertIn("inert", HOME_RUNTIME)

    def test_glances_mount_instead_of_full_pages(self) -> None:
        self.assertIn("mountGlance", HOME_RUNTIME)
        self.assertIn("from './glance_tiles.js'", HOME_RUNTIME)
        self.assertNotIn("mountWidget(", HOME_RUNTIME)
        self.assertIn("export function mountGlance", GLANCE_TILES)
        self.assertIn("function weatherHtml", GLANCE_TILES)
        self.assertIn("function wordHtml", GLANCE_TILES)
        self.assertIn("function todayHtml", GLANCE_TILES)
        self.assertIn("function workTodayHtml", GLANCE_TILES)
        self.assertIn("function countdownHtml", GLANCE_TILES)
        self.assertIn("function readingHtml", GLANCE_TILES)
        self.assertIn("function workoutHtml", GLANCE_TILES)
        self.assertIn("function goalsHtml", GLANCE_TILES)
        self.assertIn("function workBacklogHtml", GLANCE_TILES)
        self.assertIn("function dayBriefHtml", GLANCE_TILES)
        self.assertIn("function analyticsHtml", GLANCE_TILES)
        self.assertIn("function posterHtml", GLANCE_TILES)
        self.assertIn("function shellHtml", GLANCE_TILES)
        self.assertIn("glance_copy.js", GLANCE_TILES)
        self.assertIn("get_work_board", GLANCE_TILES)
        self.assertNotIn("get_today_home", GLANCE_TILES)
        self.assertIn("get_now_next_glance", GLANCE_TILES)
        self.assertIn("get_weather_forecast", GLANCE_TILES)
        self.assertIn("get_word_of_the_day", GLANCE_TILES)
        self.assertIn("get_analytics", GLANCE_TILES)
        self.assertIn("get_cluny_inbox", GLANCE_TILES)
        self.assertIn("function clunyHtml", GLANCE_TILES)
        self.assertIn("function workUnplacedHtml", GLANCE_TILES)
        self.assertIn("function workDueHtml", GLANCE_TILES)
        self.assertIn("todo-plus15", GLANCE_TILES)
        self.assertIn("work-today", GLANCE_TILES)
        self.assertIn("block-skip", GLANCE_TILES)
        self.assertIn("workout-log", GLANCE_TILES)
        self.assertIn("get_now_next_glance", GLANCE_TILES)
        self.assertNotIn("The days in a row", GLANCE_TILES)
        self.assertNotIn("A year at a glance", GLANCE_TILES)
        self.assertNotIn("The book in your hands", GLANCE_TILES)
        self.assertNotIn("Tick the small things", INDEX)
        self.assertNotIn("How this works", INDEX)
        self.assertNotIn("Forecast stays cached on this Mac", INDEX)
        self.assertNotIn("Name the work and how long it takes", INDEX)
        self.assertNotIn("Log body weight and today’s sessions", INDEX)
        self.assertIn(".glance-tile", STYLE)
        self.assertIn(".glance-kpi", STYLE)
        self.assertIn(".home-work-body > .widget-source", STYLE)
        self.assertIn("data-glance-act", GLANCE_TILES)
        self.assertIn("runGlanceAction", GLANCE_TILES)
        self.assertIn("todo-finish", GLANCE_TILES)
        self.assertIn("habit-tick", GLANCE_TILES)
        self.assertIn("counter-tap", GLANCE_TILES)
        self.assertIn("dayPart", GLANCE_TILES)
        self.assertIn("syncHomeDayPart", HOME_RUNTIME)
        self.assertIn(".glance-action", STYLE)
        self.assertIn(".glance-label", STYLE)
        self.assertIn(".home-widget.is-source", STYLE)
        self.assertNotIn("on the clock", GLANCE_TILES)
        self.assertNotIn("waiting to be dated", GLANCE_TILES)
        self.assertIn("1 event today.", (ROOT / "web" / "js" / "glance_copy.js").read_text(encoding="utf-8"))
        self.assertIn("clunyOff: 'Off'", (ROOT / "web" / "js" / "glance_copy.js").read_text(encoding="utf-8"))
        self.assertIn("noBrief: 'No brief yet'", (ROOT / "web" / "js" / "glance_copy.js").read_text(encoding="utf-8"))
        self.assertIn("unscheduled", (ROOT / "web" / "js" / "glance_copy.js").read_text(encoding="utf-8"))

    def test_live_home_opens_work_edit_home_moves(self) -> None:
        self.assertIn("home-widget-handle", HOME_RUNTIME)
        self.assertIn("closest('.home-widget-chrome')", HOME_RUNTIME)
        self.assertIn("closest('.home-widget-body')", HOME_RUNTIME)
        self.assertIn("window.addEventListener('pointermove', moveDrag)", HOME_RUNTIME)
        self.assertIn("window.addEventListener('mousemove', moveDrag)", HOME_RUNTIME)
        begin = HOME_RUNTIME.split("const beginDrag")[1].split("const moveDrag")[0]
        self.assertIn("if (!editing) return", begin)
        self.assertIn("openHomeWork", HOME_RUNTIME.split("addEventListener('click'")[-1].split("const beginDrag")[0])
        self.assertIn("runGlanceAction", HOME_RUNTIME)
        self.assertIn("data-glance-act", HOME_RUNTIME)

    def test_home_widgets_resize_by_dragging_handles(self) -> None:
        self.assertIn("export function pickResize", HOME_JS)
        self.assertIn('data-resize="se"', HOME_RUNTIME)
        self.assertIn('data-resize="e"', HOME_RUNTIME)
        self.assertIn('data-resize="s"', HOME_RUNTIME)
        self.assertNotIn('data-act="resize"', HOME_RUNTIME)
        self.assertNotIn(">Size</button>", HOME_RUNTIME)
        self.assertIn("callEel('resize_home_widget', page.id, id, w | 0, h | 0)", HOME_RUNTIME)
        self.assertIn("beginResize", HOME_RUNTIME)
        self.assertIn("cursor: nwse-resize", STYLE)
        self.assertIn("by a corner to resize it", INDEX)

    def test_home_widget_refresh_continues_after_one_failure(self) -> None:
        quiet = HOME_RUNTIME.split("async function runQuietly")[1].split("async function refreshWork")[0]
        self.assertIn("console.error(err)", quiet)
        work = HOME_RUNTIME.split("async function refreshWork")[1].split("async function refreshKeys")[0]
        self.assertIn("await runQuietly(refresh)", work)
        refresh = HOME_RUNTIME.split("async function refreshKeys")[1].split("function pageKeys")[0]
        self.assertIn("await runQuietly(() => refreshGlances", refresh)
        self.assertIn("ensureWork", HOME_RUNTIME)

    def test_native_prompts_use_in_app_dialog(self) -> None:
        self.assertIn('id="appDialog"', INDEX)
        self.assertIn("export function askText", UTILS)
        self.assertIn("export function askConfirm", UTILS)
        self.assertIn("utils.askText", HOME_RUNTIME)
        self.assertIn("utils.askConfirm", HOME_RUNTIME)
        self.assertNotIn("window.prompt", HOME_RUNTIME)
        self.assertNotIn("window.confirm", HOME_RUNTIME)
        self.assertIn("utils.askText", SETTINGS_JS)
        self.assertIn("utils.askConfirm", SETTINGS_JS)
        self.assertNotIn("window.prompt", SETTINGS_JS)
        self.assertNotIn("window.confirm", SETTINGS_JS)

    def test_webkit_hosts_implement_js_dialogs(self) -> None:
        self.assertIn("webView.uiDelegate = self", SWIFT)
        self.assertIn("runJavaScriptTextInputPanelWithPrompt", SWIFT)
        self.assertIn("setUIDelegate_", NATIVE_MAC)
        self.assertIn("runJavaScriptTextInputPanelWithPrompt", NATIVE_MAC)

    def test_calendar_ics_paste_inserts_url_instead_of_navigating(self) -> None:
        self.assertIn('<input type="text" id="calIcsUrl"', INDEX)
        self.assertIn("js/paste_insert.js", INDEX)
        self.assertIn("window.kosistenzInsertText", PASTE_JS)
        self.assertIn("kosistenzSanitizePastedUrl", PASTE_JS)
        self.assertIn("class KosistenzWebView", SWIFT)
        self.assertIn("pasteboardURLText", SWIFT)
        self.assertIn("pasteboardIcsText", SWIFT)
        self.assertIn("pasteCalendarPayload", SWIFT)
        self.assertIn('type == "icsPaste"', SWIFT)
        self.assertIn("NSSelectorFromString", SWIFT)
        self.assertIn("performWebEdit", SWIFT)
        self.assertIn('performWebEdit("copy:", on: hostWebView)', SWIFT)
        self.assertNotIn("#selector(NSResponder.", SWIFT)
        self.assertNotIn("NSResponder.paste", SWIFT)
        self.assertNotIn("NSResponder.copy", SWIFT)
        self.assertNotIn("NSResponder.cut", SWIFT)
        self.assertNotIn("NSResponder.selectAll", SWIFT)
        self.assertNotIn("hostWebView?.copy(", SWIFT)
        self.assertNotIn("webView?.copy(", SWIFT)
        self.assertNotIn("webView?.cut(", SWIFT)
        self.assertNotIn("webView?.paste(", SWIFT)
        self.assertIn("pasteFromClipboard", SWIFT)
        self.assertIn("extractURL", SWIFT)
        self.assertIn("makeFirstResponder", SWIFT)
        self.assertIn("pastePlainStringThroughWebKit", SWIFT)
        self.assertIn("class KosistenzMainWindow", SWIFT)
        self.assertIn("if let process = self.bridge, !process.isRunning", SWIFT)
        self.assertIn("process.terminationStatus", SWIFT)
        self.assertNotIn("bridge?.terminationStatus", SWIFT)
        widget = (ROOT / "macos" / "KosistenzWidget.swift").read_text(encoding="utf-8")
        self.assertIn("#if os(iOS)", widget)
        self.assertNotIn("if #available(macOS 14.0, *)", widget)
        self.assertIn("enum KosistenzApp", SWIFT)
        self.assertNotIn("self?.waitForHTTP", SWIFT)
        self.assertNotIn("super.paste", SWIFT)
        self.assertIn("override func sendEvent", SWIFT)
        self.assertIn("htmlString(from", SWIFT)
        self.assertIn("hostWebView", SWIFT)
        build_app = (ROOT / "build_app.py").read_text(encoding="utf-8")
        self.assertIn('"-parse-as-library"', build_app)
        self.assertIn('"-parse-as-library",\n        "-o", python_exe', build_app)
        chrome = (ROOT / "macos" / "KosistenzChrome.swift").read_text(encoding="utf-8")
        self.assertIn("window.toolbar = nil", chrome)
        self.assertNotIn("todayWorkout", chrome)
        self.assertNotIn("toolbarOpenToday", chrome)
        self.assertNotIn("NSToolbarDelegate", SWIFT)
        self.assertIn("origin.port == 0", chrome)
        self.assertNotIn("navigationAction.navigationType == .other", SWIFT)
        self.assertIn("kosistenzLooksLikeCalendarUrl", PASTE_JS)
        self.assertIn("looksLikeCalendarUrl", PASTE_JS)
        self.assertIn("isCalendarPage", PASTE_JS)
        self.assertIn("addEventListener('paste'", PASTE_JS)
        self.assertIn("performKeyEquivalent_", NATIVE_MAC)
        self.assertIn("class PasteWindow", NATIVE_MAC)
        self.assertIn("sendEvent_", NATIVE_MAC)
        self.assertNotIn('type="datetime-local"', INDEX)
        self.assertIn('placeholder="2026-09-08 0930"', INDEX)
        self.assertIn("fromLocalInput", CAL_JS)
        calendar_swift = (ROOT / "macos" / "KosistenzCalendar.swift").read_text(encoding="utf-8")
        self.assertIn("timeoutInterval: 120", calendar_swift)
        self.assertIn("addEventListener('paste'", CAL_JS)
        self.assertIn("kosistenzSanitizePastedUrl", CAL_JS)
        self.assertIn("clockWindow", CAL_JS)
        self.assertIn("minutesFromClock", CAL_JS)
        self.assertIn("saveAwake", CAL_JS)
        self.assertIn("import_pasted_calendar", CAL_JS)
        self.assertIn("pasteIcsButton", CAL_JS)
        self.assertIn("cal-hour-line", CAL_JS)
        self.assertIn('id="calPasteIcs"', INDEX)
        self.assertIn('id="calDayStart"', INDEX)
        self.assertIn('id="calDayEnd"', INDEX)
        self.assertIn('placeholder="0530"', INDEX)
        self.assertIn('placeholder="2130"', INDEX)
        self.assertIn("cal-hour-line", STYLE)
        self.assertNotIn("hourRange", CAL_JS)
        self.assertIn('id="calSaveItem"', INDEX)
        self.assertIn('id="calParkItem"', INDEX)
        self.assertIn("Save for later", INDEX)
        self.assertIn("update_calendar_event", CAL_JS)
        self.assertIn("park_schedule_block", CAL_JS)
        self.assertIn("schedule_work_at", CAL_JS)
        self.assertIn("onBlockPointerMove", CAL_JS)
        self.assertIn("unplaced_total", CAL_JS)
        self.assertIn("cal-due-chip", CAL_JS)
        self.assertIn("day.dues", CAL_JS)
        self.assertIn("renderDueStrip", CAL_JS)
        self.assertIn("shortTitle", CAL_JS)
        self.assertIn("dueParts", CAL_JS)
        self.assertIn("cal-week-board", CAL_JS)
        self.assertIn("cal-due-strip", CAL_JS)
        self.assertIn("showDayDues", CAL_JS)
        self.assertIn("hideDayDues", CAL_JS)
        self.assertIn("cal-block-time", CAL_JS)
        self.assertIn("replace(/^webcal:/i, 'https:')", CAL_JS)
        self.assertNotIn("dues.slice(0, 8)", CAL_JS)
        self.assertIn("grid-template-rows: subgrid", STYLE)
        self.assertIn("grid-row: 1 / span 3", STYLE)
        self.assertIn("cal-week-board", STYLE)
        self.assertIn("cal-course-badge", STYLE)
        self.assertNotIn("max-height: 2.75rem", STYLE)
        self.assertNotIn("padding-top: calc(36px + 2.75rem)", STYLE)
        self.assertNotIn("min-height: 560px", STYLE)
        self.assertIn('id="calendarFeedsList"', INDEX)
        self.assertIn("unsubscribe_calendar_feed", SETTINGS_JS)
        self.assertNotIn('id="deleteUndatedImportsBtn"', INDEX)
        self.assertNotIn('id="allWorkDeleteUndated"', INDEX)
        self.assertNotIn('id="calDeleteUndated"', INDEX)
        self.assertIn('id="calTodayRail"', INDEX)
        self.assertIn('id="calDayDues"', INDEX)
        self.assertIn("cal-feeds-panel", INDEX)
        self.assertIn('id="calFeedToggles"', INDEX)
        self.assertIn('id="calDueMenu"', INDEX)
        self.assertIn("renderDueChip", CAL_JS)
        self.assertIn("place_work_after_lecture", CAL_JS)
        self.assertIn("Add event", INDEX)
        self.assertIn("Add focus", INDEX)
        self.assertIn('id="calNewFocus"', INDEX)
        self.assertIn('id="calFocusAttach"', INDEX)
        self.assertIn("create_focus_block", CAL_JS)
        self.assertIn("kind === 'focus'", CAL_JS)
        self.assertIn("cal-block-overflow", CAL_JS)
        self.assertIn("id: 'event'", (ROOT / "web" / "js" / "appearance.js").read_text(encoding="utf-8"))
        self.assertIn("id: 'focus'", (ROOT / "web" / "js" / "appearance.js").read_text(encoding="utf-8"))
        self.assertIn("Place work", CAL_JS)
        self.assertIn("startNewEvent", CAL_JS)
        self.assertIn("Nothing to place.", CAL_JS)
        self.assertIn("Alt marks attended", INDEX)
        self.assertNotIn('id="calUnplacedBlock" hidden', INDEX)
        self.assertNotIn("Add to calendar", INDEX)
        self.assertNotIn("New lecture", INDEX)
        self.assertNotIn("Place after lecture", INDEX)
        self.assertNotIn("Office hours", INDEX)
        self.assertIn("Place after first event", INDEX)
        self.assertIn("selectedEventDays", CAL_JS)
        self.assertIn("set_calendar_feed_enabled", CAL_JS)
        self.assertIn("--due-h", CAL_JS)
        self.assertIn("kosistenz:open-todo", CAL_JS)
        self.assertIn("Open in To Do", INDEX)
        self.assertIn("data-feed-enabled", SETTINGS_JS)

    def test_calendar_tab_uses_full_width_and_taller_cells(self) -> None:
        self.assertIn("html[data-page='calendar'] .tab-content.active", STYLE)
        self.assertIn("max-width: none", STYLE)
        self.assertIn("min-height: 4.5rem", STYLE)
        self.assertIn("minmax(0, 1fr) minmax(240px, 280px)", STYLE)

    def test_home_shows_page_title_and_sidebar_pages(self) -> None:
        self.assertIn('id="homePageTitle"', INDEX)
        self.assertIn("page-head--home", INDEX)
        self.assertIn('id="homeNavPages"', INDEX)
        self.assertIn("data-home-page", HOME_RUNTIME)
        self.assertIn("paintSidebar", HOME_RUNTIME)
        self.assertIn("homePageId", TABS)
        self.assertIn("clearHomePageColors", TABS)

    def test_home_chrome_is_one_line(self) -> None:
        self.assertNotIn("home-title-strip", INDEX)
        self.assertNotIn("home-toolbar", INDEX)
        self.assertNotIn('id="homePages"', INDEX)
        self.assertNotIn("home-live-copy", INDEX)
        self.assertNotIn("paintChips", HOME_RUNTIME)
        self.assertIn('class="page-head page-head--home"', INDEX)
        self.assertIn(">Edit</button>", INDEX)
        self.assertNotIn(">Edit Home</button>", INDEX)
        # New page belongs with Rename and Delete, behind Edit.
        actions = INDEX.split('class="home-edit-actions"')[1].split("</div>")[0]
        for needle in ("homeAddPageBtn", "homeRenamePageBtn", "homeDeletePageBtn", "homeDoneEditBtn"):
            self.assertIn(needle, actions)

    def test_edit_mode_does_not_sit_on_the_tile_heading(self) -> None:
        self.assertIn(".home-shell.is-editing .glance-tile-head", STYLE)
        self.assertIn("visibility: hidden", STYLE)
        edit = HOME_RUNTIME.split("function setEditing")[1].split("\n}")[0]
        self.assertIn("editing ? 'Done' : 'Edit'", edit)
        self.assertIn("aria-expanded", edit)
        # Remove borrows btn-ghost, so it needs its own scale or it towers
        # over an 11px handle.
        btn = STYLE.split("\n.home-widget-btn {")[-1].split("}")[0]
        self.assertIn("font-size: var(--fs-micro)", btn)
        self.assertIn("min-height: 0", btn)

    def test_every_tab_names_itself_with_the_shared_head(self) -> None:
        # The topbar carried the page name and was display:none in the native
        # shell, so Journal and Settings shipped with no title at all.
        self.assertNotIn("app-topbar", INDEX)
        self.assertNotIn("app-topbar", STYLE)
        self.assertNotIn("pageCrumb", INDEX)
        self.assertNotIn("pageCrumb", TABS)
        self.assertNotIn("pageCrumb", HOME_RUNTIME)

        heads = re.findall(r'<section id="(\w+)Tab" class="tab-content', INDEX)
        self.assertEqual(
            heads,
            ["home", "calendar", "journal", "analytics", "brain", "library", "settings"],
        )
        for tab in heads:
            body = INDEX.split(f'<section id="{tab}Tab" class="tab-content')[1].split("</section>")[0]
            self.assertIn('class="page-head', body, tab)
            self.assertIn('class="page-title"', body, tab)

        # Brain and Library printed their name twice: once in the crumb, once
        # in the tab. Their two header rules were byte-identical.
        self.assertNotIn("brain-chat-head", INDEX)
        self.assertNotIn("brain-chat-head", STYLE)
        self.assertNotIn("library-head", INDEX)
        self.assertNotIn("library-head", STYLE)
        self.assertNotIn("cal-toolbar", INDEX)
        self.assertNotIn("cal-toolbar", STYLE)

    def test_tabs_that_fill_the_window_share_one_rule(self) -> None:
        fill = STYLE.split("html[data-page='journal'] .tab-content.active,")[1].split("}")[0]
        for tab in ("calendar", "analytics", "brain", "library", "settings"):
            self.assertIn(f"html[data-page='{tab}'] .tab-content.active", fill)
        self.assertIn("flex-direction: column", fill)
        # Brain and Library filled the window by subtracting a topbar height.
        self.assertNotIn("calc(100vh - 120px)", STYLE)

    def test_brain_and_library_say_cluny_is_off_once(self) -> None:
        brain = (ROOT / "web" / "js" / "brain.js").read_text(encoding="utf-8")
        library = (ROOT / "web" / "js" / "library.js").read_text(encoding="utf-8")
        # Both put the offline sentence in the subtitle and again in the
        # notice right below it. The subtitle now keeps its own job.
        self.assertIn(
            "if (line) line.textContent = 'Ask the local brain."
            " Kosistenz keeps the list and the clock.';",
            brain,
        )
        self.assertNotIn("offline_copy", library.split("if (line) {")[1].split("\n    }")[0])
        self.assertIn("#brainOffline p", brain)
        self.assertIn("offline.querySelector('p')", library)
        # One notice per Cluny surface: the Ask source, Brain, and Library.
        self.assertEqual(INDEX.count("Cluny is off. Journal, to-dos, and the clock still work."), 3)
        # Brain's header linked to a tab the sidebar already carries.
        self.assertNotIn("brainOpenLibraryBtn", INDEX)
        self.assertNotIn("brainOpenLibraryBtn", brain)
        # A full-width select stacked that header three rows deep.
        self.assertIn(".page-head-actions select", STYLE)

    def test_today_pills_are_gone_with_the_topbar(self) -> None:
        # They lived in the topbar, so the Mac app never showed them, and the
        # Home board already has a tile for each one.
        self.assertNotIn("renderPills", TODAY_JS)
        self.assertNotIn("today-pill", TODAY_JS)
        self.assertNotIn("today-pill", STYLE)
        self.assertNotIn("todayStatus", INDEX)
        self.assertNotIn("todayStatus", TODAY_JS)
        # .eyebrow outlives the topbar; Calendar, Today and To Do still use it.
        self.assertIn("\n.eyebrow {", STYLE)
        self.assertIn('class="eyebrow"', CAL_JS)

    def test_checkin_band_has_no_kicker(self) -> None:
        self.assertNotIn("homeCheckinKicker", INDEX)
        self.assertNotIn("homeCheckinKicker", HOME_RUNTIME)
        self.assertNotIn("home-checkin-kicker", STYLE)
        self.assertIn("Evening check-in", HOME_RUNTIME)
        self.assertNotIn("Everything stays on this Mac.", INDEX)

    def test_per_page_colors_and_settings_board(self) -> None:
        self.assertIn('id="colorScopeGroup"', INDEX)
        self.assertIn('data-color-scope="page"', INDEX)
        self.assertIn('id="colorPageSelect"', INDEX)
        self.assertIn("set_home_page_colors", SETTINGS_JS)
        self.assertIn("applyAppearanceOverlay", HOME_RUNTIME)
        self.assertIn('id="settingsBoard"', INDEX)
        self.assertIn('data-settings-col="cluny"', INDEX)
        self.assertIn('id="clunySqlitePath"', INDEX)
        self.assertIn('id="clunySaveBtn"', INDEX)
        self.assertIn("settings-resize", INDEX)
        self.assertIn("html[data-page='settings'] .tab-content.active", STYLE)
        self.assertIn("cursor: col-resize", STYLE)
        self.assertIn("setupSettingsResize", SETTINGS_JS)
        self.assertIn("saveClunySettings", SETTINGS_JS)
        self.assertIn("clunyBrainUrl", SETTINGS_JS)
        self.assertIn("probe_cluny_connection", SETTINGS_JS)
        self.assertIn("setPageColorSlot", SETTINGS_JS)

    def test_home_widgets_are_dense_and_scroll_the_page(self) -> None:
        self.assertIn("--home-row: var(--row-h, 54px)", STYLE)
        self.assertIn("grid-auto-rows: var(--home-row)", STYLE)
        self.assertIn("min-height: 0", STYLE)
        self.assertIn("overflow-y: auto", STYLE)
        self.assertIn("padding-bottom: 88px", STYLE)
        self.assertIn('sizes: [[2, 2]', HOME_JS)
        self.assertIn("default: [4, 6]", HOME_JS)
        self.assertIn("default: [4, 2]", HOME_JS)
        # The smallest tile is a chip: one figure, one label, no furniture.
        self.assertIn("container: tile / size", STYLE)
        tiny = container_rules("(max-height: 189px) and (max-width: 399px)")
        self.assertIn(".home-widget-body", tiny)
        self.assertIn(".home-widget-chrome", STYLE)
        self.assertIn("countdown-days", GLANCE_JS)
        tokens = (ROOT / "web" / "tokens.css").read_text(encoding="utf-8")
        self.assertIn("--row-h: 54px", tokens)
        self.assertIn("--grid-gap: 12px", tokens)
        self.assertIn("--glance-row-min:", tokens)
        self.assertIn("--sheet-max:", tokens)
        self.assertIn("--line:", tokens)
        self.assertIn('href="tokens.css"', INDEX)
        self.assertIn("max-width: 1440px", STYLE)
        self.assertNotIn("html[data-page='home'] .tab-content.active {\n    max-width: none", STYLE)

    def test_today_mini_widget_loads_without_legacy_today_page(self) -> None:
        self.assertIn('id="todayCalendarSource"', INDEX)
        self.assertIn('id="todayDateTitle"', INDEX)
        self.assertIn('id="todayAgenda"', INDEX)
        self.assertNotIn('id="todayHome"', INDEX)
        self.assertIn("getElementById('todayCalendarSource')", TODAY_JS)
        self.assertNotIn("getElementById('todayHome')", TODAY_JS)
        self.assertNotIn("paintCustomize()", TODAY_JS)
        self.assertNotIn(".today-home {", STYLE)
        self.assertNotIn(".today-card {", STYLE)
        self.assertNotIn("today_layout.js", (ROOT / "web" / "js" / "home.js").read_text(encoding="utf-8"))
        self.assertIn("get_home_boot", HOME_RUNTIME)
        self.assertIn("callEel('get_home_boot'", HOME_RUNTIME)
        self.assertIn("prefetched.ok !== false", HOME_RUNTIME)
        self.assertNotIn("loadLayout().then(() => renderHome())", HOME_RUNTIME)
        self.assertIn("weather-place-form.is-collapsed", STYLE)
        self.assertIn("pointer-events: none", STYLE)

    def test_app_opens_home_without_startup_delays(self) -> None:
        app = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        bridge = (ROOT / "bridge.py").read_text(encoding="utf-8")
        self.assertNotIn("setTimeout(resolve, 100)", app)
        self.assertNotIn("setTimeout(() => init().catch(handleInitError), 50)", app)
        self.assertNotIn("from './js/calendar.js'", app)
        self.assertNotIn("from './js/journal.js'", app)
        self.assertIn("void pullPhoneOnOpen()", app)
        self.assertNotIn("await pullPhoneOnOpen()", app)
        self.assertNotIn("maybe_pull_icloud_on_open()", bridge)
        self.assertIn("register_lazy_exposes()", bridge)
        self.assertIn("import appearance", bridge)
        self.assertNotIn("import calclock", bridge)
        self.assertNotIn("import brain", bridge)
        self.assertNotIn("bootFeature('settings')", TABS)
        boot = (ROOT / "home_boot.py").read_text(encoding="utf-8")
        self.assertIn("start_supervisor", boot)
        self.assertIn("get_home_boot", boot)
        tabs = (ROOT / "web" / "js" / "tabs.js").read_text(encoding="utf-8")
        self.assertIn("import('./calendar.js')", tabs)
        self.assertIn("bootFeature", tabs)

    def test_journal_tab_and_first_page_checkin_band(self) -> None:
        app = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        journal = (ROOT / "web" / "js" / "journal.js").read_text(encoding="utf-8")
        self.assertIn("switchTab('journal')", app)
        self.assertNotIn("ensureHomeWidget('journal')", app)
        self.assertIn("tab?.classList.contains('active')", journal)
        self.assertIn('id="homeBoard"', INDEX)
        self.assertIn('id="homeGridAbove"', INDEX)
        self.assertIn('id="homeCheckinBand"', INDEX)
        self.assertIn('id="homeCheckinToggle"', INDEX)
        self.assertIn('id="homeCheckinOther"', INDEX)
        self.assertIn("syncCheckin", HOME_RUNTIME)
        checklist = (ROOT / "web" / "js" / "daily_checklist.js").read_text(encoding="utf-8")
        self.assertIn("checklistSetupBound", checklist)
        self.assertIn("callEel('get_daily_checklist')", checklist)
        self.assertIn("eelErrorMessage", checklist)
        self.assertNotIn("[object Object]", checklist)
        self.assertNotIn("String(e)", checklist)
        self.assertIn("dropRegion", HOME_RUNTIME)
        self.assertIn("homeCheckinBand", HOME_RUNTIME)
        self.assertIn("open-evening-checkin", HOME_RUNTIME)
        self.assertNotIn("ensureHomeWidget('checklist')", HOME_RUNTIME)
        self.assertIn("home-checkin-band", STYLE)
        self.assertIn("is-empty-drop", STYLE)
        self.assertIn("html[data-page='journal'] .tab-content.active", STYLE)
        self.assertIn('class="journal-compose journal-paper"', INDEX)
        self.assertNotIn("panel journal-compose", INDEX)
        self.assertNotIn("journal-compose journal-paper panel", INDEX)
        self.assertNotIn("Last 30 days", INDEX)
        self.assertIn("Nothing saved this month.", journal)
        self.assertIn("empty-state--line", journal)
        self.assertIn("empty-state--line", STYLE)
        self.assertNotIn("On this Mac", INDEX)
        self.assertIn(".brand-tag", STYLE)
        self.assertIn('data-sidebar="compact"', INDEX)
        self.assertIn('aria-label="Expand sidebar"', INDEX)

    def test_cluny_ask_widget_and_day_hook(self) -> None:
        app = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        cluny = (ROOT / "web" / "js" / "cluny.js").read_text(encoding="utf-8")
        day = (ROOT / "web" / "js" / "day_brief.js").read_text(encoding="utf-8")
        self.assertIn('id="clunySource"', INDEX)
        self.assertIn('id="clunyAskForm"', INDEX)
        self.assertIn('id="clunyInbox"', INDEX)
        self.assertIn('id="clunyBrainUrl"', INDEX)
        self.assertIn('id="clunyTestBtn"', INDEX)
        self.assertIn('id="dayBriefCluny"', INDEX)
        self.assertIn("import('./cluny.js')", HOME_RUNTIME)
        self.assertIn("ensureWork", HOME_RUNTIME)
        self.assertIn("kosistenz:open-cluny", HOME_RUNTIME)
        self.assertIn("ensureHomeWidget('cluny')", HOME_RUNTIME)
        self.assertNotIn("ensureHomeWidget('journal')", HOME_RUNTIME)
        self.assertIn("ask_cluny", cluny)
        self.assertIn("accept_cluny_proposal", cluny)
        self.assertIn("row.citations", cluny)
        self.assertIn("row.message", cluny)
        self.assertIn("citationChips", cluny)
        self.assertIn(".cluny-inbox-row .cluny-voice", STYLE)
        self.assertIn("row?.message", GLANCE_TILES)
        brain = (ROOT / "web" / "js" / "brain.js").read_text(encoding="utf-8")
        self.assertIn("row.citations", brain)
        self.assertIn("citationChips", brain)
        self.assertIn("dayBriefOpenCluny", day)
        self.assertIn("kosistenz:open-cluny", day)
        self.assertIn("cluny-chip", STYLE)
        self.assertIn(".cluny-inbox-row .cluny-sources", STYLE)
        self.assertIn("kind === 'cluny'", GLANCE_TILES)
        self.assertIn('data-cluny-prompt="What do I have to do today?"', INDEX)
        self.assertIn('data-cluny-prompt="What should I do with my free time?"', INDEX)
        self.assertIn("promptCluny", cluny)
        self.assertIn("promptCluny", HOME_RUNTIME)
        self.assertIn("cluny-ask", GLANCE_TILES)
        self.assertIn("w-cluny", HOME_RUNTIME)
        self.assertIn("local-week", HOME_RUNTIME)
        self.assertIn("name: 'Week'", HOME_RUNTIME)
        self.assertIn("eveningAsk", (ROOT / "web" / "js" / "glance_copy.js").read_text(encoding="utf-8"))
        self.assertIn("What still matters tonight?", GLANCE_TILES)
        self.assertIn("Asking Cluny…", cluny)
        self.assertIn("brain_ready === false", GLANCE_TILES)
        self.assertIn('id="clunyBackfillBtn"', INDEX)
        self.assertIn('id="clunyBackfillLifeBtn"', INDEX)
        self.assertIn("backfill_cluny_journals", SETTINGS_JS)
        self.assertIn("backfill_cluny_life", SETTINGS_JS)
        self.assertIn("Index my life", INDEX)
        self.assertIn("Ask about what you wrote", INDEX)
        self.assertIn("Cluny does not schedule", INDEX)
        self.assertIn("never an HH:MM", INDEX)
        self.assertIn("Indexed PDFs and notes", INDEX)
        self.assertIn('id="libraryOffline"', INDEX)
        self.assertIn('option value="propose"', INDEX)
        self.assertNotIn('option value="planner"', INDEX)
        self.assertIn("Kosistenz keeps the list and the clock", INDEX)
        self.assertIn("/opt/homebrew/bin", INDEX)
        self.assertIn('id="clunySnapshotStatus"', INDEX)
        self.assertIn("backfill_cluny_journals", SETTINGS_JS)
        self.assertIn("class=\"todo-more\"", INDEX)
        self.assertIn("Day this week", INDEX)
        self.assertIn("Repeat on these days", INDEX)
        self.assertIn(">Add</button>", INDEX)
        self.assertIn("Dated is not on the clock", INDEX)
        self.assertIn("All Work", INDEX)
        self.assertIn("glance-capture", GLANCE_TILES)
        self.assertIn("runGlanceCapture", GLANCE_TILES)
        self.assertIn("w-unplaced", HOME_RUNTIME)
        self.assertIn("Save repeating to-do", (ROOT / "web" / "js" / "todo.js").read_text(encoding="utf-8"))
        self.assertIn("⌘</kbd><kbd>1</kbd> Home", INDEX)

    def test_calendar_blocks_scale_with_duration(self) -> None:
        self.assertNotIn("Math.max(20, (end - start)", CAL_JS)
        self.assertNotIn("Math.max(18, (dur / span)", CAL_JS)
        self.assertIn("const height = (dur / span) * 100", CAL_JS)
        self.assertIn("is-short", CAL_JS)
        self.assertIn("is-tiny", CAL_JS)
        self.assertIn(".cal-block.is-short", STYLE)
        self.assertIn(".cal-block.is-tiny", STYLE)
        self.assertIn("min-height: 8px", STYLE)
        self.assertIn("const heightPct = (dur / span) * 100", CAL_JS)

    def test_home_does_not_refetch_what_boot_already_returned(self) -> None:
        boot_py = (ROOT / "home_boot.py").read_text(encoding="utf-8")
        # The check-in rides in the glance pool instead of waiting behind it.
        self.assertIn("CHECKIN_TASK", boot_py)
        self.assertIn("glances = _fetch_glances(keys, extra)", boot_py)
        self.assertIn("checkin = glances.pop(CHECKIN_TASK, None)", boot_py)
        # Rate-goal voice reads every goal over three windows; off the trip.
        self.assertIn("_nudge_rate_voice_later()", boot_py)
        self.assertNotIn('_safe_call("cluny_voice", "refresh_rate_voice_safe")\n    glances', boot_py)
        self.assertIn("def wait_for_boot_background", boot_py)
        # Opening a widget loads the sheet, not the tile behind it again.
        opener = HOME_RUNTIME.split("export async function openHomeWork")[1].split("async function runQuietly")[0]
        self.assertIn("void refreshWork()", opener)
        self.assertNotIn("refreshKeys([key])", opener)
        # Coming back to a board that is still current skips another boot.
        self.assertIn("function bootIsFresh()", HOME_RUNTIME)
        self.assertIn("if (!bootIsFresh()) void refreshHomeData()", HOME_RUNTIME)
        self.assertIn("bootStale = true", HOME_RUNTIME)

    def test_main_tabs_share_one_heading_ladder(self) -> None:
        # The click sheet and the calendar read the shared scale rather than
        # picking a size per panel.
        head = STYLE.split(".home-work-head h2 {")[1].split("}")[0]
        self.assertIn("font-size: var(--fs-", head)
        # Compact density moves the reading sizes together, not half of them.
        compact = STYLE.split("html[data-density='compact'] {")[1].split("}")[0]
        for token in ("--fs-body:", "--fs-lead:", "--fs-heading:", "--fs-title:"):
            self.assertIn(token, compact)
        # A wrapped header needs a second-row gap, not just a column gap.
        head = STYLE.split("\n.page-head {")[1].split("}")[0]
        self.assertIn("row-gap: var(--space-sm)", head)
        self.assertIn("margin-bottom: var(--tab-gap)", head)
        # Three sentences of standing instructions was noise.
        self.assertNotIn("Drag Unplaced onto the day to place work.", INDEX)
        self.assertIn("Alt marks attended", INDEX)

    def test_calendar_drag_is_tracked_at_the_window(self) -> None:
        # Pointer capture alone loses the drag inside WKWebView, so the window
        # has to carry move and up the way the Home board already does.
        self.assertIn("window.addEventListener('pointermove', onDragMove)", CAL_JS)
        self.assertIn("window.addEventListener('pointerup', onDragUp)", CAL_JS)
        self.assertIn("window.addEventListener('pointercancel', onDragUp)", CAL_JS)
        self.assertIn("window.addEventListener('mousemove', onDragMove)", CAL_JS)
        self.assertIn("window.addEventListener('mouseup', onDragUp)", CAL_JS)
        self.assertIn("trackDragAtWindow()", CAL_JS)
        # A mouse event has no pointerId; the guard must not drop it.
        self.assertIn("e.pointerId == null || e.pointerId === dragState.pointerId", CAL_JS)
        self.assertNotIn("btn.addEventListener('pointermove', onDuePointerMove)", CAL_JS)
        self.assertNotIn("btn.addEventListener('pointerup', onDuePointerUp)", CAL_JS)
        self.assertNotIn("btn.addEventListener('pointermove', onBlockPointerMove)", CAL_JS)
        # A drop that lands nowhere says so instead of failing in silence.
        self.assertIn("Switch to Week view to place this on the clock.", CAL_JS)
        self.assertIn("Switch to Week to drag these onto the clock.", CAL_JS)
        # The browser must not claim the gesture before the handler sees it.
        chip = STYLE.split(".cal-due-chip {")[1].split("}")[0]
        self.assertIn("touch-action: none", chip)
        item = STYLE.split(".cal-unplaced-item {")[1].split("}")[0]
        self.assertIn("touch-action: none", item)

    def test_a_tile_is_a_head_a_middle_that_grows_and_a_foot(self) -> None:
        """The middle taking the slack is what puts every tile's buttons on the
        same line as its neighbour's. They used to float wherever the content
        stopped, so a tile with one line in it put its button halfway up."""
        self.assertIn('<header class="glance-tile-head">', GLANCE_TILES)
        self.assertIn('<div class="glance-body">', GLANCE_TILES)
        body = STYLE.split(".glance-body {", 1)[1].split("}", 1)[0]
        self.assertIn("flex: 1 1 auto", body)
        self.assertIn("min-height: 0", body)
        # The tile's own head, not the .glance-head the weather panel uses.
        self.assertIn(".glance-tile-head {", STYLE)
        self.assertNotIn('class="glance-head"', GLANCE_TILES)

    def test_a_tile_heading_does_not_shout(self) -> None:
        """Uppercase letterspaced labels on every tile made the board shout its
        own furniture before you could read anything on it."""
        label = STYLE.split("\n.glance-label {", 1)[1].split("}", 1)[0]
        self.assertNotIn("text-transform: uppercase", label)
        self.assertIn("letter-spacing: var(--letter-normal)", label)
        # The count sits apart from the heading rather than running into it.
        self.assertIn(".glance-count {", STYLE)
        self.assertIn('<span class="glance-count">', GLANCE_TILES)
        self.assertNotIn("countLabel", GLANCE_TILES)

    def test_the_smallest_tile_still_says_something_when_it_is_empty(self) -> None:
        """A 2x2 tile drops the sentence under its metric. With nothing to
        count there is no metric, and the tile came out blank."""
        tiny = container_rules("(max-height: 189px) and (max-width: 399px)")
        self.assertIn(".glance-tile.is-empty .glance-message", tiny)
        self.assertIn(".glance-tile.is-error .glance-message", tiny)
        self.assertIn(".glance-tile.is-loading .glance-message", tiny)

    def test_glance_tiles_fit_one_row_height(self) -> None:
        self.assertIn("action: w >= 4 && h >= 4", GLANCE_TILES)
        # A tile with one row of room shows a headline and nothing that needs
        # a second line to make sense.
        short = container_rules("(max-height: 189px)")
        for dropped in (".glance-list", ".glance-capture", ".glance-actions", ".glance-hourly"):
            self.assertIn(dropped, short, f"a short tile should drop {dropped}")
        self.assertIn("overflow: hidden", STYLE)

    def test_every_glance_spends_one_row_budget(self) -> None:
        # The budget comes from the height the tile actually has, because the
        # same cell count is a different number of rows on a different grid.
        self.assertIn("function rowBudget(card, h)", GLANCE_TILES)
        self.assertIn("card?.getBoundingClientRect?.().height", GLANCE_TILES)
        self.assertIn("const rows = rowBudget(card, h);", GLANCE_TILES)
        # A tile on a page nobody opened measures nothing and still paints.
        self.assertIn("if (px <= 0) return h >= 6 ? 6 : h >= 4 ? 3 : 0;", GLANCE_TILES)
        self.assertIn("capture: h >= 6", GLANCE_TILES)
        self.assertIn("function capLines(lines, size)", GLANCE_TILES)
        self.assertIn("function actionRow(actions, size)", GLANCE_TILES)
        # A narrow tile gets the move you would make plus Open, nothing more.
        self.assertIn("size.w <= 4 && list.length > 2", GLANCE_TILES)
        self.assertIn("size.capture ? todoCaptureHtml() : ''", GLANCE_TILES)
        # Buttons and day chips fit by width, so height must not add them back.
        self.assertIn("if (size.w >= 6) {", GLANCE_TILES)
        self.assertIn("size.w >= 6 ? weekdayChips", GLANCE_TILES)
        # Every list renderer reads the shared budget instead of its own number.
        self.assertGreaterEqual(GLANCE_TILES.count("size.rows"), 8)
        # A tile showing a list drops the headline rather than repeat row one.
        todo = GLANCE_TILES.split("function workTodayHtml")[1].split("function habitsHtml")[0]
        self.assertIn("pool.slice(0, size.rows)", todo)
        self.assertIn("primary: size.tall ? '' :", todo)
        self.assertIn("moreCount(extra)", todo)
        # Headline already carries the title, so the beat line drops to a time,
        # and an empty clock says so once rather than as headline and body both.
        self.assertIn("function beatBody(beat, size)", GLANCE_TILES)
        self.assertIn("item === focus ? '' :", GLANCE_TILES)
        self.assertEqual(GLANCE_TILES.count("copy.clearClock"), 1)
        # Sizes and spacing live in tokens, never hard-coded twice.
        self.assertIn("--glance-row-min:", TOKENS)
        self.assertIn("--glance-action-h:", TOKENS)
        self.assertIn("--tile-pad:", TOKENS)

    def test_goals_widget_loads_through_call_eel(self) -> None:
        self.assertIn("callEel('list_goals')", GOALS_JS)
        self.assertIn("callEel('get_goals_board')", GOALS_JS)
        self.assertIn("callEel('create_goal'", GOALS_JS)
        self.assertIn("callEel('delete_goal'", GOALS_JS)
        self.assertNotIn("eel.list_goals", GOALS_JS)
        self.assertNotIn("eel.get_goals_board", GOALS_JS)
        self.assertIn("sourceIsOpen('goalsTab')", GOALS_JS)
        self.assertIn("widget-source--active", UTILS)
        self.assertIn("data?.ok === false", GLANCE_TILES)
        self.assertIn("action: openWorkAction(key),", GLANCE_TILES)
        self.assertIn(".home-work-body .goals-layout", STYLE)
        self.assertIn("repeat(2, minmax(0, 1fr))", STYLE)
        self.assertNotIn("repeat(4, minmax(14rem, 1fr))", STYLE)
        self.assertIn("goal-horizon", GOALS_JS)
        self.assertIn("goal-add-more", GOALS_JS)
        self.assertIn("goal-remove", GOALS_JS)
        self.assertNotIn("Finish a to-do attached", GOALS_JS)
        self.assertIn(".home-work-body .goals-page-head {\n    display: none;", STYLE)
        self.assertIn("glance-meter", GLANCE_TILES)
        self.assertIn("glance-meter", STYLE)

    def test_home_and_settings_clicks_stay_off_the_brain(self) -> None:
        appearance = (ROOT / "web" / "js" / "appearance.js").read_text(encoding="utf-8")
        self.assertIn("paintedPageId", HOME_RUNTIME)
        self.assertIn("void refreshHomeData()", HOME_RUNTIME)
        self.assertIn("{ force: true }", HOME_RUNTIME)
        self.assertIn("scheduleSettingsExtras", SETTINGS_JS)
        shown = SETTINGS_JS.split("export function onSettingsTabShown")[1].split("function paintIcloudStatus")[0]
        self.assertNotIn("refreshClunyLiveStats", shown)
        self.assertNotIn("refreshClunyHealth", shown)
        self.assertNotIn("get_cluny_health", GLANCE_TILES)
        self.assertIn("persistTimer", appearance)
        self.assertNotIn("const saved = await eel.save_appearance_settings", appearance)
        self.assertIn("scheduleHomeRefresh", HOME_RUNTIME)
        self.assertIn("void scheduleHomeRefresh()", HOME_RUNTIME)
        self.assertIn("sourceIsOpen", UTILS)
        self.assertIn("widget-source--active", UTILS)
        self.assertNotIn("get_pending_recovery", (ROOT / "web" / "js" / "daily_checklist.js").read_text(encoding="utf-8"))
        self.assertNotIn("web/js/review.js", (ROOT / "setup.py").read_text(encoding="utf-8"))
        journal = (ROOT / "web" / "js" / "journal.js").read_text(encoding="utf-8")
        self.assertIn("callEel('get_recent_entries'", journal)
        self.assertIn("void mod?.loadPastEntries?.()", TABS)
        self.assertNotIn("await mod?.loadPastEntries?.()", TABS)
