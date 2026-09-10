/**
 * Home glances — one shell, filled states, no poster slogans.
 * Full UI lives in the work layer. Inline actions stay on the tile.
 */

import * as utils from './utils.js';
import { WIDGET_CATALOG } from './home_layout.js';
import { copy, moreCount, countLabel, minutesLabel } from './glance_copy.js';
import { callEel } from './lazy.js';

async function eelCall(name, ...args) {
    try {
        return await callEel(name, ...args);
    } catch (err) {
        console.error(err);
        return { ok: false, error: err?.message || String(err) };
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
    // Glance tiles need a 2×1 cell to count as actionable (Start/Finish/Ask).
    return { w, h, cells: w * h, wide: w >= 2, tall: h >= 2, board: w >= 3 || h >= 3, action: w >= 2 };
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

function actionBtn(act, label, attrs = '', extraClass = '') {
    const cls = extraClass ? ` glance-action ${extraClass}` : 'glance-action';
    return `<button type="button" class="${cls}" data-glance-act="${utils.escapeHtml(act)}"${attrs}>${utils.escapeHtml(label)}</button>`;
}

function actionRow(actions) {
    const list = (actions || []).filter(Boolean);
    if (!list.length) return '';
    return `<div class="glance-actions">${list.map((row) => actionBtn(row.act, row.label, row.attrs || '', row.cls || '')).join('')}</div>`;
}

function openWorkAction(kind, label = copy.open) {
    return { act: 'open-work', label, attrs: ` data-kind="${utils.escapeHtml(kind)}"` };
}

function shellHtml({ kind, size, state = 'ready', label, primary = '', body = '', action = null, actions = null, hero = false }) {
    const stateCls = state !== 'ready' ? ` is-${state}` : '';
    const labelHtml = `<p class="glance-label">${utils.escapeHtml(label)}</p>`;
    const row = actionRow(actions || (action ? [action] : []));
    if (state === 'empty' || state === 'error' || state === 'loading') {
        return tile(kind, size, stateCls, `
            ${labelHtml}
            <p class="glance-message">${utils.escapeHtml(primary || copy.couldNotLoad)}</p>
            ${row}`);
    }
    const primaryHtml = primary
        ? `<p class="glance-primary${hero ? ' glance-primary--hero' : ''}">${utils.escapeHtml(String(primary))}</p>`
        : '';
    return tile(kind, size, stateCls, `
        ${labelHtml}
        ${primaryHtml}
        ${body || ''}
        ${row}`);
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
    const meaning = clip(data.meaning || '', size.board ? 140 : size.tall ? 90 : 72);
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

function beatActions(beat, size) {
    if (!size.action) return [];
    const focus = beat?.now || beat?.next;
    if (!focus?.id) {
        return [openWorkAction('today_calendar', copy.open)];
    }
    const actions = [openWorkAction('today_calendar', copy.open)];
    if (beat?.can_skip && focus.id) {
        actions.push({
            act: 'block-skip',
            label: copy.skip,
            attrs: ` data-id="${utils.escapeHtml(focus.id)}"`,
            cls: 'glance-action--ghost',
        });
    }
    return actions;
}

function beatBody(beat, size) {
    const nowItem = beat?.now;
    const nextItem = beat?.next;
    const gap = Number(beat?.gap_minutes || 0);
    const nowLine = nowItem
        ? `${copy.now} · ${formatAgendaTime(nowItem)} ${clip(nowItem.title || '', 28)}`.trim()
        : '';
    const nextLine = nextItem
        ? `${copy.next} · ${formatAgendaTime(nextItem)} ${clip(nextItem.title || '', 28)}`.trim()
        : copy.clearClock;
    const gapLine = gap ? `${copy.gap} · ${minutesLabel(gap)}` : '';
    const lines = [nowLine, nextLine, size.tall ? gapLine : ''].filter(Boolean);
    return lines.map((line) => `<p class="glance-message">${utils.escapeHtml(line)}</p>`).join('');
}

function todayHtml(data, size) {
    const kind = 'today_calendar';
    if (!data || data.ok === false) {
        return emptyShell(kind, size, copy.couldNotLoad);
    }
    const label = 'Today';
    const iso = data?.local_date;
    const d = iso ? new Date(`${iso}T12:00:00`) : new Date();
    const shortWeek = Number.isNaN(d.getTime()) ? 'Now' : d.toLocaleDateString(undefined, { weekday: 'short' });
    const dayNum = Number.isNaN(d.getTime()) ? '' : String(d.getDate());
    const beat = data?.beat || {};
    const focus = beat.now || beat.next;
    const primary = beat.now
        ? clip(beat.now.title || copy.now, 28)
        : (focus ? formatAgendaTime(focus) : dayNum);
    return shellHtml({
        kind,
        size,
        label: size.wide || size.tall ? `${shortWeek} ${dayNum}` : label,
        primary: size.tall ? clip(beat.now?.title || beat.next?.title || copy.clearClock, 36) : primary,
        body: beatBody(beat, size),
        actions: beatActions(beat, size),
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
    const visible = items.filter((row) => row.status !== 'done' || size.board).slice(0, size.tall ? 4 : 2);
    const rows = listRows(visible, visible.length, (item) => (
        `<li class="${item.status === 'done' ? 'is-done' : ''}">${taskDot(item.status)}<strong>${utils.escapeHtml(clip(item.title || '', 36))}</strong></li>`
    ));
    const active = items.find((row) => row.status === 'active');
    const nextOpen = items.find((row) => row.status === 'open' || row.status === 'active');
    const target = active || nextOpen;
    const actions = [];
    if (size.action && target?.id) {
        actions.push({ act: 'todo-finish', label: copy.done, attrs: ` data-id="${utils.escapeHtml(target.id)}"` });
        actions.push({
            act: 'todo-plus15',
            label: copy.plus15,
            attrs: ` data-id="${utils.escapeHtml(target.id)}"`,
            cls: 'glance-action--ghost',
        });
        actions.push({
            act: 'todo-park',
            label: copy.park,
            attrs: ` data-id="${utils.escapeHtml(target.id)}"`,
            cls: 'glance-action--ghost',
        });
    }
    const headline = complete ? copy.allFinished : (active?.title || nextOpen?.title || '');
    const message = complete ? copy.allFinished : open ? '' : copy.nothingDated;
    return shellHtml({
        kind,
        size,
        label: countLabel(label, open || done ? open : ''),
        primary: size.tall ? clip(headline, 42) : String(complete ? done : open),
        hero: false,
        body: `${!size.tall && message ? `<p class="glance-message glance-message--quiet">${utils.escapeHtml(message)}</p>` : ''}${rows || ''}`,
        actions,
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
    const done = Boolean(workout.done || workout.session_count);
    const headline = split || sessionLine || (done ? 'Logged' : copy.nothingLogged);
    const bits = [
        sessionLine && split ? `<p class="glance-message">${utils.escapeHtml(sessionLine)}</p>` : '',
        lastDate ? `<p class="glance-message glance-message--quiet">${utils.escapeHtml(lastDate)}</p>` : '',
        done ? `<p class="glance-message glance-message--quiet">Logged</p>` : '',
    ].join('');
    const expectedKind = (data?.expected?.kinds || [])[0] || '';
    const actions = [];
    if (size.action && expectedKind && !done) {
        const needsName = expectedKind === 'other';
        actions.push({
            act: 'workout-log',
            label: `${copy.logWorkout} ${clip(split || expectedKind, 16)}`,
            attrs: ` data-kind="${utils.escapeHtml(expectedKind)}"${needsName ? ' data-needs-name="1"' : ''}`,
        });
    }
    return shellHtml({
        kind,
        size,
        label,
        primary: clip(headline, size.tall ? 36 : 22),
        body: bits || `<p class="glance-message">${utils.escapeHtml(copy.nothingLogged)}</p>`,
        actions,
    });
}

function goalsHtml(data, size) {
    const kind = 'goals';
    const label = 'Goals';
    const rows = Array.isArray(data) ? data : [];
    if (!rows.length) return emptyShell(kind, size, copy.noGoals);
    const weekly = rows.filter((row) => row.horizon === 'week');
    const focus = weekly[0] || rows[0];
    const spent = Number(focus?.spent_minutes || 0);
    const target = Number(focus?.target_minutes || 0);
    const zero = focus && target > 0 && spent === 0;
    const score = target
        ? `${minutesLabel(spent)} / ${minutesLabel(target)}`
        : minutesLabel(spent);
    const list = size.tall
        ? listRows(weekly.length ? weekly : rows, size.board ? 5 : 4, (item) => {
            const have = Number(item.spent_minutes || 0);
            const want = Number(item.target_minutes || 0);
            const meta = want ? `${minutesLabel(have)} / ${minutesLabel(want)}` : minutesLabel(have);
            return `<li><strong>${utils.escapeHtml(clip(item.title || '', 28))}</strong><span>${utils.escapeHtml(meta)}</span></li>`;
        })
        : '';
    return shellHtml({
        kind,
        size,
        label: countLabel(label, weekly.length || rows.length),
        primary: size.tall ? clip(focus?.title || '', 32) : score,
        body: `${!size.tall ? `<p class="glance-message">${utils.escapeHtml(clip(focus?.title || '', 32))}</p>` : ''}${zero ? `<p class="glance-message">${utils.escapeHtml(copy.zeroMinutes)}</p>` : ''}${list}`,
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
    const first = rows[0];
    const actions = [];
    if (size.action && first?.id) {
        actions.push({
            act: 'work-today',
            label: copy.doToday,
            attrs: ` data-id="${utils.escapeHtml(first.id)}"`,
        });
    }
    return shellHtml({
        kind,
        size,
        label: countLabel(label, rows.length),
        primary: size.tall ? clip(first?.title || '', 36) : String(rows.length),
        body: `${list}${more}`,
        actions,
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
    const intention = String(data?.morning?.intention_text || '').trim();
    const recap = String(data?.evening?.recap_text || '').trim();
    const next = (data?.agenda || [])[0];
    const nextLine = next ? `${formatAgendaTime(next)} ${next.title || ''}`.trim() : copy.noEvents;
    if (evening) {
        return shellHtml({
            kind,
            size,
            label,
            primary: leftover ? String(leftover) : (recap ? clip(recap, 28) : copy.writeRecap),
            body: `<p class="glance-message">${leftover ? `${leftover} leftover` : (recap ? utils.escapeHtml(clip(recap, 72)) : copy.writeRecap)}</p>`,
            action: size.action ? openWorkAction(kind, recap ? copy.open : copy.writeRecap) : null,
        });
    }
    return shellHtml({
        kind,
        size,
        label,
        primary: intention ? clip(intention, 32) : (next ? formatAgendaTime(next) : copy.writeIntention),
        body: `<p class="glance-message">${utils.escapeHtml(intention ? clip(intention, 72) : nextLine)}</p>`,
        action: size.action ? openWorkAction(kind, intention ? copy.open : copy.writeIntention) : null,
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
    // Glance Cluny stays a health tile when the brain is off.
    const offline = data && data.brain_ready === false;
    if (offline) {
        return shellHtml({
            kind,
            size,
            state: 'error',
            label,
            primary: copy.clunyOff, // Glance Cluny is Off
            action: size.wide ? { act: 'open-settings', label: copy.openSettings } : null,
        });
    }
    const n = Number(data?.pending_count || 0);
    const part = dayPart();
    const ask = part === 'evening'
        ? { label: copy.eveningAsk, q: 'What still matters tonight?' }
        : part === 'afternoon'
            ? { label: copy.freeTime, q: 'What should I do with my free time?' }
            : { label: copy.whatsOn, q: 'What do I have to do today?' };
    const asks = size.action
        ? actionBtn('cluny-ask', ask.label, ` data-q="${utils.escapeHtml(ask.q)}"`)
        : '';
    const pending = n
        ? `<p class="glance-message">${n === 1 ? '1 suggestion waiting' : `${n} suggestions waiting`}</p>`
        : `<p class="glance-message">${utils.escapeHtml(ask.label)}</p>`;
    return shellHtml({
        kind,
        size,
        label: n ? countLabel(label, n) : label,
        primary: n ? String(n) : '',
        body: `${pending}<div class="glance-actions">${asks}</div>`,
    });
}

function nowNextHtml(data, size) {
    const kind = 'now_next';
    const beat = data || {};
    const focus = beat.now || beat.next;
    const label = beat.now ? copy.now : copy.next;
    return shellHtml({
        kind,
        size,
        label,
        primary: focus ? clip(focus.title || '', 28) : copy.clearClock,
        body: beatBody(beat, size),
        actions: beatActions(beat, size),
    });
}

function weekdayChips(weekdays, itemId) {
    const days = weekdays || [];
    if (!days.length || !itemId) return '';
    return `<div class="glance-weekdays">${days.map((day) => (
        `<button type="button" class="glance-action glance-action--ghost glance-action--chip" data-glance-act="unplaced-day" data-id="${utils.escapeHtml(itemId)}" data-day="${utils.escapeHtml(day.date)}">${utils.escapeHtml(day.label)}</button>`
    )).join('')}</div>`;
}

function unplacedHtml(data, size) {
    const kind = 'unplaced';
    const rows = data?.items || [];
    const count = data?.count ?? rows.length;
    if (!count) {
        return emptyShell(kind, size, copy.allPlaced, openWorkAction('allwork', copy.add));
    }
    const first = rows[0];
    const list = size.tall
        ? listRows(rows, size.board ? 4 : 3, (item) => (
            `<li><strong>${utils.escapeHtml(clip(item.title || '', 28))}</strong><span>${utils.escapeHtml(minutesLabel(item.remaining_minutes || item.estimate_minutes))}</span></li>`
        ))
        : '';
    return shellHtml({
        kind,
        size,
        label: countLabel('Unplaced', count),
        primary: clip(first?.title || '', 32),
        body: `${list}${weekdayChips(data?.weekdays, first?.id)}`,
    });
}

function duesHtml(data, size) {
    const kind = 'dues';
    const rows = data?.items || [];
    if (!rows.length) {
        return emptyShell(kind, size, copy.nothingDue, openWorkAction('todo', copy.addPlace));
    }
    const first = rows[0];
    const list = listRows(rows, size.tall ? 5 : 2, (item) => (
        `<li><strong>${utils.escapeHtml(clip(item.title || '', 28))}</strong><span>${utils.escapeHtml(formatShortDate(item.due))}</span></li>`
    ));
    return shellHtml({
        kind,
        size,
        label: countLabel('Due', data.count || rows.length),
        primary: size.tall ? '' : formatShortDate(first.due),
        body: list,
        action: size.action ? openWorkAction('todo', copy.open) : null,
    });
}

function freeTodayHtml(data, size) {
    const kind = 'free_today';
    const free = Number(data?.free_minutes || 0);
    const needed = Number(data?.needed_minutes || 0);
    const open = Number(data?.open_count || 0);
    const line = `${minutesLabel(free)} free, ${minutesLabel(needed)} of open to-dos${open ? ` (${open})` : ''}.`;
    return shellHtml({
        kind,
        size,
        label: 'Free today',
        primary: minutesLabel(free),
        body: `<p class="glance-message">${utils.escapeHtml(line)}</p>`,
        action: size.action ? openWorkAction('today_calendar', copy.open) : null,
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
    if (kind === 'now_next') return eelCall('get_now_next_glance');
    if (kind === 'unplaced') return eelCall('get_unplaced_glance');
    if (kind === 'dues') return eelCall('get_dues_week_glance');
    if (kind === 'free_today') return eelCall('get_free_today_glance');
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
    if (kind === 'now_next') return nowNextHtml(data, size);
    if (kind === 'unplaced') return unplacedHtml(data, size);
    if (kind === 'dues') return duesHtml(data, size);
    if (kind === 'free_today') return freeTodayHtml(data, size);
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

export function paintGlanceFromData(kind, body, card, data) {
    if (!body) return;
    try {
        body.innerHTML = renderKind(kind, data, sizeOf(card));
    } catch (err) {
        console.error(err);
        body.innerHTML = emptyShell(kind, sizeOf(card), copy.couldNotLoad);
    }
}

export async function paintGlance(kind, body, card) {
    if (!body) return;
    const data = await loadGlance(kind);
    if (!body.isConnected) return;
    paintGlanceFromData(kind, body, card, data);
}

export async function refreshGlances(kinds, dataByKind) {
    const set = kinds ? new Set(kinds) : null;
    const cards = [...document.querySelectorAll('#homeGridAbove .home-widget, #homeGrid .home-widget')];
    await Promise.all(cards.map(async (card) => {
        const kind = card.getAttribute('data-kind');
        if (set && !set.has(kind)) return;
        const body = card.querySelector('.home-widget-body');
        if (!body) return;
        if (dataByKind && Object.prototype.hasOwnProperty.call(dataByKind, kind)) {
            paintGlanceFromData(kind, body, card, dataByKind[kind]);
            return;
        }
        await paintGlance(kind, body, card);
    }));
}

export async function runGlanceAction(btn) {
    const act = btn?.getAttribute('data-glance-act');
    const id = btn?.getAttribute('data-id') || '';
    if (!act) return;
    try {
        if (act === 'todo-finish') {
            try {
                await callEel('glance_finish_work', id);
            } catch (_) {
                await callEel('finish_work_item', id);
            }
        } else if (act === 'todo-plus15') {
            await callEel('glance_plus15', id);
        } else if (act === 'todo-park') {
            await callEel('glance_park_work', id);
        } else if (act === 'work-today') {
            await callEel('glance_do_today', id);
        } else if (act === 'unplaced-day') {
            await callEel('glance_place_unplaced', id, btn.getAttribute('data-day') || '');
        } else if (act === 'block-skip') {
            await callEel('glance_skip_block', id);
        } else if (act === 'workout-log') {
            const kind = btn.getAttribute('data-kind') || '';
            let other = '';
            if (btn.getAttribute('data-needs-name') === '1') {
                other = window.prompt('Name this session') || '';
                if (!other.trim()) return;
            }
            await callEel('glance_log_expected_workout', kind, null, other);
        } else if (act === 'todo-start') {
            await callEel('start_work_item', id);
        } else if (act === 'habit-tick') {
            await callEel('toggle_home_habit', id);
        } else if (act === 'counter-tap') {
            const step = parseInt(btn.getAttribute('data-step') || '1', 10) || 1;
            await callEel('tap_counter', id, step);
        } else if (act === 'focus-keep') {
            await callEel('keep_daily_focus', true);
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
