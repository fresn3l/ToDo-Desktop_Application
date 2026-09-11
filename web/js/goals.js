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
            (goals || []).filter((goal) => !goal.is_rate).map((goal) => {
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

function formatRateValue(goal) {
    const measure = goal.measure || 'attendance';
    const current = goal.current_value;
    const target = goal.target_value;
    if (measure === 'hours') {
        const now = current == null ? '—' : `${Number(current).toFixed(1)}h`;
        const want = target == null ? '' : ` / ${Number(target).toFixed(1)}h`;
        return `${now}${want}`;
    }
    const now = current == null ? '—' : `${Math.round(Number(current))}%`;
    const want = target == null ? '' : ` / ${Math.round(Number(target))}%`;
    return `${now}${want}`;
}

function rateCard(goal) {
    const bits = [];
    if (goal.measure_label) bits.push(utils.escapeHtml(goal.measure_label));
    if (goal.window_label) bits.push(utils.escapeHtml(goal.window_label));
    const meta = bits.length ? `<p class="goal-meta">${bits.join(' · ')}</p>` : '';
    const pct = Math.max(0, Math.min(100, goal.percent || 0));
    const meter = `
            <div class="goal-progress">
                <div class="goal-progress-meta">
                    <span>${utils.escapeHtml(formatRateValue(goal))}</span>
                    <span>${goal.percent == null ? '—' : `${pct}%`}</span>
                </div>
                <div class="goal-progress-track" role="progressbar" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100">
                    <div class="goal-progress-fill" style="width:${goal.percent == null ? 0 : pct}%"></div>
                </div>
            </div>`;
    return `
        <article class="goal-card${goal.overdue ? ' is-overdue' : ''}" data-id="${utils.escapeHtml(goal.id)}" data-rate="1">
            <div class="goal-card-head">
                <h3>${utils.escapeHtml(goal.title)}</h3>
                <button type="button" class="btn-ghost goal-remove" data-act="delete">Remove</button>
            </div>
            ${meta}
            ${meter}
        </article>`;
}

function rateForm() {
    return `
        <div class="goal-add rate-goal-add">
            <input type="text" class="checklist-text-input" data-field="title" placeholder="Show up to these" autocomplete="off">
            <button type="button" class="btn-primary" data-act="add-rate">Add</button>
            <div class="goal-add-more">
                <select class="checklist-text-input" data-field="measure" aria-label="Measure">
                    <option value="attendance">Attendance %</option>
                    <option value="hours">Hours</option>
                    <option value="todo_completion">To-do completion %</option>
                </select>
                <input type="number" class="checklist-text-input goal-hours" data-field="target" min="1" step="1" placeholder="target">
                <select class="checklist-text-input" data-field="window" aria-label="Window">
                    <option value="4">4 weeks</option>
                    <option value="12">12 weeks</option>
                    <option value="52">Year</option>
                </select>
            </div>
        </div>`;
}

function goalCard(goal) {
    if (goal.is_rate) return rateCard(goal);
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
        const rates = board.rates || { id: 'rate', label: 'Rates', hint: '', goals: [] };
        const rateCount = rates.goals?.length ? `<span class="goal-horizon-count">${rates.goals.length}</span>` : '';
        const rateBody = (rates.goals || []).map(rateCard).join('');
        const rateCol = `
                    <section class="goal-column goal-column--rate" data-horizon="rate">
                        <p class="goal-horizon">${utils.escapeHtml(rates.label || 'Rates')}${rateCount}</p>
                        ${rateForm()}
                        <div class="goal-list">${rateBody}</div>
                    </section>`;
        root.innerHTML = rateCol + (board.horizons || [])
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
        col.querySelector('[data-act="add-rate"]')?.addEventListener('click', () => {
            void addRateGoal(col);
        });
        col.querySelector('[data-field="title"]')?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                if (horizon === 'rate') void addRateGoal(col);
                else void addGoal(col, horizon);
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

async function addRateGoal(col) {
    const title = (col.querySelector('[data-field="title"]')?.value || '').trim();
    const measure = col.querySelector('[data-field="measure"]')?.value || 'attendance';
    const target = col.querySelector('[data-field="target"]')?.value || '';
    const windowWeeks = col.querySelector('[data-field="window"]')?.value || '4';
    if (!title) {
        utils.showErrorFeedback('Name the goal first.');
        return;
    }
    try {
        await callEel('create_rate_goal', title, measure, target, windowWeeks);
        utils.showSuccessFeedback('Rate goal saved.');
        utils.notifyDataChanged();
        await refreshGoals();
    } catch (e) {
        utils.showErrorFeedback(e?.message || 'Could not save that goal.');
    }
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

export function setupGoals() {
    document.addEventListener('kosistenz:data-changed', () => {
        if (utils.sourceIsOpen('goalsTab')) void refreshGoals();
    });
}

export async function onGoalsTabShown() {
    await refreshGoals();
}
