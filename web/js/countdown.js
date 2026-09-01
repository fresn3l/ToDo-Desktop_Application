/**
 * Countdown widget — pinned dates with days remaining.
 */

import * as utils from './utils.js';

function paint(data) {
    const list = document.getElementById('countdownList');
    const summary = document.getElementById('countdownSummary');
    if (!list) return;
    const items = data?.items || [];
    const nextUp = data?.next;
    if (summary) {
        summary.textContent = nextUp
            ? `${nextUp.title} · ${nextUp.label}`
            : 'Pin a trip, deadline, or birthday.';
    }
    if (!items.length) {
        list.innerHTML = '<li class="checklist-empty">No pinned dates yet.</li>';
        return;
    }
    list.innerHTML = items
        .map((item) => {
            const tone = item.is_today ? 'is-today' : item.is_past ? 'is-past' : '';
            return `
                <li class="countdown-item ${tone}" data-id="${utils.escapeHtml(item.id)}">
                    <div>
                        <strong>${utils.escapeHtml(item.title)}</strong>
                        <span class="countdown-days">${utils.escapeHtml(item.label)}</span>
                    </div>
                    <span class="countdown-date">${utils.escapeHtml(item.next_date)}${item.yearly ? ' · yearly' : ''}</span>
                    <button type="button" class="btn-ghost" data-remove="${utils.escapeHtml(item.id)}">Remove</button>
                </li>`;
        })
        .join('');
}

export async function refreshCountdowns() {
    const list = document.getElementById('countdownList');
    if (!list || typeof eel === 'undefined' || !eel.get_countdowns) return;
    try {
        paint(await eel.get_countdowns()());
    } catch (err) {
        console.error(err);
        list.innerHTML = '<li class="checklist-error">Could not load countdowns.</li>';
    }
}

export function setupCountdown() {
    const form = document.getElementById('countdownForm');
    if (!form || form.dataset.ready === '1') return;
    form.dataset.ready = '1';
    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const title = document.getElementById('countdownTitle');
        const dateEl = document.getElementById('countdownDate');
        const yearly = document.getElementById('countdownYearly');
        try {
            const data = await eel.add_countdown(
                title?.value.trim() || '',
                dateEl?.value || '',
                !!yearly?.checked,
            )();
            if (title) title.value = '';
            if (yearly) yearly.checked = false;
            paint(data);
            utils.notifyDataChanged();
            utils.showSuccessFeedback('Date pinned.');
        } catch (err) {
            console.error(err);
            utils.showErrorFeedback(err?.message || 'Could not pin that date.');
        }
    });
    document.getElementById('countdownList')?.addEventListener('click', async (event) => {
        const btn = event.target.closest('[data-remove]');
        if (!btn) return;
        try {
            paint(await eel.remove_countdown(btn.getAttribute('data-remove'))());
            utils.notifyDataChanged();
        } catch (err) {
            console.error(err);
            utils.showErrorFeedback('Could not remove that date.');
        }
    });
}
