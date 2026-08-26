/**
 * Compact Today status in the topbar — morning/evening check-ins + journal.
 */

import * as utils from './utils.js';

function pillLabel(item, suggestedId) {
    const name = item.id === 'morning' ? 'Morning' : 'Evening';
    if (item.done) return `${name} done`;
    if (item.id === suggestedId) return `Start ${name.toLowerCase()}`;
    return name;
}

function renderToday(el, data) {
    const suggested = data.suggested || 'morning';
    const journalCount = data.journal_count || 0;
    const journalLabel = journalCount
        ? `${journalCount} journal${journalCount === 1 ? '' : 's'}`
        : 'No journal yet';

    const pills = [data.morning, data.evening]
        .filter(Boolean)
        .map((item) => {
            const done = !!item.done;
            const isSuggested = !done && item.id === suggested;
            const action = done ? 'timeline' : 'checklist';
            const classes = [
                'today-pill',
                done ? 'is-done' : 'is-todo',
                isSuggested ? 'is-suggested' : '',
            ]
                .filter(Boolean)
                .join(' ');
            const title = done
                ? `${item.title} complete — open today on Timeline`
                : `Start ${item.title}`;
            return `
                <button type="button" class="${classes}"
                    data-action="${action}"
                    data-stem="${utils.escapeHtml(item.id)}"
                    title="${utils.escapeHtml(title)}">
                    ${utils.escapeHtml(pillLabel(item, suggested))}
                </button>
            `;
        })
        .join('');

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
        <div class="today-pills">${pills}</div>
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
            const stem = btn.getAttribute('data-stem');
            const date = data.local_date;
            if (action === 'checklist' && stem) {
                document.dispatchEvent(
                    new CustomEvent('kosistenz:open-checklist', { detail: { stem } }),
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
