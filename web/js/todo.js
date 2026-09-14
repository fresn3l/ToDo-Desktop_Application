/**
 * Work sheet — Today, All, Unplaced, and Due as filters on one list.
 */

import * as utils from './utils.js';
import { formatDuration, liveSeconds, tomorrowISO } from './work.js';
import { loadGoalOptions } from './goals.js';

let tickTimer = null;
let repeatKind = 'daily';
let scopeResolver = null;
let selectedDoDate = null;
let whenDays = [];
let destKind = 'today';
let listFilter = 'today';

function stopTick() {
    if (tickTimer) {
        clearInterval(tickTimer);
        tickTimer = null;
    }
}

function startTick() {
    stopTick();
    tickTimer = setInterval(() => {
        document.querySelectorAll('.work-timer[data-live="1"]').forEach((el) => {
            const started = el.getAttribute('data-started');
            const stored = Number(el.getAttribute('data-stored') || 0);
            const start = started ? new Date(started).getTime() : NaN;
            const seconds = Number.isNaN(start)
                ? stored
                : stored + Math.max(0, Math.floor((Date.now() - start) / 1000));
            el.textContent = formatDuration(seconds);
        });
    }, 1000);
}

function normalizeFilter(raw) {
    if (raw === 'backlog' || raw === 'allwork') return 'all';
    if (raw === 'all' || raw === 'unplaced' || raw === 'due') return raw;
    return 'today';
}

function askScope(copy) {
    const modal = document.getElementById('workScopeModal');
    const text = document.getElementById('workScopeCopy');
    if (!modal || !text) return Promise.resolve('occurrence');
    text.textContent = copy;
    modal.classList.remove('is-hidden');
    modal.hidden = false;
    return new Promise((resolve) => {
        scopeResolver = resolve;
    });
}

function closeScope(result) {
    const modal = document.getElementById('workScopeModal');
    if (modal) {
        modal.classList.add('is-hidden');
        modal.hidden = true;
    }
    if (scopeResolver) {
        const resolve = scopeResolver;
        scopeResolver = null;
        resolve(result);
    }
}

function selectedWeekdays() {
    return [...document.querySelectorAll('#todoWeekdays .work-day-chip.is-selected')].map((btn) =>
        Number(btn.getAttribute('data-day')),
    );
}

function fallbackWhenDays() {
    const names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    const today = new Date();
    const monday = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    const offset = (monday.getDay() + 6) % 7;
    monday.setDate(monday.getDate() - offset);
    const todayIso = utils.localISODate();
    return names.map((label, i) => {
        const day = new Date(monday);
        day.setDate(monday.getDate() + i);
        const iso = utils.localISODate(day);
        const isPast = iso < todayIso;
        const place = new Date(day);
        if (isPast) place.setDate(place.getDate() + 7);
        return {
            weekday: i,
            label,
            date: iso,
            place_date: utils.localISODate(place),
            is_today: iso === todayIso,
            is_past: isPast,
        };
    });
}

function selectedWhenDate() {
    if (destKind === 'allwork') return 'allwork';
    const chip = document.querySelector('#todoWhen .work-day-chip.is-selected');
    return chip?.getAttribute('data-date') || selectedDoDate || utils.localISODate();
}

const WEEKDAY_FULL = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

function addButtonLabel() {
    if (document.getElementById('todoRepeatToggle')?.checked) return 'Save repeating to-do';
    if (listFilter === 'unplaced') return 'Add unplaced';
    if (listFilter === 'due') return 'Add due';
    if (destKind === 'allwork' || listFilter === 'all') return 'Add to All Work';
    const iso = selectedWhenDate();
    const day = whenDays.find((row) => row.place_date === iso);
    if (day?.is_today) return 'Add';
    if (day && Number.isInteger(day.weekday)) return `Add to ${WEEKDAY_FULL[day.weekday] || day.label}`;
    return 'Add';
}

function updateAddButton() {
    const btn = document.getElementById('todoAddBtn');
    if (btn) btn.textContent = addButtonLabel();
}

function updateWhenHint() {
    const hint = document.querySelector('.todo-when-hint');
    if (!hint) return;
    const clock = 'Dated is not on the clock. With minutes, Fill week or drag places it.';
    if (listFilter === 'unplaced') {
        hint.textContent = `Parked with minutes, not on the clock. ${clock}`;
        updateAddButton();
        return;
    }
    if (listFilter === 'due') {
        hint.textContent = 'Due date is the deadline. Dated is not on the clock.';
        updateAddButton();
        return;
    }
    if (destKind === 'allwork' || listFilter === 'all') {
        hint.textContent = `Saved in All Work — not on the clock. ${clock}`;
        updateAddButton();
        return;
    }
    const iso = selectedWhenDate();
    const day = whenDays.find((row) => row.place_date === iso);
    if (!day) {
        hint.textContent = clock;
        updateAddButton();
        return;
    }
    const when = day.is_today ? 'today' : (WEEKDAY_FULL[day.weekday] || day.label);
    hint.textContent = `Dates it ${when}. ${clock}`;
    updateAddButton();
}

function paintDest() {
    document.querySelectorAll('#todoDest [data-dest]').forEach((btn) => {
        const on = btn.getAttribute('data-dest') === destKind;
        btn.classList.toggle('is-selected', on);
        btn.setAttribute('aria-checked', on ? 'true' : 'false');
    });
}

function paintFilter() {
    const tab = document.getElementById('todoTab');
    if (tab) tab.setAttribute('data-work-filter', listFilter);
    document.querySelectorAll('#todoFilter [data-filter]').forEach((btn) => {
        const on = btn.getAttribute('data-filter') === listFilter;
        btn.classList.toggle('is-selected', on);
        btn.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    const input = document.getElementById('todoNewTitle');
    if (input) {
        input.placeholder = listFilter === 'all'
            ? 'A task without a date yet'
            : listFilter === 'due'
                ? 'What’s due'
                : '45 mins board memo';
    }
    if (listFilter === 'all' || listFilter === 'unplaced') destKind = 'allwork';
    else destKind = 'today';
    paintDest();
    updateWhenHint();
}

function paintWhenChips() {
    const root = document.getElementById('todoWhen');
    if (!root) return;
    const current = selectedDoDate;
    root.innerHTML = whenDays
        .map((day) => {
            const date = day.place_date;
            const selected = current ? date === current : day.is_today;
            const classes = ['work-day-chip'];
            if (selected) classes.push('is-selected');
            if (day.is_past) classes.push('is-past');
            if (day.is_today) classes.push('is-today');
            const label = day.is_today ? 'Today' : day.label;
            const title = day.is_today ? 'Today' : day.is_past ? `Next ${day.label}` : day.label;
            return `<button type="button" class="${classes.join(' ')}" role="radio" aria-checked="${selected ? 'true' : 'false'}" data-date="${utils.escapeHtml(date)}" data-weekday="${day.weekday}" title="${utils.escapeHtml(title)}">${utils.escapeHtml(label)}</button>`;
        })
        .join('');
    const selected = root.querySelector('.is-selected');
    selectedDoDate = selected?.getAttribute('data-date') || whenDays.find((row) => row.is_today)?.place_date;
    paintDest();
    updateWhenHint();
}

async function loadWhenChips() {
    try {
        whenDays = typeof eel !== 'undefined' && eel.weekday_dates_this_week
            ? await eel.weekday_dates_this_week()()
            : fallbackWhenDays();
    } catch (e) {
        whenDays = fallbackWhenDays();
    }
    if (!Array.isArray(whenDays) || !whenDays.length) whenDays = fallbackWhenDays();
    paintWhenChips();
}

function currentRepeat() {
    const on = document.getElementById('todoRepeatToggle')?.checked;
    if (!on) return null;
    if (repeatKind === 'daily') return { kind: 'daily' };
    if (repeatKind === 'weekdays') return { kind: 'weekdays' };
    if (repeatKind === 'interval') {
        const n = Number(document.getElementById('todoEveryDays')?.value || 2);
        return { kind: 'interval', every_days: Number.isFinite(n) ? Math.max(2, n) : 2 };
    }
    const weekdays = selectedWeekdays();
    if (!weekdays.length) return { kind: 'daily' };
    return { kind: 'weekly', weekdays };
}

function syncRepeatPanel() {
    const on = document.getElementById('todoRepeatToggle')?.checked;
    document.getElementById('todoRepeatPanel')?.classList.toggle('is-hidden', !on);
    document.getElementById('todoWeekdays')?.classList.toggle('is-hidden', !on || repeatKind !== 'custom');
    document.getElementById('todoIntervalWrap')?.classList.toggle('is-hidden', !on || repeatKind !== 'interval');
    document.querySelectorAll('#todoRepeatKind [data-value]').forEach((btn) => {
        btn.classList.toggle('is-selected', btn.getAttribute('data-value') === repeatKind);
    });
}

function hideAsides() {
    const overdueEl = document.getElementById('todoOverdue');
    const tomorrowEl = document.getElementById('todoTomorrow');
    if (overdueEl) {
        overdueEl.classList.add('is-hidden');
        overdueEl.innerHTML = '';
    }
    if (tomorrowEl) {
        tomorrowEl.classList.add('is-hidden');
        tomorrowEl.innerHTML = '';
    }
}

function itemRow(item, { showDate = false } = {}) {
    const running = item.status === 'active';
    const done = item.status === 'done';
    const seconds = liveSeconds(item);
    const dateBit = showDate && item.scheduled_date
        ? `<span class="work-date">${utils.escapeHtml(item.scheduled_date)}</span>`
        : '';
    const dueIso = item.due || (item.due_at ? String(item.due_at).slice(0, 10) : '');
    const repeatBit = item.is_repeating
        ? `<span class="work-flag">${utils.escapeHtml(item.cadence_label || 'Repeats')}</span>`
        : '';
    const actions = done
        ? `<button type="button" class="btn-ghost" data-act="reopen">Reopen</button>`
        : running
            ? `
                <button type="button" class="btn-primary" data-act="finish">Finish</button>
                <button type="button" class="btn-secondary" data-act="stop">Stop</button>
              `
            : `
                <button type="button" class="btn-primary" data-act="start">Start</button>
                <button type="button" class="btn-secondary" data-act="finish">Finish</button>
              `;
    const repeatActions = item.is_repeating
        ? `<button type="button" class="btn-ghost" data-act="rename">Rename</button>`
        : '';
    return `
        <article class="work-item ${running ? 'is-active' : ''} ${done ? 'is-done' : ''}" data-id="${utils.escapeHtml(item.id)}" data-repeating="${item.is_repeating ? '1' : '0'}">
            <div class="work-item-main">
                <h3>${utils.escapeHtml(item.title)}</h3>
                <p class="work-meta">
                    <span class="work-timer" data-live="${running ? '1' : '0'}"
                        data-started="${utils.escapeHtml(item.active_started_at || '')}"
                        data-stored="${item.stored_duration_seconds ?? item.duration_seconds ?? 0}">${formatDuration(seconds)}</span>
                    ${dateBit}
                    ${dueIso ? `<span class="work-date">Due ${utils.escapeHtml(dueIso)}</span>` : ''}
                    ${item.estimate_minutes ? `<span class="work-flag">${item.estimate_minutes} min</span>` : ''}
                    ${item.remaining_minutes ? `<span class="work-flag">${item.remaining_minutes} min left</span>` : ''}
                    ${repeatBit}
                    ${done ? '<span class="work-flag">Done</span>' : running ? '<span class="work-flag is-live">In progress</span>' : ''}
                </p>
            </div>
            <div class="work-item-actions">
                ${actions}
                ${repeatActions}
                <details class="work-more">
                    <summary>More</summary>
                    <button type="button" class="btn-ghost" data-act="park">All Work</button>
                    <button type="button" class="btn-ghost" data-act="delete">Delete</button>
                </details>
            </div>
        </article>
    `;
}

function parkedRow(item) {
    const due = item.due_at
        ? `Due ${utils.escapeHtml(String(item.due_at).slice(0, 16).replace('T', ' '))}`
        : item.due
            ? `Due ${utils.escapeHtml(item.due)}`
            : 'Not dated yet';
    const mins = item.remaining_minutes || item.estimate_minutes;
    return `
        <article class="work-item" data-id="${utils.escapeHtml(item.id)}">
            <div class="work-item-main">
                <h3>${utils.escapeHtml(item.title)}</h3>
                <p class="work-meta">${due}${mins ? ` · ${mins} min` : ''}</p>
            </div>
            <div class="work-item-actions">
                <button type="button" class="btn-primary" data-act="today">Today</button>
                <button type="button" class="btn-secondary" data-act="tomorrow">Tomorrow</button>
                <button type="button" class="btn-ghost" data-act="delete">Delete</button>
            </div>
        </article>`;
}

function bindParkedList(root, onChange) {
    root.querySelectorAll('.work-item').forEach((row) => {
        const id = row.getAttribute('data-id');
        row.querySelectorAll('[data-act]').forEach((btn) => {
            btn.addEventListener('click', async () => {
                const act = btn.getAttribute('data-act');
                try {
                    if (act === 'today') {
                        const date = utils.localISODate();
                        await eel.assign_work_item(id, date)();
                        let message = 'Moved to today’s To Do.';
                        if (typeof eel.place_work_item === 'function') {
                            const placed = await eel.place_work_item(id, date)();
                            if (placed?.placed) message = placed.message || message;
                        }
                        utils.showSuccessFeedback(message);
                    } else if (act === 'tomorrow') {
                        const date = tomorrowISO();
                        await eel.assign_work_item(id, date)();
                        let message = 'Queued for tomorrow.';
                        if (typeof eel.place_work_item === 'function') {
                            const placed = await eel.place_work_item(id, date)();
                            if (placed?.placed) message = placed.message || message;
                        }
                        utils.showSuccessFeedback(message);
                    } else if (act === 'delete') {
                        await eel.delete_work_item(id)();
                    }
                    utils.notifyDataChanged();
                    await onChange();
                } catch (e) {
                    utils.showErrorFeedback('Could not update that item.');
                }
            });
        });
    });
}

function bindList(root, onChange) {
    root.querySelectorAll('.work-item, .todo-hero').forEach((row) => {
        const id = row.getAttribute('data-id');
        const repeating = row.getAttribute('data-repeating') === '1';
        row.querySelectorAll('[data-act]').forEach((btn) => {
            btn.addEventListener('click', async () => {
                const act = btn.getAttribute('data-act');
                try {
                    if (act === 'start') await eel.start_work_item(id)();
                    else if (act === 'stop') await eel.stop_work_item(id)();
                    else if (act === 'finish') await eel.finish_work_item(id)();
                    else if (act === 'reopen') await eel.reopen_work_item(id)();
                    else if (act === 'park') await eel.assign_work_item(id, '')();
                    else if (act === 'rename') {
                        const next = await utils.askText({
                            title: 'Rename task',
                            message: 'New name for this to-do.',
                            value: row.querySelector('h3')?.textContent || '',
                            ok: 'Rename',
                        });
                        if (next == null || !next.trim()) return;
                        const scope = repeating
                            ? await askScope('Rename only this day, or every future day in the series?')
                            : 'occurrence';
                        if (!scope) return;
                        await eel.update_work_item(id, next.trim(), null, scope)();
                    } else if (act === 'delete') {
                        const scope = repeating
                            ? await askScope('Remove only today’s copy, or stop the whole repeating series?')
                            : 'occurrence';
                        if (!scope) return;
                        await eel.delete_work_item(id, scope)();
                    }
                    utils.notifyDataChanged();
                    await onChange();
                } catch (e) {
                    utils.showErrorFeedback(e?.message || String(e) || 'Could not update task.');
                }
            });
        });
    });
}

async function refreshAll() {
    const list = document.getElementById('todoList');
    const summary = document.getElementById('todoSummary');
    if (!list) return;
    hideAsides();
    stopTick();
    try {
        const items = await eel.list_backlog()();
        if (summary) {
            summary.textContent = items.length
                ? `${items.length} waiting to be dated`
                : 'Empty — add work for later';
        }
        if (!items.length) {
            list.innerHTML = `
                <div class="empty-state">
                    <h3>Nothing parked in All Work</h3>
                    <p>Capture tasks here. Tonight, assign some to tomorrow or leave them for later.</p>
                </div>`;
            return;
        }
        list.innerHTML = items.map((item) => parkedRow(item)).join('');
        bindParkedList(list, refreshTodo);
    } catch (e) {
        console.error(e);
        list.innerHTML = '<p class="checklist-error">Could not load All Work.</p>';
    }
}

async function refreshUnplaced() {
    const list = document.getElementById('todoList');
    const summary = document.getElementById('todoSummary');
    if (!list) return;
    hideAsides();
    stopTick();
    try {
        const packed = await eel.get_unplaced_glance(0)();
        const items = packed?.items || [];
        const count = packed?.count ?? items.length;
        if (summary) {
            summary.textContent = count
                ? `${count} with minutes left off the clock`
                : 'Nothing unplaced';
        }
        if (!items.length) {
            list.innerHTML = `
                <div class="empty-state empty-state--line">
                    <p>Nothing to place. Add minutes, then Fill week or drag onto the clock.</p>
                </div>`;
            return;
        }
        list.innerHTML = items.map((item) => parkedRow(item)).join('');
        bindParkedList(list, refreshTodo);
    } catch (e) {
        console.error(e);
        list.innerHTML = '<p class="checklist-error">Could not load unplaced work.</p>';
    }
}

async function refreshDue() {
    const list = document.getElementById('todoList');
    const summary = document.getElementById('todoSummary');
    if (!list) return;
    hideAsides();
    stopTick();
    try {
        const packed = await eel.get_dues_week_glance(0)();
        const items = packed?.items || [];
        const count = packed?.count ?? items.length;
        if (summary) {
            summary.textContent = count
                ? `${count} due this week`
                : 'Nothing due this week';
        }
        if (!items.length) {
            list.innerHTML = `
                <div class="empty-state empty-state--line">
                    <p>No due dates this week.</p>
                </div>`;
            return;
        }
        list.innerHTML = items.map((item) => itemRow(item, { showDate: true })).join('');
        bindList(list, refreshTodo);
    } catch (e) {
        console.error(e);
        list.innerHTML = '<p class="checklist-error">Could not load due work.</p>';
    }
}

async function refreshToday(opts = {}) {
    const list = document.getElementById('todoList');
    const overdueEl = document.getElementById('todoOverdue');
    const tomorrowEl = document.getElementById('todoTomorrow');
    const summary = document.getElementById('todoSummary');
    if (!list) return;
    const focusDate = opts.focusDate || selectedDoDate || utils.localISODate();

    try {
        const board = await eel.get_work_board(focusDate)();
        const open = board.counts?.today_open || 0;
        const done = board.counts?.today_done || 0;
        if (summary) {
            summary.textContent = open
                ? `${open} open · ${done} finished`
                : done
                    ? 'All finished'
                    : 'Nothing dated for today yet';
        }

        const active = (board.today || []).find((item) => item.status === 'active');
        const rest = (board.today || []).filter((item) => item.id !== active?.id);
        const parts = [];
        if (active) {
            const seconds = liveSeconds(active);
            parts.push(`
                <article class="todo-hero" data-id="${utils.escapeHtml(active.id)}" data-repeating="${active.is_repeating ? '1' : '0'}">
                    <p class="eyebrow">In progress</p>
                    <h2>${utils.escapeHtml(active.title)}</h2>
                    <p class="todo-hero-timer work-timer" data-live="1"
                        data-started="${utils.escapeHtml(active.active_started_at || '')}"
                        data-stored="${active.stored_duration_seconds ?? active.duration_seconds ?? 0}">${formatDuration(seconds)}</p>
                    <div class="todo-hero-actions work-item-actions">
                        <button type="button" class="btn-primary" data-act="finish">Finish</button>
                        <button type="button" class="btn-secondary" data-act="stop">Stop</button>
                    </div>
                </article>
            `);
        }
        if (!board.today.length) {
            parts.push(`
                <div class="empty-state empty-state--line">
                    <p>Nothing dated for today.</p>
                </div>`);
        } else if (rest.length) {
            parts.push(rest.map((item) => itemRow(item)).join(''));
        }
        list.innerHTML = parts.join('');
        bindList(list, refreshTodo);
        if (opts.highlightId) {
            const row = document.querySelector(`[data-id="${CSS.escape(opts.highlightId)}"]`);
            row?.classList.add('is-selected');
            row?.scrollIntoView({ block: 'nearest' });
        }

        if (overdueEl) {
            if (board.overdue.length) {
                overdueEl.classList.remove('is-hidden');
                overdueEl.innerHTML = `
                    <h3>Still open from earlier</h3>
                    ${board.overdue.map((item) => itemRow(item, { showDate: true })).join('')}
                `;
                bindList(overdueEl, refreshTodo);
            } else {
                overdueEl.classList.add('is-hidden');
                overdueEl.innerHTML = '';
            }
        }

        if (tomorrowEl) {
            const upcoming = board.upcoming?.length ? board.upcoming : board.tomorrow || [];
            if (upcoming.length) {
                tomorrowEl.classList.remove('is-hidden');
                tomorrowEl.innerHTML = `
                    <h3>Coming up this week</h3>
                    <ul class="work-already">${upcoming
                        .map((item) => {
                            const when = item.scheduled_date ? utils.escapeHtml(item.scheduled_date.slice(5)) : '';
                            const mins = item.estimate_minutes ? ` · ${item.estimate_minutes} min` : '';
                            const cadence = item.cadence_label ? ` · ${utils.escapeHtml(item.cadence_label)}` : '';
                            return `<li>${when ? `<span class="work-date">${when}</span> ` : ''}${utils.escapeHtml(item.title)}${mins}${cadence}</li>`;
                        })
                        .join('')}</ul>
                `;
            } else {
                tomorrowEl.classList.add('is-hidden');
                tomorrowEl.innerHTML = '';
            }
        }

        const running = [...(board.today || []), ...(board.overdue || [])].some((item) => item.status === 'active');
        if (running) startTick();
        else stopTick();
    } catch (e) {
        console.error(e);
        list.innerHTML = '<p class="checklist-error">Could not load today’s work.</p>';
    }
}

export async function refreshTodo(opts = {}) {
    const list = document.getElementById('todoList');
    if (!list) return;
    if (opts.filter) listFilter = normalizeFilter(opts.filter);
    paintFilter();
    if (listFilter === 'all') return refreshAll();
    if (listFilter === 'unplaced') return refreshUnplaced();
    if (listFilter === 'due') return refreshDue();
    return refreshToday(opts);
}

async function addWorkTask() {
    const input = document.getElementById('todoNewTitle');
    const title = (input?.value || '').trim();
    if (!title) {
        utils.showErrorFeedback('Name the task first.');
        return;
    }
    const repeat = listFilter === 'today' ? currentRepeat() : null;
    const due = document.getElementById('todoNewDue')?.value || '';
    const estimate = document.getElementById('todoNewEstimate')?.value || '';
    const goal = document.getElementById('todoNewGoal')?.value || '';
    if (listFilter === 'today' && repeatKind === 'custom' && repeat && !(repeat.weekdays || []).length) {
        utils.showErrorFeedback('Pick at least one weekday.');
        return;
    }
    if (listFilter === 'unplaced' && !estimate && !/\d+\s*(min|mins|minutes)\b/i.test(title)) {
        utils.showErrorFeedback('Unplaced needs minutes in the title or the Min field.');
        return;
    }
    if (listFilter === 'due' && !due) {
        utils.showErrorFeedback('Pick a due date.');
        return;
    }
    try {
        let onDate = selectedWhenDate();
        if (listFilter === 'all' || listFilter === 'unplaced') onDate = 'allwork';
        else if (listFilter === 'due') onDate = due || utils.localISODate();
        const result = await eel.add_todo_to_calendar(title, onDate, due, estimate, repeat, goal)();
        if (input) input.value = '';
        const est = document.getElementById('todoNewEstimate');
        const dueEl = document.getElementById('todoNewDue');
        const goalEl = document.getElementById('todoNewGoal');
        if (est) est.value = '';
        if (dueEl) dueEl.value = '';
        if (goalEl) goalEl.value = '';
        const message = result?.message || (repeat ? 'Repeating to-do saved.' : 'Added.');
        const extra = (repeat || result?.item?.is_repeating)
            ? ' Rename or delete will ask this day or the whole series.'
            : '';
        if (result?.ok === false) {
            utils.showErrorFeedback(message);
        } else {
            utils.showSuccessFeedback(message + extra);
        }
        utils.notifyDataChanged();
        await refreshTodo();
        input?.focus();
    } catch (e) {
        utils.showErrorFeedback(e?.message || 'Could not add that task.');
    }
}

export function setupTodo() {
    const tab = document.getElementById('todoTab');
    if (!tab || tab.dataset.ready === '1') return;
    tab.dataset.ready = '1';
    const addBtn = document.getElementById('todoAddBtn');
    const input = document.getElementById('todoNewTitle');
    addBtn?.addEventListener('click', () => {
        void addWorkTask();
    });
    input?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            void addWorkTask();
        }
    });
    document.getElementById('todoFilter')?.addEventListener('click', (e) => {
        const btn = e.target.closest('#todoFilter [data-filter]');
        if (!btn) return;
        listFilter = normalizeFilter(btn.getAttribute('data-filter'));
        paintFilter();
        void refreshTodo();
    });
    document.getElementById('todoRepeatToggle')?.addEventListener('change', () => {
        syncRepeatPanel();
        updateAddButton();
    });
    document.getElementById('todoRepeatKind')?.addEventListener('click', (e) => {
        const btn = e.target.closest('[data-value]');
        if (!btn) return;
        repeatKind = btn.getAttribute('data-value') || 'daily';
        syncRepeatPanel();
    });
    document.getElementById('todoDest')?.addEventListener('click', (e) => {
        const chip = e.target.closest('#todoDest [data-dest]');
        if (!chip) return;
        e.preventDefault();
        destKind = chip.getAttribute('data-dest') === 'allwork' ? 'allwork' : 'today';
        if (destKind === 'today') {
            const today = whenDays.find((row) => row.is_today);
            if (today) selectedDoDate = today.place_date;
            document.querySelectorAll('#todoWhen .work-day-chip').forEach((btn) => {
                const on = btn.getAttribute('data-date') === selectedDoDate;
                btn.classList.toggle('is-selected', on);
                btn.setAttribute('aria-checked', on ? 'true' : 'false');
            });
        }
        paintDest();
        updateWhenHint();
    });
    document.getElementById('todoWhen')?.addEventListener('click', (e) => {
        const root = document.getElementById('todoWhen');
        const chip = e.target.closest('#todoWhen .work-day-chip');
        if (!root || !chip) return;
        e.preventDefault();
        destKind = 'today';
        selectedDoDate = chip.getAttribute('data-date');
        root.querySelectorAll('.work-day-chip').forEach((btn) => {
            const on = btn === chip;
            btn.classList.toggle('is-selected', on);
            btn.setAttribute('aria-checked', on ? 'true' : 'false');
        });
        paintDest();
        updateWhenHint();
    });
    document.getElementById('todoWeekdays')?.addEventListener('click', (e) => {
        const chip = e.target.closest('.work-day-chip');
        if (!chip) return;
        chip.classList.toggle('is-selected');
    });
    document.getElementById('workScopeOccurrence')?.addEventListener('click', () => closeScope('occurrence'));
    document.getElementById('workScopeSeries')?.addEventListener('click', () => closeScope('series'));
    document.getElementById('workScopeCancel')?.addEventListener('click', () => closeScope(null));
    document.addEventListener('kosistenz:data-changed', () => {
        if (utils.sourceIsOpen('todoTab')) {
            void refreshTodo();
        }
    });
    document.addEventListener('kosistenz:open-todo', (e) => {
        const date = e.detail?.date || '';
        const itemId = e.detail?.itemId || '';
        document.dispatchEvent(new CustomEvent('kosistenz:open-tab', { detail: { tab: 'home' } }));
        void openTodoForItem(date, itemId);
    });
    syncRepeatPanel();
    paintFilter();
    updateAddButton();
    void loadGoalOptions('todoNewGoal');
}

export async function onTodoTabShown(opts = {}) {
    if (opts.filter) listFilter = normalizeFilter(opts.filter);
    paintFilter();
    await loadWhenChips();
    await loadGoalOptions('todoNewGoal');
    await refreshTodo({ focusDate: opts.focusDate, highlightId: opts.highlightId });
}

async function openTodoForItem(date, itemId) {
    listFilter = 'today';
    destKind = 'today';
    if (date) selectedDoDate = date;
    await loadWhenChips();
    if (date) {
        document.querySelectorAll('#todoWhen .work-day-chip').forEach((btn) => {
            const on = btn.getAttribute('data-date') === date;
            btn.classList.toggle('is-selected', on);
            btn.setAttribute('aria-checked', on ? 'true' : 'false');
        });
        updateWhenHint();
    }
    await refreshTodo({ filter: 'today', focusDate: date || selectedDoDate, highlightId: itemId });
}

export { tomorrowISO };
