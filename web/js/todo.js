/**
 * Today's To Do — dated work with start / finish timers and optional repeats.
 */

import * as utils from './utils.js';
import { formatDuration, liveSeconds, tomorrowISO } from './work.js';

let tickTimer = null;
let repeatKind = 'daily';
let scopeResolver = null;
let selectedDoDate = null;
let whenDays = [];

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
    const chip = document.querySelector('#todoWhen .work-day-chip.is-selected');
    return chip?.getAttribute('data-date') || selectedDoDate || utils.localISODate();
}

function updateWhenHint() {
    const hint = document.querySelector('.todo-when-hint');
    if (!hint) return;
    const day = whenDays.find((row) => row.place_date === selectedDoDate);
    if (!day) {
        hint.textContent =
            'Pick a day this week. Minutes can live in the title (45 mins, 1h). Optional due date if it is also an assignment.';
        return;
    }
    const when = day.is_today ? 'today' : day.is_past ? `next ${day.label}` : day.label;
    hint.textContent = `Places on ${when}. Minutes can live in the title (45 mins, 1h). Optional due date if it is also an assignment.`;
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
            const title = day.is_today ? 'Today' : day.is_past ? `Next ${day.label}` : day.label;
            return `<button type="button" class="${classes.join(' ')}" data-date="${utils.escapeHtml(date)}" data-weekday="${day.weekday}" title="${utils.escapeHtml(title)}">${utils.escapeHtml(day.label)}</button>`;
        })
        .join('');
    const selected = root.querySelector('.is-selected');
    selectedDoDate = selected?.getAttribute('data-date') || whenDays.find((row) => row.is_today)?.place_date;
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

function itemRow(item, { showDate = false } = {}) {
    const running = item.status === 'active';
    const done = item.status === 'done';
    const seconds = liveSeconds(item);
    const dateBit = showDate && item.scheduled_date
        ? `<span class="work-date">${utils.escapeHtml(item.scheduled_date)}</span>`
        : '';
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
                    ${item.due_at ? `<span class="work-date">Due ${utils.escapeHtml(String(item.due_at).slice(0, 10))}</span>` : ''}
                    ${item.estimate_minutes ? `<span class="work-flag">${item.estimate_minutes} min</span>` : ''}
                    ${repeatBit}
                    ${done ? '<span class="work-flag">Done</span>' : running ? '<span class="work-flag is-live">In progress</span>' : ''}
                </p>
            </div>
            <div class="work-item-actions">
                ${actions}
                ${repeatActions}
                <button type="button" class="btn-ghost" data-act="park">All Work</button>
                <button type="button" class="btn-ghost" data-act="delete">Delete</button>
            </div>
        </article>
    `;
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
                        const next = window.prompt('New name');
                        if (!next || !next.trim()) return;
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

export async function refreshTodo() {
    const list = document.getElementById('todoList');
    const overdueEl = document.getElementById('todoOverdue');
    const tomorrowEl = document.getElementById('todoTomorrow');
    const summary = document.getElementById('todoSummary');
    if (!list) return;

    try {
        const board = await eel.get_work_board(utils.localISODate())();
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
                <div class="empty-state">
                    <h3>No tasks for today</h3>
                    <p>Type “45 mins calculus” and pick a day. Kosistenz parks it in a free gap on the calendar.</p>
                </div>`);
        } else if (rest.length) {
            parts.push(rest.map((item) => itemRow(item)).join(''));
        }
        list.innerHTML = parts.join('');
        bindList(list, refreshTodo);

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

async function addTodayTask() {
    const input = document.getElementById('todoNewTitle');
    const title = (input?.value || '').trim();
    if (!title) {
        utils.showErrorFeedback('Name the task first.');
        return;
    }
    const repeat = currentRepeat();
    const due = document.getElementById('todoNewDue')?.value || '';
    const estimate = document.getElementById('todoNewEstimate')?.value || '';
    if (repeatKind === 'custom' && repeat && !(repeat.weekdays || []).length) {
        utils.showErrorFeedback('Pick at least one weekday.');
        return;
    }
    try {
        const onDate = selectedWhenDate();
        const result = await eel.add_todo_to_calendar(title, onDate, due, estimate, repeat)();
        if (input) input.value = '';
        const est = document.getElementById('todoNewEstimate');
        const dueEl = document.getElementById('todoNewDue');
        if (est) est.value = '';
        if (dueEl) dueEl.value = '';
        const message = result?.message || (repeat ? 'Repeating to do saved.' : 'Added to the calendar.');
        if (result?.placed || repeat || result?.item?.is_repeating) {
            utils.showSuccessFeedback(message);
        } else {
            utils.showErrorFeedback(message);
        }
        utils.notifyDataChanged();
        await refreshTodo();
        input?.focus();
    } catch (e) {
        utils.showErrorFeedback(e?.message || 'Could not add that task.');
    }
}

export function setupTodo() {
    const addBtn = document.getElementById('todoAddBtn');
    const input = document.getElementById('todoNewTitle');
    addBtn?.addEventListener('click', () => {
        void addTodayTask();
    });
    input?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            void addTodayTask();
        }
    });
    document.getElementById('todoRepeatToggle')?.addEventListener('change', syncRepeatPanel);
    document.getElementById('todoRepeatKind')?.addEventListener('click', (e) => {
        const btn = e.target.closest('[data-value]');
        if (!btn) return;
        repeatKind = btn.getAttribute('data-value') || 'daily';
        syncRepeatPanel();
    });
    document.getElementById('todoWhen')?.addEventListener('click', (e) => {
        const chip = e.target.closest('.work-day-chip');
        if (!chip) return;
        selectedDoDate = chip.getAttribute('data-date');
        paintWhenChips();
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
        if (document.getElementById('todoTab')?.classList.contains('active')) {
            void refreshTodo();
        }
    });
    syncRepeatPanel();
    void loadWhenChips();
}

export async function onTodoTabShown() {
    await loadWhenChips();
    await refreshTodo();
}

export { tomorrowISO };
