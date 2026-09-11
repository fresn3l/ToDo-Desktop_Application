/**
 * Week clock — hard events, imported dues, Fill week.
 */

import * as utils from './utils.js';
import { callEel } from './lazy.js';

let weekStart = null;
let calView = 'week';
let monthCursor = { year: new Date().getFullYear(), month: new Date().getMonth() + 1 };
let yearCursor = new Date().getFullYear();
let lastSettings = {};
let editor = { mode: 'idle', kind: 'hard', id: '', workItemId: '', status: 'proposed', occurrenceDate: '', minutes: 60 };
let dragState = null;
let lastWeek = null;
let dueMenuChip = null;

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
    document.getElementById('calTodayRail')?.classList.toggle('is-hidden', calView !== 'week');
    document.querySelector('.cal-week-shell')?.classList.toggle('is-week', calView === 'week');
    document.getElementById('calMonthGrid')?.classList.toggle('is-hidden', calView !== 'month');
    document.getElementById('calYearGrid')?.classList.toggle('is-hidden', calView !== 'year');
    // Month and year views hide the week-clock hint.
    document.getElementById('calClockHint')?.classList.toggle('is-hidden', calView !== 'week');
    // Month and year views show the event / placed / due legend.
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
    if (cell.event_count) extra.push('event');
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
    try {
        const payload = await callEel('get_month', monthCursor.year, monthCursor.month);
        monthCursor = { year: payload.year, month: payload.month };
        renderMonthGrid(payload);
        renderUnplaced(payload.unplaced || [], payload.unplaced_total);
        paintAwakeFields(payload.settings);
        paintFeedToggles(payload.feeds || []);
    } catch (e) {
        console.error(e);
        const root = document.getElementById('calMonthGrid');
        if (root) root.innerHTML = '<p class="checklist-error">Could not load the month.</p>';
    }
}

async function loadYear() {
    try {
        const payload = await callEel('get_year', yearCursor);
        yearCursor = payload.year;
        renderYearGrid(payload);
        renderUnplaced(payload.unplaced || [], payload.unplaced_total);
        paintAwakeFields(payload.settings);
        paintFeedToggles(payload.feeds || []);
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
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}${pad(d.getMinutes())}`;
}

function fromLocalInput(value) {
    const raw = String(value || '').trim();
    if (!raw) return '';
    const match = raw.match(/^(\d{4}-\d{2}-\d{2})(?:[T ](\d{1,2}):?(\d{2}))?/);
    if (!match) {
        return raw.length === 16 && raw.includes('T') ? `${raw}:00` : raw;
    }
    const hour = String(match[2] || '00').padStart(2, '0');
    const minute = match[3] || '00';
    return `${match[1]}T${hour}:${minute}:00`;
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

function selectedEventDays() {
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

function shortTitle(title, fallback = 'Due') {
    const raw = String(title || '').trim() || fallback;
    const short = raw.replace(/\s*\[[^\]]+\]\s*/g, ' ').replace(/\s+/g, ' ').trim();
    return short || raw;
}

function dueParts(due) {
    const title = String(due?.title || 'Due');
    const course = String(due?.course || '').trim();
    return { title, course, short: shortTitle(title) };
}

function renderDueChip(due) {
    const parts = dueParts(due);
    const done = due.status === 'done';
    const overdue = due.is_overdue;
    const hue = Number(due.hue);
    const hueStyle = Number.isFinite(hue) ? `--due-h:${hue}` : '';
    const badge = parts.course
        ? `<span class="cal-course-badge">${utils.escapeHtml(parts.course)}</span>`
        : '';
    return `<button type="button" class="cal-due-chip${done ? ' is-done' : ''}${overdue ? ' is-overdue' : ''}"
        style="${hueStyle}"
        data-id="${utils.escapeHtml(due.id || '')}"
        data-title="${utils.escapeHtml(parts.title)}"
        data-status="${utils.escapeHtml(due.status || 'open')}"
        data-due-at="${utils.escapeHtml(due.due_at || '')}"
        data-minutes="${Number(due.estimate_minutes || 60) || 60}"
        title="${utils.escapeHtml(parts.title)}">${badge}<span class="cal-due-chip-title">${utils.escapeHtml(parts.short)}</span></button>`;
}

function renderDueStrip(dues, date) {
    const iso = utils.escapeHtml(date || '');
    if (!dues.length) {
        return `<div class="cal-due-strip is-empty" data-date="${iso}"></div>`;
    }
    const n = dues.length;
    const first = dueParts(dues[0]);
    const hue = Number(dues[0].hue);
    const hueStyle = Number.isFinite(hue) ? `style="--due-h:${hue}"` : '';
    const tip = n === 1 ? first.title : `${n} due`;
    return `<button type="button" class="cal-due-strip" data-date="${iso}" data-count="${n}" ${hueStyle}
        title="${utils.escapeHtml(tip)}">
        <span class="cal-due-count">${n}</span>
        <span class="cal-due-strip-label">${utils.escapeHtml(first.short)}</span>
    </button>`;
}

function renderBlock(item, settings) {
    const { startMin, span } = clockWindow(settings);
    const top = Math.max(0, minutesFromClock(item.start_at, startMin));
    const start = new Date(item.start_at);
    const end = new Date(item.end_at);
    const rawMin = (end - start) / 60000;
    const dur = Number.isFinite(rawMin) && rawMin > 0 ? rawMin : 15;
    const height = (dur / span) * 100;
    const topPct = (top / span) * 100;
    const kind = item.kind === 'hard' ? 'hard' : item.kind === 'workout' ? 'workout' : 'work';
    const locked = item.status === 'locked';
    const done = item.status === 'done';
    const missed = item.status === 'missed' || item.status === 'skipped';
    const selected = editor.id && editor.id === item.id ? ' is-selected' : '';
    const short = dur < 45 ? ' is-short' : '';
    const tiny = dur < 20 ? ' is-tiny' : '';
    const timeLabel = Number.isNaN(start.getTime())
        ? ''
        : formatMilitary(start.getHours() * 60 + start.getMinutes());
    return `<button type="button" class="cal-block is-${kind}${locked ? ' is-locked' : ''}${done ? ' is-done' : ''}${missed ? ' is-missed' : ''}${selected}${short}${tiny}"
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
        title="${utils.escapeHtml(blockLabel(item))}"><span class="cal-block-time">${utils.escapeHtml(timeLabel)}</span><span class="cal-block-title">${utils.escapeHtml(shortTitle(item.title || '', 'Block'))}</span></button>`;
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
            const dues = day.dues || [];
            return `<div class="cal-day${day.is_today ? ' is-today' : ''}" data-date="${utils.escapeHtml(day.date)}">
                <header class="cal-day-head"><strong>${utils.escapeHtml(day.weekday)}</strong><span>${utils.escapeHtml(day.date.slice(8))}</span></header>
                ${renderDueStrip(dues, day.date)}
                <div class="cal-day-body" style="--cal-hour-pct:${hourPct}%;--cal-hour-offset:${offsetPct}%">${hourLines}${items.map((item) => renderBlock(item, settings)).join('')}</div>
            </div>`;
        })
        .join('');
    root.innerHTML = `${hourCol}<div class="cal-week-board"><div class="cal-days">${days}</div></div>`;
}

function agendaKind(item) {
    if (item.kind === 'hard') return 'Event';
    if (item.kind === 'workout') return 'Gym';
    return 'Work';
}

function agendaTime(item) {
    const start = new Date(item.start_at);
    if (Number.isNaN(start.getTime())) return '';
    const pad = (n) => String(n).padStart(2, '0');
    return `${pad(start.getHours())}:${pad(start.getMinutes())}`;
}

function renderTodayRail(today) {
    const root = document.getElementById('calTodayRail');
    if (!root) return;
    if (!today) {
        root.innerHTML = '';
        return;
    }
    root.setAttribute('data-date', today.date || '');
    const overdue = today.overdue || [];
    const dues = today.dues || [];
    const items = today.items || [];
    const overdueHtml = overdue.length
        ? `<h4>Overdue</h4><div class="cal-due-list">${overdue.map((due) => renderDueChip(due)).join('')}</div>`
        : '';
    const duesHtml = dues.length
        ? `<h4>Due today</h4><div class="cal-due-list">${dues.map((due) => renderDueChip(due)).join('')}</div>`
        : '<h4>Due today</h4><p class="cal-due-empty">No dues</p>';
    const clockHtml = items.length
        ? `<h4>On the clock</h4><ul class="cal-today-agenda">${items.map((item) => {
            const kind = item.kind === 'hard' ? 'hard' : item.kind === 'workout' ? 'workout' : 'work';
            const outcome = item.status === 'done' ? ' is-done' : (item.status === 'missed' || item.status === 'skipped' ? ' is-missed' : '');
            return `<li class="is-${kind}${outcome}"><span>${utils.escapeHtml(agendaTime(item))}</span><b>${utils.escapeHtml(shortTitle(item.title || '', 'Block'))}</b><em>${utils.escapeHtml(agendaKind(item))}</em></li>`;
        }).join('')}</ul>`
        : '<h4>On the clock</h4><p class="cal-due-empty">Nothing placed yet. Drag a due onto the week clock to time-block it.</p>';
    root.innerHTML = `
        <header>
            <p class="eyebrow">Today</p>
            <h3>${utils.escapeHtml(today.label || today.weekday || 'Today')}</h3>
            <p class="cal-today-awake">${utils.escapeHtml(formatHHMM(today.day_start))}–${utils.escapeHtml(formatHHMM(today.day_end))}</p>
        </header>
        ${overdueHtml}
        ${duesHtml}
        ${clockHtml}
    `;
}

function paintFeedToggles(feeds) {
    const root = document.getElementById('calFeedToggles');
    if (!root) return;
    const rows = (feeds || []).filter((feed) => feed.id);
    if (!rows.length) {
        root.innerHTML = '';
        return;
    }
    root.innerHTML = `<h4>Show calendars</h4>` + rows.map((feed) => {
        const on = feed.enabled !== false;
        const host = (() => {
            try {
                const href = String(feed.url || '').replace(/^webcal:/i, 'https:');
                return href ? new URL(href).hostname.replace(/^www\./, '') : '';
            } catch (_) {
                return '';
            }
        })();
        const label = host || feed.title || feed.id;
        return `<label class="cal-feed-toggle">
            <input type="checkbox" data-feed-id="${utils.escapeHtml(feed.id || '')}" ${on ? 'checked' : ''}>
            <span title="${utils.escapeHtml(feed.title || feed.id || '')}">${utils.escapeHtml(label)}</span>
        </label>`;
    }).join('');
    root.querySelectorAll('input[data-feed-id]').forEach((input) => {
        input.addEventListener('change', async () => {
            try {
                await callEel('set_calendar_feed_enabled', input.getAttribute('data-feed-id'), input.checked);
                utils.notifyDataChanged();
                await loadCalendar();
            } catch (err) {
                utils.showErrorFeedback('Could not update that calendar.');
            }
        });
    });
}

async function refreshFeedToggles() {
    try {
        paintFeedToggles((await callEel('list_calendar_feeds')).feeds || []);
    } catch (_) {
        /* eel not ready */
    }
}

function renderUnplaced(items, total) {
    const root = document.getElementById('calUnplaced');
    const block = document.getElementById('calUnplacedBlock');
    if (!root) return;
    if (block) block.hidden = false;
    if (!items?.length) {
        root.innerHTML = '<p class="empty-state empty-state--line">Nothing to place.</p>';
        return;
    }
    const extra = Number(total || 0) > items.length
        ? `<p class="checklist-hint small">${Number(total) - items.length} more unplaced. Fill week still uses the rest.</p>`
        : '';
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
        .join('') + extra;
    root.querySelectorAll('.cal-unplaced-item').forEach((btn) => {
        btn.addEventListener('pointerdown', onDuePointerDown);
        btn.addEventListener('pointermove', onDuePointerMove);
        btn.addEventListener('pointerup', onDuePointerUp);
        btn.addEventListener('pointercancel', onDuePointerUp);
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            if (btn.dataset.didDrag === '1') {
                btn.dataset.didDrag = '';
                return;
            }
            openUnplaced(btn);
        });
    });
}

async function loadWeek() {
    if (!weekStart) weekStart = mondayISO();
    try {
        const week = await callEel('get_week', weekStart);
        weekStart = week.week_start || weekStart;
        lastWeek = week;
        lastSettings = week.settings || {};
        paintAwakeFields(lastSettings);
        renderGrid(week);
        renderTodayRail(week.today);
        hideDayDues();
        paintFeedToggles(week.feeds || week.settings?.feeds || []);
        renderUnplaced(week.unplaced || [], week.unplaced_total);
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
    const outcome = selectedBarOutcome();
    if (outcome === 'attended') return 'done';
    if (outcome === 'missed') return 'missed';
    return document.querySelector('#calBlockStatus .work-day-chip.is-selected')?.getAttribute('data-status') || 'proposed';
}

function selectedBarOutcome() {
    return document.querySelector('#calBarOutcome .work-day-chip.is-selected')?.getAttribute('data-outcome') || '';
}

function setOutcomeSelection(status) {
    const key = status === 'done' ? 'attended' : (status === 'missed' || status === 'skipped' ? 'missed' : '');
    document.querySelectorAll('#calBarOutcome .work-day-chip').forEach((btn) => {
        btn.classList.toggle('is-selected', !!key && btn.getAttribute('data-outcome') === key);
    });
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
    const fields = document.getElementById('calEditorFields');
    const weekdays = document.getElementById('calEventWeekdays');
    const status = document.getElementById('calBlockStatus');
    const outcome = document.getElementById('calBarOutcome');
    const park = document.getElementById('calParkItem');
    const remove = document.getElementById('calRemoveItem');
    const fresh = document.getElementById('calNewLecture');
    const ask = document.getElementById('calAskCluny');
    const save = document.getElementById('calSaveItem');
    const mode = editor.mode;
    const isIdle = mode === 'idle';
    const isNew = mode === 'new';
    const isHard = mode === 'hard' || isNew;
    const isUnplaced = mode === 'unplaced';
    const isBlock = mode === 'work' || mode === 'workout';
    if (heading) {
        heading.textContent = isIdle
            ? 'Clock'
            : isNew
                ? 'Add event'
                : isUnplaced
                    ? 'Place work'
                    : (document.getElementById('calEventTitle')?.value?.trim() || 'Edit');
    }
    if (hint) {
        hint.textContent = isIdle
            ? 'Drag Unplaced onto the clock, or Add event for a meeting.'
            : isNew
                ? 'Busy time — a meeting, hold, or recurring block. Work stays in Unplaced until you drag or Fill week.'
                : isUnplaced
                    ? 'Drag onto the clock, or set a start and Place. This is not a new event.'
                    : 'Alt marks attended. Shift marks did not complete. Drag to move.';
    }
    toggleHidden(fields, isIdle);
    toggleHidden(weekdays, !isHard || isIdle);
    toggleHidden(status, !isBlock);
    toggleHidden(outcome, isIdle || isNew || isUnplaced || !editor.id);
    toggleHidden(park, !(isBlock || isUnplaced));
    toggleHidden(remove, isIdle || isNew || isUnplaced);
    toggleHidden(fresh, isNew);
    toggleHidden(ask, isIdle || isNew || isUnplaced || !editor.id);
    toggleHidden(save, isIdle);
    if (fresh) fresh.textContent = isIdle ? 'Add event' : 'Add another';
    if (save) {
        save.textContent = isUnplaced ? 'Place' : 'Save';
    }
    if (park) park.textContent = isUnplaced ? 'Leave in All Work' : 'Save for later';
}

function clearEditorFields() {
    const titleEl = document.getElementById('calEventTitle');
    if (titleEl) titleEl.value = '';
    setWeekdaySelection([]);
    setStatusSelection('proposed');
    setOutcomeSelection('');
    const start = document.getElementById('calEventStart');
    const end = document.getElementById('calEventEnd');
    if (start) start.value = '';
    if (end) end.value = '';
}

function resetEditor() {
    editor = { mode: 'idle', kind: 'hard', id: '', workItemId: '', status: 'proposed', occurrenceDate: '', minutes: 60 };
    clearEditorFields();
    paintEditor();
    document.querySelectorAll('.cal-block.is-selected, .cal-unplaced-item.is-selected').forEach((el) => {
        el.classList.remove('is-selected');
    });
}

function startNewEvent() {
    editor = { mode: 'new', kind: 'hard', id: '', workItemId: '', status: 'proposed', occurrenceDate: '', minutes: 60 };
    clearEditorFields();
    defaultEventTimes(true);
    paintEditor();
    document.querySelectorAll('.cal-block.is-selected, .cal-unplaced-item.is-selected').forEach((el) => {
        el.classList.remove('is-selected');
    });
    document.getElementById('calEventTitle')?.focus();
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
    setStatusSelection(editor.status === 'done' || editor.status === 'missed' || editor.status === 'skipped' ? 'locked' : editor.status);
    setOutcomeSelection(editor.status);
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
    setOutcomeSelection('');
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
            void onExistingBarClick(e, btn);
        });
    });
    document.querySelectorAll('.cal-day-body').forEach((body) => {
        body.addEventListener('click', (e) => {
            if (e.target.closest('.cal-block')) return;
            e.stopPropagation();
            if (editor.mode === 'new' || editor.mode === 'unplaced') {
                applyGridTime(e, body);
                return;
            }
            // Empty-grid click is not capture. Add event is an explicit control.
        });
    });
    bindDueChips(document);
    document.querySelectorAll('.cal-due-strip:not(.is-empty)').forEach((btn) => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            showDayDues(btn.getAttribute('data-date'), btn);
        });
    });
}

async function onExistingBarClick(e, btn) {
    const kind = btn.getAttribute('data-kind') || 'work';
    const id = btn.getAttribute('data-id') || '';
    const occ = btn.getAttribute('data-occurrence-date') || '';
    const isWork = kind === 'work' || kind === 'workout';
    if (id && (e.altKey || e.shiftKey)) {
        try {
            await callEel('set_bar_outcome', id, e.altKey ? 'attended' : 'missed', occ);
            utils.showSuccessFeedback(e.altKey ? 'Marked attended.' : 'Marked did not complete.');
            utils.notifyDataChanged();
            await loadCalendar();
        } catch (err) {
            utils.showErrorFeedback(err?.message || 'Could not update that bar.');
        }
        return;
    }
    if (isWork && id && !e.metaKey) {
        try {
            if (btn.getAttribute('data-status') !== 'locked') {
                await callEel('set_block_status', id, 'locked');
                btn.setAttribute('data-status', 'locked');
                btn.classList.add('is-locked');
            }
        } catch (err) {
            utils.showErrorFeedback(err?.message || 'Could not update that bar.');
        }
    }
    openEditorFromBlock(btn);
}

function applyGridTime(e, body) {
    const day = body.closest('.cal-day')?.getAttribute('data-date');
    if (!day) return;
    const rect = body.getBoundingClientRect();
    const { startMin, span } = clockWindow(lastSettings);
    let mins = Math.round((((e.clientY - rect.top) / rect.height) * span) / 15) * 15;
    const dur = editor.mode === 'unplaced' ? Math.max(15, editor.minutes || 60) : 50;
    mins = Math.max(0, Math.min(span - dur, mins));
    const [y, m, d] = day.split('-').map(Number);
    const start = new Date(y, m - 1, d, 0, 0, 0);
    start.setMinutes(startMin + mins);
    const end = new Date(start.getTime() + dur * 60000);
    const startEl = document.getElementById('calEventStart');
    const endEl = document.getElementById('calEventEnd');
    if (startEl) startEl.value = toLocalInput(start);
    if (endEl) endEl.value = toLocalInput(end);
}

function bindDueChips(root) {
    (root || document).querySelectorAll('.cal-due-chip').forEach((btn) => {
        if (btn.dataset.bound === '1') return;
        btn.dataset.bound = '1';
        btn.addEventListener('pointerdown', onDuePointerDown);
        btn.addEventListener('pointermove', onDuePointerMove);
        btn.addEventListener('pointerup', onDuePointerUp);
        btn.addEventListener('pointercancel', onDuePointerUp);
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            if (btn.dataset.didDrag === '1') {
                btn.dataset.didDrag = '';
                return;
            }
            showDueMenu(btn);
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
    const day = hit.closest('.cal-day')?.getAttribute('data-date') || hit.getAttribute('data-date');
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
    if (!dragState || dragState.kind === 'due' || e.pointerId !== dragState.pointerId) return;
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
            await callEel('update_calendar_event', state.id, '', toApiIso(start), toApiIso(end), null, state.occurrenceDate);
        } else {
            await callEel('update_schedule_block', state.id, '', toApiIso(start), toApiIso(end), '');
        }
        utils.notifyDataChanged();
        await loadCalendar();
        utils.showSuccessFeedback('Moved.');
    } catch (err) {
        utils.showErrorFeedback(err?.message || 'Could not move that.');
        await loadCalendar();
    }
}

function hideDayDues() {
    const panel = document.getElementById('calDayDues');
    if (!panel) return;
    panel.hidden = true;
    panel.classList.add('is-hidden');
}

function showDayDues(date, anchor) {
    const panel = document.getElementById('calDayDues');
    const list = document.getElementById('calDayDuesList');
    const heading = document.getElementById('calDayDuesHeading');
    if (!panel || !list) return;
    const day = (lastWeek?.days || []).find((row) => row.date === date);
    const dues = day?.dues || [];
    if (!dues.length) {
        hideDayDues();
        return;
    }
    const when = day?.date ? new Date(`${day.date}T12:00:00`) : null;
    const label = when && !Number.isNaN(when.getTime())
        ? when.toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' })
        : (day?.weekday || 'Due');
    if (heading) heading.textContent = label;
    list.innerHTML = dues.map((due) => renderDueChip(due)).join('');
    bindDueChips(list);
    hideDueMenu();
    panel.setAttribute('data-date', date || '');
    panel.hidden = false;
    panel.classList.remove('is-hidden');
    const rect = (anchor || document.body).getBoundingClientRect();
    const width = 280;
    const left = Math.min(Math.max(8, rect.left), window.innerWidth - width - 8);
    const top = Math.min(rect.bottom + 8, window.innerHeight - 240);
    panel.style.left = `${left}px`;
    panel.style.top = `${Math.max(8, top)}px`;
    panel.style.width = `${width}px`;
}

function hideDueMenu() {
    const menu = document.getElementById('calDueMenu');
    if (menu) {
        menu.hidden = true;
        menu.classList.add('is-hidden');
    }
    dueMenuChip = null;
}

function showDueMenu(chip) {
    const menu = document.getElementById('calDueMenu');
    if (!menu) return;
    dueMenuChip = chip;
    const done = chip.getAttribute('data-status') === 'done';
    menu.querySelector('[data-act="done"]')?.classList.toggle('is-hidden', done);
    menu.querySelector('[data-act="reopen"]')?.classList.toggle('is-hidden', !done);
    menu.hidden = false;
    menu.classList.remove('is-hidden');
    const rect = chip.getBoundingClientRect();
    const left = Math.min(rect.left, window.innerWidth - 220);
    const top = Math.min(rect.bottom + 6, window.innerHeight - 180);
    menu.style.left = `${Math.max(8, left)}px`;
    menu.style.top = `${Math.max(8, top)}px`;
}

function onDuePointerDown(e) {
    if (e.button !== 0) return;
    const btn = e.currentTarget;
    hideDueMenu();
    dragState = {
        kind: 'due',
        el: btn,
        pointerId: e.pointerId,
        originX: e.clientX,
        originY: e.clientY,
        moved: false,
        preview: null,
        id: btn.getAttribute('data-id'),
        title: btn.getAttribute('data-title') || '',
        duration: Math.max(15, Number(btn.getAttribute('data-minutes') || 60) || 60),
        ghost: null,
    };
    try { btn.setPointerCapture(e.pointerId); } catch (_) { /* ignore */ }
}

function onDuePointerMove(e) {
    if (!dragState || dragState.kind !== 'due' || e.pointerId !== dragState.pointerId) return;
    const dx = e.clientX - dragState.originX;
    const dy = e.clientY - dragState.originY;
    if (!dragState.moved && (dx * dx + dy * dy) < 36) return;
    dragState.moved = true;
    dragState.el.dataset.didDrag = '1';
    if (!dragState.ghost) {
        const ghost = document.createElement('div');
        ghost.className = 'cal-due-ghost';
        ghost.textContent = dragState.title;
        document.body.appendChild(ghost);
        dragState.ghost = ghost;
    }
    dragState.ghost.style.left = `${e.clientX + 8}px`;
    dragState.ghost.style.top = `${e.clientY + 8}px`;
    const hit = document.elementFromPoint(e.clientX, e.clientY)?.closest('.cal-day-body');
    document.querySelectorAll('.cal-day-body.is-drop').forEach((el) => el.classList.remove('is-drop'));
    if (!hit) {
        dragState.preview = null;
        return;
    }
    hit.classList.add('is-drop');
    const day = hit.closest('.cal-day')?.getAttribute('data-date') || hit.getAttribute('data-date');
    if (!day) return;
    const rect = hit.getBoundingClientRect();
    const { startMin, span } = clockWindow(lastSettings);
    const dur = Math.min(span, dragState.duration);
    let mins = Math.round((((e.clientY - rect.top) / rect.height) * span) / 15) * 15;
    mins = Math.max(0, Math.min(span - dur, mins));
    dragState.preview = { date: day, minutesFromStart: mins, duration: dur, startMin };
}

async function onDuePointerUp(e) {
    if (!dragState || dragState.kind !== 'due' || e.pointerId !== dragState.pointerId) return;
    const state = dragState;
    dragState = null;
    state.ghost?.remove();
    document.querySelectorAll('.cal-day-body.is-drop').forEach((el) => el.classList.remove('is-drop'));
    try { state.el.releasePointerCapture(e.pointerId); } catch (_) { /* ignore */ }
    if (!state.moved || !state.preview || !state.id) return;
    const [y, m, d] = state.preview.date.split('-').map(Number);
    const start = new Date(y, m - 1, d, 0, 0, 0);
    start.setMinutes(state.preview.startMin + state.preview.minutesFromStart);
    const end = new Date(start.getTime() + state.preview.duration * 60000);
    try {
        await callEel('schedule_work_at', state.id, toApiIso(start), toApiIso(end));
        utils.notifyDataChanged();
        await loadCalendar();
        utils.showSuccessFeedback('Placed on the clock. Due date unchanged.');
    } catch (err) {
        utils.showErrorFeedback(err?.message || 'Could not place that.');
        await loadCalendar();
    }
}

async function runDueMenu(act) {
    const chip = dueMenuChip;
    hideDueMenu();
    if (!chip) return;
    const id = chip.getAttribute('data-id');
    const date = chip.closest('[data-date]')?.getAttribute('data-date')
        || String(chip.getAttribute('data-due-at') || '').slice(0, 10);
    if (!id) return;
    try {
        if (act === 'done') {
            await callEel('finish_work_item', id);
            utils.showSuccessFeedback('Marked done.');
        } else if (act === 'reopen') {
            await callEel('reopen_work_item', id);
            utils.showSuccessFeedback('Reopened.');
        } else if (act === 'place-after') {
            await callEel('place_work_after_lecture', id, date);
            utils.showSuccessFeedback('Placed after the first event.');
        } else if (act === 'todo') {
            document.dispatchEvent(new CustomEvent('kosistenz:open-todo', { detail: { date, itemId: id } }));
            return;
        }
        utils.notifyDataChanged();
        await loadCalendar();
    } catch (err) {
        utils.showErrorFeedback(err?.message || 'Could not update that due.');
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
            await callEel('create_calendar_event', title, start, end, selectedEventDays());
            resetEditor();
            utils.showSuccessFeedback('Saved on the clock.');
        } else if (editor.mode === 'hard') {
            await callEel('update_calendar_event', editor.id, title, start, end, selectedEventDays(), editor.occurrenceDate);
            const outcome = selectedBarOutcome();
            if (outcome) {
                await callEel('set_bar_outcome', editor.id, outcome, editor.occurrenceDate);
            }
            utils.showSuccessFeedback('Saved on the clock.');
        } else if (editor.mode === 'unplaced') {
            await callEel('schedule_work_at', editor.id, start, end);
            resetEditor();
            utils.showSuccessFeedback('Placed on the clock.');
        } else {
            await callEel('update_schedule_block', editor.id, title, start, end, selectedBlockStatus());
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
            await callEel('assign_work_item', editor.id, '');
            resetEditor();
            utils.showSuccessFeedback('Left in All Work.');
        } else if ((editor.mode === 'work' || editor.mode === 'workout') && editor.id) {
            await callEel('park_schedule_block', editor.id);
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
    const hard = editor.mode === 'hard';
    if (!(await utils.askConfirm({
        title: hard ? 'Remove event' : 'Remove from clock',
        message: hard
            ? 'Remove this from the calendar?'
            : 'Take this off the clock? The work stays in your lists.',
        ok: 'Remove',
        danger: true,
    }))) return;
    try {
        if (hard) {
            await callEel('delete_calendar_event', editor.id);
        } else {
            await callEel('delete_schedule_block', editor.id, true);
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
    const start = document.getElementById('calDayStart')?.value;
    const end = document.getElementById('calDayEnd')?.value;
    try {
        const saved = await callEel('save_calendar_settings', { day_start: start, day_end: end });
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
        utils.showSuccessFeedback('Pasted the calendar URL. Import ICS to load events and due dates.');
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
        const result = await callEel('import_pasted_calendar', raw);
        const duesNew = result.created || 0;
        const duesUp = result.updated || 0;
        const clock = result.events_created || 0;
        if (status) {
            status.textContent = `Imported ${duesNew} due date${duesNew === 1 ? '' : 's'} (${duesUp} updated), ${clock} on the clock.`;
        }
        if (clock || duesNew || duesUp) {
            utils.showSuccessFeedback(
                clock
                    ? 'Timed events are on the week clock. Due dates stay as chips.'
                    : 'Due dates are on that day’s To Do and as chips on the week.'
            );
        } else {
            utils.showSuccessFeedback('Imported the feed. No new events in range.');
        }
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
        utils.showErrorFeedback('Paste a calendar URL, or use Paste.');
        return;
    }
    void importPasted(url);
}

export function setupCalendar() {
    setCalView(calView);
    paintEditor();
    document.getElementById('calDueMenu')?.addEventListener('click', (e) => {
        const act = e.target.closest('[data-act]')?.getAttribute('data-act');
        if (act) void runDueMenu(act);
    });
    document.addEventListener('pointerdown', (e) => {
        if (e.target.closest('#calDueMenu') || e.target.closest('.cal-due-chip')) return;
        hideDueMenu();
        if (e.target.closest('#calDayDues') || e.target.closest('.cal-due-strip')) return;
        hideDayDues();
    });
    document.addEventListener('keydown', (e) => {
        if (e.key !== 'Escape') return;
        hideDueMenu();
        hideDayDues();
    });
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
            await callEel('fill_week', weekStart || mondayISO());
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
        startNewEvent();
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
        setOutcomeSelection('');
    });
    document.getElementById('calBarOutcome')?.addEventListener('click', (e) => {
        const chip = e.target.closest('[data-outcome]');
        if (!chip) return;
        const next = chip.classList.contains('is-selected') ? '' : chip.getAttribute('data-outcome');
        setOutcomeSelection(next === 'attended' ? 'done' : next === 'missed' ? 'missed' : '');
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
    if (editor.mode === 'idle') paintEditor();
    await loadCalendar();
}
