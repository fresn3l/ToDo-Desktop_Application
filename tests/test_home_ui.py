"""Home shell markup: two main tabs, widget sources, first-install catalog."""

from __future__ import annotations

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
STYLE = (ROOT / "web" / "style.css").read_text(encoding="utf-8")
SWIFT = (ROOT / "macos" / "KosistenzWindow.swift").read_text(encoding="utf-8")
NATIVE_MAC = (ROOT / "native_mac.py").read_text(encoding="utf-8")


class HomeUiTests(unittest.TestCase):
    def test_sidebar_is_home_journal_and_calendar(self) -> None:
        self.assertIn('data-tab="home"', INDEX)
        self.assertIn('data-tab="journal"', INDEX)
        self.assertIn('data-tab="calendar"', INDEX)
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

    def test_edit_home_controls_exist(self) -> None:
        for needle in (
            "homeEditBtn",
            "homeGrid",
            "homeGridAbove",
            "homeCheckinBand",
            "homeCheckinBody",
            "homePages",
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

    def test_js_catalog_matches_folded_tabs(self) -> None:
        for kind in (
            "todo",
            "today_calendar",
            "workout",
            "goals",
            "allwork",
            "analytics",
            "timeline",
            "weather",
            "focus",
            "countdown",
            "habits",
            "heatmap",
            "day_brief",
            "counters",
            "reading",
            "word",
            "cluny",
        ):
            self.assertIn(f"{kind}:", HOME_JS)
        self.assertNotIn("journal:", HOME_JS)
        self.assertNotIn("checklist:", HOME_JS)
        self.assertNotIn("settings:", HOME_JS)

    def test_calendar_month_year_markup(self) -> None:
        for needle in ("calViewGroup", "calMonthGrid", "calYearGrid", "calFillWeek", "calPrevWeek"):
            self.assertIn(f'id="{needle}"', INDEX)
        self.assertIn('data-cal-view="week"', INDEX)
        self.assertIn('data-cal-view="month"', INDEX)
        self.assertIn('data-cal-view="year"', INDEX)
        self.assertIn('id="calFillWeek" class="btn-primary is-hidden"', INDEX)
        self.assertIn("calView = 'month'", CAL_JS)
        self.assertIn("openWeekForDate", CAL_JS)
        self.assertIn("eel.get_month", CAL_JS)
        self.assertIn("eel.get_year", CAL_JS)
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
        self.assertIn("openHomeWork(card.getAttribute('data-kind')", HOME_RUNTIME)
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
        self.assertIn("function todoHtml", GLANCE_TILES)
        self.assertIn("function countdownHtml", GLANCE_TILES)
        self.assertIn("function readingHtml", GLANCE_TILES)
        self.assertIn("function workoutHtml", GLANCE_TILES)
        self.assertIn("function goalsHtml", GLANCE_TILES)
        self.assertIn("function allworkHtml", GLANCE_TILES)
        self.assertIn("function heatmapHtml", GLANCE_TILES)
        self.assertIn("function dayBriefHtml", GLANCE_TILES)
        self.assertIn("function analyticsHtml", GLANCE_TILES)
        self.assertIn("function timelineHtml", GLANCE_TILES)
        self.assertIn("function posterHtml", GLANCE_TILES)
        self.assertIn("function shellHtml", GLANCE_TILES)
        self.assertIn("glance_copy.js", GLANCE_TILES)
        self.assertIn("get_work_board", GLANCE_TILES)
        self.assertIn("get_today_home", GLANCE_TILES)
        self.assertIn("get_weather_forecast", GLANCE_TILES)
        self.assertIn("get_word_of_the_day", GLANCE_TILES)
        self.assertIn("get_heatmap", GLANCE_TILES)
        self.assertIn("get_analytics", GLANCE_TILES)
        self.assertIn("get_timeline_day", GLANCE_TILES)
        self.assertIn("get_cluny_inbox", GLANCE_TILES)
        self.assertIn("function clunyHtml", GLANCE_TILES)
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
        self.assertIn("keep_daily_focus", GLANCE_TILES)
        self.assertIn("todo-finish", GLANCE_TILES)
        self.assertIn("habit-tick", GLANCE_TILES)
        self.assertIn("counter-tap", GLANCE_TILES)
        self.assertIn("focus-keep", GLANCE_TILES)
        self.assertIn("dayPart", GLANCE_TILES)
        self.assertIn("syncHomeDayPart", HOME_RUNTIME)
        self.assertIn(".glance-action", STYLE)
        self.assertIn(".glance-label", STYLE)
        self.assertIn(".home-widget.is-source", STYLE)
        self.assertNotIn("on the clock", GLANCE_TILES)
        self.assertNotIn("waiting to be dated", GLANCE_TILES)
        self.assertIn("1 event today.", (ROOT / "web" / "js" / "glance_copy.js").read_text(encoding="utf-8"))
        self.assertIn("Journal and timer still available.", (ROOT / "web" / "js" / "glance_copy.js").read_text(encoding="utf-8"))
        self.assertIn("unscheduled", (ROOT / "web" / "js" / "glance_copy.js").read_text(encoding="utf-8"))

    def test_live_home_opens_work_edit_home_moves(self) -> None:
        self.assertIn("home-live-copy", INDEX)
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
        self.assertIn("eel.resize_home_widget(page.id, id, w | 0, h | 0)", HOME_RUNTIME)
        self.assertIn("beginResize", HOME_RUNTIME)
        self.assertIn("cursor: nwse-resize", STYLE)
        self.assertIn("Drag a corner or edge", INDEX)

    def test_home_widget_refresh_continues_after_one_failure(self) -> None:
        refresh = HOME_RUNTIME.split("async function refreshKinds")[1].split("function paintPages")[0]
        self.assertIn("const run = async (fn)", refresh)
        self.assertIn("await run(onWorkoutTabShown)", refresh)
        self.assertIn("await run(onTodoTabShown)", refresh)
        self.assertIn("await run(refreshWeather)", refresh)
        self.assertIn("await run(refreshDayBrief)", refresh)
        self.assertIn("await run(onWordTabShown)", refresh)

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

    def test_calendar_tab_uses_full_width_and_taller_cells(self) -> None:
        self.assertIn("html[data-page='calendar'] .tab-content.active", STYLE)
        self.assertIn("max-width: none", STYLE)
        self.assertIn("min-height: 6.5rem", STYLE)
        self.assertIn("minmax(0, 1fr) minmax(220px, 260px)", STYLE)

    def test_home_shows_page_title_and_sidebar_pages(self) -> None:
        self.assertIn('id="homePageTitle"', INDEX)
        self.assertIn("home-title-strip", INDEX)
        self.assertIn('id="homeNavPages"', INDEX)
        self.assertIn("data-home-page", HOME_RUNTIME)
        self.assertIn("paintSidebar", HOME_RUNTIME)
        self.assertIn("homePageId", TABS)
        self.assertIn("clearHomePageColors", TABS)

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
        self.assertIn("--home-row: var(--row-h, 88px)", STYLE)
        self.assertIn("grid-auto-rows: var(--home-row)", STYLE)
        self.assertIn("min-height: 0", STYLE)
        self.assertIn("overflow-y: auto", STYLE)
        self.assertIn("padding-bottom: 88px", STYLE)
        self.assertIn('sizes: [[1, 1]', HOME_JS)
        self.assertIn("default: [2, 2]", HOME_JS)
        self.assertIn("default: [2, 1]", HOME_JS)
        self.assertIn('[data-w="1"][data-h="1"]', STYLE)
        self.assertIn(".home-widget-chrome", STYLE)
        self.assertIn("countdown-days", GLANCE_JS)
        tokens = (ROOT / "web" / "tokens.css").read_text(encoding="utf-8")
        self.assertIn("--row-h: 88px", tokens)
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
        self.assertIn("loadLayout().then(() => renderHome())", HOME_RUNTIME)
        self.assertIn("weather-place-form.is-collapsed", STYLE)
        self.assertIn("pointer-events: none", STYLE)

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
        self.assertIn("setupCluny", app)
        self.assertIn("if (set.has('cluny'))", HOME_RUNTIME)
        self.assertIn("kosistenz:open-cluny", HOME_RUNTIME)
        self.assertIn("ensureHomeWidget('cluny')", HOME_RUNTIME)
        self.assertNotIn("ensureHomeWidget('journal')", HOME_RUNTIME)
        self.assertIn("ask_cluny", cluny)
        self.assertIn("accept_cluny_proposal", cluny)
        self.assertIn("dayBriefOpenCluny", day)
        self.assertIn("kosistenz:open-cluny", day)
        self.assertIn("cluny-chip", STYLE)
        self.assertIn("kind === 'cluny'", GLANCE_TILES)
        self.assertIn('data-cluny-prompt="What do I have to do today?"', INDEX)
        self.assertIn('data-cluny-prompt="What should I do with my free time?"', INDEX)
        self.assertIn("promptCluny", cluny)
        self.assertIn("promptCluny", HOME_RUNTIME)
        self.assertIn("cluny-ask", GLANCE_TILES)
        self.assertIn("w-cluny", HOME_RUNTIME)
