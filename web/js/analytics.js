/**
 * Analytics — journal, workouts, and repeating to-do misses.
 */

import * as utils from './utils.js';
import { mountWeekStrip, requestOpenTimelineDate } from './weekstrip.js';

let analyticsRange = 30;

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
        el.innerHTML = renderAnalytics(data);
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
