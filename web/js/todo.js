/**
 * Today's To Do — dated work with start / finish timers.
 */

import * as utils from './utils.js';
import { formatDuration, liveSeconds, tomorrowISO } from './work.js';

let tickTimer = null;

function stopTick() {
    if (tickTimer) {
        clearInterval(tickTimer);
        tickTimer = null;
    }
}

function startTick() {
    stopTick();
    tickTimer = setInterval(() => {
        document.querySelectorAll('#todoTab .work-timer[data-live="1"]').forEach((el) => {
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

function itemRow(item, { showDate = false } = {}) {
    const running = item.status === 'active';
    const done = item.status === 'done';
    const seconds = liveSeconds(item);
    const dateBit = showDate && item.scheduled_date
        ? `<span class="work-date">${utils.escapeHtml(item.scheduled_date)}</span>`
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
    return `
        <article class="work-item ${running ? 'is-active' : ''} ${done ? 'is-done' : ''}" data-id="${utils.escapeHtml(item.id)}">
            <div class="work-item-main">
                <h3>${utils.escapeHtml(item.title)}</h3>
                <p class="work-meta">
                    <span class="work-timer" data-live="${running ? '1' : '0'}"
                        data-started="${utils.escapeHtml(item.active_started_at || '')}"
                        data-stored="${item.stored_duration_seconds ?? item.duration_seconds ?? 0}">${formatDuration(seconds)}</span>
                    ${dateBit}
                    ${done ? '<span class="work-flag">Done</span>' : running ? '<span class="work-flag is-live">In progress</span>' : ''}
                </p>
            </div>
            <div class="work-item-actions">
                ${actions}
                <button type="button" class="btn-ghost" data-act="park">All Work</button>
                <button type="button" class="btn-ghost" data-act="delete">Delete</button>
            </div>
        </article>
    `;
}

function bindList(root, onChange) {
    root.querySelectorAll('.work-item').forEach((row) => {
        const id = row.getAttribute('data-id');
        row.querySelectorAll('[data-act]').forEach((btn) => {
            btn.addEventListener('click', async () => {
                const act = btn.getAttribute('data-act');
                try {
                    if (act === 'start') await eel.start_work_item(id)();
                    else if (act === 'stop') await eel.stop_work_item(id)();
                    else if (act === 'finish') await eel.finish_work_item(id)();
                    else if (act === 'reopen') await eel.reopen_work_item(id)();
                    else if (act === 'park') await eel.assign_work_item(id, '')();
                    else if (act === 'delete') await eel.delete_work_item(id)();
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

        if (!board.today.length) {
            list.innerHTML = `
                <div class="empty-state">
                    <h3>No tasks for today</h3>
                    <p>Add one here, or plan them tonight from All Work during the evening check-in.</p>
                </div>`;
        } else {
            list.innerHTML = board.today.map((item) => itemRow(item)).join('');
            bindList(list, refreshTodo);
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
            if (board.tomorrow.length) {
                tomorrowEl.classList.remove('is-hidden');
                tomorrowEl.innerHTML = `
                    <h3>Already set for tomorrow</h3>
                    <ul class="work-already">${board.tomorrow
                        .map((item) => `<li>${utils.escapeHtml(item.title)}</li>`)
                        .join('')}</ul>
                `;
            } else {
                tomorrowEl.classList.add('is-hidden');
                tomorrowEl.innerHTML = '';
            }
        }

        if (board.today.some((item) => item.status === 'active') || board.overdue.some((item) => item.status === 'active')) {
            startTick();
        } else {
            stopTick();
        }
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
    try {
        await eel.create_work_item(title, utils.localISODate(), '', 'manual')();
        if (input) input.value = '';
        utils.showSuccessFeedback('Added to today.');
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
    document.addEventListener('kosistenz:data-changed', () => {
        if (document.getElementById('todoTab')?.classList.contains('active')) {
            void refreshTodo();
        }
    });
}

export async function onTodoTabShown() {
    await refreshTodo();
}

export { tomorrowISO };
