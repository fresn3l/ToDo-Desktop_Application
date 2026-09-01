/**
 * Morning brief / evening review Home widget.
 */

import * as utils from './utils.js';

function agendaTime(item) {
    const start = new Date(item.start_at);
    if (Number.isNaN(start.getTime())) return '';
    return start.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
}

function selectedIds(root) {
    return [...root.querySelectorAll('[data-focus]:checked')].map((el) => el.value);
}

function paint(data) {
    const body = document.getElementById('dayBriefBody');
    const title = document.getElementById('dayBriefTitle');
    const summary = document.getElementById('dayBriefSummary');
    const toggle = document.getElementById('dayBriefSlotToggle');
    if (!body) return;
    const slot = data.slot === 'evening' ? 'evening' : 'morning';
    toggle?.querySelectorAll('[data-slot]').forEach((btn) => {
        btn.classList.toggle('is-selected', btn.getAttribute('data-slot') === slot);
    });
    if (title) title.textContent = slot === 'evening' ? 'Evening review' : 'Morning brief';
    if (summary) {
        summary.textContent = slot === 'evening'
            ? 'What got done, what didn’t, and an end-of-day journal.'
            : 'Next events, today’s focus, and what you plan to accomplish.';
    }

    if (slot === 'morning') {
        const agenda = data.agenda || [];
        const candidates = data.focus_candidates || [];
        const selected = new Set(data.selected_ids || []);
        const intention = data.morning?.intention_text || '';
        const agendaHtml = agenda.length
            ? `<ul class="day-brief-agenda">${agenda.map((item) => {
                const kind = item.kind === 'hard' ? 'Class' : item.kind === 'workout' ? 'Gym' : 'Work';
                return `<li><span>${utils.escapeHtml(agendaTime(item))}</span> ${utils.escapeHtml(item.title || '')} <em>${kind}</em></li>`;
            }).join('')}</ul>`
            : '<p class="checklist-empty">No timed events left today.</p>';
        const tasksHtml = candidates.length
            ? `<ul class="day-brief-tasks">${candidates.map((item) => {
                const on = selected.has(item.id) ? ' checked' : '';
                return `<li><label class="checklist-checkbox-label"><input type="checkbox" data-focus value="${utils.escapeHtml(item.id)}"${on}> ${utils.escapeHtml(item.title || '')}</label></li>`;
            }).join('')}</ul>`
            : '<p class="checklist-empty">No open to-dos on today. Add some on To Do, then pick two or three here.</p>';
        body.innerHTML = `
            <div class="day-brief-block">
                <h3>Next up</h3>
                ${agendaHtml}
            </div>
            <div class="day-brief-block">
                <h3>Today’s focus</h3>
                <p class="checklist-hint small">Pick up to ${data.max_focus || 3}.</p>
                ${tasksHtml}
            </div>
            <form id="morningBriefForm" class="day-brief-form">
                <label class="checklist-field-label" for="morningIntention">What do you plan to accomplish today?</label>
                <textarea id="morningIntention" class="checklist-textarea" rows="3" placeholder="The few things that would make today count…">${utils.escapeHtml(intention)}</textarea>
                <button type="submit" class="btn-primary">Save morning brief</button>
            </form>
        `;
        return;
    }

    const review = data.review || {};
    const recap = data.evening?.recap_text || '';
    const list = (items, empty, extra) => {
        if (!(items || []).length) return `<p class="checklist-empty">${empty}</p>`;
        return `<ul class="day-brief-tasks">${items.map((item) => `
            <li>
                <span>${utils.escapeHtml(item.title || '')}</span>
                ${extra ? extra(item) : ''}
            </li>`).join('')}</ul>`;
    };
    body.innerHTML = `
        <div class="day-brief-block">
            <h3>Checked off</h3>
            ${list(review.done, 'Nothing checked off yet.')}
        </div>
        <div class="day-brief-block">
            <h3>Still open</h3>
            ${list(review.leftover, 'Nothing left on today.', (item) => `<button type="button" class="btn-ghost" data-roll="${utils.escapeHtml(item.id)}">Move to tomorrow</button>`)}
        </div>
        <div class="day-brief-block">
            <h3>Moved to tomorrow</h3>
            ${list(review.rolled, 'Nothing rolled forward.')}
        </div>
        <form id="eveningReviewForm" class="day-brief-form">
            <label class="checklist-field-label" for="eveningRecap">End of day</label>
            <textarea id="eveningRecap" class="checklist-textarea" rows="3" placeholder="What happened, what you learned…">${utils.escapeHtml(recap)}</textarea>
            <button type="submit" class="btn-primary">Save evening review</button>
        </form>
    `;
}

export async function refreshDayBrief() {
    const body = document.getElementById('dayBriefBody');
    if (!body || typeof eel === 'undefined' || !eel.get_day_brief) return;
    try {
        paint(await eel.get_day_brief()());
    } catch (err) {
        console.error(err);
        body.innerHTML = '<p class="checklist-error">Could not load today’s brief.</p>';
    }
}

export function setupDayBrief() {
    const root = document.getElementById('dayBriefSource');
    if (!root || root.dataset.ready === '1') return;
    root.dataset.ready = '1';
    document.getElementById('dayBriefSlotToggle')?.addEventListener('click', async (event) => {
        const btn = event.target.closest('[data-slot]');
        if (!btn) return;
        try {
            paint(await eel.set_day_brief_override(btn.getAttribute('data-slot'))());
        } catch (err) {
            console.error(err);
            utils.showErrorFeedback('Could not switch brief and review.');
        }
    });
    root.addEventListener('submit', async (event) => {
        const form = event.target;
        if (!(form instanceof HTMLFormElement)) return;
        event.preventDefault();
        try {
            if (form.id === 'morningBriefForm') {
                const ids = selectedIds(root);
                const text = document.getElementById('morningIntention')?.value || '';
                paint(await eel.save_morning_brief(text, ids)());
                utils.notifyDataChanged();
                utils.showSuccessFeedback('Morning brief saved.');
            } else if (form.id === 'eveningReviewForm') {
                const text = document.getElementById('eveningRecap')?.value || '';
                paint(await eel.save_evening_review(text)());
                utils.notifyDataChanged();
                utils.showSuccessFeedback('Evening review saved.');
            }
        } catch (err) {
            console.error(err);
            utils.showErrorFeedback(err?.message || 'Could not save.');
        }
    });
    root.addEventListener('click', async (event) => {
        const btn = event.target.closest('[data-roll]');
        if (!btn) return;
        try {
            paint(await eel.roll_brief_item_to_tomorrow(btn.getAttribute('data-roll'))());
            utils.notifyDataChanged();
            utils.showSuccessFeedback('Moved to tomorrow.');
        } catch (err) {
            console.error(err);
            utils.showErrorFeedback('Could not move that to-do.');
        }
    });
    root.addEventListener('change', (event) => {
        const box = event.target.closest('[data-focus]');
        if (!box) return;
        const boxes = [...root.querySelectorAll('[data-focus]')];
        const checked = boxes.filter((el) => el.checked);
        if (checked.length <= 3) return;
        box.checked = false;
        utils.showErrorFeedback('Pick up to three focus tasks.');
    });
}
