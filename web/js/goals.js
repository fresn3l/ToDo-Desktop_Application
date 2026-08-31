/**
 * Goals — 1 week, 6 months, year, 5 years. Finished to-dos add minutes.
 * Weekly goals spawn a to-do each Sunday for the coming week.
 */

import * as utils from './utils.js';

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
    if (!el || typeof eel === 'undefined' || !eel.list_goals) return;
    try {
        const goals = await eel.list_goals()();
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
    const end = goal.end_date ? ` · by ${utils.escapeHtml(goal.end_date)}` : '';
    const kw = goal.keyword ? `<span class="work-flag">${utils.escapeHtml(goal.keyword)}</span>` : '';
    let meter = '';
    if (goal.has_target) {
        const pct = Math.max(0, Math.min(100, goal.percent || 0));
        meter = `
            <div class="goal-progress">
                <div class="goal-progress-meta">
                    <span>${formatMinutes(goal.spent_minutes)} of ${formatMinutes(goal.target_minutes)}</span>
                    <span>${pct}%</span>
                </div>
                <div class="goal-progress-track" role="progressbar" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100">
                    <div class="goal-progress-fill" style="width:${pct}%"></div>
                </div>
            </div>`;
    } else {
        meter = `<p class="goal-total">${formatMinutes(goal.spent_minutes)} logged</p>`;
    }
    const contribs = (goal.contributions || [])
        .slice(0, 5)
        .map(
            (row) =>
                `<li>${utils.escapeHtml(row.title)} · ${formatMinutes(row.minutes)}</li>`,
        )
        .join('');
    const list = contribs
        ? `<ul class="goal-contribs">${contribs}</ul>`
        : `<p class="checklist-hint small">Finish a to-do attached to this goal to add minutes.</p>`;
    return `
        <article class="goal-card${goal.overdue ? ' is-overdue' : ''}" data-id="${utils.escapeHtml(goal.id)}">
            <div class="goal-card-head">
                <h3>${utils.escapeHtml(goal.title)}</h3>
                <p class="work-meta">${kw}${end}</p>
            </div>
            ${meter}
            ${list}
            <div class="work-item-actions">
                <button type="button" class="btn-ghost" data-act="delete">Remove</button>
            </div>
        </article>`;
}

function addForm(horizon, label) {
    return `
        <div class="goal-add">
            <input type="text" class="checklist-text-input" data-field="title" placeholder="${utils.escapeHtml(label)} goal" autocomplete="off">
            <input type="text" class="checklist-text-input goal-keyword" data-field="keyword" placeholder="keyword" title="Match this word in a to-do title, e.g. spanish" autocomplete="off">
            <input type="number" class="checklist-text-input goal-hours" data-field="hours" min="0" step="0.5" placeholder="Hours" title="Optional target. Leave blank for a running total.">
            <input type="date" class="checklist-text-input work-due-input" data-field="end" title="Optional end date">
            <button type="button" class="btn-primary" data-act="add">Add</button>
        </div>`;
}

export async function refreshGoals() {
    const root = document.getElementById('goalsBoard');
    if (!root) return;
    try {
        const board = await eel.get_goals_board()();
        root.innerHTML = (board.horizons || [])
            .map((col) => {
                const hint = col.hint || 'Optional end date. Hours only if you want a bar.';
                const count = col.goals.length
                    ? `${col.goals.length} goal${col.goals.length === 1 ? '' : 's'}. `
                    : '';
                const body = col.goals.length
                    ? col.goals.map(goalCard).join('')
                    : `<div class="empty-state empty-state--quiet"><p>No ${utils.escapeHtml(col.label.toLowerCase())} goals yet.</p></div>`;
                return `
                    <section class="panel goal-column" data-horizon="${utils.escapeHtml(col.id)}">
                        <div class="panel-header">
                            <div>
                                <h2>${utils.escapeHtml(col.label)}</h2>
                                <p class="panel-sub">${utils.escapeHtml(count + hint)}</p>
                            </div>
                        </div>
                        ${addForm(col.id, col.label)}
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
                await eel.delete_goal(id)();
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
        await eel.create_goal(title, horizon, keyword, hours, end)();
        utils.showSuccessFeedback('Goal saved.');
        utils.notifyDataChanged();
        await refreshGoals();
    } catch (e) {
        utils.showErrorFeedback(e?.message || 'Could not save that goal.');
    }
}

export function setupGoals() {
    document.addEventListener('kosistenz:data-changed', () => {
        if (document.getElementById('goalsTab')?.classList.contains('active')) {
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
