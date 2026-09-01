/**
 * Generic tap counters — name, icon, optional daily target.
 */

import * as utils from './utils.js';

function paint(data) {
    const list = document.getElementById('countersList');
    const summary = document.getElementById('countersSummary');
    const iconSelect = document.getElementById('counterIcon');
    if (!list) return;
    const counters = data?.counters || [];
    if (summary) {
        summary.textContent = counters.length
            ? 'Tap to log. Minus undoes. Target is optional.'
            : 'Name it, pick an icon, optional daily target.';
    }
    if (iconSelect && !(iconSelect.options && iconSelect.options.length)) {
        iconSelect.innerHTML = (data.icons || []).map((icon) => `<option value="${utils.escapeHtml(icon)}">${icon}</option>`).join('');
    }
    if (!counters.length) {
        list.innerHTML = '<p class="checklist-empty">No counters yet. Water, caffeine, cigarettes — whatever you want to count.</p>';
        return;
    }
    list.innerHTML = counters
        .map((row) => {
            const target = row.target ? ` / ${row.target}` : '';
            const met = row.met ? ' is-met' : '';
            return `
                <article class="counter-card${met}" data-id="${utils.escapeHtml(row.id)}">
                    <button type="button" class="counter-tap" data-tap="${utils.escapeHtml(row.id)}" aria-label="Add one ${utils.escapeHtml(row.name)}">
                        <span class="counter-icon">${utils.escapeHtml(row.icon || '⭐')}</span>
                        <strong>${utils.escapeHtml(row.name)}</strong>
                        <span class="counter-count">${row.today || 0}${target}</span>
                    </button>
                    <div class="counter-actions">
                        <button type="button" class="btn-ghost" data-delta="${utils.escapeHtml(row.id)}" data-step="-1" aria-label="Subtract one">−</button>
                        <button type="button" class="btn-ghost" data-remove="${utils.escapeHtml(row.id)}">Remove</button>
                    </div>
                </article>`;
        })
        .join('');
}

export async function refreshCounters() {
    const list = document.getElementById('countersList');
    if (!list || typeof eel === 'undefined' || !eel.get_tap_counters) return;
    try {
        paint(await eel.get_tap_counters()());
    } catch (err) {
        console.error(err);
        list.innerHTML = '<p class="checklist-error">Could not load counters.</p>';
    }
}

export function setupCounters() {
    const form = document.getElementById('countersForm');
    const list = document.getElementById('countersList');
    if (!form || form.dataset.ready === '1') return;
    form.dataset.ready = '1';
    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const name = document.getElementById('counterName');
        const icon = document.getElementById('counterIcon');
        const target = document.getElementById('counterTarget');
        try {
            paint(await eel.add_tap_counter(name?.value.trim() || '', icon?.value || '', target?.value || '')());
            if (name) name.value = '';
            if (target) target.value = '';
            utils.notifyDataChanged();
        } catch (err) {
            console.error(err);
            utils.showErrorFeedback(err?.message || 'Could not add that counter.');
        }
    });
    list?.addEventListener('click', async (event) => {
        const remove = event.target.closest('[data-remove]');
        const delta = event.target.closest('[data-delta]');
        const tap = event.target.closest('[data-tap]');
        try {
            if (remove) {
                paint(await eel.remove_tap_counter(remove.getAttribute('data-remove'))());
            } else if (delta) {
                paint(await eel.tap_counter(delta.getAttribute('data-delta'), parseInt(delta.getAttribute('data-step') || '-1', 10))());
            } else if (tap) {
                paint(await eel.tap_counter(tap.getAttribute('data-tap'), 1)());
            } else {
                return;
            }
            utils.notifyDataChanged();
        } catch (err) {
            console.error(err);
            utils.showErrorFeedback('Could not update that counter.');
        }
    });
}
