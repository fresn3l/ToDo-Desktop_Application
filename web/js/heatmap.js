/**
 * Switchable year heatmap widget.
 */

import * as utils from './utils.js';
import { requestOpenTimelineDate } from './weekstrip.js';

function fillSelect(el, options, selected) {
    if (!el) return;
    el.innerHTML = (options || [])
        .map((row) => {
            const id = row.id || row;
            const label = row.label || row.title || id;
            const on = id === selected ? ' selected' : '';
            return `<option value="${utils.escapeHtml(id)}"${on}>${utils.escapeHtml(label)}</option>`;
        })
        .join('');
}

function paint(data) {
    const grid = document.getElementById('heatmapGrid');
    const summary = document.getElementById('heatmapSummary');
    const hint = document.getElementById('heatmapHint');
    const sourceSelect = document.getElementById('heatmapSourceSelect');
    const seriesSelect = document.getElementById('heatmapSeriesSelect');
    const filters = document.getElementById('heatmapJournalFilters');
    if (!grid) return;

    fillSelect(sourceSelect, data.sources || [], data.source);
    const series = data.series || [];
    fillSelect(
        seriesSelect,
        series.length ? series.map((row) => ({ id: row.id, label: `${row.title} · ${row.cadence_label}` })) : [{ id: '', label: 'No repeating to dos' }],
        data.series_id,
    );
    seriesSelect?.classList.toggle('is-hidden', data.source !== 'series');
    filters?.classList.toggle('is-hidden', data.source !== 'journal');
    filters?.querySelectorAll('[data-filter]').forEach((btn) => {
        btn.classList.toggle('is-selected', btn.getAttribute('data-filter') === (data.journal_filter || 'all'));
    });

    const streak = Number(data.streak || 0);
    if (summary) {
        const bits = [data.source_label || 'Heatmap'];
        if (data.source === 'series' && data.series_title) bits[0] = data.series_title;
        if (streak) bits.push(`${streak}-day streak`);
        summary.textContent = bits.join(' · ');
    }
    if (hint) {
        if (data.source === 'series' && !data.series_id) {
            hint.textContent = 'Pick a repeating to do to see done, miss, and skip days.';
        } else if (data.source === 'journal') {
            hint.textContent = 'Darker cells had more entries that day.';
        } else {
            hint.textContent = 'Click a day to open Timeline.';
        }
    }

    const days = data.days || [];
    if (!days.length) {
        grid.innerHTML = '';
        return;
    }
    const weeks = Math.ceil(days.length / 7);
    grid.style.setProperty('--heatmap-weeks', String(weeks));
    grid.innerHTML = days
        .map((day) => {
            const value = Number(day.value || 0);
            const max = Number(day.max || 1);
            const level = day.state === 'hit' ? Math.max(1, Math.min(4, Math.ceil((value / max) * 4))) : 0;
            const titleBits = [day.date, day.state === 'miss' ? 'miss' : day.state === 'skip' ? 'skipped' : day.state === 'pending' ? 'pending' : value ? `${value}` : 'none'];
            if (day.kinds && Object.keys(day.kinds).length) {
                titleBits.push(Object.entries(day.kinds).map(([k, v]) => `${k} ${v}`).join(', '));
            }
            return `<button type="button" class="heatmap-cell is-${utils.escapeHtml(day.state || 'none')} level-${level}" data-date="${utils.escapeHtml(day.date)}" title="${utils.escapeHtml(titleBits.join(' · '))}"></button>`;
        })
        .join('');
}

export async function refreshHeatmap() {
    const grid = document.getElementById('heatmapGrid');
    if (!grid || typeof eel === 'undefined' || !eel.get_heatmap) return;
    try {
        paint(await eel.get_heatmap()());
    } catch (err) {
        console.error(err);
        grid.innerHTML = '<p class="checklist-error">Could not load heatmap.</p>';
    }
}

async function persist(source, seriesId, journalFilter) {
    const data = await eel.save_heatmap_settings(source || '', seriesId || '', journalFilter || '')();
    paint(data);
}

export function setupHeatmap() {
    const sourceSelect = document.getElementById('heatmapSourceSelect');
    const seriesSelect = document.getElementById('heatmapSeriesSelect');
    const filters = document.getElementById('heatmapJournalFilters');
    const grid = document.getElementById('heatmapGrid');
    if (!sourceSelect || sourceSelect.dataset.ready === '1') return;
    sourceSelect.dataset.ready = '1';
    sourceSelect.addEventListener('change', () => {
        void persist(sourceSelect.value, seriesSelect?.value || '', document.querySelector('#heatmapJournalFilters .is-selected')?.getAttribute('data-filter') || 'all');
    });
    seriesSelect?.addEventListener('change', () => {
        void persist('series', seriesSelect.value, 'all');
    });
    filters?.addEventListener('click', (event) => {
        const btn = event.target.closest('[data-filter]');
        if (!btn) return;
        void persist('journal', '', btn.getAttribute('data-filter') || 'all');
    });
    grid?.addEventListener('click', (event) => {
        const cell = event.target.closest('[data-date]');
        if (!cell) return;
        requestOpenTimelineDate(cell.getAttribute('data-date'));
    });
}
