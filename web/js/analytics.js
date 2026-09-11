/**
 * Analytics — planned hours, attendance, to-do completion, plus journal cards.
 */

import * as utils from './utils.js';
import { callEel } from './lazy.js';
import { mountWeekStrip, requestOpenTimelineDate } from './weekstrip.js';

let analyticsRange = 28;
let allocationPeriod = 'week';

function bindExportsOnce() {
    if (document.body.dataset.analyticsExports === '1') return;
    document.body.dataset.analyticsExports = '1';
    document.querySelectorAll('[data-export]').forEach((btn) => {
        btn.addEventListener('click', async () => {
            const kind = btn.getAttribute('data-export');
            const status = document.getElementById('exportStatus');
            try {
                let result;
                if (kind === 'journal-json') result = await eel.export_journal_json()();
                else if (kind === 'journal-csv') result = await eel.export_journal_csv()();
                else if (kind === 'work-json') result = await eel.export_work_json()();
                else if (kind === 'work-csv') result = await eel.export_work_csv()();
                else if (kind === 'workouts-json') result = await eel.export_workouts_json()();
                else if (kind === 'workouts-csv') result = await eel.export_workouts_csv()();
                else if (kind === 'week-markdown') result = await eel.export_week_markdown(7)();
                else return;
                if (status) {
                    const name = result.path ? result.path.split(/[/\\]/).pop() : '';
                    if (kind === 'week-markdown') {
                        status.textContent = name
                            ? `Week ${result.start} → ${result.end} saved as ${name}`
                            : `Week ${result.start} → ${result.end} saved.`;
                    } else {
                        status.textContent = name
                            ? `Exported ${result.count} record(s) · ${name}`
                            : `Exported ${result.count} record(s).`;
                    }
                }
                utils.showSuccessFeedback(kind === 'week-markdown' ? 'Week markdown saved.' : 'Export saved.');
            } catch (e) {
                console.error(e);
                utils.showErrorFeedback('Export failed.');
            }
        });
    });
}

export function setupAnalytics() {
    bindExportsOnce();
    const group = document.getElementById('analyticsRange');
    if (group && !group.dataset.ready) {
        group.dataset.ready = '1';
        group.querySelectorAll('[data-value]').forEach((btn) => {
            btn.addEventListener('click', () => {
                analyticsRange = parseInt(btn.getAttribute('data-value') || '30', 10);
                group.querySelectorAll('[data-value]').forEach((other) => {
                    other.classList.toggle('is-selected', other === btn);
                });
                void onAnalyticsTabShown();
            });
        });
    }
}

export const setupReview = setupAnalytics;

export async function onAnalyticsTabShown() {
    const el = document.getElementById('analyticsContent');
    if (!el) return;
    el.innerHTML = '<div class="empty-state empty-state--loading"><div class="loading-spinner"></div><p>Loading analytics…</p></div>';
    await mountWeekStrip(document.getElementById('analyticsWeekStrip'), {
        selectedDate: utils.localISODate(),
        onSelect: (date) => requestOpenTimelineDate(date),
    });
    try {
        const data = await eel.get_analytics(analyticsRange)();
        paintConsistency(data.consistency || {});
        await paintRateGoals();
        el.innerHTML = renderAnalytics(data);
        await paintTimeAllocation();
        document.getElementById('savePatternNote')?.addEventListener('click', async () => {
            const ta = document.getElementById('patternNoteInput');
            try {
                await eel.save_weekly_pattern_note(ta?.value.trim() || '')();
                utils.showSuccessFeedback('Pattern note saved.');
            } catch (e) {
                utils.showErrorFeedback('Could not save note.');
            }
        });
        el.querySelectorAll('[data-open-day]').forEach((btn) => {
            btn.addEventListener('click', () => {
                const date = btn.getAttribute('data-open-day');
                if (date) requestOpenTimelineDate(date);
            });
        });
    } catch (e) {
        console.error(e);
        el.innerHTML = '<p class="checklist-error">Could not load analytics.</p>';
    }
}

export const onReviewTabShown = onAnalyticsTabShown;

async function paintTimeAllocation() {
    const host = document.getElementById('timeAllocation');
    if (!host || typeof eel === 'undefined' || !eel.get_time_allocation) return;
    try {
        const data = await eel.get_time_allocation(allocationPeriod)();
        host.innerHTML = renderTimeAllocation(data);
        host.querySelectorAll('[data-alloc]').forEach((btn) => {
            btn.addEventListener('click', () => {
                allocationPeriod = btn.getAttribute('data-alloc') || 'week';
                void paintTimeAllocation();
            });
        });
    } catch (err) {
        console.error(err);
        host.innerHTML = '<p class="checklist-error">Could not load time allocation.</p>';
    }
}

function renderTimeAllocation(data) {
    const rows = data.categories || [];
    const bars = rows
        .map((row) => `
            <li class="alloc-row">
                <div class="alloc-row-head">
                    <strong>${utils.escapeHtml(row.label)}</strong>
                    <span>${row.hours}h · ${row.pct}%</span>
                </div>
                <div class="alloc-bar" aria-hidden="true"><span style="width:${Math.max(row.pct || 0, row.minutes ? 2 : 0)}%"></span></div>
            </li>`)
        .join('') || '<li class="checklist-empty">Nothing on the calendar for this stretch.</li>';
    return `
        <div class="review-card review-card--wide">
            <div class="panel-header compact-widget-head">
                <div>
                    <h3>Time allocation</h3>
                    <p class="review-detail">${utils.escapeHtml(data.period_label || '')} · ${utils.escapeHtml(data.start || '')} → ${utils.escapeHtml(data.end || '')} · ${data.total_hours || 0}h on the clock</p>
                </div>
                <div class="segmented" role="group" aria-label="Week or month">
                    <button type="button" data-alloc="week" class="${data.period === 'week' ? 'is-selected' : ''}">Last week</button>
                    <button type="button" data-alloc="month" class="${data.period === 'month' ? 'is-selected' : ''}">This month</button>
                </div>
            </div>
            <ul class="review-list alloc-list">${bars}</ul>
        </div>
    `;
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
    const pct = Math.max(0, Math.min(100, goal.percent || 0));
    return `
        <article class="goal-card${goal.overdue ? ' is-overdue' : ''}" data-id="${utils.escapeHtml(goal.id)}">
            <div class="goal-card-head">
                <h3>${utils.escapeHtml(goal.title)}</h3>
                <button type="button" class="btn-ghost goal-remove" data-act="delete-rate">Remove</button>
            </div>
            <p class="goal-meta">${utils.escapeHtml(goal.measure_label || goal.measure || '')} · ${utils.escapeHtml(goal.window_label || '')}</p>
            <div class="goal-progress">
                <div class="goal-progress-meta">
                    <span>${utils.escapeHtml(formatRateValue(goal))}</span>
                    <span>${goal.percent == null ? '—' : `${pct}%`}</span>
                </div>
                <div class="goal-progress-track" role="progressbar" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100">
                    <div class="goal-progress-fill" style="width:${goal.percent == null ? 0 : pct}%"></div>
                </div>
            </div>
        </article>`;
}

async function paintRateGoals() {
    const host = document.getElementById('rateGoalsBoard');
    if (!host) return;
    try {
        const board = await callEel('get_goals_board');
        const rates = board.rates?.goals || [];
        host.innerHTML = `
            <div class="review-card review-card--wide rate-goal-panel">
                <h3>Rate goals</h3>
                <p class="review-detail">Attendance, hours, or to-do completion. Title is yours. Attendance counts every bar.</p>
                <form id="rateGoalForm" class="rate-goal-form">
                    <input type="text" name="title" class="checklist-text-input" placeholder="Show up to these" autocomplete="off">
                    <select name="measure" class="checklist-text-input" aria-label="Measure">
                        <option value="attendance">Attendance %</option>
                        <option value="hours">Hours</option>
                        <option value="todo_completion">To-do completion %</option>
                    </select>
                    <input type="number" name="target" class="checklist-text-input" min="1" step="1" placeholder="Target" required>
                    <select name="window" class="checklist-text-input" aria-label="Window">
                        <option value="4">4 weeks</option>
                        <option value="12">12 weeks</option>
                        <option value="52">Year</option>
                    </select>
                    <button type="submit" class="btn-primary">Add rate</button>
                </form>
                <div class="rate-goal-list">${rates.map(rateCard).join('') || '<p class="checklist-empty">No rate goals yet.</p>'}</div>
            </div>`;
        host.querySelector('#rateGoalForm')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const form = e.currentTarget;
            const title = (form.title?.value || '').trim();
            const measure = form.measure?.value || 'attendance';
            const target = form.target?.value || '';
            const windowWeeks = form.window?.value || '4';
            if (!title) {
                utils.showErrorFeedback('Name the goal first.');
                return;
            }
            try {
                await callEel('create_rate_goal', title, measure, target, windowWeeks);
                utils.showSuccessFeedback('Rate goal saved.');
                utils.notifyDataChanged();
                await paintRateGoals();
            } catch (err) {
                utils.showErrorFeedback(err?.message || 'Could not save that goal.');
            }
        });
        host.querySelectorAll('[data-act="delete-rate"]').forEach((btn) => {
            btn.addEventListener('click', async () => {
                const id = btn.closest('[data-id]')?.getAttribute('data-id');
                if (!id) return;
                try {
                    await callEel('delete_goal', id);
                    utils.notifyDataChanged();
                    await paintRateGoals();
                } catch (err) {
                    utils.showErrorFeedback('Could not remove that goal.');
                }
            });
        });
    } catch (err) {
        console.error(err);
        host.innerHTML = '<p class="checklist-error">Could not load rate goals.</p>';
    }
}

function paintConsistency(data) {
    const host = document.getElementById('consistencyCharts');
    if (!host) return;
    const weeks = data.weeks || [];
    host.innerHTML = `
        <div class="review-grid consistency-grid">
            <div class="review-card">
                <h3>Hours</h3>
                <p class="review-stat">${data.hours || 0}</p>
                <p class="review-detail">planned hours on the clock</p>
            </div>
            <div class="review-card">
                <h3>Attendance</h3>
                <p class="review-stat">${data.attendance_pct == null ? '—' : `${data.attendance_pct}%`}</p>
                <p class="review-detail">${data.attended || 0} of ${data.closed || 0} closed bars</p>
            </div>
            <div class="review-card">
                <h3>To-dos</h3>
                <p class="review-stat">${data.todo_pct == null ? '—' : `${data.todo_pct}%`}</p>
                <p class="review-detail">${data.todo_done || 0} of ${data.todo_total || 0} dated finished</p>
            </div>
        </div>
        <div class="review-card review-card--wide">
            <h3>Weekly hours</h3>
            ${weekChart(weeks, 'hours', 'Hours planned each week')}
        </div>
        <div class="review-card review-card--wide">
            <h3>Attendance</h3>
            ${weekChart(weeks, 'attendance_pct', 'Attendance percent each week', true)}
        </div>
        <div class="review-card review-card--wide">
            <h3>To-do completion</h3>
            ${weekChart(weeks, 'todo_pct', 'To-do completion percent each week', true)}
        </div>`;
}

function weekChart(weeks, key, aria, percent = false) {
    const rows = (weeks || []).map((row) => ({
        label: row.label || row.week_start || '',
        value: row[key] == null ? 0 : Number(row[key]),
        empty: row[key] == null,
    }));
    if (!rows.length) {
        return '<p class="checklist-empty">Nothing in this range yet.</p>';
    }
    const width = 640;
    const height = 148;
    const padL = 8;
    const padR = 8;
    const padT = 10;
    const padB = 28;
    const max = percent ? 100 : Math.max(...rows.map((row) => row.value), 1);
    const inner = width - padL - padR;
    const gap = rows.length > 20 ? 2 : 6;
    const barW = Math.max(4, (inner / rows.length) - gap);
    const bars = rows.map((row, index) => {
        const x = padL + index * (inner / rows.length) + gap / 2;
        const h = row.empty ? 0 : (row.value / max) * (height - padT - padB);
        const y = height - padB - h;
        const label = rows.length <= 16 || index % Math.ceil(rows.length / 8) === 0
            ? `<text x="${(x + barW / 2).toFixed(1)}" y="${height - 8}" text-anchor="middle">${utils.escapeHtml(String(row.label))}</text>`
            : '';
        return `<rect class="consistency-bar${row.empty ? ' is-empty' : ''}" x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${barW.toFixed(1)}" height="${Math.max(h, 0).toFixed(1)}" rx="3"></rect>${label}`;
    }).join('');
    return `
        <svg class="consistency-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="${utils.escapeHtml(aria)}">
            ${bars}
        </svg>`;
}

function renderAnalytics(data) {
    const journal = data.journal || {};
    const workout = data.workout || {};
    const work = data.work || {};
    const byKind = Object.entries(workout.by_kind || {})
        .map(([k, v]) => `<li>${utils.escapeHtml(k)}: ${utils.escapeHtml(String(v))}</li>`)
        .join('') || '<li class="checklist-empty">No sessions this period</li>';
    const series = (work.series || [])
        .filter((row) => row.expected || row.done || row.missed)
        .map((row) => {
            const rate = row.expected ? Math.round((row.done / row.expected) * 100) : 0;
            return `<li><strong>${utils.escapeHtml(row.title)}</strong> · ${utils.escapeHtml(row.cadence_label)} · ${row.done}/${row.expected} (${rate}%)</li>`;
        })
        .join('') || '<li class="checklist-empty">No repeating to dos this period</li>';
    const capacity = data.capacity || {};
    const plan = data.workout_plan || {};

    return `
        <div class="review-grid">
            <div class="review-card">
                <h3>Journal</h3>
                <p class="review-stat">${journal.streak || 0}</p>
                <p class="review-detail">day writing streak</p>
                <ul class="review-list">
                    <li>${journal.days_written || 0} of ${data.days} days written</li>
                    <li>${journal.entries || 0} entries · ${journal.minutes || 0} min</li>
                </ul>
            </div>
            <div class="review-card">
                <h3>Capacity</h3>
                <p class="review-stat">${capacity.completion_pct || 0}%</p>
                <p class="review-detail">morning focus finished</p>
                <ul class="review-list">
                    <li>${capacity.done_count || 0} of ${capacity.focus_count || 0} planned · ${capacity.days_planned || 0} days with a brief</li>
                    <li>${capacity.rolled_count || 0} moved to tomorrow · ${capacity.leftover_count || 0} left undone</li>
                </ul>
            </div>
            <div class="review-card">
                <h3>Workout</h3>
                <p class="review-stat">${workout.miles || 0}</p>
                <p class="review-detail">miles · ${workout.days_trained || 0} days trained</p>
                <ul class="review-list">${byKind}</ul>
            </div>
            <div class="review-card">
                <h3>To Do</h3>
                <p class="review-stat">${work.repeat_missed || 0}</p>
                <p class="review-detail">missed repeating days</p>
                <ul class="review-list">
                    <li>${work.repeat_done || 0} of ${work.repeat_expected || 0} expected (${work.repeat_completion_pct || 0}%)</li>
                    <li>${plan.done || 0} of ${plan.expected || 0} template sessions</li>
                </ul>
            </div>
            <div class="review-card review-card--wide">
                <h3>Weight</h3>
                ${weightSparkline(workout.weight_log || [])}
            </div>
            <div class="review-card review-card--wide">
                <h3>Repeating series</h3>
                <p class="review-detail">Amber dots on the week strip are misses. They stay on that date — click a day to open Timeline.</p>
                <ul class="review-list">${series}</ul>
            </div>
            <div class="review-card review-card--wide">
                <h3>${utils.escapeHtml(data.pattern_prompt || 'What pattern do you notice?')}</h3>
                <textarea id="patternNoteInput" class="checklist-textarea" rows="3" placeholder="Your reflection for week ${utils.escapeHtml(data.week_key || '')}…">${utils.escapeHtml(data.pattern_note || '')}</textarea>
                <button type="button" id="savePatternNote" class="btn-primary">Save reflection</button>
            </div>
        </div>
        <p class="checklist-hint small">Period: ${utils.escapeHtml(data.period_start)} → ${utils.escapeHtml(data.period_end)} · ${utils.escapeHtml(plan.label || '')}</p>
    `;
}

function weightSparkline(log) {
    const points = (log || []).filter((row) => row && row.weight != null && !Number.isNaN(Number(row.weight)));
    if (!points.length) {
        return '<p class="checklist-empty">No weight logged</p>';
    }
    const vals = points.map((row) => Number(row.weight));
    const last = vals[vals.length - 1];
    const first = vals[0];
    const delta = last - first;
    const deltaLabel = `${delta > 0 ? '+' : ''}${delta.toFixed(1)} lb`;
    const latestDate = points[points.length - 1].date || '';
    if (vals.length === 1) {
        return `
            <p class="review-stat">${utils.escapeHtml(String(last))}</p>
            <p class="review-detail">lb on ${utils.escapeHtml(String(latestDate))}</p>
        `;
    }
    const min = Math.min(...vals);
    const max = Math.max(...vals);
    const span = max - min || 1;
    const width = 320;
    const height = 56;
    const pad = 4;
    const coords = vals.map((value, index) => {
        const x = pad + (index / (vals.length - 1)) * (width - pad * 2);
        const y = pad + (1 - (value - min) / span) * (height - pad * 2);
        return `${x.toFixed(1)},${y.toFixed(1)}`;
    });
    return `
        <svg class="weight-sparkline" viewBox="0 0 ${width} ${height}" role="img" aria-label="Body weight trend">
            <polyline fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" points="${coords.join(' ')}"></polyline>
        </svg>
        <p class="review-detail">${utils.escapeHtml(String(last))} lb · ${utils.escapeHtml(deltaLabel)} over ${points.length} weigh-ins${latestDate ? ` · last ${utils.escapeHtml(String(latestDate))}` : ''}</p>
    `;
}
