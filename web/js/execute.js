/**
 * Home go circuit — Execute, Aim, Close.
 */

import * as utils from './utils.js';
import { callEel } from './lazy.js';

let state = null;
let bound = false;
let tickTimer = 0;

const DIFFICULTY_LABELS = {
    too_easy: 'Too easy',
    about_right: 'About right',
    too_hard: 'Too hard',
};

export function setupExecute() {
    if (bound) return;
    const board = document.getElementById('executeBoard');
    if (!board) return;
    bound = true;
    board.addEventListener('click', (event) => {
        const btn = event.target.closest('button[data-act]');
        if (!btn) return;
        event.preventDefault();
        void handleAction(btn);
    });
    board.addEventListener('submit', (event) => {
        const form = event.target.closest('form[data-form]');
        if (!form) return;
        event.preventDefault();
        void handleForm(form);
    });
    board.addEventListener('change', (event) => {
        const habit = event.target.closest('input[data-habit]');
        if (habit) {
            void run('toggle_execute_habit', habit.getAttribute('data-habit') || '');
            return;
        }
        const pin = event.target.closest('select[data-pin]');
        if (pin) void run('pin_execute_priority', pin.value || '');
    });
}

export async function loadExecute() {
    try {
        paintExecute(await callEel('get_execute_home'));
    } catch (err) {
        utils.showErrorFeedback(err?.message || 'Could not load Home.');
    }
}

export function paintExecute(data) {
    if (!data || data.ok === false || !data.phase) return;
    state = data;
    const phase = data.phase;
    const phaseEl = document.getElementById('executePhase');
    if (phaseEl) phaseEl.textContent = phase.label || 'Hard window';
    document.getElementById('executeBoard')?.setAttribute('data-phase', phase.name || 'hard');
    paintThing(data);
    paintBout(data);
    paintAim(data);
    paintHabits(data);
    paintClose(data);
    armTick(data);
}

function paintThing(data) {
    const thing = data.one_thing || {};
    const title = document.getElementById('executeThing');
    const meta = document.getElementById('executeThingMeta');
    if (title) title.textContent = thing.title || 'Name the hard thing';
    if (!meta) return;
    const bits = [];
    if (thing.kind === 'clock') bits.push(thing.when === 'now' ? 'On the clock now' : 'Next on the clock');
    if (thing.kind === 'intention') bits.push('Your line for today');
    if (thing.kind === 'todo') bits.push(data.priority_id === thing.id ? 'Pinned To Do' : 'First open To Do');
    if (data.bouts_done) bits.push(`${data.bouts_done} bout${data.bouts_done === 1 ? '' : 's'} today`);
    meta.textContent = bits.join(' · ');
}

function remainingLabel(seconds) {
    const n = Math.max(0, Number(seconds) || 0);
    const m = Math.floor(n / 60);
    const s = n % 60;
    if (m <= 0) return `${s}s`;
    return `${m}:${String(s).padStart(2, '0')}`;
}

function timerText(status, seconds) {
    if (status === 'target') return `Look at the work. ${remainingLabel(seconds)}`;
    if (status === 'defocus') return `Defocus ${remainingLabel(seconds)}`;
    return `${remainingLabel(seconds)} left`;
}

function startButtons(bout) {
    return (bout.options || [45, 70, 90]).map((mins) => (
        `<button type="button" class="btn-ghost execute-length" data-act="start" data-minutes="${mins}">${mins} min</button>`
    )).join('');
}

function paintBout(data) {
    const host = document.getElementById('executeBout');
    if (!host) return;
    const bout = data.bout || {};
    const status = bout.status || 'idle';
    const todos = (data.todos || []).filter((row) => row.open);
    const pin = data.priority_id || '';
    const pinOpts = ['<option value="">Your line, then the clock</option>']
        .concat(todos.map((row) => {
            const sel = row.id === pin ? ' selected' : '';
            return `<option value="${utils.escapeHtml(row.id)}"${sel}>${utils.escapeHtml(row.title)}</option>`;
        }))
        .join('');

    let body = '';
    if (status === 'target' || status === 'work' || status === 'defocus') {
        const timer = `<p id="executeTimer" class="execute-timer">${timerText(status, bout.remaining_seconds)}</p>`;
        if (status === 'target') {
            body = `${timer}
                <div class="execute-inline"><button type="button" class="btn-ghost" data-act="skip-visual">Skip and start</button></div>`;
        } else if (status === 'work') {
            body = `${timer}
                <div class="execute-inline">
                    <button type="button" class="btn-primary" data-act="happened">Happened</button>
                    <button type="button" class="btn-ghost" data-act="still-open">Still open</button>
                </div>
                <input type="text" id="executeResume" class="checklist-text-input" placeholder="If still open: where you pick up next" value="${utils.escapeHtml(bout.resume || '')}">`;
        } else {
            body = `${timer}
                <p class="execute-meta">Look away from the work. Walk, sky, nothing useful.</p>
                <div class="execute-inline"><button type="button" class="btn-ghost" data-act="finish-defocus">Done defocusing</button></div>`;
        }
    } else if (status === 'review') {
        body = `
            <p class="execute-meta">Time. Did it happen?</p>
            <div class="execute-inline">
                <button type="button" class="btn-primary" data-act="happened">Happened</button>
                <button type="button" class="btn-ghost" data-act="still-open">Still open</button>
            </div>
            <input type="text" id="executeResume" class="checklist-text-input" placeholder="If still open: where you pick up next" value="${utils.escapeHtml(bout.resume || '')}">`;
    } else {
        let lead = '45, 70, or 90 minutes. Then a real break.';
        if (status === 'done' && bout.coin === 'heads') lead = 'Coin came up heads. Take a small reward if you want one.';
        else if (status === 'done' && bout.coin === 'tails') lead = 'Coin came up tails. The work was the reward.';
        else if (status === 'done' && bout.happened === false) lead = 'Still open. Your pick-up line is saved as today’s line.';
        body = `
            <p class="execute-meta">${lead}</p>
            <div class="execute-inline">${startButtons(bout)}</div>
            <div class="execute-fields">
                <label class="checklist-field-label" for="executePin">Today’s priority</label>
                <select id="executePin" class="checklist-text-input" data-pin>${pinOpts}</select>
                <label class="checklist-field-label" for="executeFirst">Or say it in one line</label>
                <form data-form="first" class="execute-form execute-form--row">
                    <input type="text" id="executeFirst" name="first" class="checklist-text-input" placeholder="After coffee, 70 minutes on the board memo" value="${utils.escapeHtml(data.first_bout || '')}">
                    <button type="submit" class="btn-ghost">Save</button>
                </form>
            </div>`;
    }

    const suck = `
        <form data-form="suck" class="execute-suck execute-form execute-form--row">
            <input type="text" name="suck" class="checklist-text-input" placeholder="One optional hard extra, like no phone until noon" value="${utils.escapeHtml(data.micro_suck || '')}" aria-label="One optional hard extra">
            <button type="submit" class="btn-ghost">Save</button>
            ${data.micro_suck ? `<button type="button" class="btn-ghost${data.micro_suck_done ? ' is-selected' : ''}" data-act="toggle-suck">${data.micro_suck_done ? 'Done' : 'Did it'}</button>` : ''}
        </form>`;
    host.innerHTML = body + suck;
}

function paintAim(data) {
    const host = document.getElementById('executeAim');
    if (!host) return;
    const aim = data.aim || {};
    if (!aim.set) {
        host.innerHTML = `
            <p class="execute-meta">One priority for the next 12 weeks, measured in minutes per week.</p>
            <form data-form="aim" class="execute-form">
                <input type="text" name="title" class="checklist-text-input" placeholder="Ship the board memo series" required>
                <input type="number" name="weekly" class="checklist-text-input" min="30" step="30" placeholder="Minutes per week" required>
                <button type="submit" class="btn-primary">Set the aim</button>
            </form>`;
        return;
    }
    const pct = aim.weekly_minutes ? Math.min(100, Math.round((aim.spent_minutes / aim.weekly_minutes) * 100)) : 0;
    const ask = aim.ask_difficulty
        ? `<p class="execute-meta">How was last week?</p>
           <div class="execute-inline">${Object.entries(DIFFICULTY_LABELS).map(([level, label]) => (
                `<button type="button" class="btn-ghost${aim.difficulty === level ? ' is-selected' : ''}" data-act="difficulty" data-level="${level}">${label}</button>`
            )).join('')}</div>`
        : '';
    host.innerHTML = `
        <p class="execute-aim-title">${utils.escapeHtml(aim.title)}</p>
        <p class="execute-meta">${aim.spent_minutes} of ${aim.weekly_minutes} min this week · ${aim.remaining_weeks} weeks left</p>
        <div class="goal-progress-track" role="progressbar" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100">
            <div class="goal-progress-fill" style="width:${pct}%"></div>
        </div>
        ${ask}`;
}

function paintHabits(data) {
    const host = document.getElementById('executeHabits');
    const meta = document.getElementById('executeHabitsMeta');
    const packed = data.habits || {};
    if (meta) {
        const mode = packed.mode === 'test' ? 'Test window, no new habits' : '21-day block';
        const score = packed.total ? `${packed.done} of ${packed.total} today` : 'None yet';
        meta.textContent = `${mode} · ${score}${packed.success ? ' · enough for today' : ''}`;
    }
    if (!host) return;
    const phase = data.phase?.name || 'hard';
    const rows = packed.habits || [];
    const list = rows.map((row) => {
        const side = row.bucket === 'easy' ? 'easy' : 'hard';
        const offPhase = phase === 'wind_down' || (phase === 'hard' && side === 'easy') || (phase === 'easy' && side === 'hard');
        return `<li class="execute-habit${offPhase ? ' is-off-phase' : ''}">
            <label class="checklist-checkbox-label">
                <input type="checkbox" data-habit="${utils.escapeHtml(row.id)}"${row.done ? ' checked' : ''}>
                <span>${utils.escapeHtml(row.title)}</span>
            </label>
            <button type="button" class="btn-ghost execute-bucket" data-act="bucket" data-id="${utils.escapeHtml(row.id)}" data-bucket="${side === 'hard' ? 'easy' : 'hard'}" title="Switch to ${side === 'hard' ? 'easy' : 'hard'} window">${side === 'hard' ? 'Hard' : 'Easy'}</button>
            ${packed.can_add ? `<button type="button" class="btn-ghost execute-remove" data-act="remove-habit" data-id="${utils.escapeHtml(row.id)}" aria-label="Remove ${utils.escapeHtml(row.title)}">Remove</button>` : ''}
        </li>`;
    }).join('');
    let add = '';
    if (packed.can_add && rows.length < (packed.cap || 6)) {
        add = `<form data-form="habit" class="execute-form execute-form--row">
                <input type="text" name="title" class="checklist-text-input" placeholder="Add a habit" required>
                <select name="bucket" class="checklist-text-input" aria-label="Window">
                    <option value="hard">Hard window</option>
                    <option value="easy">Easy window</option>
                </select>
                <button type="submit" class="btn-ghost">Add</button>
           </form>`;
    } else if (!packed.can_add) {
        add = '<p class="execute-meta">Test window. See which ones hold without effort.</p>';
    }
    const empty = '<p class="checklist-empty">Four to six habits. Doing four counts as a good day.</p>';
    host.innerHTML = `${rows.length ? `<ul class="execute-habit-list">${list}</ul>` : empty}${add}`;
}

function paintClose(data) {
    const block = document.getElementById('executeCloseBlock');
    const host = document.getElementById('executeClose');
    const show = Boolean(data.phase?.close) || Boolean(data.closed);
    block?.classList.toggle('is-hidden', !show);
    if (!host || !show) return;
    const leftovers = data.leftovers || [];
    const rows = leftovers.map((row) => `
        <li>
            <span>${utils.escapeHtml(row.title)}</span>
            <span class="execute-inline">
                <button type="button" class="btn-ghost" data-act="park" data-id="${utils.escapeHtml(row.id)}">Park</button>
                <button type="button" class="btn-ghost" data-act="tomorrow" data-id="${utils.escapeHtml(row.id)}">Tomorrow</button>
            </span>
        </li>`).join('');
    host.innerHTML = `
        <p class="execute-meta">What you meant to do, what happened, one lesson. Then name tomorrow’s first bout.</p>
        <form data-form="close" class="execute-form">
            <textarea name="recap" class="checklist-textarea" rows="3" placeholder="Planned vs happened. One lesson.">${utils.escapeHtml(data.close_recap || '')}</textarea>
            <input type="text" name="tomorrow" class="checklist-text-input" placeholder="Tomorrow: after coffee, 70 minutes on…" value="${utils.escapeHtml(data.tomorrow_bout || '')}">
            <button type="submit" class="btn-primary">${data.closed ? 'Update close' : 'Close the day'}</button>
        </form>
        ${leftovers.length ? `<ul class="execute-leftovers">${rows}</ul>` : '<p class="checklist-empty">Nothing left open on Today.</p>'}`;
}

function armTick(data) {
    window.clearInterval(tickTimer);
    const status = data?.bout?.status;
    if (status !== 'target' && status !== 'work' && status !== 'defocus') return;
    const endsAt = Date.now() + Math.max(0, Number(data.bout.remaining_seconds) || 0) * 1000;
    tickTimer = window.setInterval(() => {
        const left = Math.max(0, Math.round((endsAt - Date.now()) / 1000));
        const timer = document.getElementById('executeTimer');
        if (timer) timer.textContent = timerText(status, left);
        if (left <= 0) {
            window.clearInterval(tickTimer);
            void loadExecute();
        }
    }, 1000);
}

async function run(name, ...args) {
    try {
        paintExecute(await callEel(name, ...args));
        utils.notifyDataChanged('execute');
    } catch (err) {
        utils.showErrorFeedback(err?.message || 'Could not save that.');
        void loadExecute();
    }
}

function tomorrowIso() {
    const day = new Date();
    day.setDate(day.getDate() + 1);
    return `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, '0')}-${String(day.getDate()).padStart(2, '0')}`;
}

function closeDraft() {
    const form = document.querySelector('#executeClose form[data-form="close"]');
    return {
        recap: form?.elements.recap?.value ?? state?.close_recap ?? '',
        tomorrow: form?.elements.tomorrow?.value ?? state?.tomorrow_bout ?? '',
    };
}

async function handleAction(btn) {
    const act = btn.getAttribute('data-act');
    const id = btn.getAttribute('data-id') || '';
    const resume = () => document.getElementById('executeResume')?.value || '';
    if (act === 'start') await run('start_execute_bout', Number(btn.getAttribute('data-minutes') || 70), true);
    else if (act === 'skip-visual') await run('skip_execute_visual');
    else if (act === 'happened') await run('set_execute_outcome', true, resume());
    else if (act === 'still-open') await run('set_execute_outcome', false, resume());
    else if (act === 'finish-defocus') await run('finish_execute_defocus');
    else if (act === 'toggle-suck') await run('toggle_micro_suck');
    else if (act === 'difficulty') await run('set_aim_difficulty', btn.getAttribute('data-level') || '');
    else if (act === 'bucket') await run('set_habit_bucket', id, btn.getAttribute('data-bucket') || 'hard');
    else if (act === 'remove-habit') await run('remove_execute_habit', id);
    else if (act === 'park' || act === 'tomorrow') {
        const draft = closeDraft();
        const parks = act === 'park' ? [id] : [];
        const dates = act === 'tomorrow' ? { [id]: tomorrowIso() } : {};
        await run('close_execute_day', draft.recap, draft.tomorrow, parks, dates);
    }
}

async function handleForm(form) {
    const kind = form.getAttribute('data-form');
    const body = new FormData(form);
    const text = (name) => String(body.get(name) || '');
    if (kind === 'first') await run('save_first_bout', text('first'));
    else if (kind === 'suck') await run('save_micro_suck', text('suck'));
    else if (kind === 'aim') await run('save_execute_aim', text('title'), Number(body.get('weekly') || 0));
    else if (kind === 'habit') await run('add_execute_habit', text('title'), text('bucket') || 'hard');
    else if (kind === 'close') await run('close_execute_day', text('recap'), text('tomorrow'), [], {});
}
