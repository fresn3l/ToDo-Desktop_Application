/**
 * Home glances — one shell, filled states, no poster slogans.
 * Full UI lives in the work layer. Inline actions stay on the tile.
 */

import * as utils from './utils.js';
import { WIDGET_CATALOG } from './home_layout.js';
import { copy, eventsToday, moreCount, countLabel } from './glance_copy.js';

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
    return { w, h, cells: w * h, wide: w >= 2, tall: h >= 2, board: w >= 3 || h >= 3, action: w >= 2 && h >= 2 };
}

export function dayPart(hour) {
    const h = Number.isFinite(Number(hour)) ? Number(hour) : new Date().getHours();
    if (h < 12) return 'morning';
    if (h < 17) return 'afternoon';
    return 'evening';
}

export function syncHomeDayPart(hour) {
    const part = dayPart(hour);
    document.documentElement.setAttribute('data-daypart', part);
}

function tile(kind, size, extraClass, inner) {
    return `<div class="glance-tile glance-tile--${kind} glance-tile--${size.w}x${size.h}${extraClass ? ` ${extraClass}` : ''}" data-glance="${kind}">${inner}</div>`;
}

function actionBtn(act, label, attrs = '') {
    return `<button type="button" class="glance-action" data-glance-act="${utils.escapeHtml(act)}"${attrs}>${utils.escapeHtml(label)}</button>`;
}

function openWorkAction(kind, label = copy.open) {
    return { act: 'open-work', label, attrs: ` data-kind="${utils.escapeHtml(kind)}"` };
}

function shellHtml({ kind, size, state = 'ready', label, primary = '', body = '', action = null, hero = false }) {
    const stateCls = state !== 'ready' ? ` is-${state}` : '';
    const labelHtml = `<p class="glance-label">${utils.escapeHtml(label)}</p>`;
    if (state === 'empty' || state === 'error' || state === 'loading') {
        const act = action ? actionBtn(action.act, action.label, action.attrs || '') : '';
        return tile(kind, size, stateCls, `
            ${labelHtml}
            <p class="glance-message">${utils.escapeHtml(primary || copy.couldNotLoad)}</p>
            ${act}`);
    }
    const primaryHtml = primary
        ? `<p class="glance-primary${hero ? ' glance-primary--hero' : ''}">${utils.escapeHtml(String(primary))}</p>`
        : '';
    const act = action ? actionBtn(action.act, action.label, action.attrs || '') : '';
    return tile(kind, size, stateCls, `
        ${labelHtml}
        ${primaryHtml}
        ${body || ''}
        ${act}`);
}

function emptyShell(kind, size, message, action) {
    return shellHtml({
        kind,
        size,
        state: 'empty',
        label: (WIDGET_CATALOG[kind] || { label: kind }).label,
        primary: message,
        action: action || openWorkAction(kind),
    });
}

function listRows(items, limit, render) {
    const rows = (items || []).slice(0, limit);
    if (!rows.length) return '';
    return `<ul class="glance-list">${rows.map(render).join('')}</ul>`;
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

function formatHourly(iso) {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return '';
    return d.toLocaleTimeString(undefined, { hour: 'numeric' });
}

function taskDot(status) {
    const cls = status === 'done' ? 'is-done' : status === 'active' ? 'is-active' : 'is-open';
    return `<i class="glance-dot ${cls}" aria-hidden="true"></i>`;
}

function formatShortDate(iso) {
    if (!iso) return '';
    const d = new Date(`${String(iso).slice(0, 10)}T12:00:00`);
    if (Number.isNaN(d.getTime())) return String(iso).slice(0, 10);
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function weatherHtml(data, size) {
    const kind = 'weather';
    const label = 'Weather';
    if (!data || data.need_place) {
        return emptyShell(kind, size, copy.setPlace, { act: 'open-work', label: copy.setPlace, attrs: ' data-kind="weather"' });
    }
    if (!data.ok) {
        return emptyShell(kind, size, data.error ? copy.couldNotLoad : copy.noForecast);
    }
    const cur = data.current || {};
    const unit = data.unit_symbol || '°';
    const temp = cur.temp == null ? '—' : `${cur.temp}${unit}`;
    const cond = cur.label || '';
    const glyph = weatherGlyph(cond);
    const day = (data.daily || [])[0] || {};
    const high = day.high == null ? '' : `${day.high}${unit}`;
    const low = day.low == null ? '' : `${day.low}${unit}`;
    const hilow = high && low ? `${high} / ${low}` : high || low;
    if (!size.wide && !size.tall) {
        return shellHtml({
            kind,
            size,
            label,
            primary: temp,
            hero: true,
            body: `${glyph}${cond ? `<p class="glance-message">${utils.escapeHtml(clip(cond, 14))}</p>` : ''}`,
        });
    }
    const hours = (data.hourly || []).slice(0, 4);
    const hourly = hours.length
        ? `<ul class="glance-hourly">${hours.map((row) => {
            const t = row.hour || formatHourly(row.at || row.time);
            const val = row.temp == null ? '—' : `${row.temp}°`;
            return `<li><span>${utils.escapeHtml(t)}</span><strong>${utils.escapeHtml(val)}</strong></li>`;
        }).join('')}</ul>`
        : '';
    return shellHtml({
        kind,
        size,
        label,
        primary: temp,
        hero: true,
        body: `
            <div class="glance-row">
                ${glyph}
                <p class="glance-message">${utils.escapeHtml(cond)}${hilow ? ` · ${utils.escapeHtml(hilow)}` : ''}</p>
            </div>
            ${hourly}`,
    });
}

function wordHtml(data, size) {
    const kind = 'word';
    const label = 'Word';
    if (!data?.word) return emptyShell(kind, size, copy.noWord);
    const head = data.display || data.word;
    const pos = [data.language_label || (data.language === 'de' ? 'German' : 'English'), data.pos].filter(Boolean).join(' · ');
    const meaning = clip(data.meaning || '', size.board ? 140 : size.tall ? 90 : 42);
    const example = clip(data.example || '', size.board ? 120 : 72);
    const used = Boolean((data.used_tonight || '').trim());
    if (!size.wide && !size.tall) {
        return shellHtml({ kind, size, label, primary: clip(head, 12), hero: true });
    }
    const parts = [
        pos ? `<p class="glance-message">${utils.escapeHtml(pos)}</p>` : '',
        meaning ? `<p class="glance-message">${utils.escapeHtml(meaning)}</p>` : '',
        example && size.tall ? `<p class="glance-message glance-message--quiet">${utils.escapeHtml(example)}</p>` : '',
        used ? `<p class="glance-message glance-message--quiet">${utils.escapeHtml(copy.usedTonight)}</p>` : '',
    ].join('');
    return shellHtml({ kind, size, label, primary: head, hero: true, body: parts });
}

function todayHtml(data, size) {
    const kind = 'today_calendar';
    const label = 'Today';
    const iso = data?.local_date;
    const d = iso ? new Date(`${iso}T12:00:00`) : new Date();
    const shortWeek = Number.isNaN(d.getTime()) ? 'Now' : d.toLocaleDateString(undefined, { weekday: 'short' });
    const dayNum = Number.isNaN(d.getTime()) ? '' : String(d.getDate());
    const month = Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString(undefined, { month: 'short' });
    const agenda = data?.agenda || [];
    if (!size.wide && !size.tall) {
        return shellHtml({ kind, size, label, primary: dayNum, hero: true, body: `<p class="glance-message">${utils.escapeHtml(shortWeek)}</p>` });
    }
    if (!size.tall) {
        const next = agenda[0];
        const line = next ? `${formatAgendaTime(next)} ${clip(next.title || '', 28)}`.trim() : copy.noEvents;
        return shellHtml({
            kind,
            size,
            label,
            primary: `${shortWeek} ${dayNum}`,
            hero: true,
            body: `<p class="glance-message">${utils.escapeHtml(line)}</p>`,
        });
    }
    const limit = 4;
    const extra = Math.max(0, agenda.length - limit);
    const rows = listRows(agenda, limit, (item) => {
        const hh = formatAgendaTime(item);
        return `<li><span>${utils.escapeHtml(hh)}</span><strong>${utils.escapeHtml(clip(item.title || '', 32))}</strong></li>`;
    });
    const more = extra ? `<p class="glance-message glance-message--quiet">${utils.escapeHtml(moreCount(extra))}</p>` : '';
    return shellHtml({
        kind,
        size,
        label,
        primary: `${shortWeek} ${dayNum}`,
        hero: true,
        body: `
            <p class="glance-message">${utils.escapeHtml(eventsToday(agenda.length))}</p>
            ${rows || ''}
            ${more}`,
    });
}

function todoHtml(data, size) {
    const kind = 'todo';
    const label = 'To Do';
    const items = data?.today || [];
    const open = data?.counts?.today_open ?? items.filter((row) => row.status !== 'done').length;
    const done = data?.counts?.today_done ?? items.filter((row) => row.status === 'done').length;
    const complete = open === 0 && done > 0;
    if (!items.length && !open && !done) {
        return emptyShell(kind, size, copy.nothingDated, { act: 'open-work', label: copy.addPlace, attrs: ' data-kind="todo"' });
    }
    const visible = items.filter((row) => row.status !== 'done' || size.board).slice(0, size.tall ? 5 : 2);
    const rows = listRows(visible, visible.length, (item) => (
        `<li class="${item.status === 'done' ? 'is-done' : ''}">${taskDot(item.status)}<strong>${utils.escapeHtml(clip(item.title || '', 36))}</strong></li>`
    ));
    const active = items.find((row) => row.status === 'active');
    const nextOpen = items.find((row) => row.status === 'open');
    let action = null;
    if (size.action && active) {
        action = { act: 'todo-finish', label: copy.finish, attrs: ` data-id="${utils.escapeHtml(active.id)}"` };
    } else if (size.action && nextOpen) {
        action = { act: 'todo-start', label: copy.start, attrs: ` data-id="${utils.escapeHtml(nextOpen.id)}"` };
    }
    const message = complete ? copy.allFinished : open ? '' : copy.nothingDated;
    return shellHtml({
        kind,
        size,
        label: countLabel(label, open || done ? open : ''),
        primary: size.tall ? '' : String(complete ? done : open),
        hero: false,
        body: `${message ? `<p class="glance-message glance-message--quiet">${utils.escapeHtml(message)}</p>` : ''}${rows || ''}`,
        action,
    });
}

function habitsHtml(data, size) {
    const kind = 'habits';
    const label = 'Habits';
    const total = data?.total || 0;
    const done = data?.done || 0;
    if (!total) return emptyShell(kind, size, copy.noHabits);
    const next = (data?.habits || []).find((row) => !row.done);
    const rows = size.tall
        ? listRows(data?.habits || [], size.board ? 6 : 4, (item) => (
            `<li class="${item.done ? 'is-done' : ''}">${taskDot(item.done ? 'done' : 'open')}<strong>${utils.escapeHtml(clip(item.title || '', 28))}</strong></li>`
        ))
        : '';
    const action = size.action && next
        ? { act: 'habit-tick', label: `${copy.tick} ${clip(next.title, 16)}`, attrs: ` data-id="${utils.escapeHtml(next.id)}"` }
        : null;
    const quiet = done === total ? 'All ticked.' : '';
    return shellHtml({
        kind,
        size,
        label: countLabel(label, `${done}/${total}`),
        primary: size.tall ? '' : `${done}/${total}`,
        body: `${quiet ? `<p class="glance-message glance-message--quiet">${quiet}</p>` : ''}${rows}`,
        action,
    });
}

function countersHtml(data, size) {
    const kind = 'counters';
    const label = 'Counters';
    const rows = data?.counters || [];
    const first = rows[0];
    if (!first) return emptyShell(kind, size, copy.noCounters);
    if (!size.wide && !size.tall) {
        return shellHtml({
            kind,
            size,
            label: clip(first.name || label, 16),
            primary: String(first.today || 0),
            action: { act: 'counter-tap', label: '+', attrs: ` data-id="${utils.escapeHtml(first.id)}" data-step="1"` },
        });
    }
    const chips = (size.tall ? rows.slice(0, 6) : rows.slice(0, 2)).map((item) => `
        <div class="glance-counter">
            <span class="glance-counter-name">${utils.escapeHtml(clip(item.name || '', 18))}</span>
            <span class="glance-counter-value">${item.today || 0}${item.target ? `/${item.target}` : ''}</span>
            <button type="button" class="glance-action glance-action--icon" data-glance-act="counter-tap" data-id="${utils.escapeHtml(item.id)}" data-step="-1" aria-label="Minus">−</button>
            <button type="button" class="glance-action glance-action--icon" data-glance-act="counter-tap" data-id="${utils.escapeHtml(item.id)}" data-step="1" aria-label="Plus">+</button>
        </div>`).join('');
    return shellHtml({
        kind,
        size,
        label: countLabel(label, rows.length),
        body: `<div class="glance-counters">${chips}</div>`,
    });
}

function focusHtml(data, size) {
    const kind = 'focus';
    const label = 'Focus';
    const text = (data?.text || '').trim();
    const kept = Boolean(data?.kept && text);
    if (!text) return emptyShell(kind, size, copy.noFocus);
    const action = size.action && text && !kept
        ? { act: 'focus-keep', label: copy.kept }
        : null;
    return shellHtml({
        kind,
        size,
        label,
        primary: clip(text, size.wide ? 42 : 14),
        body: kept ? `<p class="glance-message glance-message--quiet">${utils.escapeHtml(copy.heldToday)}</p>` : '',
        action,
    });
}

function countdownHtml(data, size) {
    const kind = 'countdown';
    const label = 'Countdown';
    const rows = Array.isArray(data) ? data : [];
    const next = rows.find((row) => row.state !== 'past') || rows[0];
    if (!next) return emptyShell(kind, size, copy.noDates);
    const days = Number(next.days);
    const count = next.state === 'today' ? '0' : (Number.isFinite(days) ? String(Math.abs(days)) : '—');
    const unit = next.state === 'today' ? 'today' : Number(next.days) < 0 ? 'ago' : 'days';
    const list = size.tall
        ? listRows(rows, size.board ? 6 : 4, (item) => {
            const n = item.state === 'today' ? '0' : String(Math.abs(Number(item.days) || 0));
            return `<li><span>${utils.escapeHtml(n)}</span><strong>${utils.escapeHtml(clip(item.title || '', 28))}</strong></li>`;
        })
        : '';
    return shellHtml({
        kind,
        size,
        label,
        primary: count,
        body: `<p class="glance-message">${utils.escapeHtml(clip(next.title || '', 36))} · ${unit}</p>${list}`,
    });
}

function readingHtml(data, size) {
    const kind = 'reading';
    const label = 'Reading';
    if (!data?.title) return emptyShell(kind, size, copy.noBook);
    const pages = data.pages_today ? String(data.pages_today) : String(data.page || '·');
    return shellHtml({
        kind,
        size,
        label,
        primary: pages,
        body: `<p class="glance-message">${utils.escapeHtml(clip(data.title, 48))}</p>
            <p class="glance-message glance-message--quiet">${utils.escapeHtml(data.page ? `Page ${data.page}` : 'pages today')}</p>`,
    });
}

function workoutHtml(data, size) {
    const kind = 'workout';
    const label = 'Workout';
    const workout = data?.workout || data || {};
    const split = (data?.expected?.labels || []).join(' · ');
    const last = workout.last_session || data?.last_session;
    const latest = (workout.sessions || [])[(workout.sessions || []).length - 1];
    const session = latest || last;
    if (!split && !session && !workout.session_count) {
        return emptyShell(kind, size, copy.nothingLogged);
    }
    const lastDate = formatShortDate(last?.local_date || (workout.done ? data?.local_date : ''));
    const sessionLine = session
        ? [session.label || session.kind_label, session.miles ? `${session.miles} mi` : '', session.minutes ? `${session.minutes} min` : '']
            .filter(Boolean)
            .join(' · ')
        : '';
    const bits = [
        split ? `<p class="glance-message">${utils.escapeHtml(split)}</p>` : '',
        lastDate ? `<p class="glance-message glance-message--quiet">${utils.escapeHtml(lastDate)}</p>` : '',
        sessionLine ? `<p class="glance-message">${utils.escapeHtml(sessionLine)}</p>` : '',
    ].join('');
    return shellHtml({
        kind,
        size,
        label,
        primary: workout.session_count ? String(workout.session_count) : '',
        body: bits || `<p class="glance-message">${utils.escapeHtml(copy.nothingLogged)}</p>`,
    });
}

function goalsHtml(data, size) {
    const kind = 'goals';
    const label = 'Goals';
    const rows = Array.isArray(data) ? data : [];
    if (!rows.length) return emptyShell(kind, size, copy.noGoals);
    const weekly = rows.find((row) => row.horizon === 'week');
    const list = size.tall
        ? listRows(rows, size.board ? 5 : 4, (item) => `<li><strong>${utils.escapeHtml(clip(item.title || '', 32))}</strong></li>`)
        : '';
    return shellHtml({
        kind,
        size,
        label: countLabel(label, rows.length),
        primary: size.tall ? '' : String(rows.length),
        body: `${weekly ? `<p class="glance-message">${utils.escapeHtml(clip(weekly.title, 36))}</p>` : ''}${list}`,
    });
}

function allworkHtml(data, size) {
    const kind = 'allwork';
    const label = 'All Work';
    const rows = Array.isArray(data) ? data : [];
    if (!rows.length) {
        return emptyShell(kind, size, copy.backlogClear, { act: 'open-work', label: copy.add, attrs: ' data-kind="allwork"' });
    }
    const limit = size.tall ? 5 : 2;
    const extra = Math.max(0, rows.length - limit);
    const list = listRows(rows, limit, (item) => (
        `<li><strong>${utils.escapeHtml(clip(item.title || '', 36))}</strong></li>`
    ));
    const more = extra ? `<p class="glance-message glance-message--quiet">${utils.escapeHtml(moreCount(extra))}</p>` : '';
    return shellHtml({
        kind,
        size,
        label: countLabel(label, rows.length),
        body: `${list}${more}`,
        action: size.action ? openWorkAction(kind, copy.open) : null,
    });
}

function heatmapHtml(data, size) {
    const kind = 'heatmap';
    const label = 'Heatmap';
    if (!data) return emptyShell(kind, size, copy.noActivity);
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
    return shellHtml({
        kind,
        size,
        label: source,
        primary: String(streak),
        body: `<p class="glance-message glance-message--quiet">${streak ? 'day streak' : copy.noStreak}</p>${strip}`,
    });
}

function dayBriefHtml(data, size) {
    const kind = 'day_brief';
    const evening = data?.slot === 'evening';
    const label = evening ? 'Evening' : 'Morning';
    const leftover = data?.review?.leftover?.length || 0;
    const next = (data?.agenda || [])[0];
    const nextLine = next ? `${formatAgendaTime(next)} ${next.title || ''}`.trim() : copy.noEvents;
    if (evening) {
        return shellHtml({
            kind,
            size,
            label,
            primary: leftover ? String(leftover) : '',
            body: `<p class="glance-message">${leftover ? `${leftover} leftover` : 'Review saved.'}</p>`,
        });
    }
    return shellHtml({
        kind,
        size,
        label,
        primary: next ? formatAgendaTime(next) : '',
        body: `<p class="glance-message">${utils.escapeHtml(nextLine)}</p>`,
    });
}

function analyticsHtml(data, size) {
    const kind = 'analytics';
    const label = 'Analytics';
    if (!data) return emptyShell(kind, size, copy.noStreak);
    const streak = Number(data.journal?.streak || 0);
    const missed = (data.work?.series || []).reduce((n, row) => n + Number(row.missed || 0), 0);
    const written = Number(data.journal?.days_written || 0);
    const detail = missed ? `${missed} misses` : `${written} days written`;
    return shellHtml({
        kind,
        size,
        label,
        primary: String(streak),
        body: `<p class="glance-message glance-message--quiet">${utils.escapeHtml(detail)}</p>`,
    });
}

function timelineHtml(data, size) {
    const kind = 'timeline';
    const label = 'Timeline';
    if (!data) return emptyShell(kind, size, copy.nothingLogged);
    const n = Number(data.journal_count || 0)
        + Number(data.work_count || 0)
        + Number(data.workout_count || 0)
        + Number(data.submission_count || 0);
    const iso = data.local_date || utils.localISODate();
    const when = formatShortDate(iso) || 'Today';
    return shellHtml({
        kind,
        size,
        label,
        primary: String(n),
        body: `<p class="glance-message glance-message--quiet">${utils.escapeHtml(when)}</p>`,
    });
}

function clunyHtml(data, size) {
    const kind = 'cluny';
    const label = 'Ask Cluny';
    const offline = data && data.ok === false;
    if (offline) {
        return shellHtml({
            kind,
            size,
            state: 'error',
            label,
            primary: copy.clunyOff,
            action: { act: 'open-settings', label: copy.openSettings },
        });
    }
    const n = Number(data?.pending_count || 0);
    const asks = size.action
        ? `${actionBtn('cluny-ask', copy.whatsOn, ' data-q="What do I have to do today?"')}
           ${actionBtn('cluny-ask', copy.freeTime, ' data-q="What should I do with my free time?"')}`
        : '';
    const pending = n
        ? `<p class="glance-message">${n === 1 ? '1 suggestion waiting' : `${n} suggestions waiting`}</p>`
        : `<p class="glance-message">${utils.escapeHtml(copy.whatsOn)}</p>`;
    return shellHtml({
        kind,
        size,
        label: n ? countLabel(label, n) : label,
        primary: n ? String(n) : '',
        body: `${pending}<div class="glance-actions">${asks}</div>`,
    });
}

function posterHtml(kind, _data, size) {
    return emptyShell(kind, size, copy.couldNotLoad);
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
    if (kind === 'cluny') {
        const inbox = await eelCall('get_cluny_inbox') || {};
        const health = await eelCall('get_cluny_health') || {};
        return { ...inbox, ...health };
    }
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
    body.innerHTML = shellHtml({
        kind,
        size,
        state: 'loading',
        label: spec.label,
        primary: copy.loading,
    });
}

export async function paintGlance(kind, body, card) {
    if (!body) return;
    const size = sizeOf(card);
    const data = await loadGlance(kind);
    if (!body.isConnected) return;
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
            const step = parseInt(btn.getAttribute('data-step') || '1', 10) || 1;
            await eel.tap_counter(id, step)();
        } else if (act === 'focus-keep' && hasEel('keep_daily_focus')) {
            await eel.keep_daily_focus(true)();
        } else if (act === 'cluny-ask') {
            document.dispatchEvent(new CustomEvent('kosistenz:open-cluny', {
                detail: { question: btn.getAttribute('data-q') || '' },
            }));
            return;
        } else if (act === 'open-settings') {
            document.dispatchEvent(new CustomEvent('kosistenz:open-tab', { detail: { tab: 'settings' } }));
            return;
        } else if (act === 'open-work') {
            document.dispatchEvent(new CustomEvent('kosistenz:open-home-work', {
                detail: { kind: btn.getAttribute('data-kind') || '' },
            }));
            return;
        } else {
            return;
        }
        utils.notifyDataChanged();
    } catch (err) {
        console.error(err);
        utils.showErrorFeedback(err?.message || 'Could not update that.');
    }
}
