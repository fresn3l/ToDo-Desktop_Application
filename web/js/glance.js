/**
 * Glance Home widgets — today's focus, countdowns, and daily habits.
 */

import * as utils from './utils.js';

function hasEel(name) {
    return typeof eel !== 'undefined' && typeof eel[name] === 'function';
}

export function paintFocus(data) {
    const input = document.getElementById('focusInput');
    if (!input) return;
    const text = data?.text || '';
    if (document.activeElement === input) return;
    input.value = text;
}

export async function refreshFocus() {
    if (!hasEel('get_daily_focus')) return;
    try {
        paintFocus(await eel.get_daily_focus()());
    } catch (err) {
        console.error(err);
    }
}

async function persistFocus() {
    const input = document.getElementById('focusInput');
    if (!input || !hasEel('set_daily_focus')) return;
    try {
        paintFocus(await eel.set_daily_focus(input.value)());
    } catch (err) {
        console.error(err);
        utils.showErrorFeedback(err?.message || 'Could not save focus.');
    }
}

export function paintCountdowns(items) {
    const el = document.getElementById('countdownList');
    if (!el) return;
    const rows = Array.isArray(items) ? items : [];
    if (!rows.length) {
        el.innerHTML = '<li class="checklist-empty">Add an exam, trip, or due date.</li>';
        return;
    }
    el.innerHTML = rows
        .map((row) => {
            const state = row.state === 'today' ? ' is-today' : row.state === 'past' ? ' is-past' : '';
            const days = Number(row.days);
            const count = Number.isFinite(days) ? String(Math.abs(days)) : '—';
            return `<li class="countdown-item${state}" data-id="${utils.escapeHtml(row.id)}">
                <div>
                    <strong>${utils.escapeHtml(row.title)}</strong>
                    <span class="countdown-date">${utils.escapeHtml(row.phrase)}</span>
                </div>
                <em class="countdown-days">${utils.escapeHtml(count)}</em>
                <button type="button" class="btn-ghost" data-act="remove" aria-label="Remove">Remove</button>
            </li>`;
        })
        .join('');
}

export async function refreshCountdown() {
    if (!hasEel('get_countdowns')) return;
    try {
        paintCountdowns(await eel.get_countdowns()());
    } catch (err) {
        console.error(err);
        const el = document.getElementById('countdownList');
        if (el) el.innerHTML = '<li class="checklist-error">Could not load countdowns.</li>';
    }
}

export function paintHabits(data) {
    const el = document.getElementById('habitList');
    const summary = document.getElementById('habitsSummary');
    if (summary) {
        const total = data?.total || 0;
        const done = data?.done || 0;
        summary.textContent = total ? `${done} of ${total} today` : 'Tick the small things that keep the day honest.';
    }
    if (!el) return;
    const rows = data?.habits || [];
    if (!rows.length) {
        el.innerHTML = '<li class="checklist-empty">Add water, stretch, or whatever you repeat.</li>';
        return;
    }
    el.innerHTML = rows
        .map((row) => {
            const on = row.done ? ' is-done' : '';
            return `<li class="${on}" data-id="${utils.escapeHtml(row.id)}">
                <button type="button" class="habit-tick" data-act="toggle" aria-pressed="${row.done ? 'true' : 'false'}">
                    <span class="habit-box" aria-hidden="true"></span>
                    <span>${utils.escapeHtml(row.title)}</span>
                </button>
                <button type="button" class="btn-ghost" data-act="remove" aria-label="Remove">Remove</button>
            </li>`;
        })
        .join('');
}

export async function refreshHabits() {
    if (!hasEel('get_habits')) return;
    try {
        paintHabits(await eel.get_habits()());
    } catch (err) {
        console.error(err);
        const el = document.getElementById('habitList');
        if (el) el.innerHTML = '<li class="checklist-error">Could not load habits.</li>';
    }
}

export function setupGlance() {
    const focus = document.getElementById('focusInput');
    if (focus && focus.dataset.ready !== '1') {
        focus.dataset.ready = '1';
        focus.addEventListener('blur', () => {
            void persistFocus();
        });
        focus.addEventListener('keydown', (e) => {
            if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
                e.preventDefault();
                focus.blur();
            }
        });
    }

    const countdownForm = document.getElementById('countdownForm');
    if (countdownForm && countdownForm.dataset.ready !== '1') {
        countdownForm.dataset.ready = '1';
        countdownForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const title = document.getElementById('countdownTitle')?.value || '';
            const when = document.getElementById('countdownDate')?.value || '';
            if (!hasEel('add_home_countdown')) return;
            void (async () => {
                try {
                    paintCountdowns(await eel.add_home_countdown(title, when)());
                    const titleEl = document.getElementById('countdownTitle');
                    if (titleEl) titleEl.value = '';
                    utils.notifyDataChanged();
                } catch (err) {
                    console.error(err);
                    utils.showErrorFeedback(err?.message || 'Could not add countdown.');
                }
            })();
        });
    }

    const countdownList = document.getElementById('countdownList');
    if (countdownList && countdownList.dataset.ready !== '1') {
        countdownList.dataset.ready = '1';
        countdownList.addEventListener('click', (e) => {
            const btn = e.target.closest('[data-act="remove"]');
            const row = e.target.closest('[data-id]');
            if (!btn || !row || !hasEel('remove_home_countdown')) return;
            void (async () => {
                try {
                    paintCountdowns(await eel.remove_home_countdown(row.getAttribute('data-id'))());
                    utils.notifyDataChanged();
                } catch (err) {
                    console.error(err);
                    utils.showErrorFeedback(err?.message || 'Could not remove that.');
                }
            })();
        });
    }

    const habitForm = document.getElementById('habitForm');
    if (habitForm && habitForm.dataset.ready !== '1') {
        habitForm.dataset.ready = '1';
        habitForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const title = document.getElementById('habitTitle')?.value || '';
            if (!hasEel('add_home_habit')) return;
            void (async () => {
                try {
                    paintHabits(await eel.add_home_habit(title)());
                    const titleEl = document.getElementById('habitTitle');
                    if (titleEl) titleEl.value = '';
                    utils.notifyDataChanged();
                } catch (err) {
                    console.error(err);
                    utils.showErrorFeedback(err?.message || 'Could not add habit.');
                }
            })();
        });
    }

    const habitList = document.getElementById('habitList');
    if (habitList && habitList.dataset.ready !== '1') {
        habitList.dataset.ready = '1';
        habitList.addEventListener('click', (e) => {
            const btn = e.target.closest('[data-act]');
            const row = e.target.closest('[data-id]');
            if (!btn || !row) return;
            const act = btn.getAttribute('data-act');
            void (async () => {
                try {
                    if (act === 'toggle' && hasEel('toggle_home_habit')) {
                        paintHabits(await eel.toggle_home_habit(row.getAttribute('data-id'))());
                        utils.notifyDataChanged();
                    } else if (act === 'remove' && hasEel('remove_home_habit')) {
                        paintHabits(await eel.remove_home_habit(row.getAttribute('data-id'))());
                        utils.notifyDataChanged();
                    }
                } catch (err) {
                    console.error(err);
                    utils.showErrorFeedback(err?.message || 'Could not update habit.');
                }
            })();
        });
    }
}
