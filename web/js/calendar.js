/**
 * Week clock — hard events, imported dues, Fill week.
 */

import * as utils from './utils.js';

let weekStart = null;
let calView = 'month';
let monthCursor = { year: new Date().getFullYear(), month: new Date().getMonth() + 1 };
let yearCursor = new Date().getFullYear();
let lastSettings = {};
let editor = { mode: 'new', kind: 'hard', id: '', workItemId: '', status: 'proposed', occurrenceDate: '', minutes: 60 };
let dragState = null;

function mondayISO(d = new Date()) {
    const day = new Date(d.getFullYear(), d.getMonth(), d.getDate());
    const offset = (day.getDay() + 6) % 7;
    day.setDate(day.getDate() - offset);
    return utils.localISODate(day);
}

function humanWeekRange(startIso, endIso) {
    // The week label is human, like Sep 1 – 7.
    const start = new Date(`${startIso}T12:00:00`);
    const end = new Date(`${endIso}T12:00:00`);
    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
        return `${startIso} – ${endIso}`;
    }
    const sameMonth = start.getMonth() === end.getMonth();
    const left = start.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    const right = end.toLocaleDateString(undefined, sameMonth ? { day: 'numeric' } : { month: 'short', day: 'numeric' });
    return `${left} – ${right}`;
}

function setCalView(next) {
    calView = next === 'week' || next === 'year' ? next : 'month';
    // Fill week stays visible in month and year; it still packs this week.
    document.getElementById('calGrid')?.classList.toggle('is-hidden', calView !== 'week');
    document.getElementById('calMonthGrid')?.classList.toggle('is-hidden', calView !== 'month');
    document.getElementById('calYearGrid')?.classList.toggle('is-hidden', calView !== 'year');
    // Month and year views hide the week-clock hint.
    document.getElementById('calClockHint')?.classList.toggle('is-hidden', calView !== 'week');
    // Month and year views show the lecture / placed / due legend.
    document.getElementById('calMonthLegend')?.classList.toggle('is-hidden', calView === 'week');
    document.querySelectorAll('#calViewGroup [data-cal-view]').forEach((btn) => {
        btn.classList.toggle('is-selected', btn.getAttribute('data-cal-view') === calView);
    });
}

function openWeekForDate(iso) {
    const [y, m, d] = String(iso || '').split('-').map(Number);
    if (!y) return;
    weekStart = mondayISO(new Date(y, m - 1, d));
    setCalView('week');
    void loadWeek();
}

function weekdayHeads() {
    return ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        .map((name) => `<span class="cal-month-dow">${name}</span>`)
        .join('');
}

function renderMonthCell(cell, compact) {
    const extra = [];
    if (cell.event_count) extra.push('lecture');
    if (cell.block_count) extra.push('block');
    if (cell.due_count) extra.push('due');
    const marks = extra.length
        ? `<span class="cal-month-dots">${extra.map((kind) => `<i class="is-${kind}"></i>`).join('')}</span>`
        : '';
    return `<button type="button" class="cal-month-cell${compact ? ' is-compact' : ''}${cell.in_month ? '' : ' is-out'}${cell.is_today ? ' is-today' : ''}${cell.has_items ? ' has-items' : ''}" data-date="${utils.escapeHtml(cell.date)}">
        <span class="cal-month-num">${cell.day}</span>${marks}
    </button>`;
}

function renderMonthGrid(payload) {
    const root = document.getElementById('calMonthGrid');
    const label = document.getElementById('calWeekLabel');
    if (label) label.textContent = payload.label || 'This month';
    if (!root) return;
    const weeks = payload.weeks || [];
    root.innerHTML = `<div class="cal-month-head">${weekdayHeads()}</div>` + weeks
        .map((week) => `<div class="cal-month-week">${week.map((cell) => renderMonthCell(cell, false)).join('')}</div>`)
        .join('');
}

function renderYearGrid(payload) {
    const root = document.getElementById('calYearGrid');
    const label = document.getElementById('calWeekLabel');
    if (label) label.textContent = payload.label || String(yearCursor);
    if (!root) return;
    root.innerHTML = (payload.months || [])
        .map((month) => {
            const weeks = (month.weeks || [])
                .map((week) => `<div class="cal-month-week is-compact">${week.map((cell) => renderMonthCell(cell, true)).join('')}</div>`)
                .join('');
            return `<section class="cal-year-month" data-month="${month.month}">
                <h3 data-jump-month="${month.month}">${utils.escapeHtml(month.label)}</h3>
                <div class="cal-month-head is-compact">${weekdayHeads()}</div>
                ${weeks}
            </section>`;
        })
        .join('');
}

async function loadMonth() {
    if (typeof eel === 'undefined' || !eel.get_month) return;
    try {
        const payload = await eel.get_month(monthCursor.year, monthCursor.month)();
        monthCursor = { year: payload.year, month: payload.month };
        renderMonthGrid(payload);
        renderUnplaced(payload.unplaced || []);
        paintAwakeFields(payload.settings);
    } catch (e) {
        console.error(e);
        const root = document.getElementById('calMonthGrid');
        if (root) root.innerHTML = '<p class="checklist-error">Could not load the month.</p>';
    }
}

async function loadYear() {
    if (typeof eel === 'undefined' || !eel.get_year) return;
    try {
        const payload = await eel.get_year(yearCursor)();
        yearCursor = payload.year;
        renderYearGrid(payload);
        renderUnplaced(payload.unplaced || []);
        paintAwakeFields(payload.settings);
    } catch (e) {
        console.error(e);
        const root = document.getElementById('calYearGrid');
        if (root) root.innerHTML = '<p class="checklist-error">Could not load the year.</p>';
    }
}

async function loadCalendar() {
    setCalView(calView);
    if (calView === 'year') {
        await loadYear();
        return;
    }
    if (calView === 'month') {
        await loadMonth();
        return;
    }
    await loadWeek();
}

function shiftCalendar(dir) {
    if (calView === 'year') {
        yearCursor += dir;
        void loadYear();
        return;
    }
    if (calView === 'month') {
        let month = monthCursor.month + dir;
        let year = monthCursor.year;
        if (month < 1) {
            month = 12;
            year -= 1;
        } else if (month > 12) {
            month = 1;
            year += 1;
        }
        monthCursor = { year, month };
        void loadMonth();
        return;
    }
    weekStart = shiftWeek(dir * 7);
    void loadWeek();
}

function jumpToday() {
    const now = new Date();
    weekStart = mondayISO(now);
    monthCursor = { year: now.getFullYear(), month: now.getMonth() + 1 };
    yearCursor = now.getFullYear();
    void loadCalendar();
}

function shiftWeek(days) {
    const [y, m, d] = (weekStart || mondayISO()).split('-').map(Number);
    const dt = new Date(y, m - 1, d + days);
    return utils.localISODate(dt);
}

function toLocalInput(value) {
    const d = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(d.getTime())) return '';
    const pad = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function fromLocalInput(value) {
    if (!value) return '';
    return `${value}:00`;
}

function minutesFromClock(iso, startMin) {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return 0;
    return d.getHours() * 60 + d.getMinutes() - startMin;
}

function parseHHMM(raw) {
    let text = String(raw || '05:30').trim().replace('.', ':').replace(/\s/g, '');
    if (/^\d{3,4}$/.test(text)) {
        text = text.padStart(4, '0');
        text = `${text.slice(0, 2)}:${text.slice(2)}`;
    }
    const [h, m] = text.split(':').map(Number);
    return { hour: h || 0, minute: Number.isFinite(m) ? m : 0 };
}

function formatHHMM(raw) {
    const { hour, minute } = parseHHMM(raw);
    return `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`;
}

function clockWindow(settings) {
    const start = parseHHMM(settings?.day_start || '05:30');
    const end = parseHHMM(settings?.day_end || '21:30');
    const startMin = start.hour * 60 + start.minute;
    let endMin = end.hour * 60 + end.minute;
    if (endMin <= startMin) endMin = startMin + 60;
    return { startMin, endMin, span: endMin - startMin };
}

function hourMarks(startMin, endMin) {
    const marks = [{ min: startMin }];
    let t = Math.floor(startMin / 60) * 60 + 60;
    while (t < endMin) {
        marks.push({ min: t });
        t += 60;
    }
    return marks;
}

function formatMilitary(min) {
    const wrapped = ((min % (24 * 60)) + 24 * 60) % (24 * 60);
    const h = Math.floor(wrapped / 60);
    const m = wrapped % 60;
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

function selectedLectureDays() {
    return [...document.querySelectorAll('#calEventWeekdays .work-day-chip.is-selected')].map((btn) =>
        Number(btn.getAttribute('data-day')),
    );
}

function blockLabel(item) {
    if (item.kind === 'hard') return item.title;
    const mins = item.minutes ? `${item.minutes}m` : '';
    const status = item.status && item.status !== 'proposed' ? item.status : '';
    return [item.title, mins, status].filter(Boolean).join(' · ');
}

function renderBlock(item, settings) {
    const { startMin, span } = clockWindow(settings);
    const top = Math.max(0, minutesFromClock(item.start_at, startMin));
    const start = new Date(item.start_at);
    const end = new Date(item.end_at);
    const dur = Math.max(20, (end - start) / 60000);
    const height = Math.max(18, (dur / span) * 100);
    const topPct = (top / span) * 100;
    const kind = item.kind === 'hard' ? 'hard' : item.kind === 'workout' ? 'workout' : 'work';
    const locked = item.status === 'locked';
    const selected = editor.id && editor.id === item.id ? ' is-selected' : '';
    return `<button type="button" class="cal-block is-${kind}${locked ? ' is-locked' : ''}${selected}"
        style="top:${topPct}%;height:${height}%"
        data-id="${utils.escapeHtml(item.id || '')}"
        data-kind="${kind}"
        data-status="${utils.escapeHtml(item.status || '')}"
        data-title="${utils.escapeHtml(item.title || '')}"
        data-start-at="${utils.escapeHtml(item.start_at || '')}"
        data-end-at="${utils.escapeHtml(item.end_at || '')}"
        data-work-item-id="${utils.escapeHtml(item.work_item_id || '')}"
        data-occurrence-date="${utils.escapeHtml(item.occurrence_date || item.local_date || '')}"
        data-weekdays="${utils.escapeHtml((item.recurrence && item.recurrence.weekdays ? item.recurrence.weekdays : []).join(','))}"
        title="${utils.escapeHtml(blockLabel(item))}">${utils.escapeHtml(blockLabel(item))}</button>`;
}

function renderGrid(week) {
    const root = document.getElementById('calGrid');
    const label = document.getElementById('calWeekLabel');
    if (!root) return;
    const settings = week.settings || {};
    const { startMin, endMin, span } = clockWindow(settings);
    const hourPct = (60 / span) * 100;
    const offsetMin = (60 - (startMin % 60)) % 60;
    const offsetPct = (offsetMin / span) * 100;
    const marks = hourMarks(startMin, endMin)
        .map((mark) => {
            const top = ((mark.min - startMin) / span) * 100;
            return `<span style="top:${top}%">${formatMilitary(mark.min)}</span>`;
        })
        .join('');
    if (label) {
        const start = week.week_start || '';
        const end = week.week_end || '';
        label.textContent = start && end ? humanWeekRange(start, end) : 'This week';
    }
    const hourLines = hourMarks(startMin, endMin)
        .filter((mark) => mark.min !== startMin)
        .map((mark) => {
            const top = ((mark.min - startMin) / span) * 100;
            return `<span class="cal-hour-line" style="top:${top}%"></span>`;
        })
        .join('');
    const hourCol = `<div class="cal-hours"><div class="cal-hours-scale">${marks}</div></div>`;
    const days = (week.days || [])
        .map((day) => {
            const items = [...(day.events || []), ...(day.blocks || [])];
            return `<div class="cal-day${day.is_today ? ' is-today' : ''}" data-date="${utils.escapeHtml(day.date)}">
                <header class="cal-day-head"><strong>${utils.escapeHtml(day.weekday)}</strong><span>${utils.escapeHtml(day.date.slice(8))}</span></header>
                <div class="cal-day-body" style="--cal-hour-pct:${hourPct}%;--cal-hour-offset:${offsetPct}%">${hourLines}${items.map((item) => renderBlock(item, settings)).join('')}</div>
            </div>`;
        })
        .join('');
    root.innerHTML = `${hourCol}<div class="cal-days">${days}</div>`;
}

function renderUnplaced(items) {
    const root = document.getElementById('calUnplaced');
    if (!root) return;
    if (!items?.length) {
        root.innerHTML = '<p class="empty-state empty-state--line">Nothing to place.</p>';
        return;
    }
    root.innerHTML = items
        .map((item) => {
            const due = item.due_at ? String(item.due_at).replace('T', ' ').slice(0, 16) : 'No due';
            const mins = item.remaining_minutes || item.estimate_minutes || 0;
            const selected = editor.mode === 'unplaced' && editor.id === item.id ? ' is-selected' : '';
            return `<button type="button" class="cal-unplaced-item${selected}" data-id="${utils.escapeHtml(item.id || '')}" data-title="${utils.escapeHtml(item.title || '')}" data-minutes="${mins}">
                <h4>${utils.escapeHtml(item.title)}</h4>
                <p>${utils.escapeHtml(due)} · ${mins} min left</p>
            </button>`;
        })
        .join('');
    root.querySelectorAll('.cal-unplaced-item').forEach((btn) => {
        btn.addEventListener('click', () => openUnplaced(btn));
    });
}

async function loadWeek() {
    if (!weekStart) weekStart = mondayISO();
    if (typeof eel === 'undefined' || !eel.get_week) return;
    try {
        const week = await eel.get_week(weekStart)();
        weekStart = week.week_start || weekStart;
        lastSettings = week.settings || {};
        paintAwakeFields(lastSettings);
        renderGrid(week);
        renderUnplaced(week.unplaced || []);
        const url = document.getElementById('calIcsUrl');
        if (url && week.settings?.ics_url && !url.value) url.value = week.settings.ics_url;
        bindGrid();
    } catch (e) {
        console.error(e);
        const root = document.getElementById('calGrid');
        if (root) root.innerHTML = '<p class="checklist-error">Could not load the week.</p>';
    }
}

function selectedBlockStatus() {
    return document.querySelector('#calBlockStatus .work-day-chip.is-selected')?.getAttribute('data-status') || 'proposed';
}

function setWeekdaySelection(days) {
    const want = new Set((days || []).map((d) => String(d)));
    document.querySelectorAll('#calEventWeekdays .work-day-chip').forEach((btn) => {
        btn.classList.toggle('is-selected', want.has(btn.getAttribute('data-day')));
    });
}

function setStatusSelection(status) {
    document.querySelectorAll('#calBlockStatus .work-day-chip').forEach((btn) => {
        btn.classList.toggle('is-selected', btn.getAttribute('data-status') === status);
    });
}

function toggleHidden(el, hide) {
    if (el) el.classList.toggle('is-hidden', !!hide);
}

function paintEditor() {
    const heading = document.getElementById('calEditorHeading');
    const hint = document.getElementById('calEditorHint');
    const weekdays = document.getElementById('calEventWeekdays');
    const status = document.getElementById('calBlockStatus');
    const park = document.getElementById('calParkItem');
    const remove = document.getElementById('calRemoveItem');
    const fresh = document.getElementById('calNewLecture');
    const ask = document.getElementById('calAskCluny');
    const save = document.getElementById('calSaveItem');
    const mode = editor.mode;
    const isNew = mode === 'new';
    const isHard = mode === 'hard' || isNew;
    const isUnplaced = mode === 'unplaced';
    const isBlock = mode === 'work' || mode === 'workout';
    if (heading) {
        heading.textContent = isNew
            ? 'New lecture'
            : isUnplaced
                ? 'Place on the clock'
                : (document.getElementById('calEventTitle')?.value?.trim() || 'Edit');
    }
    if (hint) {
        hint.textContent = isNew
            ? 'Click a block to edit it. Drag to move.'
            : isUnplaced
                ? 'Pick a start time, then Save to place this work.'
                : 'Rename, change the times, or drag the block.';
    }
    toggleHidden(weekdays, !isHard);
    toggleHidden(status, !isBlock);
    toggleHidden(park, !(isBlock || isUnplaced));
    toggleHidden(remove, isNew || isUnplaced);
    toggleHidden(fresh, isNew);
    toggleHidden(ask, isNew || isUnplaced || !editor.id);
    if (save) {
        save.textContent = isUnplaced ? 'Place' : 'Save';
    }
    if (park) park.textContent = isUnplaced ? 'Leave in All Work' : 'Save for later';
}

function resetEditor() {
    editor = { mode: 'new', kind: 'hard', id: '', workItemId: '', status: 'proposed', occurrenceDate: '', minutes: 60 };
    const titleEl = document.getElementById('calEventTitle');
    if (titleEl) titleEl.value = '';
    setWeekdaySelection([]);
    setStatusSelection('proposed');
    const start = document.getElementById('calEventStart');
    const end = document.getElementById('calEventEnd');
    if (start) start.value = '';
    if (end) end.value = '';
    defaultEventTimes(true);
    paintEditor();
    document.querySelectorAll('.cal-block.is-selected, .cal-unplaced-item.is-selected').forEach((el) => {
        el.classList.remove('is-selected');
    });
}

function openEditorFromBlock(btn) {
    const kind = btn.getAttribute('data-kind') || 'work';
    editor = {
        mode: kind,
        kind,
        id: btn.getAttribute('data-id') || '',
        workItemId: btn.getAttribute('data-work-item-id') || '',
        status: btn.getAttribute('data-status') || 'proposed',
        occurrenceDate: btn.getAttribute('data-occurrence-date') || '',
        minutes: 60,
    };
    const titleEl = document.getElementById('calEventTitle');
    if (titleEl) titleEl.value = btn.getAttribute('data-title') || '';
    const startEl = document.getElementById('calEventStart');
    const endEl = document.getElementById('calEventEnd');
    const startIso = btn.getAttribute('data-start-at') || '';
    if (startEl) startEl.value = toLocalInput(startIso);
    if (endEl) endEl.value = toLocalInput(btn.getAttribute('data-end-at'));
    const rawDays = (btn.getAttribute('data-weekdays') || '').split(',').map((d) => d.trim()).filter(Boolean);
    if (rawDays.length) {
        setWeekdaySelection(rawDays);
    } else if (kind === 'hard' && startIso) {
        const d = new Date(startIso);
        setWeekdaySelection(Number.isNaN(d.getTime()) ? [] : [String((d.getDay() + 6) % 7)]);
    } else {
        setWeekdaySelection([]);
    }
    setStatusSelection(editor.status);
    paintEditor();
    document.querySelectorAll('.cal-block.is-selected, .cal-unplaced-item.is-selected').forEach((el) => {
        el.classList.remove('is-selected');
    });
    btn.classList.add('is-selected');
}

function openUnplaced(btn) {
    const minutes = Number(btn.getAttribute('data-minutes') || 60) || 60;
    editor = {
        mode: 'unplaced',
        kind: 'work',
        id: btn.getAttribute('data-id') || '',
        workItemId: btn.getAttribute('data-id') || '',
        status: 'proposed',
        occurrenceDate: '',
        minutes,
    };
    const titleEl = document.getElementById('calEventTitle');
    if (titleEl) titleEl.value = btn.getAttribute('data-title') || '';
    defaultEventTimes(true);
    const start = document.getElementById('calEventStart');
    const end = document.getElementById('calEventEnd');
    if (start?.value && end) {
        const d = new Date(start.value);
        if (!Number.isNaN(d.getTime())) {
            end.value = toLocalInput(new Date(d.getTime() + Math.max(15, minutes) * 60000));
        }
    }
    setWeekdaySelection([]);
    setStatusSelection('proposed');
    paintEditor();
    document.querySelectorAll('.cal-block.is-selected, .cal-unplaced-item.is-selected').forEach((el) => {
        el.classList.remove('is-selected');
    });
    btn.classList.add('is-selected');
}

function isoFromEditor() {
    return {
        title: document.getElementById('calEventTitle')?.value?.trim() || '',
        start: fromLocalInput(document.getElementById('calEventStart')?.value),
        end: fromLocalInput(document.getElementById('calEventEnd')?.value),
    };
}

function bindGrid() {
    document.querySelectorAll('.cal-block').forEach((btn) => {
        btn.addEventListener('pointerdown', onBlockPointerDown);
        btn.addEventListener('pointermove', onBlockPointerMove);
        btn.addEventListener('pointerup', onBlockPointerUp);
        btn.addEventListener('pointercancel', onBlockPointerUp);
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            if (btn.dataset.didDrag === '1') {
                btn.dataset.didDrag = '';
                return;
            }
            openEditorFromBlock(btn);
        });
    });
}

function onBlockPointerDown(e) {
    if (e.button !== 0) return;
    const btn = e.currentTarget;
    dragState = {
        el: btn,
        pointerId: e.pointerId,
        originX: e.clientX,
        originY: e.clientY,
        moved: false,
        preview: null,
        id: btn.getAttribute('data-id'),
        kind: btn.getAttribute('data-kind'),
        startAt: btn.getAttribute('data-start-at'),
        endAt: btn.getAttribute('data-end-at'),
        occurrenceDate: btn.getAttribute('data-occurrence-date'),
    };
    try { btn.setPointerCapture(e.pointerId); } catch (_) { /* ignore */ }
}

function onBlockPointerMove(e) {
    if (!dragState || e.pointerId !== dragState.pointerId) return;
    const dx = e.clientX - dragState.originX;
    const dy = e.clientY - dragState.originY;
    if (!dragState.moved && (dx * dx + dy * dy) < 36) return;
    dragState.moved = true;
    dragState.el.dataset.didDrag = '1';
    dragState.el.classList.add('is-dragging');
    const hit = document.elementFromPoint(e.clientX, e.clientY)?.closest('.cal-day-body');
    if (!hit) return;
    const day = hit.closest('.cal-day')?.getAttribute('data-date');
    if (!day) return;
    const rect = hit.getBoundingClientRect();
    const { startMin, span } = clockWindow(lastSettings);
    const origStart = new Date(dragState.startAt);
    const origEnd = new Date(dragState.endAt);
    const dur = Math.max(15, Math.round((origEnd - origStart) / 60000));
    let mins = Math.round((((e.clientY - rect.top) / rect.height) * span) / 15) * 15;
    mins = Math.max(0, Math.min(span - dur, mins));
    const topPct = (mins / span) * 100;
    const heightPct = (dur / span) * 100;
    if (hit !== dragState.el.parentElement) hit.appendChild(dragState.el);
    dragState.el.style.top = `${topPct}%`;
    dragState.el.style.height = `${heightPct}%`;
    dragState.preview = { date: day, minutesFromStart: mins, duration: dur };
}

async function onBlockPointerUp(e) {
    if (!dragState || e.pointerId !== dragState.pointerId) return;
    const state = dragState;
    dragState = null;
    state.el.classList.remove('is-dragging');
    try { state.el.releasePointerCapture(e.pointerId); } catch (_) { /* ignore */ }
    if (!state.moved || !state.preview) return;
    const { startMin } = clockWindow(lastSettings);
    const [y, m, d] = state.preview.date.split('-').map(Number);
    const start = new Date(y, m - 1, d, 0, 0, 0);
    start.setMinutes(startMin + state.preview.minutesFromStart);
    const end = new Date(start.getTime() + state.preview.duration * 60000);
    try {
        if (state.kind === 'hard') {
            await eel.update_calendar_event(state.id, '', toApiIso(start), toApiIso(end), null, state.occurrenceDate)();
        } else {
            await eel.update_schedule_block(state.id, '', toApiIso(start), toApiIso(end), '')();
        }
        utils.notifyDataChanged();
        await loadCalendar();
        utils.showSuccessFeedback('Moved.');
    } catch (err) {
        utils.showErrorFeedback(err?.message || 'Could not move that.');
        await loadCalendar();
    }
}

function toApiIso(d) {
    const pad = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:00`;
}

async function saveEditor() {
    const { title, start, end } = isoFromEditor();
    if (!title) {
        utils.showErrorFeedback('Name it first.');
        return;
    }
    if (!start || !end) {
        utils.showErrorFeedback('Set start and end times.');
        return;
    }
    try {
        if (editor.mode === 'new' || editor.mode === 'hard' && !editor.id) {
            await eel.create_calendar_event(title, start, end, selectedLectureDays())();
            resetEditor();
            utils.showSuccessFeedback('Saved on the clock.');
        } else if (editor.mode === 'hard') {
            await eel.update_calendar_event(editor.id, title, start, end, selectedLectureDays(), editor.occurrenceDate)();
            utils.showSuccessFeedback('Lecture updated.');
        } else if (editor.mode === 'unplaced') {
            await eel.schedule_work_at(editor.id, start, end)();
            resetEditor();
            utils.showSuccessFeedback('Placed on the clock.');
        } else {
            await eel.update_schedule_block(editor.id, title, start, end, selectedBlockStatus())();
            utils.showSuccessFeedback('Saved.');
        }
        utils.notifyDataChanged();
        await loadCalendar();
    } catch (e) {
        utils.showErrorFeedback(e?.message || 'Could not save that.');
    }
}

async function parkEditor() {
    try {
        if (editor.mode === 'unplaced' && editor.id) {
            await eel.assign_work_item(editor.id, '')();
            resetEditor();
            utils.showSuccessFeedback('Left in All Work.');
        } else if ((editor.mode === 'work' || editor.mode === 'workout') && editor.id) {
            await eel.park_schedule_block(editor.id)();
            resetEditor();
            utils.showSuccessFeedback(editor.mode === 'workout' ? 'Taken off the clock.' : 'Saved for later in All Work.');
        } else {
            return;
        }
        utils.notifyDataChanged();
        await loadCalendar();
    } catch (e) {
        utils.showErrorFeedback(e?.message || 'Could not park that.');
    }
}

async function removeEditor() {
    if (!editor.id) return;
    const lecture = editor.mode === 'hard';
    if (!(await utils.askConfirm({
        title: lecture ? 'Remove lecture' : 'Remove from clock',
        message: lecture
            ? 'Remove this lecture from the calendar?'
            : 'Take this off the clock? The work stays in your lists.',
        ok: 'Remove',
        danger: true,
    }))) return;
    try {
        if (lecture) {
            await eel.delete_calendar_event(editor.id)();
        } else {
            await eel.delete_schedule_block(editor.id, true)();
        }
        resetEditor();
        utils.notifyDataChanged();
        await loadCalendar();
        utils.showSuccessFeedback('Removed.');
    } catch (e) {
        utils.showErrorFeedback(e?.message || 'Could not remove that.');
    }
}

function paintAwakeFields(settings) {
    if (settings && typeof settings === 'object') {
        lastSettings = { ...lastSettings, ...settings };
    }
    const start = document.getElementById('calDayStart');
    const end = document.getElementById('calDayEnd');
    if (start && document.activeElement !== start) {
        start.value = formatHHMM(lastSettings.day_start || '05:30');
    }
    if (end && document.activeElement !== end) {
        end.value = formatHHMM(lastSettings.day_end || '21:30');
    }
}

async function saveAwake() {
    if (typeof eel === 'undefined' || !eel.save_calendar_settings) return;
    const start = document.getElementById('calDayStart')?.value;
    const end = document.getElementById('calDayEnd')?.value;
    try {
        const saved = await eel.save_calendar_settings({ day_start: start, day_end: end })();
        lastSettings = { ...lastSettings, ...saved };
        paintAwakeFields(saved);
        utils.showSuccessFeedback('Awake window saved. Fill week stays inside it; nights stay empty.');
        if (calView === 'week') await loadWeek();
    } catch (e) {
        utils.showErrorFeedback(e?.message || 'Time must be 24-hour, like 0530 or 21:30.');
    }
}

async function applyPastedCalendar(raw) {
    const text = String(raw || '');
    const isIcs = /BEGIN:VCALENDAR/i.test(text);
    const cleaned = (typeof window.kosistenzSanitizePastedUrl === 'function')
        ? window.kosistenzSanitizePastedUrl(text)
        : text.trim();
    const field = document.getElementById('calIcsUrl');
    if (!isIcs && cleaned) {
        if (field) {
            field.value = cleaned;
            field.dispatchEvent(new Event('input', { bubbles: true }));
            field.dispatchEvent(new Event('change', { bubbles: true }));
            try { field.focus(); } catch (err) { /* ignore */ }
        }
        utils.showSuccessFeedback('Pasted the calendar URL. Import ICS to load dues.');
        return true;
    }
    if (isIcs) {
        if (field) field.value = '';
        return importPasted(text);
    }
    return false;
}

async function importPasted(raw) {
    const status = document.getElementById('calImportStatus');
    if (status) status.textContent = 'Importing…';
    try {
        const result = await eel.import_pasted_calendar(raw)();
        if (status) {
            status.textContent = `Imported ${result.created || 0} new, updated ${result.updated || 0}. Due dates only — not busy time.`;
        }
        utils.showSuccessFeedback('Due dates are in the unplaced list.');
        utils.notifyDataChanged();
        await loadCalendar();
        return true;
    } catch (e) {
        if (status) status.textContent = '';
        utils.showErrorFeedback(e?.message || 'Could not import that calendar.');
        return false;
    }
}

function requestNativeIcsPaste() {
    try {
        if (!window.webkit?.messageHandlers?.kosistenz) return false;
        window.webkit.messageHandlers.kosistenz.postMessage({ type: 'icsPaste' });
        return true;
    } catch (_) {
        return false;
    }
}

async function pasteIcsButton() {
    if (requestNativeIcsPaste()) return;
    if (navigator.clipboard?.readText) {
        try {
            const raw = await navigator.clipboard.readText();
            if (raw) {
                await applyPastedCalendar(raw);
                return;
            }
        } catch (_) { /* fall through */ }
    }
    utils.showErrorFeedback('Paste the URL into the ICS box, or use Cmd+V in the installed app.');
}

function importApple() {
    const status = document.getElementById('calImportStatus');
    try {
        window.webkit?.messageHandlers?.kosistenz?.postMessage({ type: 'calendarImport' });
        if (status) status.textContent = 'Asking macOS for Calendar access…';
    } catch (_) {
        utils.showErrorFeedback('Apple Calendar import only works in the installed Kosistenz app.');
    }
}

function defaultEventTimes(force = false) {
    const start = document.getElementById('calEventStart');
    const end = document.getElementById('calEventEnd');
    if (!start || (!force && start.value)) return;
    const d = new Date();
    d.setMinutes(0, 0, 0);
    d.setHours(9, 30, 0, 0);
    start.value = toLocalInput(d);
    const e = new Date(d.getTime() + 50 * 60000);
    if (end) end.value = toLocalInput(e);
}

function importIcs() {
    const raw = document.getElementById('calIcsUrl')?.value || '';
    if (/BEGIN:VCALENDAR/i.test(raw)) {
        void importPasted(raw);
        return;
    }
    const url = (typeof window.kosistenzSanitizePastedUrl === 'function')
        ? window.kosistenzSanitizePastedUrl(raw)
        : raw.trim();
    if (url && document.getElementById('calIcsUrl')) {
        document.getElementById('calIcsUrl').value = url;
    }
    if (!url) {
        utils.showErrorFeedback('Paste the class calendar URL, or use Paste.');
        return;
    }
    void importPasted(url);
}

export function setupCalendar() {
    setCalView(calView);
    paintEditor();
    document.getElementById('calViewGroup')?.addEventListener('click', (e) => {
        const btn = e.target.closest('[data-cal-view]');
        if (!btn) return;
        setCalView(btn.getAttribute('data-cal-view'));
        void loadCalendar();
    });
    document.getElementById('calPrevWeek')?.addEventListener('click', () => {
        shiftCalendar(-1);
    });
    document.getElementById('calNextWeek')?.addEventListener('click', () => {
        shiftCalendar(1);
    });
    document.getElementById('calThisWeek')?.addEventListener('click', () => {
        jumpToday();
    });
    document.getElementById('calFillWeek')?.addEventListener('click', async () => {
        try {
            await eel.fill_week(weekStart || mondayISO())();
            utils.showSuccessFeedback('Placed what fit before each due date.');
            utils.notifyDataChanged();
            await loadCalendar();
        } catch (e) {
            utils.showErrorFeedback(e?.message || 'Could not fill the week.');
        }
    });
    document.getElementById('calSaveItem')?.addEventListener('click', () => {
        void saveEditor();
    });
    document.getElementById('calParkItem')?.addEventListener('click', () => {
        void parkEditor();
    });
    document.getElementById('calRemoveItem')?.addEventListener('click', () => {
        void removeEditor();
    });
    document.getElementById('calNewLecture')?.addEventListener('click', () => {
        resetEditor();
    });
    document.getElementById('calAskCluny')?.addEventListener('click', () => {
        // Ask about this week or this event from the editor. Never auto-placement.
        // Ask about this month stays a seeded question, never Fill week.
        const title = (document.getElementById('calEventTitle')?.value || '').trim() || 'this';
        const date = editor.occurrenceDate || String(document.getElementById('calEventStart')?.value || '').slice(0, 10);
        const start = document.getElementById('calEventStart')?.value || '';
        const end = document.getElementById('calEventEnd')?.value || '';
        const question = date
            ? `What should I know about ${title} on ${date}?`
            : `What should I know about ${title}?`;
        const focus = {
            title,
            date,
            kind: editor.kind,
            id: editor.id,
            start_at: start,
            end_at: end,
        };
        document.dispatchEvent(new CustomEvent('kosistenz:open-cluny', { detail: { question, focus } }));
    });
    document.getElementById('calBlockStatus')?.addEventListener('click', (e) => {
        const chip = e.target.closest('[data-status]');
        if (!chip) return;
        setStatusSelection(chip.getAttribute('data-status'));
    });
    document.getElementById('calImportIcs')?.addEventListener('click', () => {
        void importIcs();
    });
    document.getElementById('calPasteIcs')?.addEventListener('click', () => {
        void pasteIcsButton();
    });
    ['calDayStart', 'calDayEnd'].forEach((id) => {
        const field = document.getElementById(id);
        field?.addEventListener('change', () => { void saveAwake(); });
        field?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                void saveAwake();
            }
        });
    });
    document.getElementById('calIcsUrl')?.addEventListener('paste', (e) => {
        const dt = e.clipboardData;
        if (!dt) return;
        const raw = dt.getData('text/uri-list') || dt.getData('text/plain');
        if (!raw) return;
        e.preventDefault();
        void applyPastedCalendar(raw);
    });
    document.addEventListener('paste', (e) => {
        const tab = document.getElementById('calendarTab');
        if (!tab?.classList.contains('active')) return;
        const tag = (e.target?.tagName || '').toLowerCase();
        if (tag === 'input' || tag === 'textarea' || e.target?.isContentEditable) return;
        const dt = e.clipboardData;
        if (!dt) return;
        const raw = dt.getData('text/uri-list') || dt.getData('text/plain');
        if (!raw) return;
        e.preventDefault();
        void applyPastedCalendar(raw);
    });
    document.getElementById('calImportApple')?.addEventListener('click', importApple);
    document.getElementById('calEventWeekdays')?.addEventListener('click', (e) => {
        const chip = e.target.closest('.work-day-chip');
        if (!chip) return;
        chip.classList.toggle('is-selected');
    });
    document.getElementById('calMonthGrid')?.addEventListener('click', (e) => {
        const cell = e.target.closest('[data-date]');
        if (cell) openWeekForDate(cell.getAttribute('data-date'));
    });
    document.getElementById('calYearGrid')?.addEventListener('click', (e) => {
        const monthHead = e.target.closest('[data-jump-month]');
        if (monthHead) {
            monthCursor = { year: yearCursor, month: Number(monthHead.getAttribute('data-jump-month')) };
            setCalView('month');
            void loadMonth();
            return;
        }
        const cell = e.target.closest('[data-date]');
        if (cell) openWeekForDate(cell.getAttribute('data-date'));
    });
    document.addEventListener('kosistenz:calendar-imported', (e) => {
        const status = document.getElementById('calImportStatus');
        const detail = e.detail || {};
        if (status) {
            status.textContent = detail.error
                ? detail.error
                : `Apple calendars: ${detail.created || 0} new, ${detail.updated || 0} updated.`;
        }
        void loadCalendar();
    });
    document.addEventListener('kosistenz:data-changed', () => {
        if (document.getElementById('calendarTab')?.classList.contains('active')) {
            void loadCalendar();
        }
    });
    window.kosistenzImportIcsText = (raw) => {
        void applyPastedCalendar(raw);
        return true;
    };
}

export async function onCalendarTabShown() {
    if (!weekStart) weekStart = mondayISO();
    defaultEventTimes();
    await loadCalendar();
}
