/**
 * Goals — 1 week, 6 months, year, 5 years. Finished to-dos add minutes.
 * Weekly goals spawn a to-do each Sunday for the coming week.
 */

import * as utils from './utils.js';
import { callEel } from './lazy.js';

function formatMinutes(n) {
    const m = Math.max(0, Number(n) || 0);
    const h = Math.floor(m / 60);
    const r = m % 60;
    if (h && r) return `${h}h ${r}m`;
    if (h) return `${h}h`;
    return `${r}m`;
}

export async function loadGoalOptions(selectId, selected) {
    const el = document.getElementById(selectId);
    if (!el) return;
    try {
        const goals = await callEel('list_goals');
        const current = selected || el.value || '';
        const opts = ['<option value="">Goal (optional)</option>'].concat(
            (goals || []).map((goal) => {
                const kw = goal.keyword ? ` · ${goal.keyword}` : '';
                const label = `${goal.title} · ${goal.horizon_label}${kw}`;
                const sel = goal.id === current ? ' selected' : '';
                return `<option value="${utils.escapeHtml(goal.id)}"${sel}>${utils.escapeHtml(label)}</option>`;
            }),
        );
        el.innerHTML = opts.join('');
    } catch (e) {
        console.error(e);
    }
}

function goalCard(goal) {
    const bits = [];
    if (goal.keyword) bits.push(`<span class="work-flag">${utils.escapeHtml(goal.keyword)}</span>`);
    if (goal.end_date) bits.push(`by ${utils.escapeHtml(goal.end_date)}`);
    const meta = bits.length ? `<p class="goal-meta">${bits.join(' · ')}</p>` : '';
    let meter = '';
    if (goal.has_target) {
        const pct = Math.max(0, Math.min(100, goal.percent || 0));
        meter = `
            <div class="goal-progress">
                <div class="goal-progress-meta">
                    <span>${formatMinutes(goal.spent_minutes)} / ${formatMinutes(goal.target_minutes)}</span>
                    <span>${pct}%</span>
                </div>
                <div class="goal-progress-track" role="progressbar" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100">
                    <div class="goal-progress-fill" style="width:${pct}%"></div>
                </div>
            </div>`;
    } else if (goal.spent_minutes) {
        meter = `<p class="goal-total">${formatMinutes(goal.spent_minutes)} logged</p>`;
    }
    const contribs = (goal.contributions || [])
        .slice(0, 3)
        .map((row) => `<li>${utils.escapeHtml(row.title)} · ${formatMinutes(row.minutes)}</li>`)
        .join('');
    const list = contribs ? `<ul class="goal-contribs">${contribs}</ul>` : '';
    return `
        <article class="goal-card${goal.overdue ? ' is-overdue' : ''}" data-id="${utils.escapeHtml(goal.id)}">
            <div class="goal-card-head">
                <h3>${utils.escapeHtml(goal.title)}</h3>
                <button type="button" class="btn-ghost goal-remove" data-act="delete">Remove</button>
            </div>
            ${meta}
            ${meter}
            ${list}
        </article>`;
}

function addForm(label) {
    return `
        <div class="goal-add">
            <input type="text" class="checklist-text-input" data-field="title" placeholder="${utils.escapeHtml(label)}" autocomplete="off">
            <button type="button" class="btn-primary" data-act="add">Add</button>
            <div class="goal-add-more">
                <input type="text" class="checklist-text-input goal-keyword" data-field="keyword" placeholder="keyword" title="Match this word in a to-do title" autocomplete="off">
                <input type="number" class="checklist-text-input goal-hours" data-field="hours" min="0" step="0.5" placeholder="hrs" title="Optional hour target">
                <input type="date" class="checklist-text-input work-due-input" data-field="end" title="Optional end date">
            </div>
        </div>`;
}

export async function refreshGoals() {
    const root = document.getElementById('goalsBoard');
    if (!root) return;
    try {
        const board = await callEel('get_goals_board');
        root.innerHTML = (board.horizons || [])
            .map((col) => {
                const n = col.goals.length;
                const count = n ? `<span class="goal-horizon-count">${n}</span>` : '';
                const body = n ? col.goals.map(goalCard).join('') : '';
                return `
                    <section class="goal-column" data-horizon="${utils.escapeHtml(col.id)}">
                        <p class="goal-horizon">${utils.escapeHtml(col.label)}${count}</p>
                        ${addForm(col.label)}
                        <div class="goal-list">${body}</div>
                    </section>`;
            })
            .join('');
        bindGoals(root);
        await loadGoalOptions('todoNewGoal');
        await loadGoalOptions('todayNewGoal');
        await loadGoalOptions('allWorkNewGoal');
    } catch (e) {
        console.error(e);
        root.innerHTML = '<p class="checklist-error">Could not load goals.</p>';
    }
}

function bindGoals(root) {
    root.querySelectorAll('.goal-column').forEach((col) => {
        const horizon = col.getAttribute('data-horizon');
        const addBtn = col.querySelector('[data-act="add"]');
        addBtn?.addEventListener('click', () => {
            void addGoal(col, horizon);
        });
        col.querySelector('[data-field="title"]')?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                void addGoal(col, horizon);
            }
        });
    });
    root.querySelectorAll('.goal-card').forEach((card) => {
        const id = card.getAttribute('data-id');
        card.querySelector('[data-act="delete"]')?.addEventListener('click', async () => {
            try {
                await callEel('delete_goal', id);
                utils.notifyDataChanged();
                await refreshGoals();
            } catch (e) {
                utils.showErrorFeedback('Could not remove that goal.');
            }
        });
    });
}

async function addGoal(col, horizon) {
    const title = (col.querySelector('[data-field="title"]')?.value || '').trim();
    const keyword = (col.querySelector('[data-field="keyword"]')?.value || '').trim();
    const hours = col.querySelector('[data-field="hours"]')?.value || '';
    const end = col.querySelector('[data-field="end"]')?.value || '';
    if (!title) {
        utils.showErrorFeedback('Name the goal first.');
        return;
    }
    try {
        await callEel('create_goal', title, horizon, keyword, hours, end);
        utils.showSuccessFeedback('Goal saved.');
        utils.notifyDataChanged();
        await refreshGoals();
    } catch (e) {
        utils.showErrorFeedback(e?.message || 'Could not save that goal.');
    }
}

function goalsBoardIsOpen() {
    const tab = document.getElementById('goalsTab');
    return Boolean(
        tab
        && (tab.classList.contains('active') || tab.classList.contains('widget-source--active')),
    );
}

export function setupGoals() {
    document.addEventListener('kosistenz:data-changed', () => {
        if (goalsBoardIsOpen()) {
            void refreshGoals();
        } else {
            void loadGoalOptions('todoNewGoal');
            void loadGoalOptions('todayNewGoal');
            void loadGoalOptions('allWorkNewGoal');
        }
    });
}

export async function onGoalsTabShown() {
    await refreshGoals();
}
