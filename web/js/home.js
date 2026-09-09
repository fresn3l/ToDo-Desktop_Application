/**
 * Customizable Home — snap-to-grid widgets, extra pages, Edit Home mode.
 */

import * as utils from './utils.js';
import { WIDGET_CATALOG, GRID_COLUMNS, catalogList, canPlace, snapCell, pickResize, isFirstHomePage, widgetRegion, widgetsInRegion } from './home_layout.js';
import { mountGlance, refreshGlances, runGlanceAction, syncHomeDayPart } from './glance_tiles.js';
import { getAppearance, onAppearanceChange, applyAppearance, applyAppearanceOverlay, notifyNativeTab } from './appearance.js';
import { bootFeature, loadOnce } from './lazy.js';

const FALLBACK_LAYOUT = {
    columns: 4,
    active_page_id: 'local-home',
    pages: [
        {
            id: 'local-home',
            name: 'Home',
            widgets: [
                { id: 'w-todo', kind: 'todo', x: 0, y: 0, w: 2, h: 2, region: 'above' },
                { id: 'w-today', kind: 'today_calendar', x: 2, y: 0, w: 2, h: 2, region: 'above' },
                { id: 'w-weather', kind: 'weather', x: 0, y: 0, w: 2, h: 1 },
                { id: 'w-word', kind: 'word', x: 2, y: 0, w: 2, h: 1 },
                { id: 'w-day', kind: 'day_brief', x: 0, y: 1, w: 2, h: 2 },
                { id: 'w-cluny', kind: 'cluny', x: 2, y: 1, w: 2, h: 2 },
            ],
        },
        {
            id: 'local-week',
            name: 'Week',
            widgets: [
                { id: 'w-workout', kind: 'workout', x: 0, y: 0, w: 2, h: 2 },
                { id: 'w-goals', kind: 'goals', x: 2, y: 0, w: 2, h: 2 },
                { id: 'w-allwork', kind: 'allwork', x: 0, y: 2, w: 2, h: 2 },
                { id: 'w-habits', kind: 'habits', x: 2, y: 2, w: 2, h: 2 },
                { id: 'w-heatmap', kind: 'heatmap', x: 0, y: 4, w: 2, h: 1 },
                { id: 'w-reading', kind: 'reading', x: 2, y: 4, w: 2, h: 1 },
                { id: 'w-unplaced', kind: 'unplaced', x: 0, y: 5, w: 2, h: 2 },
                { id: 'w-dues', kind: 'dues', x: 2, y: 5, w: 2, h: 2 },
                { id: 'w-free', kind: 'free_today', x: 0, y: 7, w: 2, h: 1 },
                { id: 'w-now', kind: 'now_next', x: 2, y: 7, w: 2, h: 1 },
            ],
        },
    ],
};

let layout = FALLBACK_LAYOUT;
let editing = false;
let drag = null;
let workKind = null;
let workOpener = null;
let workHideTimer = 0;
let checkinForceOpen = null;
let checkinSlotOverride = '';
let lastViewedDone = false;
let lastViewedSlot = 'morning';

function rack() {
    return document.getElementById('widgetSourceRack');
}

function activePage() {
    if (!layout) return null;
    return layout.pages.find((page) => page.id === layout.active_page_id) || layout.pages[0];
}

function firstPageActive() {
    return isFirstHomePage(layout, activePage());
}

function homeWidgetCards() {
    return document.querySelectorAll('#homeGridAbove .home-widget, #homeGrid .home-widget');
}

async function persist(next) {
    if (typeof eel === 'undefined' || !eel.save_home_layout) {
        layout = next;
        return layout;
    }
    layout = await eel.save_home_layout(next)();
    return layout;
}

async function fetchHomeBoot(pageId) {
    try {
        if (typeof eel !== 'undefined' && eel.get_home_boot) {
            return await eel.get_home_boot(pageId || '')();
        }
    } catch (err) {
        console.warn(err);
    }
    return { layout: layout || structuredClone(FALLBACK_LAYOUT), glances: {}, checkin: null };
}

async function loadLayout() {
    try {
        if (typeof eel !== 'undefined' && eel.get_home_layout) {
            layout = await eel.get_home_layout()();
            return layout;
        }
    } catch (err) {
        console.warn(err);
    }
    if (!layout || !layout.pages?.length) {
        layout = structuredClone(FALLBACK_LAYOUT);
    }
    return layout;
}

const KIND_FEATURE = {
    today_calendar: 'today',
    todo: 'todo',
    allwork: 'allwork',
    workout: 'workout',
    goals: 'goals',
    analytics: 'analytics',
    timeline: 'timeline',
    weather: 'weather',
    focus: 'glance',
    countdown: 'glance',
    habits: 'glance',
    heatmap: 'heatmap',
    day_brief: 'day_brief',
    counters: 'counters',
    reading: 'reading',
    word: 'word',
    cluny: 'cluny',
    now_next: 'today',
    unplaced: 'allwork',
    dues: 'todo',
    free_today: 'today',
};

async function ensureWork(kind) {
    return loadOnce(`work:${kind}`, async () => {
        const feature = KIND_FEATURE[kind];
        if (feature) await bootFeature(feature);
        if (kind === 'today_calendar' || kind === 'now_next' || kind === 'free_today') {
            const m = await import('./today.js');
            m.setupToday();
            return () => m.onTodayTabShown().then(() => m.refreshToday());
        }
        if (kind === 'todo' || kind === 'dues') {
            const m = await import('./todo.js');
            m.setupTodo();
            return () => m.onTodoTabShown();
        }
        if (kind === 'allwork' || kind === 'unplaced') {
            const m = await import('./all_work.js');
            m.setupAllWork();
            return () => m.onAllWorkTabShown();
        }
        if (kind === 'workout') {
            const m = await import('./workouts.js');
            m.setupWorkouts();
            return () => m.onWorkoutTabShown();
        }
        if (kind === 'goals') {
            const m = await import('./goals.js');
            m.setupGoals();
            return () => m.onGoalsTabShown();
        }
        if (kind === 'analytics') {
            const m = await import('./analytics.js');
            m.setupAnalytics();
            return () => m.onAnalyticsTabShown();
        }
        if (kind === 'timeline') {
            const m = await import('./timeline.js');
            m.setupTimeline();
            return () => m.onTimelineTabShown();
        }
        if (kind === 'weather') {
            const m = await import('./weather.js');
            m.setupWeather();
            return () => m.refreshWeather();
        }
        if (kind === 'focus' || kind === 'countdown' || kind === 'habits') {
            const m = await import('./glance.js');
            m.setupGlance();
            if (kind === 'focus') return () => m.refreshFocus();
            if (kind === 'countdown') return () => m.refreshCountdown();
            return () => m.refreshHabits();
        }
        if (kind === 'heatmap') {
            const m = await import('./heatmap.js');
            m.setupHeatmap();
            return () => m.refreshHeatmap();
        }
        if (kind === 'day_brief') {
            const m = await import('./day_brief.js');
            m.setupDayBrief();
            return () => m.refreshDayBrief();
        }
        if (kind === 'counters') {
            const m = await import('./counters.js');
            m.setupCounters();
            return () => m.refreshCounters();
        }
        if (kind === 'reading') {
            const m = await import('./reading.js');
            m.setupReading();
            return () => m.refreshReading();
        }
        if (kind === 'word') {
            const m = await import('./word.js');
            m.setupWord();
            return () => m.onWordTabShown();
        }
        if (kind === 'cluny') {
            const m = await import('./cluny.js');
            m.setupCluny();
            return () => m.onClunyTabShown();
        }
        return async () => {};
    });
}

function returnSources() {
    const host = rack();
    if (!host) return;
    document.querySelectorAll('.home-widget-body > .widget-source, #homeWorkBody > .widget-source, #homeCheckinBody > .widget-source').forEach((node) => {
        node.classList.remove('widget-source--active');
        host.appendChild(node);
    });
}

function workLayer() {
    return document.getElementById('homeWorkLayer');
}

function workPanel() {
    return document.getElementById('homeWorkPanel');
}

function isWorkOpen() {
    const layer = workLayer();
    return !!(layer && !layer.hidden && layer.classList.contains('is-open'));
}

function reduceMotion() {
    return Boolean(window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches);
}

function clearSourceTile() {
    document.querySelectorAll('.home-widget.is-source').forEach((node) => node.classList.remove('is-source'));
}

function markSourceTile(tile) {
    clearSourceTile();
    tile?.classList.add('is-source');
}

function tileBox(tile, layer) {
    if (!tile || !layer || !document.contains(tile)) return null;
    const host = layer.getBoundingClientRect();
    const rect = tile.getBoundingClientRect();
    if (rect.width < 8 || rect.height < 8) return null;
    return {
        top: rect.top - host.top,
        left: rect.left - host.left,
        width: rect.width,
        height: rect.height,
        radius: getComputedStyle(tile).borderRadius || '14px',
    };
}

function settledBox(layer) {
    const host = layer.getBoundingClientRect();
    const width = Math.min(760, Math.max(280, host.width - 36));
    return {
        top: 10,
        left: Math.max(10, host.width - 10 - width),
        width,
        height: Math.max(160, host.height - 20),
        radius: '18px',
    };
}

function applyPanelBox(panel, box) {
    if (!panel || !box) return;
    panel.style.top = `${box.top}px`;
    panel.style.left = `${box.left}px`;
    panel.style.width = `${box.width}px`;
    panel.style.height = `${box.height}px`;
    panel.style.borderRadius = box.radius;
}

function clearPanelBox(panel) {
    if (!panel) return;
    panel.style.top = '';
    panel.style.left = '';
    panel.style.width = '';
    panel.style.height = '';
    panel.style.borderRadius = '';
    panel.style.transition = '';
}

function mountWorkSource(kind) {
    const spec = WIDGET_CATALOG[kind];
    const body = document.getElementById('homeWorkBody');
    const title = document.getElementById('homeWorkTitle');
    const kicker = document.getElementById('homeWorkKicker');
    if (title) title.textContent = spec?.label || kind;
    if (kicker) kicker.textContent = 'Home';
    if (!spec || !body) return false;
    const source = document.getElementById(spec.source);
    if (!source) {
        body.innerHTML = `<p class="checklist-error">Could not load ${spec.label}.</p>`;
        return false;
    }
    body.appendChild(source);
    source.classList.add('widget-source--active');
    return true;
}

export function closeHomeWork(immediate = false) {
    const layer = workLayer();
    const panel = workPanel();
    if (!layer) return;
    const opener = workOpener;
    const from = tileBox(opener, layer);
    workKind = null;
    workOpener = null;
    document.documentElement.classList.remove('home-work-open');
    document.getElementById('homeShell')?.classList.remove('is-working');
    document.getElementById('homeShell')?.removeAttribute('inert');
    layer.classList.remove('is-open');
    const finish = () => {
        if (layer.classList.contains('is-open')) return;
        layer.classList.add('is-hidden');
        layer.hidden = true;
        clearPanelBox(panel);
        clearSourceTile();
        returnSources();
        if (opener && document.contains(opener)) {
            try {
                opener.focus({ preventScroll: true });
            } catch (_) {
                opener.focus();
            }
        }
    };
    if (workHideTimer) {
        window.clearTimeout(workHideTimer);
        workHideTimer = 0;
    }
    if (immediate || reduceMotion() || !from || !panel) {
        finish();
        return;
    }
    panel.style.transition = '';
    applyPanelBox(panel, from);
    workHideTimer = window.setTimeout(() => {
        workHideTimer = 0;
        finish();
    }, 420);
}

export async function openHomeWork(kind, opener) {
    const spec = WIDGET_CATALOG[kind];
    if (!spec || editing) return;
    closeHomeWork(true);
    workKind = kind;
    workOpener = opener || document.querySelector(`#homeGridAbove .home-widget[data-kind="${kind}"], #homeGrid .home-widget[data-kind="${kind}"]`);
    const layer = workLayer();
    const panel = workPanel();
    if (!layer || !panel) return;
    mountWorkSource(kind);
    layer.hidden = false;
    layer.classList.remove('is-hidden');
    layer.setAttribute('data-kind', kind);
    document.documentElement.classList.add('home-work-open');
    document.getElementById('homeShell')?.classList.add('is-working');
    document.getElementById('homeShell')?.setAttribute('inert', '');
    markSourceTile(workOpener);
    const from = tileBox(workOpener, layer);
    const to = settledBox(layer);
    if (from && !reduceMotion()) {
        panel.style.transition = 'none';
        applyPanelBox(panel, from);
        layer.offsetHeight;
        panel.style.transition = '';
        requestAnimationFrame(() => {
            applyPanelBox(panel, to);
            layer.classList.add('is-open');
        });
    } else {
        applyPanelBox(panel, to);
        requestAnimationFrame(() => layer.classList.add('is-open'));
    }
    requestAnimationFrame(() => {
        const closeBtn = document.getElementById('homeWorkClose');
        try {
            closeBtn?.focus({ preventScroll: true });
        } catch (_) {
            closeBtn?.focus();
        }
    });
    await refreshKinds([kind]);
}

async function refreshKinds(kinds, glances) {
    const set = new Set(kinds);
    const run = async (fn) => {
        try {
            await fn();
        } catch (err) {
            console.error(err);
        }
    };
    if (workKind) {
        const refresh = await ensureWork(workKind);
        await run(refresh);
    }
    await run(() => refreshGlances([...set], glances));
}

const HOME_NAV_ICON = '<svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M4.5 11 12 4.5 19.5 11v8a1.5 1.5 0 0 1-1.5 1.5h-4v-5h-4v5H6A1.5 1.5 0 0 1 4.5 19v-8Z"/></svg>';
const PAGE_NAV_ICON = '<svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><rect x="5" y="4.5" width="14" height="15" rx="1.5"/><path d="M8 9h8M8 12.5h8M8 16h5"/></svg>';

function paintPages() {
    const el = document.getElementById('homePages');
    if (!el || !layout) return;
    el.innerHTML = layout.pages
        .map((page) => {
            const on = page.id === layout.active_page_id;
            return `<button type="button" class="home-page-chip${on ? ' is-selected' : ''}" data-page="${utils.escapeHtml(page.id)}" aria-selected="${on ? 'true' : 'false'}">${utils.escapeHtml(page.name)}</button>`;
        })
        .join('');
    paintSidebar();
    paintTitle();
    syncPageColors();
}

function paintTitle() {
    const page = activePage();
    const name = page?.name || 'Home';
    const titleEl = document.getElementById('homePageTitle');
    if (titleEl) titleEl.textContent = name;
    document.documentElement.setAttribute('data-home-page', page?.id || '');
    if (document.documentElement.getAttribute('data-page') === 'home' || document.getElementById('homeTab')?.classList.contains('active')) {
        document.title = `${name} · Kosistenz`;
        const crumb = document.getElementById('pageCrumb');
        if (crumb) crumb.textContent = name;
        notifyNativeTab('home', name);
    }
}

function paintSidebar() {
    const el = document.getElementById('homeNavPages');
    if (!el || !layout) return;
    const onHome = document.documentElement.getAttribute('data-page') === 'home';
    el.innerHTML = layout.pages
        .map((page, index) => {
            const selected = onHome && page.id === layout.active_page_id;
            const icon = index === 0 ? HOME_NAV_ICON : PAGE_NAV_ICON;
            return `<button type="button" class="nav-item${selected ? ' active' : ''}" data-tab="home" data-home-page="${utils.escapeHtml(page.id)}" aria-current="${selected ? 'page' : 'false'}">${icon}<span class="nav-label">${utils.escapeHtml(page.name)}</span></button>`;
        })
        .join('');
}

function syncPageColors() {
    const onHome = document.getElementById('homeTab')?.classList.contains('active');
    if (!onHome) return;
    applyAppearanceOverlay(activePage()?.colors || {});
}

export function clearHomePageColors() {
    applyAppearance(getAppearance());
}

function paintCatalog() {
    const el = document.getElementById('homeCatalog');
    if (!el) return;
    const page = activePage();
    const used = new Set((page?.widgets || []).map((item) => item.kind));
    el.innerHTML = catalogList()
        .map((spec) => {
            const disabled = used.has(spec.kind) ? ' disabled' : '';
            return `<button type="button" class="btn-ghost home-catalog-btn" data-kind="${spec.kind}"${disabled}>${utils.escapeHtml(spec.label)}</button>`;
        })
        .join('');
}

function widgetCardHtml(item, live) {
    const spec = WIDGET_CATALOG[item.kind] || { label: item.kind };
    const label = utils.escapeHtml(spec.label);
    return `
        <article class="home-widget" data-id="${utils.escapeHtml(item.id)}" data-kind="${utils.escapeHtml(item.kind)}" data-w="${item.w}" data-h="${item.h}" style="grid-column:${item.x + 1} / span ${item.w};grid-row:${item.y + 1} / span ${item.h}" role="${live ? 'button' : 'group'}" tabindex="${live ? '0' : '-1'}" aria-label="${live ? `Open ${label}` : label}">
            <div class="home-widget-chrome">
                <span class="home-widget-handle"><span class="home-widget-grip" aria-hidden="true"></span>${label}</span>
                <span class="home-widget-size">${item.w}×${item.h}</span>
                <button type="button" class="btn-ghost home-widget-btn" data-act="remove">Remove</button>
            </div>
            <div class="home-widget-body"></div>
            <button type="button" class="home-widget-resize" data-resize="e" aria-label="Resize width"></button>
            <button type="button" class="home-widget-resize" data-resize="s" aria-label="Resize height"></button>
            <button type="button" class="home-widget-resize" data-resize="se" aria-label="Resize"></button>
        </article>`;
}

function paintOneGrid(grid, widgets, live) {
    if (!grid) return;
    grid.innerHTML = widgets.map((item) => widgetCardHtml(item, live)).join('');
    widgets.forEach((item) => {
        const card = grid.querySelector(`.home-widget[data-id="${item.id}"]`);
        mountGlance(item.kind, card?.querySelector('.home-widget-body'), card);
    });
}

function paintGrid() {
    const above = document.getElementById('homeGridAbove');
    const below = document.getElementById('homeGrid');
    const band = document.getElementById('homeCheckinBand');
    if (!below || !layout) return;
    returnSources();
    const page = activePage();
    const first = firstPageActive();
    const live = !editing;
    const aboveWidgets = first ? widgetsInRegion(page, 'above', true) : [];
    const belowWidgets = first ? widgetsInRegion(page, 'below', true) : (page?.widgets || []);
    if (above) {
        above.classList.toggle('is-absent', !first);
        paintOneGrid(above, aboveWidgets, live);
        above.classList.toggle('is-empty-drop', first && aboveWidgets.length === 0);
    }
    if (band) {
        band.hidden = !first;
        if (!first) band.classList.remove('is-open');
    }
    paintOneGrid(below, belowWidgets, live);
}

function parkCheckin() {
    const source = document.getElementById('checklistTab');
    const host = rack();
    if (!source || !host) return;
    source.classList.remove('widget-source--active');
    host.appendChild(source);
}

function viewedCheckinSlot(info) {
    return checkinSlotOverride || info?.slot || lastViewedSlot || 'morning';
}

function paintCheckinChrome(info, slot, done, open) {
    const kicker = document.getElementById('homeCheckinKicker');
    const title = document.getElementById('homeCheckinTitle');
    const status = document.getElementById('homeCheckinStatus');
    const toggle = document.getElementById('homeCheckinToggle');
    const other = document.getElementById('homeCheckinOther');
    const morningLabel = 'Morning check-in';
    const eveningLabel = 'Evening check-in';
    const label = slot === 'evening' ? eveningLabel : morningLabel;
    if (kicker) kicker.textContent = slot === 'evening' ? 'Evening' : 'Morning';
    if (title) title.textContent = done ? `${label} done` : label;
    if (status) {
        if (info?.morning_done && info?.evening_done) status.textContent = 'Morning and evening saved';
        else if (done) status.textContent = 'Saved today';
        else status.textContent = 'Not yet';
    }
    if (toggle) toggle.textContent = open ? 'Fold' : 'Open';
    if (other) {
        other.textContent = slot === 'evening' ? 'Morning instead' : 'Evening instead';
        other.hidden = false;
    }
}

async function syncCheckin(prefetched) {
    const band = document.getElementById('homeCheckinBand');
    const body = document.getElementById('homeCheckinBody');
    if (!band) return;
    if (!firstPageActive()) {
        band.hidden = true;
        band.classList.remove('is-open');
        parkCheckin();
        return;
    }
    band.hidden = false;
    let info = { slot: 'morning', morning_done: false, evening_done: false, current_done: false };
    try {
        if (prefetched) {
            info = prefetched;
        } else if (typeof eel !== 'undefined' && eel.get_home_checkin) {
            info = await eel.get_home_checkin()();
        }
    } catch (err) {
        console.error(err);
    }
    const slot = viewedCheckinSlot(info);
    lastViewedSlot = slot;
    const done = slot === 'evening' ? !!info.evening_done : !!info.morning_done;
    if (done && !lastViewedDone) checkinForceOpen = null;
    lastViewedDone = done;
    const open = checkinForceOpen == null ? !done : checkinForceOpen;
    band.classList.toggle('is-open', open);
    paintCheckinChrome(info, slot, done, open);
    if (!open) {
        parkCheckin();
        return;
    }
    const source = document.getElementById('checklistTab');
    if (source && body) {
        body.appendChild(source);
        source.classList.add('widget-source--active');
    }
    try {
        await bootFeature('checklist');
        const { setupDailyChecklist, openChecklistTemplate } = await import('./daily_checklist.js');
        await setupDailyChecklist();
        await openChecklistTemplate(slot);
    } catch (err) {
        console.error(err);
    }
}

function setEditing(on) {
    const next = !!on;
    if (next) closeHomeWork(true);
    editing = next;
    document.getElementById('homeShell')?.classList.toggle('is-editing', editing);
    document.getElementById('homeEditBar')?.classList.toggle('is-hidden', !editing);
    const howTo = document.querySelector('.home-live-copy');
    if (howTo) howTo.hidden = true;
    const editBtn = document.getElementById('homeEditBtn');
    if (editBtn) editBtn.textContent = editing ? 'Done' : 'Edit Home';
    if (editing) {
        paintCatalog();
    }
    const page = activePage();
    const first = firstPageActive();
    const above = document.getElementById('homeGridAbove');
    if (above) {
        above.classList.toggle('is-empty-drop', first && widgetsInRegion(page, 'above', true).length === 0);
    }
    homeWidgetCards().forEach((card) => {
        const spec = WIDGET_CATALOG[card.getAttribute('data-kind')] || { label: card.getAttribute('data-kind') };
        card.setAttribute('role', editing ? 'group' : 'button');
        card.tabIndex = editing ? -1 : 0;
        card.setAttribute('aria-label', editing ? spec.label : `Open ${spec.label}`);
    });
}

async function renderHome(pageId) {
    const boot = await fetchHomeBoot(pageId);
    if (boot.layout?.pages?.length) layout = boot.layout;
    paintPages();
    paintGrid();
    paintCatalog();
    syncHomeDayPart();
    const page = activePage();
    await refreshKinds((page?.widgets || []).map((item) => item.kind), boot.glances);
    await syncCheckin(boot.checkin);
}

async function refreshHomeData() {
    const boot = await fetchHomeBoot();
    if (boot.layout?.pages?.length) layout = boot.layout;
    const page = activePage();
    await refreshKinds((page?.widgets || []).map((item) => item.kind), boot.glances);
    await syncCheckin(boot.checkin);
}

async function run(action) {
    try {
        layout = await action();
        await renderHome();
    } catch (err) {
        console.error(err);
        utils.showErrorFeedback(err?.message || 'Could not update Home.');
        await renderHome();
    }
}

function bindHome() {
    const root = document.getElementById('homeTab');
    if (!root || root.dataset.homeReady === '1') return;
    root.dataset.homeReady = '1';

    document.getElementById('homePages')?.addEventListener('click', (e) => {
        const btn = e.target.closest('[data-page]');
        if (!btn) return;
        closeHomeWork(true);
        void renderHome(btn.getAttribute('data-page'));
    });

    document.getElementById('homeAddPageBtn')?.addEventListener('click', async () => {
        const name = await utils.askText({
            title: 'New page',
            message: 'Name this Home page.',
            value: `Page ${(layout?.pages.length || 0) + 1}`,
            ok: 'Add page',
        });
        if (name == null) return;
        void run(() => eel.add_home_page(name.trim())());
    });

    document.getElementById('homeRenamePageBtn')?.addEventListener('click', async () => {
        const page = activePage();
        if (!page) return;
        const name = await utils.askText({
            title: 'Rename page',
            message: 'New name for this Home page.',
            value: page.name,
            ok: 'Rename',
        });
        if (name == null) return;
        void run(() => eel.rename_home_page(page.id, name.trim())());
    });

    document.getElementById('homeDeletePageBtn')?.addEventListener('click', async () => {
        const page = activePage();
        if (!page || (layout?.pages.length || 0) <= 1) {
            utils.showErrorFeedback('Keep at least one Home page.');
            return;
        }
        const ok = await utils.askConfirm({
            title: 'Delete page',
            message: `Delete “${page.name}”? Widgets on it go away.`,
            ok: 'Delete',
            danger: true,
        });
        if (!ok) return;
        void run(() => eel.delete_home_page(page.id)());
    });

    document.getElementById('homeEditBtn')?.addEventListener('click', () => {
        setEditing(!editing);
    });
    document.getElementById('homeDoneEditBtn')?.addEventListener('click', () => {
        setEditing(false);
    });

    document.getElementById('homeCatalog')?.addEventListener('click', (e) => {
        const btn = e.target.closest('[data-kind]');
        if (!btn || btn.disabled) return;
        const page = activePage();
        if (!page) return;
        void run(() => eel.add_home_widget(page.id, btn.getAttribute('data-kind'))());
    });

    document.getElementById('homeBoard')?.addEventListener('click', (e) => {
        if (editing) {
            const btn = e.target.closest('[data-act]');
            if (!btn) return;
            const card = btn.closest('.home-widget');
            const page = activePage();
            if (!card || !page) return;
            const id = card.getAttribute('data-id');
            if (btn.getAttribute('data-act') === 'remove') {
                void run(() => eel.remove_home_widget(page.id, id)());
            }
            return;
        }
        const act = e.target.closest('[data-glance-act]');
        if (act) {
            e.preventDefault();
            e.stopPropagation();
            void runGlanceAction(act);
            return;
        }
        const card = e.target.closest('.home-widget');
        if (!card) return;
        void openHomeWork(card.getAttribute('data-kind'), card);
    });
    document.getElementById('homeBoard')?.addEventListener('keydown', (e) => {
        if (editing) return;
        if (e.key !== 'Enter' && e.key !== ' ') return;
        const card = e.target.closest('.home-widget');
        if (!card || e.target !== card) return;
        e.preventDefault();
        void openHomeWork(card.getAttribute('data-kind'), card);
    });

    document.getElementById('homeCheckinToggle')?.addEventListener('click', () => {
        const band = document.getElementById('homeCheckinBand');
        checkinForceOpen = !band?.classList.contains('is-open');
        void syncCheckin();
    });
    document.getElementById('homeCheckinOther')?.addEventListener('click', () => {
        checkinSlotOverride = viewedCheckinSlot() === 'evening' ? 'morning' : 'evening';
        checkinForceOpen = true;
        void syncCheckin();
    });

    const dropTargetAt = (clientX, clientY) => {
        const above = document.getElementById('homeGridAbove');
        const below = document.getElementById('homeGrid');
        if (!firstPageActive() || !above || above.classList.contains('is-absent')) {
            return { grid: below, region: 'below' };
        }
        const aboveRect = above.getBoundingClientRect();
        const belowRect = below.getBoundingClientRect();
        const mid = (aboveRect.bottom + belowRect.top) / 2;
        if (clientY < mid) return { grid: above, region: 'above' };
        return { grid: below, region: 'below' };
    };

    const findCard = (id) => document.querySelector(`#homeGridAbove .home-widget[data-id="${id}"], #homeGrid .home-widget[data-id="${id}"]`);

    const paintWidgetBox = (card, x, y, w, h) => {
        if (!card) return;
        card.style.gridColumn = `${x + 1} / span ${w}`;
        card.style.gridRow = `${y + 1} / span ${h}`;
        card.dataset.w = String(w);
        card.dataset.h = String(h);
        const label = card.querySelector('.home-widget-size');
        if (label) label.textContent = `${w}×${h}`;
    };

    const beginDrag = (e) => {
        if (!editing) return;
        if (e.button != null && e.button !== 0) return;
        if (e.target.closest('[data-act]')) return;
        if (e.target.closest('[data-resize]')) return;
        if (e.target.closest('.home-widget-body')) return;
        const chrome = e.target.closest('.home-widget-chrome');
        const card = e.target.closest('.home-widget');
        if (!chrome || !card) return;
        const page = activePage();
        const widget = page?.widgets.find((item) => item.id === card.getAttribute('data-id'));
        if (!widget) return;
        e.preventDefault();
        e.stopPropagation();
        drag = {
            type: 'move',
            id: widget.id,
            originX: widget.x,
            originY: widget.y,
            originRegion: widgetRegion(widget, firstPageActive()),
        };
        card.classList.add('is-dragging');
        card.draggable = false;
        card.dataset.dropX = String(widget.x);
        card.dataset.dropY = String(widget.y);
        card.dataset.dropRegion = widgetRegion(widget, firstPageActive());
        try {
            chrome.setPointerCapture?.(e.pointerId);
        } catch (_) {
            /* window listeners still track the drag if capture is unavailable */
        }
    };

    const beginResize = (e) => {
        if (!editing) return;
        if (e.button != null && e.button !== 0) return;
        const handle = e.target.closest('[data-resize]');
        const card = e.target.closest('.home-widget');
        if (!handle || !card) return;
        const page = activePage();
        const widget = page?.widgets.find((item) => item.id === card.getAttribute('data-id'));
        if (!widget) return;
        const axisRaw = handle.getAttribute('data-resize');
        const axis = axisRaw === 'e' ? 'x' : axisRaw === 's' ? 'y' : 'both';
        e.preventDefault();
        e.stopPropagation();
        drag = {
            type: 'resize',
            id: widget.id,
            originW: widget.w,
            originH: widget.h,
            axis,
        };
        card.classList.add('is-resizing');
        card.draggable = false;
        card.dataset.dropW = String(widget.w);
        card.dataset.dropH = String(widget.h);
        try {
            handle.setPointerCapture?.(e.pointerId);
        } catch (_) {
            /* window listeners still track the drag if capture is unavailable */
        }
    };

    const moveDrag = (e) => {
        if (!drag) return;
        if (!Number.isFinite(e.clientX) || !Number.isFinite(e.clientY)) return;
        const page = activePage();
        const widget = page?.widgets.find((item) => item.id === drag.id);
        const card = findCard(drag.id);
        if (!widget || !card) return;
        const first = firstPageActive();
        if (drag.type === 'resize') {
            const region = widgetRegion(widget, first);
            const occupied = widgetsInRegion(page, region, first);
            const grid = card.parentElement;
            const cell = snapCell(e.clientX, e.clientY, grid);
            const wantW = drag.axis === 'y' ? widget.w : Math.max(1, cell.x - widget.x + 1);
            const wantH = drag.axis === 'x' ? widget.h : Math.max(1, cell.y - widget.y + 1);
            const next = pickResize(widget.kind, widget, wantW, wantH, occupied, drag.axis);
            paintWidgetBox(card, widget.x, widget.y, next.w, next.h);
            card.dataset.dropW = String(next.w);
            card.dataset.dropH = String(next.h);
            return;
        }
        const target = dropTargetAt(e.clientX, e.clientY);
        if (target.grid && card.parentElement !== target.grid) {
            target.grid.appendChild(card);
            target.grid.classList.remove('is-empty-drop');
        }
        const occupied = widgetsInRegion(page, target.region, first);
        const cell = snapCell(e.clientX, e.clientY, target.grid);
        const x = Math.max(0, Math.min(GRID_COLUMNS - widget.w, cell.x));
        const y = Math.max(0, cell.y);
        if (canPlace(occupied, widget, x, y)) {
            paintWidgetBox(card, x, y, widget.w, widget.h);
            card.dataset.dropX = String(x);
            card.dataset.dropY = String(y);
            card.dataset.dropRegion = target.region;
        }
    };

    const endDrag = () => {
        if (!drag) return;
        const page = activePage();
        const id = drag.id;
        const type = drag.type;
        const originX = drag.originX;
        const originY = drag.originY;
        const originW = drag.originW;
        const originH = drag.originH;
        const originRegion = drag.originRegion;
        const card = findCard(id);
        const x = Number(card?.dataset.dropX);
        const y = Number(card?.dataset.dropY);
        const w = Number(card?.dataset.dropW);
        const h = Number(card?.dataset.dropH);
        const region = card?.dataset.dropRegion || originRegion || 'below';
        drag = null;
        card?.classList.remove('is-dragging');
        card?.classList.remove('is-resizing');
        const widget = page?.widgets.find((item) => item.id === id);
        if (type === 'resize') {
            if (!page || !widget || Number.isNaN(w) || Number.isNaN(h) || (w === originW && h === originH)) {
                if (widget) paintWidgetBox(card, widget.x, widget.y, widget.w, widget.h);
                return;
            }
            void run(() => eel.resize_home_widget(page.id, id, w | 0, h | 0)());
            return;
        }
        const regionChanged = region !== originRegion;
        if (!page || Number.isNaN(x) || Number.isNaN(y) || (x === originX && y === originY && !regionChanged)) {
            if (card && widget) paintWidgetBox(card, widget.x, widget.y, widget.w, widget.h);
            return;
        }
        void run(() => eel.move_home_widget(page.id, id, x | 0, y | 0, region)());
    };

    const onPointerDown = (e) => {
        if (e.target.closest('[data-resize]')) {
            beginResize(e);
            return;
        }
        beginDrag(e);
    };

    const board = document.getElementById('homeBoard');
    board?.addEventListener('pointerdown', onPointerDown);
    board?.addEventListener('dragstart', (e) => e.preventDefault());
    window.addEventListener('pointermove', moveDrag);
    window.addEventListener('pointerup', endDrag);
    window.addEventListener('mousemove', moveDrag);
    window.addEventListener('mouseup', endDrag);

    document.getElementById('homeWorkClose')?.addEventListener('click', () => closeHomeWork());
    document.getElementById('homeWorkBackdrop')?.addEventListener('click', () => closeHomeWork());
    document.addEventListener(
        'keydown',
        (e) => {
            if (e.key !== 'Escape') return;
            if (utils.dialogIsOpen()) return;
            if (!isWorkOpen()) return;
            e.preventDefault();
            e.stopPropagation();
            closeHomeWork();
        },
        true,
    );
}

export function setupHome() {
    bindHome();
    syncHomeDayPart();
    onAppearanceChange(() => {
        if (document.getElementById('homeTab')?.classList.contains('active')) {
            syncPageColors();
        }
    });
    document.addEventListener('kosistenz:data-changed', () => {
        if (document.getElementById('homeTab')?.classList.contains('active')) {
            void refreshHomeData();
        }
    });
    document.addEventListener('kosistenz:open-home-work', (event) => {
        const kind = event.detail?.kind;
        if (kind) void openHomeWork(kind);
    });
    document.addEventListener('kosistenz:open-evening-checkin', () => {
        checkinSlotOverride = 'evening';
        checkinForceOpen = true;
        const firstId = layout?.pages?.[0]?.id;
        document.dispatchEvent(new CustomEvent('kosistenz:open-tab', {
            detail: { tab: 'home', homePageId: firstId },
        }));
    });
    document.addEventListener('kosistenz:open-cluny', (event) => {
        document.dispatchEvent(new CustomEvent('kosistenz:open-tab', {
            detail: { tab: 'home' },
        }));
        const question = event.detail?.question || '';
        const focus = event.detail?.focus || null;
        void ensureHomeWidget('cluny').then(async () => {
            if (!question) return;
            const { promptCluny } = await import('./cluny.js');
            void promptCluny(question, focus);
        });
    });
}

export async function onHomeTabShown(pageId) {
    closeHomeWork(true);
    setEditing(false);
    await renderHome(pageId);
}

export async function ensureHomeWidget(kind) {
    await loadLayout();
    const page = activePage();
    if (!page) return;
    if (!(page.widgets || []).some((item) => item.kind === kind)) {
        try {
            layout = await eel.add_home_widget(page.id, kind)();
        } catch (err) {
            console.error(err);
        }
    }
    await renderHome();
    await openHomeWork(kind);
}
