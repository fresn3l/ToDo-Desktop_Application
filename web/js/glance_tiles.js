/**
 * Home glances — one shell, filled states, no poster slogans.
 * Full UI lives in the work layer. Inline actions stay on the tile.
 */

import * as utils from './utils.js';
import { splitKey, widgetLabel } from './home_layout.js';
import { copy, moreCount, minutesLabel } from './glance_copy.js';
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

// How many list rows a tile holds. These mirror the tile's own metrics in
// style.css: a row is a line of body text plus the list gap, and the chrome is
// the padding, the heading and the button row the list sits between.
const GLANCE_ROW_PX = 24;
const GLANCE_CHROME_PX = 111;
// A counter carries two icon buttons, so it stands about two text rows tall.
const GLANCE_BLOCK_ROWS = 2;
const GLANCE_MAX_ROWS = 14;

function rowBudget(card, h) {
    const px = card?.getBoundingClientRect?.().height || 0;
    // A tile on a page nobody has opened measures nothing. The cell count is
    // the fallback; it undercounts, which shows fewer rows rather than none.
    if (px <= 0) return h >= 6 ? 6 : h >= 4 ? 3 : 0;
    const fits = Math.floor((px - GLANCE_CHROME_PX) / GLANCE_ROW_PX);
    return Math.max(0, Math.min(GLANCE_MAX_ROWS, fits));
}

function sizeOf(card) {
    const w = Math.max(1, Number(card?.dataset.w) || 1);
    const h = Math.max(1, Number(card?.dataset.h) || 1);
    // One budget for every tile. Rows follow the height the tile actually has,
    // because the same cell count is a different number of rows depending on
    // how the grid is divided. Buttons follow width. A short row is label plus
    // metric. Capture belongs on a six-high tile.
    const rows = rowBudget(card, h);
    return {
        w,
        h,
        cells: w * h,
        wide: w >= 4,
        tall: h >= 4,
        board: w >= 6 || h >= 6,
        action: w >= 4 && h >= 4,
        rows,
        blocks: Math.max(1, Math.floor(rows / GLANCE_BLOCK_ROWS)),
        capture: h >= 6,
    };
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

function keyLabel(key) {
    const { kind, settings } = splitKey(key);
    return widgetLabel(kind, settings);
}

function tile(key, size, extraClass, inner) {
    const { kind } = splitKey(key);
    return `<div class="glance-tile glance-tile--${kind} glance-tile--${size.w}x${size.h}${extraClass ? ` ${extraClass}` : ''}" data-glance="${utils.escapeHtml(key)}">${inner}</div>`;
}

function actionBtn(act, label, attrs = '', extraClass = '') {
    const cls = extraClass ? ` glance-action ${extraClass}` : 'glance-action';
    return `<button type="button" class="${cls}" data-glance-act="${utils.escapeHtml(act)}"${attrs}>${utils.escapeHtml(label)}</button>`;
}

function actionRow(actions, size) {
    let list = (actions || []).filter(Boolean);
    if (!list.length) return '';
    // Two buttons is all a narrow tile can hold on one line: the move you
    // would make, and Open. The rest of the tools live in the sheet.
    if (size && size.w <= 4 && list.length > 2) {
        const open = list.find((row) => row.act === 'open-work');
        const first = list.find((row) => row !== open);
        list = [first, open].filter(Boolean);
    }
    return `<div class="glance-actions">${list.map((row) => actionBtn(row.act, row.label, row.attrs || '', row.cls || '')).join('')}</div>`;
}

function openWorkAction(key, label = copy.open) {
    return { act: 'open-work', label, attrs: ` data-key="${utils.escapeHtml(key)}"` };
}

/**
 * Every tile is a heading, a middle that grows, and a row of buttons at the
 * foot. The middle is what makes the buttons line up across the board: a tile
 * with one line in it used to leave its button floating halfway up.
 *
 * The count is its own element rather than part of the heading string, so a
 * tile reads "Today's work 7" with the number set apart instead of
 * "Today's work · 7" run together.
 */
function shellHtml({ key, size, state = 'ready', label, count = '', primary = '', body = '', action = null, actions = null, hero = false }) {
    const stateCls = state !== 'ready' ? ` is-${state}` : '';
    const countHtml = count === '' || count == null
        ? ''
        : `<span class="glance-count">${utils.escapeHtml(String(count))}</span>`;
    const head = `<header class="glance-tile-head"><h3 class="glance-label">${utils.escapeHtml(label)}</h3>${countHtml}</header>`;
    const quiet = state === 'empty' || state === 'error' || state === 'loading';
    const lead = quiet
        ? `<p class="glance-message">${utils.escapeHtml(primary || copy.couldNotLoad)}</p>`
        : (primary ? `<p class="glance-primary${hero ? ' glance-primary--hero' : ''}">${utils.escapeHtml(String(primary))}</p>` : '');
    const row = actionRow(actions || (action ? [action] : []), size);
    return tile(key, size, stateCls, `${head}<div class="glance-body">${lead}${body || ''}</div>${row}`);
}

function emptyShell(key, size, message, action) {
    return shellHtml({
        key,
        size,
        state: 'empty',
        label: keyLabel(key),
        primary: message,
        action: action || openWorkAction(key),
    });
}

function listRows(items, limit, render) {
    const rows = (items || []).slice(0, limit);
    if (!rows.length) return '';
    return `<ul class="glance-list">${rows.map(render).join('')}</ul>`;
}

// Prose tiles spend the same row budget as list tiles, so a short tile shows
// the one line that matters instead of four lines squeezed to nothing.
function capLines(lines, size) {
    return (lines || []).filter(Boolean).slice(0, Math.max(1, size.rows || 1)).join('');
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
    const key = 'weather';
    const label = 'Weather';
    if (!data || data.need_place) {
        return emptyShell(key, size, copy.setPlace, { act: 'open-work', label: copy.setPlace, attrs: ` data-key="${key}"` });
    }
    if (!data.ok) {
        return emptyShell(key, size, data.error ? copy.couldNotLoad : copy.noForecast);
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
            key,
            size,
            label,
            primary: temp,
            hero: true,
            body: `${glyph}${cond ? `<p class="glance-message">${utils.escapeHtml(clip(cond, 14))}</p>` : ''}`,
        });
    }
    const hours = size.tall ? (data.hourly || []).slice(0, 4) : [];
    const hourly = hours.length
        ? `<ul class="glance-hourly">${hours.map((row) => {
            const t = row.hour || formatHourly(row.at || row.time);
            const val = row.temp == null ? '—' : `${row.temp}°`;
            return `<li><span>${utils.escapeHtml(t)}</span><strong>${utils.escapeHtml(val)}</strong></li>`;
        }).join('')}</ul>`
        : '';
    return shellHtml({
        key,
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
    const key = 'word';
    const label = 'Word';
    if (!data?.word) return emptyShell(key, size, copy.noWord);
    const head = data.display || data.word;
    const pos = [data.language_label || (data.language === 'de' ? 'German' : 'English'), data.pos].filter(Boolean).join(' · ');
    const meaning = clip(data.meaning || '', size.board ? 140 : size.tall ? 90 : 48);
    const example = clip(data.example || '', size.board ? 120 : 72);
    const used = Boolean((data.used_tonight || '').trim());
    if (!size.wide && !size.tall) {
        return shellHtml({ key, size, label, primary: clip(head, 12), hero: true });
    }
    // Meaning first: it is the reason to look at the tile at all.
    const parts = capLines([
        meaning && size.tall ? `<p class="glance-message">${utils.escapeHtml(meaning)}</p>` : '',
        pos ? `<p class="glance-message glance-message--quiet">${utils.escapeHtml(pos)}</p>` : '',
        example && size.tall ? `<p class="glance-message glance-message--quiet">${utils.escapeHtml(example)}</p>` : '',
        used && size.tall ? `<p class="glance-message glance-message--quiet">${utils.escapeHtml(copy.usedTonight)}</p>` : '',
    ], size);
    return shellHtml({ key, size, label, primary: head, hero: true, body: parts });
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

// The headline carries the title of whatever is in focus, so these lines carry
// the clock instead. A tile that says "Clear clock." twice, once as its
// headline and once underneath, is what this arrangement exists to avoid.
function beatBody(beat, size) {
    const nowItem = beat?.now;
    const nextItem = beat?.next;
    const focus = nowItem || nextItem;
    const gap = Number(beat?.gap_minutes || 0);
    const line = (word, item) => (item
        ? `${word} · ${formatAgendaTime(item)}${item === focus ? '' : ` ${clip(item.title || '', 28)}`}`.trim()
        : '');
    // With nothing on either side of it, the same figure is not a gap between
    // two things, it is what is left of the day.
    const tail = gap
        ? (focus ? `${copy.gap} · ${minutesLabel(gap)}` : `${minutesLabel(gap)} ${copy.leftToday}`)
        : '';
    const lines = size.tall
        ? [line(copy.now, nowItem), line(copy.next, nextItem), tail]
        : [line(nowItem ? copy.now : copy.next, focus)];
    return lines.filter(Boolean).map((row) => `<p class="glance-message">${utils.escapeHtml(row)}</p>`).join('');
}

function todayHtml(data, size) {
    const key = 'today_calendar';
    if (!data || data.ok === false) {
        return emptyShell(key, size, copy.couldNotLoad);
    }
    const iso = data?.local_date;
    const d = iso ? new Date(`${iso}T12:00:00`) : new Date();
    const dated = !Number.isNaN(d.getTime());
    const shortWeek = dated ? d.toLocaleDateString(undefined, { weekday: 'short' }) : 'Now';
    const dayNum = dated ? String(d.getDate()) : '';
    const beat = data?.beat || {};
    const focus = beat.now || beat.next;
    return shellHtml({
        key,
        size,
        label: size.wide || size.tall ? `${shortWeek} ${dayNum}` : 'Today',
        primary: focus
            ? clip(focus.title || (beat.now ? copy.now : copy.next), size.tall ? 36 : 28)
            : copy.clearClock,
        body: beatBody(beat, size),
        actions: beatActions(beat, size),
    });
}

function todoCaptureHtml() {
    return `<form class="glance-capture" data-glance-capture="todo" action="#">
        <input type="text" class="glance-capture-input" placeholder="${utils.escapeHtml(copy.addLine)}" autocomplete="off">
    </form>`;
}

function workTodayHtml(data, size) {
    const key = 'work:slice=today';
    const label = keyLabel(key);
    const items = data?.today || [];
    const open = data?.counts?.today_open ?? items.filter((row) => row.status !== 'done').length;
    const done = data?.counts?.today_done ?? items.filter((row) => row.status === 'done').length;
    const complete = open === 0 && done > 0;
    const capture = size.capture ? todoCaptureHtml() : '';
    const openBtn = openWorkAction(key, copy.open);
    if (!items.length && !open && !done) {
        return shellHtml({
            key,
            size,
            state: 'empty',
            label,
            primary: copy.nothingDated,
            body: capture,
            action: openBtn,
        });
    }
    const pool = items.filter((row) => row.status !== 'done' || size.board);
    const visible = size.tall ? pool.slice(0, size.rows) : [];
    const extra = Math.max(0, pool.length - visible.length);
    const rows = listRows(visible, visible.length, (item) => (
        `<li class="${item.status === 'done' ? 'is-done' : ''}">${taskDot(item.status)}<strong>${utils.escapeHtml(clip(item.title || '', 80))}</strong></li>`
    ));
    const more = extra ? `<p class="glance-message glance-message--quiet">${utils.escapeHtml(moreCount(extra))}</p>` : '';
    const active = items.find((row) => row.status === 'active');
    const nextOpen = items.find((row) => row.status === 'open' || row.status === 'active');
    const target = active || nextOpen;
    const actions = [];
    if (size.action && target?.id) {
        actions.push({ act: 'todo-finish', label: copy.done, attrs: ` data-id="${utils.escapeHtml(target.id)}"` });
        // Buttons fit by width, not by area: a two-wide tile holds Done and
        // Open on one line and nothing more, however tall it gets.
        if (size.w >= 6) {
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
    }
    actions.push(openBtn);
    // The list carries the titles; the headline would only say them twice.
    const message = complete ? copy.allFinished : open ? '' : copy.nothingDated;
    return shellHtml({
        key,
        size,
        label,
        count: open || done ? open : '',
        primary: size.tall ? '' : String(complete ? done : open),
        hero: false,
        body: `${message ? `<p class="glance-message glance-message--quiet">${utils.escapeHtml(message)}</p>` : ''}${rows || ''}${more}${capture}`,
        actions,
    });
}

function habitsHtml(data, size) {
    const key = 'habits';
    const label = 'Habits';
    const total = data?.total || 0;
    const done = data?.done || 0;
    if (!total) return emptyShell(key, size, copy.noHabits);
    const next = (data?.habits || []).find((row) => !row.done);
    const rows = size.tall
        ? listRows(data?.habits || [], size.rows, (item) => (
            `<li class="${item.done ? 'is-done' : ''}">${taskDot(item.done ? 'done' : 'open')}<strong>${utils.escapeHtml(clip(item.title || '', 60))}</strong></li>`
        ))
        : '';
    const action = size.action && next
        ? { act: 'habit-tick', label: `${copy.tick} ${clip(next.title, 16)}`, attrs: ` data-id="${utils.escapeHtml(next.id)}"` }
        : null;
    const quiet = done === total ? 'All ticked.' : '';
    return shellHtml({
        key,
        size,
        label,
        count: `${done}/${total}`,
        primary: size.tall ? '' : `${done}/${total}`,
        body: `${quiet ? `<p class="glance-message glance-message--quiet">${quiet}</p>` : ''}${rows}`,
        action,
    });
}

function countersHtml(data, size) {
    const key = 'counters';
    const label = 'Counters';
    const rows = data?.counters || [];
    const first = rows[0];
    if (!first) return emptyShell(key, size, copy.noCounters);
    if (!size.tall) {
        return shellHtml({
            key,
            size,
            label: clip(first.name || label, 16),
            primary: String(first.today || 0),
            action: { act: 'counter-tap', label: '+', attrs: ` data-id="${utils.escapeHtml(first.id)}" data-step="1"` },
        });
    }
    // The grid is two columns when the tile is wide, so trim to a whole number
    // of rows rather than leaving a half-empty one at the bottom. A counter is
    // taller than a line of text, hence blocks rather than rows.
    const cols = size.w >= 4 ? 2 : 1;
    const cap = Math.max(cols, size.blocks * cols);
    const chips = rows.slice(0, cap).map((item) => `
        <div class="glance-counter">
            <span class="glance-counter-name">${utils.escapeHtml(clip(item.name || '', 18))}</span>
            <span class="glance-counter-value">${item.today || 0}${item.target ? `/${item.target}` : ''}</span>
            <button type="button" class="glance-action glance-action--icon" data-glance-act="counter-tap" data-id="${utils.escapeHtml(item.id)}" data-step="-1" aria-label="Minus">−</button>
            <button type="button" class="glance-action glance-action--icon" data-glance-act="counter-tap" data-id="${utils.escapeHtml(item.id)}" data-step="1" aria-label="Plus">+</button>
        </div>`).join('');
    return shellHtml({
        key,
        size,
        label,
        count: rows.length,
        body: `<div class="glance-counters">${chips}</div>`,
    });
}


function countdownHtml(data, size) {
    const key = 'countdown';
    const label = 'Countdown';
    const rows = Array.isArray(data) ? data : [];
    const next = rows.find((row) => row.state !== 'past') || rows[0];
    if (!next) return emptyShell(key, size, copy.noDates);
    const days = Number(next.days);
    const count = next.state === 'today' ? '0' : (Number.isFinite(days) ? String(Math.abs(days)) : '—');
    const unit = next.state === 'today' ? 'today' : Number(next.days) < 0 ? 'ago' : 'days';
    const list = size.tall
        ? listRows(rows, size.rows, (item) => {
            const n = item.state === 'today' ? '0' : String(Math.abs(Number(item.days) || 0));
            return `<li><span>${utils.escapeHtml(n)}</span><strong>${utils.escapeHtml(clip(item.title || '', 60))}</strong></li>`;
        })
        : '';
    return shellHtml({
        key,
        size,
        label,
        primary: count,
        body: `<p class="glance-message">${utils.escapeHtml(clip(next.title || '', 36))} · ${unit}</p>${list}`,
    });
}

function readingHtml(data, size) {
    const key = 'reading';
    const label = 'Reading';
    if (!data?.title) return emptyShell(key, size, copy.noBook);
    const pages = data.pages_today ? String(data.pages_today) : String(data.page || '·');
    const pageLine = data.page ? `Page ${data.page}` : 'pages today';
    return shellHtml({
        key,
        size,
        label,
        primary: pages,
        body: size.tall
            ? `<p class="glance-message">${utils.escapeHtml(clip(data.title, 48))}</p>
            <p class="glance-message glance-message--quiet">${utils.escapeHtml(pageLine)}</p>`
            : `<p class="glance-message">${utils.escapeHtml(clip(data.title, 32))}</p>`,
    });
}

function workoutHtml(data, size) {
    const key = 'workout';
    const label = 'Workout';
    const workout = data?.workout || data || {};
    const split = (data?.expected?.labels || []).join(' · ');
    const last = workout.last_session || data?.last_session;
    const latest = (workout.sessions || [])[(workout.sessions || []).length - 1];
    const session = latest || last;
    if (!split && !session && !workout.session_count) {
        return emptyShell(key, size, copy.nothingLogged);
    }
    const lastDate = formatShortDate(last?.local_date || (workout.done ? data?.local_date : ''));
    const sessionLine = session
        ? [session.label || session.kind_label, session.miles ? `${session.miles} mi` : '', session.minutes ? `${session.minutes} min` : '']
            .filter(Boolean)
            .join(' · ')
        : '';
    const done = Boolean(workout.done || workout.session_count);
    const headline = split || sessionLine || (done ? 'Logged' : copy.nothingLogged);
    const bits = size.tall
        ? capLines([
            sessionLine && split ? `<p class="glance-message">${utils.escapeHtml(sessionLine)}</p>` : '',
            done ? `<p class="glance-message glance-message--quiet">Logged</p>` : '',
            lastDate ? `<p class="glance-message glance-message--quiet">${utils.escapeHtml(lastDate)}</p>` : '',
        ], size)
        : (sessionLine && split ? `<p class="glance-message">${utils.escapeHtml(sessionLine)}</p>` : '');
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
        key,
        size,
        label,
        primary: clip(headline, size.tall ? 36 : 22),
        body: bits || `<p class="glance-message">${utils.escapeHtml(copy.nothingLogged)}</p>`,
        actions,
    });
}

function goalsHtml(data, size) {
    const key = 'goals';
    const label = 'Goals';
    if (data?.ok === false) return emptyShell(key, size, copy.couldNotLoad);
    const rows = Array.isArray(data) ? data : [];
    if (!rows.length) return emptyShell(key, size, copy.noGoals);
    const weekly = rows.filter((row) => row.horizon === 'week');
    const focus = weekly[0] || rows[0];
    const spent = Number(focus?.spent_minutes || 0);
    const target = Number(focus?.target_minutes || 0);
    const zero = focus && target > 0 && spent === 0;
    const score = target
        ? `${minutesLabel(spent)} / ${minutesLabel(target)}`
        : minutesLabel(spent);
    const pct = target ? Math.max(0, Math.min(100, Math.round((spent / target) * 100))) : 0;
    const bar = target
        ? `<div class="glance-meter" role="progressbar" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100"><i style="width:${pct}%"></i></div>`
        : '';
    const list = size.tall
        ? listRows(weekly.length ? weekly : rows, size.rows, (item) => {
            const have = Number(item.spent_minutes || 0);
            const want = Number(item.target_minutes || 0);
            const meta = want ? `${minutesLabel(have)} / ${minutesLabel(want)}` : minutesLabel(have);
            return `<li><strong>${utils.escapeHtml(clip(item.title || '', 60))}</strong><span>${utils.escapeHtml(meta)}</span></li>`;
        })
        : '';
    return shellHtml({
        key,
        size,
        label,
        count: weekly.length || rows.length,
        primary: size.tall ? '' : score,
        body: `${!size.tall ? `<p class="glance-message">${utils.escapeHtml(clip(focus?.title || '', 32))}</p>` : ''}${bar}${zero && size.tall ? `<p class="glance-message">${utils.escapeHtml(copy.zeroMinutes)}</p>` : ''}${list}`,
        action: openWorkAction(key),
    });
}

function workBacklogHtml(data, size) {
    const key = 'work:slice=backlog';
    const label = keyLabel(key);
    const rows = Array.isArray(data) ? data : [];
    if (!rows.length) {
        return emptyShell(key, size, copy.backlogClear, { act: 'open-work', label: copy.add, attrs: ` data-key="${key}"` });
    }
    const limit = size.rows;
    const extra = size.tall ? Math.max(0, rows.length - limit) : 0;
    const list = size.tall
        ? listRows(rows, limit, (item) => (
            `<li><strong>${utils.escapeHtml(clip(item.title || '', 80))}</strong></li>`
        ))
        : '';
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
        key,
        size,
        label,
        count: rows.length,
        primary: size.tall ? '' : String(rows.length),
        body: `${list}${more}`,
        actions,
    });
}


function dayBriefHtml(data, size) {
    const key = 'day_brief';
    const evening = data?.slot === 'evening';
    const label = evening ? 'Evening' : 'Morning';
    const leftover = data?.review?.leftover?.length || 0;
    const intention = String(data?.morning?.intention_text || '').trim();
    const recap = String(data?.evening?.recap_text || '').trim();
    const next = (data?.agenda || [])[0];
    const nextLine = next ? `${formatAgendaTime(next)} ${next.title || ''}`.trim() : copy.noEvents;
    if (evening) {
        return shellHtml({
            key,
            size,
            label,
            primary: leftover ? String(leftover) : (recap ? clip(recap, 28) : copy.writeRecap),
            body: `<p class="glance-message">${leftover ? `${leftover} leftover` : (recap ? utils.escapeHtml(clip(recap, 72)) : copy.writeRecap)}</p>`,
            action: size.action ? openWorkAction(key, recap ? copy.open : copy.writeRecap) : null,
        });
    }
    return shellHtml({
        key,
        size,
        label,
        primary: intention ? clip(intention, 32) : (next ? formatAgendaTime(next) : copy.writeIntention),
        body: `<p class="glance-message">${utils.escapeHtml(intention ? clip(intention, 72) : nextLine)}</p>`,
        action: size.action ? openWorkAction(key, intention ? copy.open : copy.writeIntention) : null,
    });
}

function analyticsHtml(data, size) {
    const key = 'analytics';
    const label = 'Analytics';
    if (!data) return emptyShell(key, size, copy.noStreak);
    const streak = Number(data.journal?.streak || 0);
    const attendance = data.consistency?.attendance_pct;
    const missed = (data.work?.series || []).reduce((n, row) => n + Number(row.missed || 0), 0);
    const written = Number(data.journal?.days_written || 0);
    const detail = attendance != null
        ? `${attendance}% attendance`
        : (missed ? `${missed} misses` : `${written} days written`);
    return shellHtml({
        key,
        size,
        label,
        primary: attendance != null ? `${attendance}%` : String(streak),
        body: `<p class="glance-message glance-message--quiet">${utils.escapeHtml(detail)}</p>`,
    });
}


function clunyHtml(data, size) {
    const key = 'cluny';
    const label = 'Ask Cluny';
    // Glance Cluny stays a health tile when the brain is off.
    const offline = data && data.brain_ready === false;
    if (offline) {
        return shellHtml({
            key,
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
    const voice = (data?.pending || []).find((row) => String(row?.message || '').trim());
    const pending = voice?.message
        ? `<p class="glance-message">${utils.escapeHtml(voice.message)}</p>`
        : n
            ? `<p class="glance-message">${n === 1 ? '1 suggestion waiting' : `${n} suggestions waiting`}</p>`
            : `<p class="glance-message">${utils.escapeHtml(ask.label)}</p>`;
    return shellHtml({
        key,
        size,
        label,
        count: n || '',
        primary: n ? String(n) : '',
        body: `${pending}${asks ? `<div class="glance-actions">${asks}</div>` : ''}`,
    });
}


function weekdayChips(weekdays, itemId) {
    const days = weekdays || [];
    if (!days.length || !itemId) return '';
    return `<div class="glance-weekdays">${days.map((day) => (
        `<button type="button" class="glance-action glance-action--ghost glance-action--chip" data-glance-act="unplaced-day" data-id="${utils.escapeHtml(itemId)}" data-day="${utils.escapeHtml(day.date)}">${utils.escapeHtml(day.label)}</button>`
    )).join('')}</div>`;
}

function workUnplacedHtml(data, size) {
    const key = 'work:slice=unplaced';
    const rows = data?.items || [];
    const count = data?.count ?? rows.length;
    if (!count) {
        return emptyShell(key, size, copy.allPlaced, openWorkAction(key, copy.add));
    }
    const first = rows[0];
    const list = size.tall
        ? listRows(rows, size.rows, (item) => (
            `<li><strong>${utils.escapeHtml(clip(item.title || '', 60))}</strong><span>${utils.escapeHtml(minutesLabel(item.remaining_minutes || item.estimate_minutes))}</span></li>`
        ))
        : '';
    return shellHtml({
        key,
        size,
        label: keyLabel(key),
        count,
        primary: size.tall ? '' : clip(first?.title || '', 32),
        // Seven day chips only fit on one line on a wide tile; wrapped they
        // would eat the rows the list needs.
        body: `${list}${size.w >= 6 ? weekdayChips(data?.weekdays, first?.id) : ''}`,
    });
}

function workDueHtml(data, size) {
    const key = 'work:slice=due';
    const rows = data?.items || [];
    if (!rows.length) {
        return emptyShell(key, size, copy.nothingDue, openWorkAction(key, copy.addPlace));
    }
    const first = rows[0];
    const list = size.tall
        ? listRows(rows, size.rows, (item) => (
            `<li><strong>${utils.escapeHtml(clip(item.title || '', 60))}</strong><span>${utils.escapeHtml(formatShortDate(item.due))}</span></li>`
        ))
        : '';
    return shellHtml({
        key,
        size,
        label: keyLabel(key),
        count: data.count || rows.length,
        primary: size.tall ? '' : formatShortDate(first.due),
        body: list,
        action: size.action ? openWorkAction(key, copy.open) : null,
    });
}


function posterHtml(key, _data, size) {
    return emptyShell(key, size, copy.couldNotLoad);
}

// Four cuts of one list. Today and Due come off the dated board; All work and
// Unplaced come off the backlog.
const WORK_SLICE_CALL = {
    today: () => eelCall('get_work_board', utils.localISODate()),
    backlog: () => eelCall('list_backlog'),
    unplaced: () => eelCall('get_unplaced_glance'),
    due: () => eelCall('get_dues_week_glance'),
};

const WORK_SLICE_HTML = {
    today: workTodayHtml,
    backlog: workBacklogHtml,
    unplaced: workUnplacedHtml,
    due: workDueHtml,
};

async function loadGlance(key) {
    const { kind, settings } = splitKey(key);
    if (kind === 'work') return (WORK_SLICE_CALL[settings.slice] || WORK_SLICE_CALL.today)();
    if (kind === 'weather') return eelCall('get_weather_forecast', false);
    if (kind === 'word') return eelCall('get_word_of_the_day');
    if (kind === 'today_calendar') {
        const beat = await eelCall('get_now_next_glance');
        if (!beat || beat.ok === false) return beat;
        return { ok: true, beat, local_date: beat.local_date };
    }
    if (kind === 'countdown') return eelCall('get_countdowns');
    if (kind === 'habits') return eelCall('get_habits');
    if (kind === 'reading') return eelCall('get_reading');
    if (kind === 'counters') return eelCall('get_tap_counters');
    if (kind === 'workout') return eelCall('get_today_status');
    if (kind === 'goals') return eelCall('list_goals');
    if (kind === 'day_brief') return eelCall('get_day_brief');
    if (kind === 'analytics') return eelCall('get_analytics', 7);
    if (kind === 'cluny') return eelCall('get_cluny_inbox');
    return null;
}

function renderKey(key, data, size) {
    const { kind, settings } = splitKey(key);
    if (kind === 'work') return (WORK_SLICE_HTML[settings.slice] || workTodayHtml)(data, size);
    if (kind === 'weather') return weatherHtml(data, size);
    if (kind === 'word') return wordHtml(data, size);
    if (kind === 'today_calendar') return todayHtml(data, size);
    if (kind === 'habits') return habitsHtml(data, size);
    if (kind === 'counters') return countersHtml(data, size);
    if (kind === 'countdown') return countdownHtml(data, size);
    if (kind === 'reading') return readingHtml(data, size);
    if (kind === 'workout') return workoutHtml(data, size);
    if (kind === 'goals') return goalsHtml(data, size);
    if (kind === 'day_brief') return dayBriefHtml(data, size);
    if (kind === 'analytics') return analyticsHtml(data, size);
    if (kind === 'cluny') return clunyHtml(data, size);
    return posterHtml(key, data, size);
}

export function mountGlance(key, body, card) {
    if (!body) return;
    body.innerHTML = shellHtml({
        key,
        size: sizeOf(card),
        state: 'loading',
        label: keyLabel(key),
        primary: copy.loading,
    });
}

export function paintGlanceFromData(key, body, card, data) {
    if (!body) return;
    try {
        body.innerHTML = renderKey(key, data, sizeOf(card));
    } catch (err) {
        console.error(err);
        body.innerHTML = emptyShell(key, sizeOf(card), copy.couldNotLoad);
    }
}

export async function paintGlance(key, body, card) {
    if (!body) return;
    const data = await loadGlance(key);
    if (!body.isConnected) return;
    paintGlanceFromData(key, body, card, data);
}

export async function refreshGlances(keys, dataByKey) {
    const set = keys ? new Set(keys) : null;
    const cards = [...document.querySelectorAll('#homeGridAbove .home-widget, #homeGrid .home-widget')];
    await Promise.all(cards.map(async (card) => {
        const key = card.getAttribute('data-key');
        if (set && !set.has(key)) return;
        const body = card.querySelector('.home-widget-body');
        if (!body) return;
        if (dataByKey && Object.prototype.hasOwnProperty.call(dataByKey, key)) {
            paintGlanceFromData(key, body, card, dataByKey[key]);
            return;
        }
        await paintGlance(key, body, card);
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
                detail: { key: btn.getAttribute('data-key') || '' },
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

export async function runGlanceCapture(form) {
    const kind = form?.getAttribute('data-glance-capture');
    const input = form?.querySelector('input');
    const title = (input?.value || '').trim();
    if (!kind || !title) {
        if (!title) utils.showErrorFeedback('Name the task first.');
        return;
    }
    try {
        if (kind === 'todo') {
            const result = await callEel(
                'add_todo_to_calendar',
                title,
                utils.localISODate(),
                '',
                '',
                null,
                '',
            );
            if (input) input.value = '';
            const message = result?.message || 'Dated for today.';
            if (result?.ok === false) utils.showErrorFeedback(message);
            else utils.showSuccessFeedback(message);
        } else {
            return;
        }
        utils.notifyDataChanged();
    } catch (err) {
        console.error(err);
        utils.showErrorFeedback(err?.message || 'Could not add that.');
    }
}
