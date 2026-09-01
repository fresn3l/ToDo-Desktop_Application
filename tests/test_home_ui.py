"""Home shell markup: two main tabs, widget sources, first-install catalog."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
TABS = (ROOT / "web" / "js" / "tabs.js").read_text(encoding="utf-8")
HOME_JS = (ROOT / "web" / "js" / "home_layout.js").read_text(encoding="utf-8")
HOME_RUNTIME = (ROOT / "web" / "js" / "home.js").read_text(encoding="utf-8")
TODAY_JS = (ROOT / "web" / "js" / "today.js").read_text(encoding="utf-8")
GLANCE_JS = (ROOT / "web" / "js" / "glance.js").read_text(encoding="utf-8")
CAL_JS = (ROOT / "web" / "js" / "calendar.js").read_text(encoding="utf-8")
UTILS = (ROOT / "web" / "js" / "utils.js").read_text(encoding="utf-8")
SETTINGS_JS = (ROOT / "web" / "js" / "settings.js").read_text(encoding="utf-8")
STYLE = (ROOT / "web" / "style.css").read_text(encoding="utf-8")
SWIFT = (ROOT / "macos" / "KosistenzWindow.swift").read_text(encoding="utf-8")
NATIVE_MAC = (ROOT / "native_mac.py").read_text(encoding="utf-8")


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
            "weatherSource",
            "focusSource",
            "countdownSource",
            "habitsSource",
            "heatmapSource",
            "dayBriefSource",
            "countersSource",
            "readingSource",
            "wordTab",
            "checklistTab",
        ):
            self.assertIn(f'id="{source_id}"', INDEX)
            self.assertIn("widget-source", INDEX)
        self.assertIn('id="wordCard"', INDEX)
        self.assertIn('id="checklistWizard"', INDEX)

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
            "weather",
            "focus",
            "countdown",
            "habits",
            "heatmap",
            "day_brief",
            "counters",
            "reading",
            "word",
            "checklist",
        ):
            self.assertIn(f"{kind}:", HOME_JS)
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

    def test_live_home_drags_from_title_without_edit(self) -> None:
        self.assertIn("home-live-copy", INDEX)
        self.assertIn("home-widget-handle", HOME_RUNTIME)
        self.assertIn("closest('.home-widget-chrome')", HOME_RUNTIME)
        self.assertIn("closest('.home-widget-body')", HOME_RUNTIME)
        self.assertIn("window.addEventListener('pointermove', moveDrag)", HOME_RUNTIME)
        self.assertIn("window.addEventListener('mousemove', moveDrag)", HOME_RUNTIME)
        begin = HOME_RUNTIME.split("const beginDrag")[1].split("const moveDrag")[0]
        self.assertNotIn("if (!editing)", begin)
        click = HOME_RUNTIME.split("addEventListener('click'")[-1].split("const beginDrag")[0]
        self.assertIn("if (!editing) return;", click)

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
        self.assertIn("setPageColorSlot", SETTINGS_JS)

    def test_home_widgets_are_dense_and_scroll_the_page(self) -> None:
        self.assertIn("--home-row: 5.75rem", STYLE)
        self.assertIn("grid-auto-rows: var(--home-row)", STYLE)
        self.assertIn("min-height: 0", STYLE)
        self.assertIn("overflow-y: auto", STYLE)
        self.assertIn("padding-bottom: 88px", STYLE)
        self.assertIn('sizes: [[1, 1]', HOME_JS)
        self.assertIn("default: [1, 1]", HOME_JS)
        self.assertIn("default: [2, 1]", HOME_JS)
        self.assertIn('[data-w="1"][data-h="1"]', STYLE)
        self.assertIn(".home-widget-chrome", STYLE)
        self.assertIn("linear-gradient(to bottom", STYLE)
        self.assertIn("countdown-days", GLANCE_JS)

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
