/**
 * Today home — open to-dos, expected workout, short journal.
 * Also paints the compact status pills used in the web topbar.
 */

import * as utils from './utils.js';
import { formatDuration, liveSeconds } from './work.js';
import { logWorkoutKind, renderWorkoutChips } from './workout_chips.js';
import { getAppearance, persistAppearance, onAppearanceChange } from './appearance.js';
import {
    applyTodayOrder,
    moveTodayModule,
    renderTodayOrderList,
} from './today_layout.js';

let homeTick = null;

function stopHomeTick() {
    if (homeTick) {
        clearInterval(homeTick);
        homeTick = null;
    }
}

function startHomeTick() {
    stopHomeTick();
    homeTick = setInterval(() => {
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

function mastheadParts(iso) {
    const d = iso ? new Date(`${iso}T12:00:00`) : new Date();
    if (Number.isNaN(d.getTime())) {
        return { weekday: 'Today', rest: '' };
    }
    return {
        weekday: d.toLocaleDateString(undefined, { weekday: 'long' }),
        rest: d.toLocaleDateString(undefined, { month: 'long', day: 'numeric', year: 'numeric' }),
    };
}

function paintPulse(data) {
    const el = document.getElementById('todayPulse');
    if (!el) return;
    const work = data.work || {};
    const workout = data.workout || {};
    const expected = (data.expected && data.expected.labels) || [];
    const bits = [];
    if (work.open) bits.push(`${work.open} open`);
    else if (work.total) bits.push('To do done');
    if (workout.done) bits.push(workout.session_count === 1 ? 'Workout logged' : `${workout.session_count} workouts`);
    else if (expected.length) bits.push(expected.join(' · '));
    if (data.journal_count) bits.push(`${data.journal_count} journal`);
    else if (data.journal_streak) bits.push(`${data.journal_streak}-day streak`);
    el.textContent = bits.join('  ·  ') || 'A quiet day so far';
}

function paintCustomize() {
    const s = getAppearance();
    const todo = document.getElementById('todayShowTodo');
    const workout = document.getElementById('todayShowWorkout');
    const journal = document.getElementById('todayShowJournal');
    if (todo) todo.checked = s.todayTodo !== false;
    if (workout) workout.checked = s.todayWorkout !== false;
    if (journal) journal.checked = s.todayJournal !== false;
    document.querySelectorAll('#todayLayoutGroup [data-value]').forEach((btn) => {
        btn.classList.toggle('is-selected', btn.getAttribute('data-value') === (s.todayLayout || 'split'));
    });
    applyTodayOrder(s.todayOrder);
    renderTodayOrderList(document.getElementById('todayOrderList'), s.todayOrder);
}

function setCustomizeOpen(open) {
    const panel = document.getElementById('todayCustomizePanel');
    const btn = document.getElementById('todayCustomizeBtn');
    if (!panel) return;
    panel.classList.toggle('is-hidden', !open);
    panel.hidden = !open;
    if (btn) {
        btn.setAttribute('aria-expanded', open ? 'true' : 'false');
        btn.textContent = open ? 'Done' : 'Customize';
    }
}

function renderPills(el, data) {
    const journalCount = data.journal_count || 0;
    const journalLabel = journalCount
        ? `${journalCount} journal${journalCount === 1 ? '' : 's'}`
        : 'No journal yet';

    const workout = data.workout || {};
    const workoutDone = !!workout.done;
    const expected = (data.expected && data.expected.labels) || [];
    let workoutLabel = expected.length ? expected.join(' · ') : 'Workout';
    if (workoutDone) {
        const sessionCount = workout.session_count || 0;
        workoutLabel = sessionCount === 1 ? 'Workout done' : `${sessionCount} workouts`;
        if (workout.miles) workoutLabel += ` · ${workout.miles} mi`;
    }
    const workoutClasses = [
        'today-pill',
        workoutDone ? 'is-done' : 'is-todo',
        workoutDone ? '' : 'is-suggested',
    ]
        .filter(Boolean)
        .join(' ');

    const work = data.work || {};
    const workOpen = work.open || 0;
    const workTotal = work.total || 0;
    const workLabel = workTotal
        ? (workOpen ? `${workOpen} to do` : 'To do done')
        : 'No to do';
    const workClasses = [
        'today-pill',
        workTotal && !workOpen ? 'is-done' : '',
        workOpen ? 'is-todo' : 'is-muted',
    ]
        .filter(Boolean)
        .join(' ');

    el.innerHTML = `
        <span class="today-label">Today</span>
        <button type="button" class="${workoutClasses}" data-action="today" title="Open Today">
            ${utils.escapeHtml(workoutLabel)}
        </button>
        <button type="button" class="${workClasses}" data-action="today" title="Open Today">
            ${utils.escapeHtml(workLabel)}
        </button>
        <button type="button" class="today-pill today-journal ${journalCount ? 'is-done' : 'is-muted'}"
            data-action="${journalCount ? 'timeline' : 'journal'}"
            title="${journalCount ? 'Open today on Timeline' : 'Write a journal entry'}">
            ${utils.escapeHtml(journalLabel)}
        </button>
    `;

    el.querySelectorAll('[data-action]').forEach((btn) => {
        btn.addEventListener('click', () => {
            const action = btn.getAttribute('data-action');
            const date = data.local_date;
            if (action === 'today') {
                document.dispatchEvent(new CustomEvent('kosistenz:open-tab', { detail: { tab: 'today' } }));
            } else if (action === 'timeline' && date) {
                document.dispatchEvent(new CustomEvent('kosistenz:open-day', { detail: { date } }));
            } else if (action === 'journal') {
                document.dispatchEvent(new CustomEvent('kosistenz:open-tab', { detail: { tab: 'journal' } }));
            }
        });
    });
}

function heroCard(item) {
    const seconds = liveSeconds(item);
    return `
        <article class="todo-hero" data-id="${utils.escapeHtml(item.id)}">
            <div class="todo-hero-copy">
                <p class="eyebrow">In progress</p>
                <h2>${utils.escapeHtml(item.title)}</h2>
            </div>
            <p class="todo-hero-timer work-timer" data-live="1"
                data-started="${utils.escapeHtml(item.active_started_at || '')}"
                data-stored="${item.stored_duration_seconds ?? item.duration_seconds ?? 0}">${formatDuration(seconds)}</p>
            <div class="todo-hero-actions">
                <button type="button" class="btn-primary" data-act="finish">Finish</button>
                <button type="button" class="btn-secondary" data-act="stop">Stop</button>
            </div>
        </article>
    `;
}

function compactRow(item) {
    const running = item.status === 'active';
    const done = item.status === 'done';
    return `
        <article class="work-item ${running ? 'is-active' : ''} ${done ? 'is-done' : ''}" data-id="${utils.escapeHtml(item.id)}">
            <div class="work-item-main">
                <h3>${utils.escapeHtml(item.title)}</h3>
                <p class="work-meta">${done ? 'Done' : running ? 'In progress' : 'Open'}</p>
            </div>
            <div class="work-item-actions">
                ${
                    done
                        ? ''
                        : running
                          ? `<button type="button" class="btn-primary" data-act="finish">Finish</button>`
                          : `<button type="button" class="btn-primary" data-act="start">Start</button>`
                }
            </div>
        </article>
    `;
}

async function bindActs(root) {
    root.querySelectorAll('[data-act]').forEach((btn) => {
        btn.addEventListener('click', async () => {
            const id = btn.closest('[data-id]')?.getAttribute('data-id');
            const act = btn.getAttribute('data-act');
            if (!id) return;
            try {
                if (act === 'start') await eel.start_work_item(id)();
                else if (act === 'stop') await eel.stop_work_item(id)();
                else if (act === 'finish') await eel.finish_work_item(id)();
                utils.notifyDataChanged();
                await refreshTodayHome();
            } catch (e) {
                utils.showErrorFeedback(e?.message || String(e) || 'Could not update task.');
            }
        });
    });
}

function syncTodayExtras(kind) {
    const miles = kind === 'running';
    const other = kind === 'other';
    document.getElementById('todayMilesWrap')?.classList.toggle('is-hidden', !miles);
    document.getElementById('todayOtherWrap')?.classList.toggle('is-hidden', !other);
    const logBtn = document.getElementById('todayLogSpecial');
    if (logBtn) {
        logBtn.classList.toggle('is-hidden', !miles && !other);
        logBtn.textContent = miles ? 'Log run' : 'Log other';
    }
}

async function handleTodayChip(kind) {
    syncTodayExtras(kind);
    if (kind === 'running' || kind === 'other') {
        const field = document.getElementById(kind === 'running' ? 'todayMiles' : 'todayOtherLabel');
        field?.focus();
        return;
    }
    try {
        await logWorkoutKind(kind);
        utils.showSuccessFeedback('Session logged.');
        await refreshTodayHome();
    } catch (e) {
        utils.showErrorFeedback(e?.message || String(e) || 'Could not log that session.');
    }
}

async function confirmTodaySpecial() {
    const milesWrap = document.getElementById('todayMilesWrap');
    const otherWrap = document.getElementById('todayOtherWrap');
    try {
        if (milesWrap && !milesWrap.classList.contains('is-hidden')) {
            const miles = document.getElementById('todayMiles')?.value;
            await logWorkoutKind('running', { miles: miles === '' ? null : miles });
            const input = document.getElementById('todayMiles');
            if (input) input.value = '';
        } else if (otherWrap && !otherWrap.classList.contains('is-hidden')) {
            const other = document.getElementById('todayOtherLabel')?.value || '';
            await logWorkoutKind('other', { other_label: other });
            const input = document.getElementById('todayOtherLabel');
            if (input) input.value = '';
        } else {
            return;
        }
        utils.showSuccessFeedback('Session logged.');
        syncTodayExtras('');
        await refreshTodayHome();
    } catch (e) {
        utils.showErrorFeedback(e?.message || String(e) || 'Could not log that session.');
    }
}

async function addTodayTask() {
    const input = document.getElementById('todayNewTitle');
    const title = (input?.value || '').trim();
    if (!title) {
        utils.showErrorFeedback('Name the task first.');
        return;
    }
    try {
        await eel.create_work_item(title, utils.localISODate())();
        if (input) input.value = '';
        utils.showSuccessFeedback('Added to today.');
        utils.notifyDataChanged();
        await refreshTodayHome();
        input?.focus();
    } catch (e) {
        utils.showErrorFeedback('Could not add that task.');
    }
}

async function saveTodayJournal() {
    const ta = document.getElementById('todayJournal');
    const text = (ta?.value || '').trim();
    if (!text) {
        utils.showErrorFeedback('Write a sentence first.');
        return;
    }
    try {
        await eel.save_journal_entry(text, 0, false, [])();
        if (ta) ta.value = '';
        utils.showSuccessFeedback('Journal saved.');
        utils.notifyDataChanged();
        await refreshTodayHome();
    } catch (e) {
        utils.showErrorFeedback('Could not save that entry.');
    }
}

export async function refreshTodayHome() {
    const root = document.getElementById('todayHome');
    if (!root) return;
    try {
        const data = await eel.get_today_home()();
        const heading = document.getElementById('todayDateTitle');
        const sub = document.getElementById('todayDateSub');
        const parts = mastheadParts(data.local_date);
        if (heading) heading.textContent = parts.weekday;
        if (sub) sub.textContent = parts.rest;
        paintPulse(data);
        paintCustomize();
        const items = data.today || [];
        const active = items.find((item) => item.status === 'active');
        const rest = items.filter((item) => item.id !== active?.id);
        const hero = document.getElementById('todayActiveTodo');
        if (hero) {
            hero.innerHTML = active
                ? heroCard(active)
                : '';
            if (active) await bindActs(hero);
        }
        const list = document.getElementById('todayTodoList');
        if (list) {
            const open = rest.filter((item) => item.status !== 'done');
            const done = rest.filter((item) => item.status === 'done');
            if (!items.length) {
                list.innerHTML = `
                    <div class="empty-state empty-state--quiet">
                        <p>Nothing dated for today.</p>
                    </div>`;
            } else {
                list.innerHTML = `${open.map(compactRow).join('')}${done.map(compactRow).join('')}`;
                await bindActs(list);
            }
        }
        const expectedEl = document.getElementById('todayExpected');
        const expected = data.expected || {};
        if (expectedEl) {
            expectedEl.textContent = expected.labels?.length
                ? `Expected today: ${expected.labels.join(' · ')}`
                : 'No template session expected today';
        }
        const chips = document.getElementById('todayWorkoutChips');
        const logged = (data.workout_day?.sessions || []).map((s) => s.kind);
        renderWorkoutChips(chips, { expected: expected.kinds || [], logged });
        chips?.querySelectorAll('[data-kind]').forEach((btn) => {
            btn.addEventListener('click', () => {
                void handleTodayChip(btn.getAttribute('data-kind'));
            });
        });
        const sessions = document.getElementById('todaySessions');
        if (sessions) {
            const rows = data.workout_day?.sessions || [];
            sessions.innerHTML = rows.length
                ? rows.map((s) => `<li>${utils.escapeHtml(s.label || s.kind_label)}</li>`).join('')
                : '<li class="today-session-empty">No session yet</li>';
        }
        const streak = document.getElementById('todayJournalMeta');
        if (streak) {
            const count = data.journal_count || 0;
            const n = data.journal_streak || 0;
            streak.textContent = count
                ? `${count} saved today${n ? ` · ${n}-day streak` : ''}`
                : n
                  ? `${n}-day writing streak`
                  : '';
        }
        if (active) startHomeTick();
        else stopHomeTick();
    } catch (e) {
        console.error(e);
        const list = document.getElementById('todayTodoList');
        if (list) list.innerHTML = '<p class="checklist-error">Could not load today.</p>';
    }
}

export async function refreshToday() {
    const el = document.getElementById('todayStatus');
    if (el) {
        try {
            const data = await eel.get_today_status()();
            renderPills(el, data);
        } catch (e) {
            console.error(e);
            el.innerHTML = '<span class="today-label">Today</span><span class="today-fallback">Status unavailable</span>';
        }
    }
    if (document.getElementById('todayTab')?.classList.contains('active')) {
        await refreshTodayHome();
    }
}

export function setupToday() {
    document.getElementById('todayAddBtn')?.addEventListener('click', () => {
        void addTodayTask();
    });
    document.getElementById('todayNewTitle')?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            void addTodayTask();
        }
    });
    document.getElementById('todayJournalSave')?.addEventListener('click', () => {
        void saveTodayJournal();
    });
    document.getElementById('todayOpenJournal')?.addEventListener('click', () => {
        document.dispatchEvent(new CustomEvent('kosistenz:open-tab', { detail: { tab: 'journal' } }));
    });
    document.getElementById('todayOpenTodo')?.addEventListener('click', () => {
        document.dispatchEvent(new CustomEvent('kosistenz:open-tab', { detail: { tab: 'todo' } }));
    });
    document.getElementById('todayOpenWorkout')?.addEventListener('click', () => {
        document.dispatchEvent(new CustomEvent('kosistenz:open-tab', { detail: { tab: 'workout' } }));
    });
    document.getElementById('todayCustomizeBtn')?.addEventListener('click', () => {
        const panel = document.getElementById('todayCustomizePanel');
        setCustomizeOpen(!!panel?.classList.contains('is-hidden'));
        paintCustomize();
    });
    document.getElementById('todayShowTodo')?.addEventListener('change', (e) => {
        persistAppearance({ todayTodo: e.target.checked });
    });
    document.getElementById('todayShowWorkout')?.addEventListener('change', (e) => {
        persistAppearance({ todayWorkout: e.target.checked });
    });
    document.getElementById('todayShowJournal')?.addEventListener('change', (e) => {
        persistAppearance({ todayJournal: e.target.checked });
    });
    document.getElementById('todayLayoutGroup')?.querySelectorAll('[data-value]').forEach((btn) => {
        btn.addEventListener('click', () => {
            persistAppearance({ todayLayout: btn.getAttribute('data-value') });
            paintCustomize();
        });
    });
    document.getElementById('todayOrderList')?.addEventListener('click', (e) => {
        const btn = e.target.closest('[data-move]');
        if (!btn || btn.disabled) return;
        const moduleId = btn.closest('[data-module]')?.getAttribute('data-module');
        if (!moduleId) return;
        const next = moveTodayModule(getAppearance().todayOrder, moduleId, btn.getAttribute('data-move'));
        persistAppearance({ todayOrder: next.join(',') });
        paintCustomize();
    });
    onAppearanceChange(() => paintCustomize());
    document.getElementById('todayLogSpecial')?.addEventListener('click', () => {
        void confirmTodaySpecial();
    });
    void refreshToday();
    document.addEventListener('kosistenz:data-changed', () => {
        void refreshToday();
    });
    document.addEventListener('kosistenz:tab-shown', (e) => {
        if (e.detail?.tab === 'today') void refreshTodayHome();
        else void refreshToday();
    });
}

export async function onTodayTabShown() {
    await refreshTodayHome();
}
