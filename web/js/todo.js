/**
 * Today's To Do — dated work with start / finish timers and optional repeats.
 */

import * as utils from './utils.js';
import { formatDuration, liveSeconds, tomorrowISO } from './work.js';

let tickTimer = null;
let repeatKind = 'daily';
let scopeResolver = null;

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
                    <p>Add a one-off or a repeating to do. Missed repeats stay on that past day for Analytics.</p>
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
            if (board.tomorrow.length) {
                tomorrowEl.classList.remove('is-hidden');
                tomorrowEl.innerHTML = `
                    <h3>Already set for tomorrow</h3>
                    <ul class="work-already">${board.tomorrow
                        .map((item) => `<li>${utils.escapeHtml(item.title)}${item.cadence_label ? ` · ${utils.escapeHtml(item.cadence_label)}` : ''}</li>`)
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
    if (repeatKind === 'custom' && repeat && !(repeat.weekdays || []).length) {
        utils.showErrorFeedback('Pick at least one weekday.');
        return;
    }
    try {
        await eel.create_work_item(title, utils.localISODate(), '', 'manual', repeat)();
        if (input) input.value = '';
        utils.showSuccessFeedback(repeat ? 'Repeating to do saved.' : 'Added to today.');
        utils.notifyDataChanged();
        await refreshTodo();
        input?.focus();
    } catch (e) {
        utils.showErrorFeedback('Could not add that task.');
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
}

export async function onTodoTabShown() {
    await refreshTodo();
}

export { tomorrowISO };
