/**
 * Purpose-built Home glances — small tiles that summarize a widget.
 * Full UI lives in the work layer, not in the cell.
 */

import * as utils from './utils.js';
import { WIDGET_CATALOG } from './home_layout.js';

function hasEel(name) {
    return typeof eel !== 'undefined' && typeof eel[name] === 'function';
}

async function eelCall(name, ...args) {
    if (!hasEel(name)) return null;
    try {
        return await eel[name](...args)();
    } catch (err) {
        console.error(err);
        return null;
    }
}

function clip(text, n) {
    const s = String(text || '').trim();
    if (!s) return '';
    if (s.length <= n) return s;
    return `${s.slice(0, Math.max(1, n - 1)).trim()}…`;
}

function sizeOf(card) {
    const w = Math.max(1, Number(card?.dataset.w) || 1);
    const h = Math.max(1, Number(card?.dataset.h) || 1);
    return { w, h, cells: w * h, wide: w >= 2, tall: h >= 2, board: w >= 4 || h >= 3, action: w >= 2 && h >= 2 };
}

export function dayPart(hour) {
    const h = Number.isFinite(Number(hour)) ? Number(hour) : new Date().getHours();
    if (h < 12) return 'morning';
    if (h < 17) return 'afternoon';
    return 'evening';
}

function weatherSky(data) {
    const t = String(data?.current?.label || data?.label || '').toLowerCase();
    if (t.includes('thunder')) return 'storm';
    if (t.includes('snow')) return 'snow';
    if (t.includes('rain') || t.includes('drizzle') || t.includes('shower')) return 'rain';
    if (t.includes('fog') || t.includes('haze')) return 'fog';
    if (t.includes('cloud') || t.includes('overcast')) return 'cloud';
    if (t.includes('clear') || t.includes('sun')) return 'clear';
    return data?.ok ? 'clear' : '';
}

function isComplete(kind, data) {
    if (kind === 'todo') {
        const items = data?.today || [];
        const open = data?.counts?.today_open ?? items.filter((row) => row.status !== 'done').length;
        const done = data?.counts?.today_done ?? items.filter((row) => row.status === 'done').length;
        return open === 0 && done > 0;
    }
    if (kind === 'habits') {
        const total = data?.total || 0;
        return total > 0 && data.done === total;
    }
    if (kind === 'workout') {
        return !!(data?.workout || data || {}).done;
    }
    if (kind === 'word') {
        return Boolean((data?.used_tonight || '').trim());
    }
    if (kind === 'focus') {
        return Boolean(data?.kept && (data?.text || '').trim());
    }
    if (kind === 'counters') {
        const rows = data?.counters || [];
        return rows.length > 0 && rows.every((row) => !row.target || row.met);
    }
    return false;
}

function applyAtmosphere(kind, data, card) {
    if (!card) return;
    card.classList.toggle('is-complete', isComplete(kind, data));
    const part = dayPart(data?.hour);
    if (kind === 'today_calendar' || kind === 'day_brief') {
        card.setAttribute('data-daypart', part);
    } else {
        card.removeAttribute('data-daypart');
    }
    if (kind === 'weather') {
        const sky = weatherSky(data);
        if (sky) card.setAttribute('data-sky', sky);
        else card.removeAttribute('data-sky');
    } else {
        card.removeAttribute('data-sky');
    }
}

export function syncHomeDayPart(hour) {
    const part = dayPart(hour);
    document.documentElement.setAttribute('data-daypart', part);
    document.getElementById('homeShell')?.setAttribute('data-daypart', part);
}

function tile(kind, size, extraClass, inner) {
    return `<div class="glance-tile glance-tile--${kind} glance-tile--${size.w}x${size.h}${extraClass ? ` ${extraClass}` : ''}" data-glance="${kind}">${inner}</div>`;
}

function kicker(text) {
    return `<p class="glance-kicker">${utils.escapeHtml(text)}</p>`;
}

function kpi(text, extra = '') {
    return `<p class="glance-kpi${extra}">${utils.escapeHtml(String(text))}</p>`;
}

function line(text, extra = '') {
    return `<p class="glance-line${extra}">${utils.escapeHtml(text)}</p>`;
}

function hint() {
    return '<span class="glance-open-hint">Open</span>';
}

function doneMark() {
    return '<span class="glance-complete" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m5 12 5 5 9-10"/></svg></span>';
}

function actionBtn(act, label, attrs = '') {
    return `<button type="button" class="glance-action" data-glance-act="${utils.escapeHtml(act)}"${attrs}>${utils.escapeHtml(label)}</button>`;
}

function emptyTile(kind, label, message, size) {
    return tile(kind, size, 'is-empty', `${kicker(label)}${line(message)}${size.wide ? hint() : ''}`);
}

function compactTile(kind, size, label, value, detail, complete) {
    const mark = complete ? doneMark() : '';
    const cls = complete ? 'is-complete' : '';
    if (!size.wide && !size.tall) {
        return tile(kind, size, cls, `${mark}${kicker(label)}${kpi(value)}${detail ? line(clip(detail, 14), ' glance-line--tiny') : ''}`);
    }
    return tile(kind, size, cls, `
        ${mark}
        ${kicker(label)}
        ${kpi(value)}
        ${detail ? line(detail) : ''}
        ${hint()}`);
}

function weatherGlyph(label) {
    const t = String(label || '').toLowerCase();
    let paths = '<circle cx="12" cy="12" r="4.2"/><path d="M12 3.5v2.2M12 18.3v2.2M3.5 12h2.2M18.3 12h2.2M5.6 5.6l1.6 1.6M16.8 16.8l1.6 1.6M5.6 18.4l1.6-1.6M16.8 7.2l1.6-1.6"/>';
    if (t.includes('thunder')) {
        paths = '<path d="M13 3 6.5 13h5L10 21l7.2-11h-5L13 3Z"/>';
    } else if (t.includes('snow')) {
        paths = '<path d="M12 4v16M5.4 7.5l13.2 9M5.4 16.5l13.2-9"/><circle cx="12" cy="12" r="1.4"/>';
    } else if (t.includes('rain') || t.includes('drizzle') || t.includes('shower')) {
        paths = '<path d="M7 11.5a5 5 0 0 1 9.7-1.6A3.6 3.6 0 0 1 18.2 16H7.6A3.2 3.2 0 0 1 7 11.5Z"/><path d="M9 18.2 8 21M12.5 18.2 11.5 21M16 18.2 15 21"/>';
    } else if (t.includes('fog') || t.includes('haze')) {
        paths = '<path d="M5 10h14M6 13h12M5 16h14"/>';
    } else if (t.includes('cloud') || t.includes('overcast')) {
        paths = '<path d="M7.2 16.5a4.2 4.2 0 0 1 .4-8.3 5.2 5.2 0 0 1 10 1.6 3.6 3.6 0 0 1 .2 6.7H7.2Z"/>';
    }
    return `<span class="glance-glyph" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">${paths}</svg></span>`;
}

function formatAgendaTime(item) {
    const start = new Date(item.start_at);
    if (Number.isNaN(start.getTime())) return '';
    return start.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
}

function taskDot(status) {
    const cls = status === 'done' ? 'is-done' : status === 'active' ? 'is-active' : 'is-open';
    return `<i class="glance-dot ${cls}" aria-hidden="true"></i>`;
}

function listRows(items, limit, render) {
    const rows = (items || []).slice(0, limit);
    if (!rows.length) return '';
    return `<ul class="glance-list">${rows.map(render).join('')}</ul>`;
}

function weatherHtml(data, size) {
    const label = 'Weather';
    if (!data || data.need_place) {
        return emptyTile('weather', label, 'Set a place', size);
    }
    if (!data.ok) {
        return emptyTile('weather', label, data.error ? 'Could not load' : 'No forecast yet', size);
    }
    const cur = data.current || {};
    const unit = data.unit_symbol || '°';
    const temp = cur.temp == null ? '—' : `${cur.temp}${unit}`;
    const cond = cur.label || '';
    const place = data.place || '';
    const glyph = weatherGlyph(cond);
    if (!size.wide && !size.tall) {
        return tile('weather', size, '', `${glyph}${kpi(temp)}${cond ? line(clip(cond, 14), ' glance-line--tiny') : ''}`);
    }
    if (!size.tall) {
        return tile('weather', size, '', `
            <div class="glance-row">
                ${glyph}
                <div class="glance-copy">
                    ${kicker(place || label)}
                    ${kpi(temp)}
                    ${line(cond)}
                </div>
            </div>`);
    }
    const days = (data.daily || []).slice(0, size.board ? 5 : 3);
    const forecast = days.length
        ? `<ul class="glance-forecast">${days.map((row) => {
            const high = row.high == null ? '—' : `${row.high}°`;
            const low = row.low == null ? '' : `${row.low}°`;
            return `<li><span>${utils.escapeHtml(row.day || '')}</span><em>${utils.escapeHtml(high)}${low ? ` <small>${utils.escapeHtml(low)}</small>` : ''}</em></li>`;
        }).join('')}</ul>`
        : '';
    return tile('weather', size, '', `
        ${kicker(place || label)}
        <div class="glance-row">
            ${glyph}
            ${kpi(temp)}
        </div>
        ${line(cond)}
        ${forecast}
        ${hint()}`);
}

function wordHtml(data, size) {
    const label = 'Word';
    if (!data?.word) {
        return emptyTile('word', label, 'No word yet', size);
    }
    const head = data.display || data.word;
    const pos = [data.language_label || (data.language === 'de' ? 'German' : 'English'), data.pos].filter(Boolean).join(' · ');
    const used = Boolean((data.used_tonight || '').trim());
    const mark = used ? doneMark() : '';
    const usedLine = used ? line('Used tonight', ' glance-line--muted') : '';
    if (!size.wide && !size.tall) {
        return tile('word', size, used ? 'is-complete' : '', `${mark}${kicker(label)}${kpi(clip(head, 12), ' glance-kpi--word')}`);
    }
    if (!size.tall) {
        return tile('word', size, used ? 'is-complete' : '', `${mark}${kicker(pos || label)}${kpi(clip(head, 22), ' glance-kpi--word')}${usedLine}${hint()}`);
    }
    return tile('word', size, used ? 'is-complete' : '', `
        ${mark}
        ${kicker(pos || label)}
        ${kpi(head, ' glance-kpi--word')}
        ${line(clip(data.meaning || '', size.board ? 140 : 90))}
        ${usedLine}
        ${hint()}`);
}

function todayHtml(data, size) {
    const label = 'Today';
    const iso = data?.local_date;
    const d = iso ? new Date(`${iso}T12:00:00`) : new Date();
    const weekday = Number.isNaN(d.getTime()) ? 'Today' : d.toLocaleDateString(undefined, { weekday: 'long' });
    const shortWeek = Number.isNaN(d.getTime()) ? 'Now' : d.toLocaleDateString(undefined, { weekday: 'short' });
    const dayNum = Number.isNaN(d.getTime()) ? '' : String(d.getDate());
    const month = Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString(undefined, { month: 'short' });
    const agenda = data?.agenda || [];
    const next = agenda[0];
    const nextLine = next
        ? `${formatAgendaTime(next)} ${next.title || ''}`.trim()
        : 'Nothing timed';
    const part = dayPart(data?.hour);
    if (!size.wide && !size.tall) {
        return tile('today_calendar', size, '', `${kicker(shortWeek)}${kpi(dayNum)}${line(month, ' glance-line--tiny')}`);
    }
    if (!size.tall) {
        return tile('today_calendar', size, '', `
            <div class="glance-copy">
                ${kicker(`${weekday} ${dayNum}`)}
                ${line(clip(nextLine, 42))}
            </div>
            ${hint()}`);
    }
    const work = data?.work || {};
    const pulse = work.open
        ? `${work.open} open`
        : work.total
            ? 'To do done'
            : '';
    const limit = size.board ? 5 : 4;
    const rows = listRows(agenda, limit, (item) => {
        const hh = formatAgendaTime(item);
        return `<li><span>${utils.escapeHtml(hh)}</span><strong>${utils.escapeHtml(clip(item.title || '', 28))}</strong></li>`;
    });
    const partLine = part === 'morning' ? 'Morning' : part === 'afternoon' ? 'Afternoon' : 'Evening';
    return tile('today_calendar', size, '', `
        ${kicker(`${label} · ${partLine}`)}
        ${kpi(`${shortWeek} ${dayNum}`)}
        ${line(pulse || (agenda.length ? `${agenda.length} on the clock` : 'Nothing timed yet'))}
        ${rows || `<p class="glance-empty">${utils.escapeHtml(nextLine)}</p>`}
        ${hint()}`);
}

function todoHtml(data, size) {
    const label = 'To Do';
    const items = data?.today || [];
    const open = data?.counts?.today_open ?? items.filter((row) => row.status !== 'done').length;
    const done = data?.counts?.today_done ?? items.filter((row) => row.status === 'done').length;
    const complete = open === 0 && done > 0;
    const mark = complete ? doneMark() : '';
    if (!size.tall) {
        return tile('todo', size, complete ? 'is-complete' : '', `
            ${mark}
            ${kicker(label)}
            <div class="glance-row">
                ${kpi(complete ? '✓' : open)}
                <div class="glance-copy">
                    ${line(complete ? 'All finished' : 'open today')}
                    ${done && !complete ? line(`${done} finished`, ' glance-line--muted') : ''}
                </div>
            </div>
            ${hint()}`);
    }
    const visible = items.filter((row) => row.status !== 'done' || size.board).slice(0, size.board ? 6 : 5);
    const rows = listRows(visible, visible.length, (item) => (
        `<li class="${item.status === 'done' ? 'is-done' : ''}">${taskDot(item.status)}<strong>${utils.escapeHtml(clip(item.title || '', 36))}</strong></li>`
    ));
    const sub = complete
        ? 'All finished'
        : open
            ? `${open} open${done ? ` · ${done} done` : ''}`
            : 'Nothing dated yet';
    const active = items.find((row) => row.status === 'active');
    const nextOpen = items.find((row) => row.status === 'open');
    let action = '';
    if (size.action && active) {
        action = actionBtn('todo-finish', 'Finish', ` data-id="${utils.escapeHtml(active.id)}"`);
    } else if (size.action && nextOpen) {
        action = actionBtn('todo-start', 'Start', ` data-id="${utils.escapeHtml(nextOpen.id)}"`);
    }
    return tile('todo', size, complete ? 'is-complete' : '', `
        ${mark}
        ${kicker(label)}
        ${kpi(complete ? 'Done' : open)}
        ${line(sub)}
        ${rows || '<p class="glance-empty">Nothing dated yet.</p>'}
        ${action}
        ${hint()}`);
}

function habitsHtml(data, size) {
    const label = 'Habits';
    const total = data?.total || 0;
    const done = data?.done || 0;
    const complete = total > 0 && done === total;
    const mark = complete ? doneMark() : '';
    if (!size.action) {
        if (!total) return emptyTile('habits', label, 'No habits yet.', size);
        return compactTile('habits', size, label, `${done}/${total}`, complete ? 'All ticked' : 'today', complete);
    }
    const next = (data?.habits || []).find((row) => !row.done);
    const action = next
        ? actionBtn('habit-tick', `Tick ${clip(next.title, 18)}`, ` data-id="${utils.escapeHtml(next.id)}"`)
        : '';
    const rows = listRows(data?.habits || [], size.board ? 6 : 4, (item) => (
        `<li class="${item.done ? 'is-done' : ''}">${taskDot(item.done ? 'done' : 'open')}<strong>${utils.escapeHtml(clip(item.title || '', 28))}</strong></li>`
    ));
    return tile('habits', size, complete ? 'is-complete' : '', `
        ${mark}
        ${kicker(label)}
        ${kpi(total ? `${done}/${total}` : '0')}
        ${line(complete ? 'All ticked' : total ? 'ticked today' : 'No habits yet.')}
        ${rows || '<p class="glance-empty">No habits yet.</p>'}
        ${action}
        ${hint()}`);
}

function countersHtml(data, size) {
    const label = 'Counters';
    const rows = data?.counters || [];
    const first = rows[0];
    const complete = rows.length > 0 && rows.every((row) => !row.target || row.met);
    if (!size.action) {
        if (!first) return emptyTile('counters', label, 'No counters yet.', size);
        return compactTile('counters', size, label, String(first.today || 0), first.name || '', complete);
    }
    const action = first
        ? actionBtn('counter-tap', `+1 ${clip(first.name, 16)}`, ` data-id="${utils.escapeHtml(first.id)}"`)
        : '';
    const list = listRows(rows, size.board ? 5 : 3, (item) => (
        `<li class="${item.met ? 'is-done' : ''}"><strong>${utils.escapeHtml(clip(item.name || '', 22))}</strong><span>${item.today || 0}${item.target ? `/${item.target}` : ''}</span></li>`
    ));
    return tile('counters', size, complete ? 'is-complete' : '', `
        ${complete ? doneMark() : ''}
        ${kicker(label)}
        ${kpi(first ? String(first.today || 0) : '·')}
        ${line(first ? clip(first.name, 28) : 'No counters yet.')}
        ${list}
        ${action}
        ${hint()}`);
}

function focusHtml(data, size) {
    const label = 'Focus';
    const text = (data?.text || '').trim();
    const kept = Boolean(data?.kept && text);
    if (!size.action) {
        if (!text) return emptyTile('focus', label, 'No focus yet.', size);
        return compactTile('focus', size, label, clip(text, size.wide ? 28 : 12), kept ? 'Kept' : '', kept);
    }
    const action = text && !kept
        ? actionBtn('focus-keep', 'Kept')
        : '';
    return tile('focus', size, kept ? 'is-complete' : '', `
        ${kept ? doneMark() : ''}
        ${kicker(label)}
        ${kpi(text ? clip(text, 42) : '·', ' glance-kpi--word')}
        ${line(kept ? 'Held for today' : text ? 'Today' : 'No focus yet.')}
        ${action}
        ${hint()}`);
}

function countdownHtml(data, size) {
    const label = 'Countdown';
    const rows = Array.isArray(data) ? data : [];
    const next = rows.find((row) => row.state !== 'past') || rows[0];
    if (!next) return emptyTile('countdown', label, 'No dates yet.', size);
    const days = Number(next.days);
    const count = next.state === 'today' ? '0' : (Number.isFinite(days) ? String(Math.abs(days)) : '—');
    const unit = next.state === 'today' ? 'today' : Number(next.days) < 0 ? 'ago' : 'days';
    if (!size.tall) {
        return compactTile('countdown', size, label, count, `${clip(next.title || '', 28)} · ${unit}`);
    }
    const list = listRows(rows, size.board ? 6 : 4, (item) => {
        const n = item.state === 'today' ? '0' : String(Math.abs(Number(item.days) || 0));
        return `<li><span>${utils.escapeHtml(n)}</span><strong>${utils.escapeHtml(clip(item.title || '', 28))}</strong></li>`;
    });
    return tile('countdown', size, '', `
        ${kicker(label)}
        ${kpi(count)}
        ${line(clip(next.title || '', 36))}
        ${list}
        ${hint()}`);
}

function readingHtml(data, size) {
    const label = 'Reading';
    if (!data?.title) return emptyTile('reading', label, 'No book yet.', size);
    const pages = data.pages_today ? String(data.pages_today) : String(data.page || '·');
    const detail = data.pages_today ? `${clip(data.title, 28)} · today` : clip(data.title, 36);
    if (!size.tall) {
        return compactTile('reading', size, label, pages, detail);
    }
    return tile('reading', size, '', `
        ${kicker(label)}
        ${kpi(pages)}
        ${line(clip(data.title, 48))}
        ${line(data.page ? `Page ${data.page}` : 'pages today', ' glance-line--muted')}
        ${hint()}`);
}

function workoutHtml(data, size) {
    const label = 'Workout';
    const workout = data?.workout || data || {};
    const session = workout.session_count || 0;
    const done = Boolean(workout.done);
    const expected = (data?.expected?.labels || []).join(' · ');
    if (done) {
        return compactTile('workout', size, label, '✓', session === 1 ? 'Session logged' : `${session} sessions`, true);
    }
    if (!size.tall) {
        return compactTile('workout', size, label, session || '·', expected || 'Nothing logged');
    }
    return tile('workout', size, '', `
        ${kicker(label)}
        ${kpi(session || '·')}
        ${line(expected || 'Nothing logged')}
        ${hint()}`);
}

function goalsHtml(data, size) {
    const label = 'Goals';
    const rows = Array.isArray(data) ? data : [];
    if (!rows.length) return emptyTile('goals', label, 'No goals yet.', size);
    const weekly = rows.find((row) => row.horizon === 'week');
    const sub = weekly?.title
        ? clip(weekly.title, 36)
        : rows.length === 1
            ? '1 in motion'
            : `${rows.length} in motion`;
    if (!size.tall) {
        return compactTile('goals', size, label, String(rows.length), sub);
    }
    const list = listRows(rows, size.board ? 5 : 4, (item) => (
        `<li><strong>${utils.escapeHtml(clip(item.title || '', 32))}</strong></li>`
    ));
    return tile('goals', size, '', `
        ${kicker(label)}
        ${kpi(String(rows.length))}
        ${line(sub)}
        ${list}
        ${hint()}`);
}

function allworkHtml(data, size) {
    const label = 'All Work';
    const rows = Array.isArray(data) ? data : [];
    if (!rows.length) return emptyTile('allwork', label, 'Backlog is clear.', size);
    const sub = rows.length === 1 ? clip(rows[0].title || '', 36) : `${rows.length} waiting`;
    if (!size.tall) {
        return compactTile('allwork', size, label, String(rows.length), sub);
    }
    const list = listRows(rows, size.board ? 6 : 4, (item) => (
        `<li><strong>${utils.escapeHtml(clip(item.title || '', 36))}</strong></li>`
    ));
    return tile('allwork', size, '', `
        ${kicker(label)}
        ${kpi(String(rows.length))}
        ${line(sub)}
        ${list}
        ${hint()}`);
}

function heatmapHtml(data, size) {
    const label = 'Heatmap';
    if (!data) return emptyTile('heatmap', label, 'No activity yet.', size);
    const streak = Number(data.streak || 0);
    const source = data.series_title || data.source_label || label;
    const days = data.days || [];
    const recent = days.slice(-14);
    const strip = (size.tall || size.board) && recent.length
        ? `<div class="glance-heat" aria-hidden="true">${recent.map((day) => {
            const hit = day.state === 'hit' || Number(day.value || 0) > 0;
            const level = Math.max(0, Math.min(4, Number(day.level) || (hit ? 2 : 0)));
            return `<i class="is-${utils.escapeHtml(day.state || 'none')} level-${level}"></i>`;
        }).join('')}</div>`
        : '';
    if (!size.tall && !size.board) {
        return compactTile('heatmap', size, source, streak ? String(streak) : '0', streak ? 'day streak' : 'No streak');
    }
    return tile('heatmap', size, '', `
        ${kicker(source)}
        ${kpi(streak ? String(streak) : '0')}
        ${line(streak ? 'day streak' : 'No streak')}
        ${strip}
        ${hint()}`);
}

function dayBriefHtml(data, size) {
    const evening = data?.slot === 'evening';
    const slot = evening ? 'Evening' : 'Morning';
    const leftover = data?.review?.leftover?.length || 0;
    const next = (data?.agenda || [])[0];
    const nextLine = next
        ? `${formatAgendaTime(next)} ${next.title || ''}`.trim()
        : '';
    if (evening) {
        const detail = leftover ? `${leftover} leftover` : 'Review';
        if (!size.tall) return compactTile('day_brief', size, slot, leftover ? String(leftover) : '✓', detail);
        return tile('day_brief', size, leftover ? '' : 'is-complete', `
            ${kicker(slot)}
            ${kpi(leftover ? String(leftover) : 'Done')}
            ${line(detail)}
            ${hint()}`);
    }
    if (!size.tall) {
        return compactTile('day_brief', size, slot, next ? formatAgendaTime(next) || '·' : '·', nextLine || 'No events yet');
    }
    return tile('day_brief', size, '', `
        ${kicker(slot)}
        ${kpi(next ? formatAgendaTime(next) || 'Brief' : 'Brief')}
        ${line(nextLine || 'No events yet')}
        ${hint()}`);
}

function analyticsHtml(data, size) {
    const label = 'Analytics';
    if (!data) return emptyTile('analytics', label, 'No streak yet.', size);
    const streak = Number(data.journal?.streak || 0);
    const missed = (data.work?.series || []).reduce((n, row) => n + Number(row.missed || 0), 0);
    const written = Number(data.journal?.days_written || 0);
    const detail = missed ? `${missed} misses` : `${written} days written`;
    return compactTile('analytics', size, label, String(streak), detail);
}

function timelineHtml(data, size) {
    const label = 'Timeline';
    if (!data) return emptyTile('timeline', label, 'Nothing logged.', size);
    const n = Number(data.journal_count || 0)
        + Number(data.work_count || 0)
        + Number(data.workout_count || 0)
        + Number(data.submission_count || 0);
    const iso = data.local_date || utils.localISODate();
    const d = new Date(`${iso}T12:00:00`);
    const when = Number.isNaN(d.getTime())
        ? 'Today'
        : d.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
    return compactTile('timeline', size, label, String(n), when);
}

function clunyHtml(_data, size) {
    return compactTile('cluny', size, 'Cluny', '?', 'Open to ask');
}

function posterHtml(kind, _data, size) {
    const spec = WIDGET_CATALOG[kind] || { label: kind };
    return emptyTile(kind, spec.label, 'Could not load.', size);
}

async function loadGlance(kind) {
    if (kind === 'weather') return eelCall('get_weather_forecast', false);
    if (kind === 'word') return eelCall('get_word_of_the_day');
    if (kind === 'today_calendar') return eelCall('get_today_home');
    if (kind === 'todo') return eelCall('get_work_board', utils.localISODate());
    if (kind === 'focus') return eelCall('get_daily_focus');
    if (kind === 'countdown') return eelCall('get_countdowns');
    if (kind === 'habits') return eelCall('get_habits');
    if (kind === 'reading') return eelCall('get_reading');
    if (kind === 'counters') return eelCall('get_tap_counters');
    if (kind === 'workout') return eelCall('get_today_status');
    if (kind === 'goals') return eelCall('list_goals');
    if (kind === 'allwork') return eelCall('list_backlog');
    if (kind === 'day_brief') return eelCall('get_day_brief');
    if (kind === 'heatmap') return eelCall('get_heatmap');
    if (kind === 'analytics') return eelCall('get_analytics', 7);
    if (kind === 'timeline') return eelCall('get_timeline_day', utils.localISODate());
    return null;
}

function renderKind(kind, data, size) {
    if (kind === 'weather') return weatherHtml(data, size);
    if (kind === 'word') return wordHtml(data, size);
    if (kind === 'today_calendar') return todayHtml(data, size);
    if (kind === 'todo') return todoHtml(data, size);
    if (kind === 'habits') return habitsHtml(data, size);
    if (kind === 'counters') return countersHtml(data, size);
    if (kind === 'focus') return focusHtml(data, size);
    if (kind === 'countdown') return countdownHtml(data, size);
    if (kind === 'reading') return readingHtml(data, size);
    if (kind === 'workout') return workoutHtml(data, size);
    if (kind === 'goals') return goalsHtml(data, size);
    if (kind === 'allwork') return allworkHtml(data, size);
    if (kind === 'heatmap') return heatmapHtml(data, size);
    if (kind === 'day_brief') return dayBriefHtml(data, size);
    if (kind === 'analytics') return analyticsHtml(data, size);
    if (kind === 'timeline') return timelineHtml(data, size);
    if (kind === 'cluny') return clunyHtml(data, size);
    return posterHtml(kind, data, size);
}

export function mountGlance(kind, body, card) {
    const spec = WIDGET_CATALOG[kind] || { label: kind };
    if (!body) return;
    const size = sizeOf(card);
    body.innerHTML = emptyTile(kind, spec.label, '…', size);
}

export async function paintGlance(kind, body, card) {
    if (!body) return;
    const size = sizeOf(card);
    const data = await loadGlance(kind);
    if (!body.isConnected) return;
    applyAtmosphere(kind, data, card);
    body.innerHTML = renderKind(kind, data, size);
}

export async function refreshGlances(kinds) {
    const set = kinds ? new Set(kinds) : null;
    const cards = [...document.querySelectorAll('#homeGridAbove .home-widget, #homeGrid .home-widget')];
    await Promise.all(cards.map(async (card) => {
        const kind = card.getAttribute('data-kind');
        if (set && !set.has(kind)) return;
        const body = card.querySelector('.home-widget-body');
        if (body) await paintGlance(kind, body, card);
    }));
}

export async function runGlanceAction(btn) {
    const act = btn?.getAttribute('data-glance-act');
    const id = btn?.getAttribute('data-id') || '';
    if (!act) return;
    try {
        if (act === 'todo-finish' && hasEel('finish_work_item')) {
            await eel.finish_work_item(id)();
        } else if (act === 'todo-start' && hasEel('start_work_item')) {
            await eel.start_work_item(id)();
        } else if (act === 'habit-tick' && hasEel('toggle_home_habit')) {
            await eel.toggle_home_habit(id)();
        } else if (act === 'counter-tap' && hasEel('tap_counter')) {
            await eel.tap_counter(id, 1)();
        } else if (act === 'focus-keep' && hasEel('keep_daily_focus')) {
            await eel.keep_daily_focus(true)();
        } else {
            return;
        }
        utils.notifyDataChanged();
    } catch (err) {
        console.error(err);
        utils.showErrorFeedback(err?.message || 'Could not update that.');
    }
}
