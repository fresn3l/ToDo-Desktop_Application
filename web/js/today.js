/**
 * Compact Today status in the topbar — workout, to do, journal.
 */

import * as utils from './utils.js';

function renderToday(el, data) {
    const journalCount = data.journal_count || 0;
    const journalLabel = journalCount
        ? `${journalCount} journal${journalCount === 1 ? '' : 's'}`
        : 'No journal yet';

    const workout = data.workout || {};
    const workoutDone = !!workout.done;
    const sessionCount = workout.session_count || 0;
    let workoutLabel = 'Workout';
    if (workoutDone) {
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

    const journalAction = journalCount ? 'timeline' : 'journal';
    el.innerHTML = `
        <span class="today-label">Today</span>
        <div class="today-pills">
            <button type="button" class="${workoutClasses}"
                data-action="${workoutDone ? 'timeline' : 'workout'}"
                title="${workoutDone ? 'Open today on Timeline' : 'Log a workout'}">
                ${utils.escapeHtml(workoutLabel)}
            </button>
        </div>
        <button type="button" class="${workClasses}"
            data-action="todo"
            title="${workOpen ? 'Open today’s To Do' : 'Open To Do'}">
            ${utils.escapeHtml(workLabel)}
        </button>
        <button type="button" class="today-pill today-journal ${journalCount ? 'is-done' : 'is-muted'}"
            data-action="${journalAction}"
            title="${journalCount ? 'Open today on Timeline' : 'Write a journal entry'}">
            ${utils.escapeHtml(journalLabel)}
        </button>
    `;

    el.querySelectorAll('[data-action]').forEach((btn) => {
        btn.addEventListener('click', () => {
            const action = btn.getAttribute('data-action');
            const date = data.local_date;
            if (action === 'workout') {
                document.dispatchEvent(
                    new CustomEvent('kosistenz:open-tab', { detail: { tab: 'workout' } }),
                );
            } else if (action === 'timeline' && date) {
                document.dispatchEvent(
                    new CustomEvent('kosistenz:open-day', { detail: { date } }),
                );
            } else if (action === 'journal') {
                document.dispatchEvent(
                    new CustomEvent('kosistenz:open-tab', { detail: { tab: 'journal' } }),
                );
            } else if (action === 'todo') {
                document.dispatchEvent(
                    new CustomEvent('kosistenz:open-tab', { detail: { tab: 'todo' } }),
                );
            }
        });
    });
}

export async function refreshToday() {
    const el = document.getElementById('todayStatus');
    if (!el) return;
    try {
        const data = await eel.get_today_status()();
        renderToday(el, data);
    } catch (e) {
        console.error(e);
        el.innerHTML = '<span class="today-label">Today</span><span class="today-fallback">Status unavailable</span>';
    }
}

export function setupToday() {
    void refreshToday();
    document.addEventListener('kosistenz:data-changed', () => {
        void refreshToday();
    });
    document.addEventListener('kosistenz:tab-shown', () => {
        void refreshToday();
    });
}
