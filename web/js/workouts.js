/**
 * Workout tab — body weight and sessions for the day.
 */

import * as utils from './utils.js';

const KINDS = [
    { value: 'running', label: 'Running' },
    { value: 'legs', label: 'Leg day' },
    { value: 'push', label: 'Push day' },
    { value: 'pull', label: 'Pull day' },
    { value: 'other', label: 'Other' },
];

function selectedKind() {
    return document.getElementById('workoutKind')?.value || 'running';
}

function syncKindFields() {
    const kind = selectedKind();
    document.getElementById('workoutMilesWrap')?.classList.toggle('is-hidden', kind !== 'running' && kind !== 'other');
    document.getElementById('workoutOtherWrap')?.classList.toggle('is-hidden', kind !== 'other');
}

function sessionLine(session) {
    const bits = [session.label || session.kind_label];
    if (session.miles != null) bits.push(`${session.miles} mi`);
    if (session.minutes != null) bits.push(`${session.minutes} min`);
    return `
        <article class="work-item" data-id="${utils.escapeHtml(session.id)}">
            <div class="work-item-main">
                <h3>${utils.escapeHtml(bits[0])}</h3>
                <p class="work-meta">${utils.escapeHtml(bits.slice(1).join(' · ') || 'Logged')}</p>
            </div>
            <div class="work-item-actions">
                <button type="button" class="btn-ghost" data-act="delete">Delete</button>
            </div>
        </article>
    `;
}

export async function refreshWorkouts() {
    const list = document.getElementById('workoutSessionList');
    const recent = document.getElementById('workoutRecent');
    const summary = document.getElementById('workoutSummary');
    if (!list) return;
    const day = utils.localISODate();
    try {
        const data = await eel.get_workout_day(day)();
        const weight = document.getElementById('workoutWeight');
        if (weight && data.body_weight != null && document.activeElement !== weight) {
            weight.value = String(data.body_weight);
        }
        if (summary) {
            summary.textContent = data.done
                ? `${data.session_count} session${data.session_count === 1 ? '' : 's'}${data.miles ? ` · ${data.miles} mi` : ''}`
                : 'No session logged today';
        }
        if (!data.sessions.length) {
            list.innerHTML = `
                <div class="empty-state">
                    <h3>No workout yet today</h3>
                    <p>Log a run, lift day, or something else like pickleball.</p>
                </div>`;
        } else {
            list.innerHTML = data.sessions.map(sessionLine).join('');
            list.querySelectorAll('[data-act="delete"]').forEach((btn) => {
                btn.addEventListener('click', async () => {
                    const id = btn.closest('.work-item')?.getAttribute('data-id');
                    if (!id) return;
                    await eel.delete_workout_session(id)();
                    utils.notifyDataChanged();
                    await refreshWorkouts();
                });
            });
        }
        const days = await eel.list_recent_workout_days(10)();
        if (recent) {
            const others = (days || []).filter((row) => row.local_date !== day);
            recent.innerHTML = others.length
                ? others
                      .map((row) => {
                          const labels = (row.sessions || []).map((s) => s.label).join(', ') || 'Weight only';
                          return `<li><strong>${utils.escapeHtml(row.local_date)}</strong> · ${utils.escapeHtml(labels)}</li>`;
                      })
                      .join('')
                : '<p class="checklist-empty">No earlier days yet.</p>';
        }
    } catch (e) {
        console.error(e);
        list.innerHTML = '<p class="checklist-error">Could not load workouts.</p>';
    }
}

async function saveWeight() {
    const raw = document.getElementById('workoutWeight')?.value;
    try {
        await eel.save_body_weight(utils.localISODate(), raw === '' ? null : raw, '')();
        utils.showSuccessFeedback('Weight saved.');
        utils.notifyDataChanged();
        await refreshWorkouts();
    } catch (e) {
        utils.showErrorFeedback('Could not save weight.');
    }
}

async function addSession() {
    const kind = selectedKind();
    const other = document.getElementById('workoutOtherLabel')?.value || '';
    const miles = document.getElementById('workoutMiles')?.value;
    const minutes = document.getElementById('workoutMinutes')?.value;
    try {
        await eel.add_workout_session(
            utils.localISODate(),
            kind,
            other,
            miles === '' ? null : miles,
            minutes === '' ? null : minutes,
        )();
        const otherInput = document.getElementById('workoutOtherLabel');
        const milesInput = document.getElementById('workoutMiles');
        const minutesInput = document.getElementById('workoutMinutes');
        if (otherInput) otherInput.value = '';
        if (milesInput) milesInput.value = '';
        if (minutesInput) minutesInput.value = '';
        utils.showSuccessFeedback('Session logged.');
        utils.notifyDataChanged();
        await refreshWorkouts();
    } catch (e) {
        utils.showErrorFeedback(e?.message || e || 'Could not log that session.');
    }
}

const WEEKDAYS = [
    { value: '0', label: 'Mon' },
    { value: '1', label: 'Tue' },
    { value: '2', label: 'Wed' },
    { value: '3', label: 'Thu' },
    { value: '4', label: 'Fri' },
    { value: '5', label: 'Sat' },
    { value: '6', label: 'Sun' },
];

const LIFT_OPTIONS = [
    { value: '', label: '—' },
    { value: 'push', label: 'Push' },
    { value: 'pull', label: 'Pull' },
    { value: 'legs', label: 'Legs' },
];

function readTemplateForm() {
    const lifts = {};
    WEEKDAYS.forEach((day) => {
        const select = document.getElementById(`weekLift-${day.value}`);
        const kind = select?.value || '';
        if (kind) lifts[day.value] = kind;
    });
    const everyOther = document.getElementById('weekRunEveryOther')?.checked;
    return {
        lifts,
        running: {
            enabled: !!everyOther,
            mode: 'interval',
            every_days: 2,
            anchor: '2020-01-06',
            weekdays: [],
        },
    };
}

function renderWeekTemplate(plan) {
    const form = document.getElementById('weekTemplateForm');
    if (!form) return;
    const lifts = plan?.lifts || {};
    const running = plan?.running || {};
    const rows = WEEKDAYS.map((day) => {
        const current = lifts[day.value] || lifts[Number(day.value)] || '';
        const options = LIFT_OPTIONS.map(
            (opt) =>
                `<option value="${opt.value}"${opt.value === current ? ' selected' : ''}>${opt.label}</option>`,
        ).join('');
        return `
            <label class="week-template-row">
                <span>${day.label}</span>
                <select id="weekLift-${day.value}" class="checklist-select">${options}</select>
            </label>`;
    }).join('');
    const everyOther = running.enabled !== false && (running.mode || 'interval') === 'interval';
    form.innerHTML = `
        ${rows}
        <label class="week-template-run">
            <input type="checkbox" id="weekRunEveryOther"${everyOther ? ' checked' : ''}>
            Run every other day
        </label>
    `;
}

async function loadWeekTemplate() {
    const form = document.getElementById('weekTemplateForm');
    if (!form) return;
    try {
        const plan = await eel.get_week_template()();
        renderWeekTemplate(plan);
    } catch (e) {
        console.error(e);
        renderWeekTemplate({ lifts: { 0: 'push', 2: 'pull', 4: 'legs' }, running: { enabled: true } });
    }
}

async function saveWeekTemplate() {
    try {
        await eel.save_week_template(readTemplateForm())();
        utils.showSuccessFeedback('Week template saved.');
        utils.notifyDataChanged();
    } catch (e) {
        utils.showErrorFeedback('Could not save the week template.');
    }
}

export function setupWorkouts() {
    const kind = document.getElementById('workoutKind');
    if (kind && !kind.dataset.ready) {
        kind.dataset.ready = '1';
        kind.innerHTML = KINDS.map((item) => `<option value="${item.value}">${item.label}</option>`).join('');
        kind.addEventListener('change', syncKindFields);
        syncKindFields();
    }
    document.getElementById('workoutWeightSave')?.addEventListener('click', () => {
        void saveWeight();
    });
    document.getElementById('workoutAddBtn')?.addEventListener('click', () => {
        void addSession();
    });
    document.getElementById('weekTemplateSave')?.addEventListener('click', () => {
        void saveWeekTemplate();
    });
    document.addEventListener('kosistenz:data-changed', () => {
        if (document.getElementById('workoutTab')?.classList.contains('active')) {
            void refreshWorkouts();
        }
    });
}

export async function onWorkoutTabShown() {
    syncKindFields();
    await Promise.all([refreshWorkouts(), loadWeekTemplate()]);
}
