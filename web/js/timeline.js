/**
 * Unified timeline — journal + checklist for one day.
 */

import * as utils from './utils.js';
import { mountWeekStrip } from './weekstrip.js';

let timelineDateBound = false;
let timelineHealthBound = false;

function todayLocal() {
    return utils.localISODate();
}

export function setupTimeline() {
    const picker = document.getElementById('timelineDate');
    const todayBtn = document.getElementById('timelineToday');
    if (!picker) return;

    const today = todayLocal();
    picker.value = today;
    picker.max = today;

    if (!timelineHealthBound) {
        timelineHealthBound = true;
        document.getElementById('importHealthBtn')?.addEventListener('click', async () => {
            const path = document.getElementById('healthExportPath')?.value.trim();
            const status = document.getElementById('healthImportStatus');
            try {
                const result = await eel.import_health_export(path)();
                if (status) status.textContent = `Imported ${result.days_imported} day(s).`;
                utils.showSuccessFeedback('Health data imported.');
                await loadTimelineDay(document.getElementById('timelineDate')?.value || todayLocal());
            } catch (e) {
                utils.showErrorFeedback(typeof e === 'string' ? e : e?.message || 'Import failed.');
            }
        });

        document.getElementById('refreshScreenTimeBtn')?.addEventListener('click', async () => {
            const status = document.getElementById('healthImportStatus');
            try {
                const result = await eel.refresh_screen_time_for_recent_days(7)();
                if (status) status.textContent = result.note || `Updated ${result.updated} day(s).`;
                if (result.ok) utils.showSuccessFeedback('Screen Time refresh attempted.');
                else utils.showErrorFeedback(result.note || 'Screen Time refresh unavailable.');
                await loadTimelineDay(document.getElementById('timelineDate')?.value || todayLocal());
            } catch (e) {
                utils.showErrorFeedback('Screen Time refresh failed.');
            }
        });
    }

    if (!timelineDateBound) {
        timelineDateBound = true;
        picker.addEventListener('change', () => loadTimelineDay(picker.value));
        todayBtn?.addEventListener('click', () => {
            const d = todayLocal();
            picker.value = d;
            picker.max = d;
            loadTimelineDay(d);
        });
    }
}

export async function onTimelineTabShown() {
    setupTimeline();
    const picker = document.getElementById('timelineDate');
    await loadTimelineDay(picker?.value || todayLocal());
}

async function refreshWeekStrip(selectedDate) {
    const el = document.getElementById('timelineWeekStrip');
    await mountWeekStrip(el, {
        endDate: selectedDate || todayLocal(),
        selectedDate,
        onSelect: (date) => {
            const picker = document.getElementById('timelineDate');
            if (picker) picker.value = date;
            loadTimelineDay(date, { refreshStrip: false });
        },
    });
}

async function loadTimelineDay(localDate, { refreshStrip = true } = {}) {
    const el = document.getElementById('timelineContent');
    if (!el || !localDate) return;
    el.innerHTML = '<div class="empty-state empty-state--loading"><div class="loading-spinner"></div><p>Loading…</p></div>';
    if (refreshStrip) {
        void refreshWeekStrip(localDate);
    } else {
        document.querySelectorAll('#timelineWeekStrip .week-day').forEach((btn) => {
            const on = btn.getAttribute('data-date') === localDate;
            btn.classList.toggle('is-selected', on);
            btn.setAttribute('aria-pressed', on ? 'true' : 'false');
        });
    }
    try {
        const data = await eel.get_timeline_day(localDate)();
        let health = {};
        try {
            health = await eel.get_health_snapshot(localDate)();
        } catch (_) {
            /* optional */
        }
        el.innerHTML = renderTimeline(data, health);
    } catch (e) {
        console.error(e);
        el.innerHTML = '<p class="checklist-error">Could not load timeline.</p>';
    }
}

function renderTimeline(data, health) {
    let checkHtml = '';
    if (!data.submissions.length) {
        checkHtml = '<p class="checklist-empty">No checklist submissions this day.</p>';
    } else {
        data.submissions.forEach((sub) => {
            const when = new Date(sub.created_at).toLocaleTimeString();
            const title = sub.title || sub.checklist_id || 'Checklist';
            let rows = (sub.answers_formatted || [])
                .map(
                    (a) =>
                        `<tr><td>${utils.escapeHtml(a.label)}</td><td>${utils.escapeHtml(a.value)}</td></tr>`,
                )
                .join('');
            const summary = sub.summary
                ? `<p class="checklist-history-summary">${utils.escapeHtml(sub.summary)}</p>`
                : '';
            checkHtml += `
                <div class="timeline-block">
                    <div class="timeline-block-meta">${utils.escapeHtml(title)} · ${utils.escapeHtml(when)}</div>
                    ${summary}
                    <table class="timeline-answers"><tbody>${rows}</tbody></table>
                </div>
            `;
        });
    }

    let journalHtml = '';
    if (!data.journal_entries.length) {
        journalHtml = '<p class="checklist-empty">No journal entries this day.</p>';
    } else {
        data.journal_entries.forEach((e) => {
            const tags = (e.tags || [])
                .map((t) => `<span class="journal-tag">${utils.escapeHtml(t)}</span>`)
                .join('');
            journalHtml += `
                <article class="timeline-journal-entry">
                    <div class="timeline-block-meta">
                        ${e.duration_label ? utils.escapeHtml(e.duration_label) : ''}
                        ${tags}
                    </div>
                    <p>${utils.escapeHtml(e.content)}</p>
                </article>
            `;
        });
    }

    const writingMin = Math.round((data.total_writing_seconds || 0) / 60);

    let healthHtml = '';
    if (health && Object.keys(health).length) {
        const parts = [];
        if (health.sleep_hours) parts.push(`Sleep: ${health.sleep_hours}h`);
        if (health.steps) parts.push(`Steps: ${health.steps}`);
        if (health.screen_time_hours) {
            parts.push(`Screen time (experimental): ${health.screen_time_hours}h`);
        }
        if (Array.isArray(health.workouts) && health.workouts.length) {
            parts.push(`Workouts: ${health.workouts.length}`);
        }
        if (parts.length) {
            healthHtml = `
                <section class="timeline-section">
                    <h3>Health / Screen Time</h3>
                    <p class="timeline-health-summary">${utils.escapeHtml(parts.join(' · '))}</p>
                </section>
            `;
        }
    }

    return `
        <div class="timeline-summary">
            <span>${data.submission_count} checklist(s)</span>
            <span>${data.journal_count} journal entry(ies)</span>
            <span>${writingMin} min writing</span>
        </div>
        ${healthHtml}
        <section class="timeline-section">
            <h3>Checklist</h3>
            ${checkHtml}
        </section>
        <section class="timeline-section">
            <h3>Journal</h3>
            ${journalHtml}
        </section>
    `;
}
