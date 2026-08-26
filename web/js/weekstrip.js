/**
 * Shared 7-day week strip for Review and Timeline.
 */

import * as utils from './utils.js';

function shiftIsoDate(iso, days) {
    const d = new Date(`${iso}T12:00:00`);
    d.setDate(d.getDate() + days);
    return utils.localISODate(d);
}

function formatStreaks(streaks) {
    if (!streaks) return '';
    const parts = [];
    const showUp = streaks.show_up || 0;
    const writing = streaks.writing || 0;
    const checkin = streaks.checkin || 0;
    if (showUp > 0) {
        parts.push(`${showUp}-day streak`);
    }
    if (writing > 0) {
        parts.push(`${writing} day${writing === 1 ? '' : 's'} writing`);
    }
    if (checkin > 0 && checkin !== showUp) {
        parts.push(`${checkin} day${checkin === 1 ? '' : 's'} check-in`);
    }
    return parts.length ? utils.escapeHtml(parts.join(' · ')) : 'No streak yet';
}

export function renderWeekStrip(el, data, { selectedDate, onSelect } = {}) {
    if (!el || !data) return;
    const selected = selectedDate || data.end_date;
    const today = utils.localISODate();
    const days = (data.days || [])
        .map((day) => {
            const filled = day.filled ? 'is-filled' : 'is-empty';
            const isSelected = day.date === selected ? 'is-selected' : '';
            const isToday = day.is_today || day.date === today ? 'is-today' : '';
            const titleParts = [];
            if (day.checklist_count) titleParts.push(`${day.checklist_count} checklist`);
            if (day.journal_count) titleParts.push(`${day.journal_count} journal`);
            if (day.work_count) titleParts.push(`${day.work_count} to do`);
            const title = titleParts.join(' · ') || 'No activity';
            return `
                <button type="button" class="week-day ${filled} ${isSelected} ${isToday}"
                    data-date="${utils.escapeHtml(day.date)}"
                    title="${utils.escapeHtml(day.date)} · ${utils.escapeHtml(title)}"
                    aria-pressed="${day.date === selected ? 'true' : 'false'}">
                    <span class="week-day-name">${utils.escapeHtml(day.weekday)}</span>
                    <span class="week-day-num">${day.day}</span>
                    <span class="week-day-dot" aria-hidden="true"></span>
                </button>
            `;
        })
        .join('');

    const canGoForward = data.end_date < today;
    const streakLine = formatStreaks(data.streaks);

    el.innerHTML = `
        <div class="week-strip-block">
            ${streakLine ? `<p class="week-streaks">${streakLine}</p>` : ''}
            <div class="week-strip">
            <button type="button" class="week-nav" data-shift="-7" aria-label="Previous week">‹</button>
            <div class="week-days" role="list">${days}</div>
            <button type="button" class="week-nav" data-shift="7" aria-label="Next week" ${canGoForward ? '' : 'disabled'}>›</button>
            </div>
        </div>
    `;

    el.querySelectorAll('.week-day').forEach((btn) => {
        btn.addEventListener('click', () => {
            const date = btn.getAttribute('data-date');
            if (date && onSelect) onSelect(date);
        });
    });
    el.querySelectorAll('.week-nav').forEach((btn) => {
        btn.addEventListener('click', async () => {
            if (btn.disabled) return;
            const shift = parseInt(btn.getAttribute('data-shift') || '0', 10);
            const nextEnd = shiftIsoDate(data.end_date, shift);
            await mountWeekStrip(el, { endDate: nextEnd, selectedDate, onSelect });
        });
    });
}

export async function mountWeekStrip(el, { endDate, selectedDate, onSelect } = {}) {
    if (!el) return;
    try {
        const data = await eel.get_week_overview(endDate || selectedDate || '')();
        renderWeekStrip(el, data, { selectedDate, onSelect });
    } catch (e) {
        console.error(e);
        el.innerHTML = '';
    }
}

export function requestOpenTimelineDate(localDate) {
    document.dispatchEvent(
        new CustomEvent('kosistenz:open-day', { detail: { date: localDate } }),
    );
}
