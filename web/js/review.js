/**
 * Weekly review — automated summary and pattern reflection.
 */

import * as utils from './utils.js';
import { mountWeekStrip, requestOpenTimelineDate } from './weekstrip.js';

export async function setupReview() {
    document.querySelectorAll('[data-export]').forEach((btn) => {
        btn.addEventListener('click', async () => {
            const kind = btn.getAttribute('data-export');
            const status = document.getElementById('exportStatus');
            try {
                let result;
                if (kind === 'checklist-json') result = await eel.export_checklist_json()();
                else if (kind === 'checklist-csv') result = await eel.export_checklist_csv()();
                else if (kind === 'journal-json') result = await eel.export_journal_json()();
                else if (kind === 'journal-csv') result = await eel.export_journal_csv()();
                else return;
                if (status) {
                    status.textContent = `Exported ${result.count} record(s).`;
                }
                utils.showSuccessFeedback('Export saved.');
            } catch (e) {
                console.error(e);
                utils.showErrorFeedback('Export failed.');
            }
        });
    });
}

export async function onReviewTabShown() {
    const el = document.getElementById('reviewContent');
    if (!el) return;
    el.innerHTML = '<div class="empty-state empty-state--loading"><div class="loading-spinner"></div><p>Loading review…</p></div>';
    await mountWeekStrip(document.getElementById('reviewWeekStrip'), {
        selectedDate: utils.localISODate(),
        onSelect: (date) => requestOpenTimelineDate(date),
    });
    try {
        const data = await eel.get_weekly_review(7)();
        el.innerHTML = renderReview(data);
        document.getElementById('savePatternNote')?.addEventListener('click', async () => {
            const ta = document.getElementById('patternNoteInput');
            try {
                await eel.save_weekly_pattern_note(ta?.value.trim() || '')();
                utils.showSuccessFeedback('Pattern note saved.');
            } catch (e) {
                utils.showErrorFeedback('Could not save note.');
            }
        });
    } catch (e) {
        console.error(e);
        el.innerHTML = '<p class="checklist-error">Could not load weekly review.</p>';
    }
}

function renderReview(data) {
    const workouts = Object.entries(data.workout_types || {})
        .map(([k, v]) => `<li>${utils.escapeHtml(k)}: ${v}</li>`)
        .join('') || '<li class="checklist-empty">No workouts logged</li>';

    const breakdown = Object.entries(data.checklist_breakdown || {})
        .map(([k, v]) => `<li>${utils.escapeHtml(k)}: ${v} submission(s)</li>`)
        .join('') || '<li class="checklist-empty">No submissions</li>';

    let customHtml = '';
    (data.custom_question_trends || []).forEach((t) => {
        if (!t.responses) return;
        let detail = '';
        if (t.type === 'yes_no' && t.yes_rate !== undefined) {
            detail = `${Math.round(t.yes_rate * 100)}% yes (${t.yes_count}/${t.responses})`;
        } else if (t.choices) {
            detail = Object.entries(t.choices)
                .map(([k, v]) => `${k}: ${v}`)
                .join(', ');
        }
        customHtml += `<li><strong>${utils.escapeHtml(t.question)}</strong> — ${utils.escapeHtml(detail)}</li>`;
    });
    if (!customHtml) {
        customHtml = '<li class="checklist-empty">No custom question data this week</li>';
    }

    return `
        <div class="review-grid">
            <div class="review-card">
                <h3>Checklist</h3>
                <p class="review-stat">${data.checklist_completion_pct}%</p>
                <p class="review-detail">${data.days_with_checkin} of ${data.days} days with a check-in</p>
                <ul class="review-list">${breakdown}</ul>
            </div>
            <div class="review-card">
                <h3>Exercise</h3>
                <p class="review-stat">${data.exercise_sessions}</p>
                <p class="review-detail">${data.exercise_days ?? data.exercise_sessions} days with exercise logged</p>
                <ul class="review-list">${workouts}</ul>
            </div>
            <div class="review-card">
                <h3>Journal</h3>
                <p class="review-stat">${data.journal_entry_count}</p>
                <p class="review-detail">entries · ${data.journal_writing_minutes} min writing</p>
            </div>
            <div class="review-card review-card--wide">
                <h3>Custom questions</h3>
                <ul class="review-list">${customHtml}</ul>
            </div>
            <div class="review-card review-card--wide">
                <h3>${utils.escapeHtml(data.pattern_prompt)}</h3>
                <textarea id="patternNoteInput" class="checklist-textarea" rows="4" placeholder="Your reflection for week ${utils.escapeHtml(data.week_key)}…">${utils.escapeHtml(data.pattern_note || '')}</textarea>
                <button type="button" id="savePatternNote" class="btn-primary">Save reflection</button>
            </div>
        </div>
        <p class="checklist-hint small">Period: ${utils.escapeHtml(data.period_start)} → ${utils.escapeHtml(data.period_end)}</p>
    `;
}
