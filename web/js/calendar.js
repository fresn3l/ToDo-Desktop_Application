/**
 * Week clock — hard events, imported dues, Fill week.
 */

import * as utils from './utils.js';

let weekStart = null;

function mondayISO(d = new Date()) {
    const day = new Date(d.getFullYear(), d.getMonth(), d.getDate());
    const offset = (day.getDay() + 6) % 7;
    day.setDate(day.getDate() - offset);
    return utils.localISODate(day);
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

function minutesFromMidnight(iso, dayStartHour) {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return 0;
    return d.getHours() * 60 + d.getMinutes() - dayStartHour * 60;
}

function parseHHMM(raw) {
    const [h, m] = String(raw || '07:00').split(':').map(Number);
    return { hour: h || 7, minute: m || 0 };
}

function hourRange(settings) {
    const start = parseHHMM(settings?.day_start || '07:00');
    const end = parseHHMM(settings?.day_end || '22:00');
    return { startHour: start.hour, endHour: Math.max(start.hour + 1, end.hour) };
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
    const { startHour, endHour } = hourRange(settings);
    const span = (endHour - startHour) * 60;
    const top = Math.max(0, minutesFromMidnight(item.start_at, startHour));
    const start = new Date(item.start_at);
    const end = new Date(item.end_at);
    const dur = Math.max(20, (end - start) / 60000);
    const height = Math.max(18, (dur / span) * 100);
    const topPct = (top / span) * 100;
    const kind = item.kind === 'hard' ? 'hard' : item.kind === 'workout' ? 'workout' : 'work';
    const locked = item.status === 'locked';
    return `<button type="button" class="cal-block is-${kind}${locked ? ' is-locked' : ''}"
        style="top:${topPct}%;height:${height}%"
        data-id="${utils.escapeHtml(item.id || '')}"
        data-kind="${kind}"
        data-status="${utils.escapeHtml(item.status || '')}"
        title="${utils.escapeHtml(blockLabel(item))}">${utils.escapeHtml(blockLabel(item))}</button>`;
}

function renderGrid(week) {
    const root = document.getElementById('calGrid');
    const label = document.getElementById('calWeekLabel');
    if (!root) return;
    const settings = week.settings || {};
    const { startHour, endHour } = hourRange(settings);
    const hours = [];
    for (let h = startHour; h < endHour; h += 1) hours.push(h);
    if (label) {
        const start = week.week_start || '';
        const end = week.week_end || '';
        label.textContent = start && end ? `${start} – ${end}` : 'This week';
    }
    const hourCol = `<div class="cal-hours">${hours.map((h) => `<span>${String(h).padStart(2, '0')}:00</span>`).join('')}</div>`;
    const days = (week.days || [])
        .map((day) => {
            const items = [...(day.events || []), ...(day.blocks || [])];
            return `<div class="cal-day${day.is_today ? ' is-today' : ''}" data-date="${utils.escapeHtml(day.date)}">
                <header class="cal-day-head"><strong>${utils.escapeHtml(day.weekday)}</strong><span>${utils.escapeHtml(day.date.slice(8))}</span></header>
                <div class="cal-day-body">${items.map((item) => renderBlock(item, settings)).join('')}</div>
            </div>`;
        })
        .join('');
    root.innerHTML = `${hourCol}<div class="cal-days">${days}</div>`;
}

function renderUnplaced(items) {
    const root = document.getElementById('calUnplaced');
    if (!root) return;
    if (!items?.length) {
        root.innerHTML = '<p class="checklist-hint small">Inbox is clear — or items need an estimate.</p>';
        return;
    }
    root.innerHTML = items
        .map((item) => {
            const due = item.due_at ? String(item.due_at).replace('T', ' ').slice(0, 16) : 'No due';
            const mins = item.remaining_minutes || item.estimate_minutes || 0;
            return `<article class="cal-unplaced-item">
                <h4>${utils.escapeHtml(item.title)}</h4>
                <p>${utils.escapeHtml(due)} · ${mins} min left</p>
            </article>`;
        })
        .join('');
}

async function loadWeek() {
    if (!weekStart) weekStart = mondayISO();
    if (typeof eel === 'undefined' || !eel.get_week) return;
    try {
        const week = await eel.get_week(weekStart)();
        weekStart = week.week_start || weekStart;
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

function bindGrid() {
    document.querySelectorAll('.cal-block[data-kind="work"], .cal-block[data-kind="workout"]').forEach((btn) => {
        btn.addEventListener('click', async (e) => {
            e.stopPropagation();
            const id = btn.getAttribute('data-id');
            const status = btn.getAttribute('data-status');
            const next = status === 'locked' ? 'proposed' : status === 'done' ? 'proposed' : 'locked';
            try {
                if (status === 'skipped') await eel.set_block_status(id, 'proposed')();
                else if (e.shiftKey) await eel.set_block_status(id, 'skipped')();
                else if (e.altKey) await eel.set_block_status(id, 'done')();
                else await eel.set_block_status(id, next)();
                utils.notifyDataChanged();
                await loadWeek();
            } catch (err) {
                utils.showErrorFeedback(err?.message || 'Could not update that block.');
            }
        });
    });
    document.querySelectorAll('.cal-block[data-kind="hard"]').forEach((btn) => {
        btn.addEventListener('click', async (e) => {
            e.stopPropagation();
            if (!window.confirm('Remove this lecture / hard event?')) return;
            try {
                await eel.delete_calendar_event(btn.getAttribute('data-id'))();
                utils.notifyDataChanged();
                await loadWeek();
            } catch (err) {
                utils.showErrorFeedback(err?.message || 'Could not delete that event.');
            }
        });
    });
}

async function addLecture() {
    const title = document.getElementById('calEventTitle')?.value?.trim();
    const start = fromLocalInput(document.getElementById('calEventStart')?.value);
    const end = fromLocalInput(document.getElementById('calEventEnd')?.value);
    if (!title) {
        utils.showErrorFeedback('Name the lecture first.');
        return;
    }
    if (!start || !end) {
        utils.showErrorFeedback('Set start and end times.');
        return;
    }
    try {
        await eel.create_calendar_event(title, start, end, selectedLectureDays())();
        const titleEl = document.getElementById('calEventTitle');
        if (titleEl) titleEl.value = '';
        utils.showSuccessFeedback('Saved on the clock.');
        utils.notifyDataChanged();
        await loadWeek();
    } catch (e) {
        utils.showErrorFeedback(e?.message || 'Could not save that event.');
    }
}

async function importIcs() {
    const status = document.getElementById('calImportStatus');
    const url = document.getElementById('calIcsUrl')?.value?.trim();
    if (!url) {
        utils.showErrorFeedback('Paste the class calendar URL.');
        return;
    }
    if (status) status.textContent = 'Importing…';
    try {
        const result = await eel.import_ics_url(url)();
        if (status) {
            status.textContent = `Imported ${result.created || 0} new, updated ${result.updated || 0}. Due dates only — not busy time.`;
        }
        utils.showSuccessFeedback('Due dates are in the unplaced list.');
        utils.notifyDataChanged();
        await loadWeek();
    } catch (e) {
        if (status) status.textContent = '';
        utils.showErrorFeedback(e?.message || 'Could not import that calendar.');
    }
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

function defaultEventTimes() {
    const start = document.getElementById('calEventStart');
    const end = document.getElementById('calEventEnd');
    if (!start || start.value) return;
    const d = new Date();
    d.setMinutes(0, 0, 0);
    d.setHours(9, 30, 0, 0);
    start.value = toLocalInput(d);
    const e = new Date(d.getTime() + 50 * 60000);
    if (end) end.value = toLocalInput(e);
}

export function setupCalendar() {
    document.getElementById('calPrevWeek')?.addEventListener('click', () => {
        weekStart = shiftWeek(-7);
        void loadWeek();
    });
    document.getElementById('calNextWeek')?.addEventListener('click', () => {
        weekStart = shiftWeek(7);
        void loadWeek();
    });
    document.getElementById('calThisWeek')?.addEventListener('click', () => {
        weekStart = mondayISO();
        void loadWeek();
    });
    document.getElementById('calFillWeek')?.addEventListener('click', async () => {
        try {
            await eel.fill_week(weekStart || mondayISO())();
            utils.showSuccessFeedback('Placed what fit before each due date.');
            utils.notifyDataChanged();
            await loadWeek();
        } catch (e) {
            utils.showErrorFeedback(e?.message || 'Could not fill the week.');
        }
    });
    document.getElementById('calAddEvent')?.addEventListener('click', () => {
        void addLecture();
    });
    document.getElementById('calImportIcs')?.addEventListener('click', () => {
        void importIcs();
    });
    document.getElementById('calImportApple')?.addEventListener('click', importApple);
    document.getElementById('calEventWeekdays')?.addEventListener('click', (e) => {
        const chip = e.target.closest('.work-day-chip');
        if (!chip) return;
        chip.classList.toggle('is-selected');
    });
    document.addEventListener('kosistenz:calendar-imported', (e) => {
        const status = document.getElementById('calImportStatus');
        const detail = e.detail || {};
        if (status) {
            status.textContent = detail.error
                ? detail.error
                : `Apple calendars: ${detail.created || 0} new, ${detail.updated || 0} updated.`;
        }
        void loadWeek();
    });
    document.addEventListener('kosistenz:data-changed', () => {
        if (document.getElementById('calendarTab')?.classList.contains('active')) {
            void loadWeek();
        }
    });
}

export async function onCalendarTabShown() {
    if (!weekStart) weekStart = mondayISO();
    defaultEventTimes();
    await loadWeek();
}
