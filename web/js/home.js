/**
 * Customizable Home — snap-to-grid widgets, extra pages, Edit Home mode.
 */

import * as utils from './utils.js';
import { WIDGET_CATALOG, GRID_COLUMNS, catalogList, canPlace, snapCell, pickResize } from './home_layout.js';
import { mountGlance, refreshGlances } from './glance_tiles.js';
import { getAppearance, persistAppearance, onAppearanceChange, resolveColors, applyAppearance, applyAppearanceOverlay, notifyNativeTab } from './appearance.js';
import { onTodayTabShown, refreshToday } from './today.js';
import { onTodoTabShown } from './todo.js';
import { onAllWorkTabShown } from './all_work.js';
import { onWorkoutTabShown } from './workouts.js';
import { onGoalsTabShown } from './goals.js';
import { onAnalyticsTabShown } from './analytics.js';
import { onTimelineTabShown } from './timeline.js';
import { loadPastEntries } from './journal.js';
import { refreshWeather } from './weather.js';
import { refreshFocus, refreshCountdown, refreshHabits } from './glance.js';
import { refreshHeatmap } from './heatmap.js';
import { refreshDayBrief } from './day_brief.js';
import { refreshCounters } from './counters.js';
import { refreshReading } from './reading.js';
import { onWordTabShown } from './word.js';
import { onChecklistTabShown, openChecklistTemplate } from './daily_checklist.js';

const FALLBACK_LAYOUT = {
    columns: 4,
    active_page_id: 'local-home',
    pages: [
        {
            id: 'local-home',
            name: 'Home',
            widgets: [
                { id: 'w-todo', kind: 'todo', x: 0, y: 0, w: 2, h: 2 },
                { id: 'w-today', kind: 'today_calendar', x: 2, y: 0, w: 2, h: 2 },
                { id: 'w-weather', kind: 'weather', x: 0, y: 2, w: 1, h: 1 },
                { id: 'w-word', kind: 'word', x: 1, y: 2, w: 1, h: 1 },
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

function rack() {
    return document.getElementById('widgetSourceRack');
}

function activePage() {
    if (!layout) return null;
    return layout.pages.find((page) => page.id === layout.active_page_id) || layout.pages[0];
}

async function persist(next) {
    if (typeof eel === 'undefined' || !eel.save_home_layout) {
        layout = next;
        return layout;
    }
    layout = await eel.save_home_layout(next)();
    return layout;
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

function returnSources() {
    const host = rack();
    if (!host) return;
    document.querySelectorAll('.home-widget-body > .widget-source, #homeWorkBody > .widget-source').forEach((node) => {
        node.classList.remove('widget-source--active');
        host.appendChild(node);
    });
}

function workLayer() {
    return document.getElementById('homeWorkLayer');
}

function isWorkOpen() {
    const layer = workLayer();
    return !!(layer && !layer.hidden && layer.classList.contains('is-open'));
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
    if (!layer) return;
    const opener = workOpener;
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
    if (immediate) {
        finish();
        return;
    }
    workHideTimer = window.setTimeout(() => {
        workHideTimer = 0;
        finish();
    }, 340);
}

export async function openHomeWork(kind, opener) {
    const spec = WIDGET_CATALOG[kind];
    if (!spec || editing) return;
    closeHomeWork(true);
    workKind = kind;
    workOpener = opener || document.querySelector(`#homeGrid .home-widget[data-kind="${kind}"]`);
    const layer = workLayer();
    const panel = document.getElementById('homeWorkPanel');
    if (!layer || !panel) return;
    mountWorkSource(kind);
    layer.hidden = false;
    layer.classList.remove('is-hidden');
    layer.setAttribute('data-kind', kind);
    document.documentElement.classList.add('home-work-open');
    document.getElementById('homeShell')?.classList.add('is-working');
    document.getElementById('homeShell')?.setAttribute('inert', '');
    requestAnimationFrame(() => {
        layer.classList.add('is-open');
        const closeBtn = document.getElementById('homeWorkClose');
        try {
            closeBtn?.focus({ preventScroll: true });
        } catch (_) {
            closeBtn?.focus();
        }
    });
    await refreshKinds([kind]);
}

async function refreshKinds(kinds) {
    const set = new Set(kinds);
    const run = async (fn) => {
        try {
            await fn();
        } catch (err) {
            console.error(err);
        }
    };
    if (set.has('today_calendar')) await run(onTodayTabShown);
    if (set.has('todo')) await run(onTodoTabShown);
    if (set.has('allwork')) await run(onAllWorkTabShown);
    if (set.has('workout')) await run(onWorkoutTabShown);
    if (set.has('goals')) await run(onGoalsTabShown);
    if (set.has('journal')) await run(loadPastEntries);
    if (set.has('analytics')) await run(onAnalyticsTabShown);
    if (set.has('timeline')) await run(onTimelineTabShown);
    if (set.has('weather')) await run(refreshWeather);
    if (set.has('focus')) await run(refreshFocus);
    if (set.has('countdown')) await run(refreshCountdown);
    if (set.has('habits')) await run(refreshHabits);
    if (set.has('heatmap')) await run(refreshHeatmap);
    if (set.has('day_brief')) await run(refreshDayBrief);
    if (set.has('counters')) await run(refreshCounters);
    if (set.has('reading')) await run(refreshReading);
    if (set.has('word')) await run(onWordTabShown);
    if (set.has('checklist')) await run(onChecklistTabShown);
    await run(refreshToday);
    await run(() => refreshGlances([...set]));
}

const HOME_NAV_ICON = '<svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M4.5 11 12 4.5 19.5 11v8a1.5 1.5 0 0 1-1.5 1.5h-4v-5h-4v5H6A1.5 1.5 0 0 1 4.5 19v-8Z"/></svg>';
const PAGE_NAV_ICON = '<svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><rect x="5" y="4.5" width="14" height="15" rx="1.5"/><path d="M8 9h8M8 12.5h8M8 16h5"/></svg>';

function paintPages() {
    const el = document.getElementById('homePages');
    if (!el || !layout) return;
    el.innerHTML = layout.pages
        .map((page) => {
            const on = page.id === layout.active_page_id;
            return `<button type="button" class="home-page-chip${on ? ' is-selected' : ''}" data-page="${utils.escapeHtml(page.id)}">${utils.escapeHtml(page.name)}</button>`;
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
    const onHome = document.documentElement.getAttribute('data-page') !== 'calendar'
        && document.documentElement.getAttribute('data-page') !== 'settings';
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

function paintGrid() {
    const grid = document.getElementById('homeGrid');
    if (!grid || !layout) return;
    returnSources();
    const page = activePage();
    const widgets = page?.widgets || [];
    const live = !editing;
    grid.innerHTML = widgets
        .map((item) => {
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
        })
        .join('');
    widgets.forEach((item) => {
        const card = grid.querySelector(`.home-widget[data-id="${item.id}"]`);
        mountGlance(item.kind, card?.querySelector('.home-widget-body'), card);
    });
}

function paintBorderControls() {
    const settings = getAppearance();
    const colors = resolveColors(settings);
    const width = document.getElementById('homeBorderWidth');
    const widthVal = document.getElementById('homeBorderWidthValue');
    const color = document.getElementById('homeBorderColor');
    if (width) width.value = String(settings.widgetBorderWidth ?? 1);
    if (widthVal) widthVal.textContent = `${settings.widgetBorderWidth ?? 1}px`;
    if (color) color.value = colors.widgetBorder;
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
        paintBorderControls();
    }
    document.querySelectorAll('#homeGrid .home-widget').forEach((card) => {
        const spec = WIDGET_CATALOG[card.getAttribute('data-kind')] || { label: card.getAttribute('data-kind') };
        card.setAttribute('role', editing ? 'group' : 'button');
        card.tabIndex = editing ? -1 : 0;
        card.setAttribute('aria-label', editing ? spec.label : `Open ${spec.label}`);
    });
}

async function renderHome() {
    paintPages();
    paintGrid();
    paintCatalog();
    const page = activePage();
    await refreshKinds((page?.widgets || []).map((item) => item.kind));
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
        void run(() => eel.set_active_home_page(btn.getAttribute('data-page'))());
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

    document.getElementById('homeBorderWidth')?.addEventListener('input', (e) => {
        const n = parseInt(e.target.value, 10);
        const label = document.getElementById('homeBorderWidthValue');
        if (label) label.textContent = `${n}px`;
        void persistAppearance({ widgetBorderWidth: n });
    });
    document.getElementById('homeBorderColor')?.addEventListener('input', (e) => {
        const colorOverrides = { ...(getAppearance().colorOverrides || {}), widgetBorder: e.target.value };
        void persistAppearance({ colorOverrides });
    });

    document.getElementById('homeCatalog')?.addEventListener('click', (e) => {
        const btn = e.target.closest('[data-kind]');
        if (!btn || btn.disabled) return;
        const page = activePage();
        if (!page) return;
        void run(() => eel.add_home_widget(page.id, btn.getAttribute('data-kind'))());
    });

    document.getElementById('homeGrid')?.addEventListener('click', (e) => {
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
        const card = e.target.closest('.home-widget');
        if (!card) return;
        void openHomeWork(card.getAttribute('data-kind'), card);
    });
    document.getElementById('homeGrid')?.addEventListener('keydown', (e) => {
        if (editing) return;
        if (e.key !== 'Enter' && e.key !== ' ') return;
        const card = e.target.closest('.home-widget');
        if (!card || e.target !== card) return;
        e.preventDefault();
        void openHomeWork(card.getAttribute('data-kind'), card);
    });

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
        };
        card.classList.add('is-dragging');
        card.draggable = false;
        card.dataset.dropX = String(widget.x);
        card.dataset.dropY = String(widget.y);
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
        const grid = document.getElementById('homeGrid');
        const page = activePage();
        const widget = page?.widgets.find((item) => item.id === drag.id);
        if (!grid || !widget) return;
        const card = grid.querySelector(`.home-widget[data-id="${drag.id}"]`);
        if (!card) return;
        const cell = snapCell(e.clientX, e.clientY, grid);
        if (drag.type === 'resize') {
            const wantW = drag.axis === 'y' ? widget.w : Math.max(1, cell.x - widget.x + 1);
            const wantH = drag.axis === 'x' ? widget.h : Math.max(1, cell.y - widget.y + 1);
            const next = pickResize(widget.kind, widget, wantW, wantH, page.widgets, drag.axis);
            paintWidgetBox(card, widget.x, widget.y, next.w, next.h);
            card.dataset.dropW = String(next.w);
            card.dataset.dropH = String(next.h);
            return;
        }
        const x = Math.max(0, Math.min(GRID_COLUMNS - widget.w, cell.x));
        const y = Math.max(0, cell.y);
        if (canPlace(page.widgets, widget, x, y)) {
            paintWidgetBox(card, x, y, widget.w, widget.h);
            card.dataset.dropX = String(x);
            card.dataset.dropY = String(y);
        }
    };

    const endDrag = () => {
        if (!drag) return;
        const page = activePage();
        const grid = document.getElementById('homeGrid');
        const card = grid?.querySelector(`.home-widget[data-id="${drag.id}"]`);
        const id = drag.id;
        const type = drag.type;
        const originX = drag.originX;
        const originY = drag.originY;
        const originW = drag.originW;
        const originH = drag.originH;
        const x = Number(card?.dataset.dropX);
        const y = Number(card?.dataset.dropY);
        const w = Number(card?.dataset.dropW);
        const h = Number(card?.dataset.dropH);
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
        if (!page || Number.isNaN(x) || Number.isNaN(y) || (x === originX && y === originY)) {
            if (card && widget) paintWidgetBox(card, widget.x, widget.y, widget.w, widget.h);
            return;
        }
        void run(() => eel.move_home_widget(page.id, id, x | 0, y | 0)());
    };

    const onPointerDown = (e) => {
        if (e.target.closest('[data-resize]')) {
            beginResize(e);
            return;
        }
        beginDrag(e);
    };

    const grid = document.getElementById('homeGrid');
    grid?.addEventListener('pointerdown', onPointerDown);
    grid?.addEventListener('dragstart', (e) => e.preventDefault());
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
    paintBorderControls();
    onAppearanceChange(() => {
        paintBorderControls();
        if (document.getElementById('homeTab')?.classList.contains('active')) {
            syncPageColors();
        }
    });
    void loadLayout().then(() => renderHome());
    document.addEventListener('kosistenz:data-changed', () => {
        if (document.getElementById('homeTab')?.classList.contains('active')) {
            const page = activePage();
            void refreshKinds((page?.widgets || []).map((item) => item.kind));
        } else {
            void refreshToday();
        }
    });
    document.addEventListener('kosistenz:open-evening-checkin', () => {
        void (async () => {
            await ensureHomeWidget('checklist');
            try {
                await openChecklistTemplate('evening');
            } catch (err) {
                console.error(err);
            }
        })();
    });
}

export async function onHomeTabShown(pageId) {
    await loadLayout();
    if (pageId && pageId !== layout.active_page_id && typeof eel !== 'undefined' && eel.set_active_home_page) {
        try {
            layout = await eel.set_active_home_page(pageId)();
        } catch (err) {
            console.error(err);
        }
    }
    closeHomeWork(true);
    setEditing(false);
    await renderHome();
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
