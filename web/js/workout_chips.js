/**
 * One-tap workout session chips — shared by Today and the Workout tab.
 */

import * as utils from './utils.js';

export const CHIP_KINDS = [
    { value: 'push', label: 'Push' },
    { value: 'pull', label: 'Pull' },
    { value: 'legs', label: 'Legs' },
    { value: 'running', label: 'Run' },
    { value: 'other', label: 'Other' },
];

export function renderWorkoutChips(container, { expected = [], logged = [] } = {}) {
    if (!container) return;
    const expectedSet = new Set(expected);
    const loggedSet = new Set(logged);
    container.innerHTML = CHIP_KINDS.map((kind) => {
        const due = expectedSet.has(kind.value);
        const done = loggedSet.has(kind.value);
        const classes = ['workout-chip', due ? 'is-expected' : '', done ? 'is-logged' : '']
            .filter(Boolean)
            .join(' ');
        const hint = done ? 'Logged' : due ? 'Expected today' : '';
        return `<button type="button" class="${classes}" data-kind="${kind.value}" title="${hint}">
            ${kind.label}${done ? ' ✓' : ''}
        </button>`;
    }).join('');
}

export async function logWorkoutKind(kind, extras = {}) {
    const day = utils.localISODate();
    const miles = extras.miles === '' || extras.miles == null ? null : extras.miles;
    const minutes = extras.minutes === '' || extras.minutes == null ? null : extras.minutes;
    const other = extras.other_label || extras.other || '';
    if (kind === 'running' && miles == null) {
        throw new Error('Add miles for a run');
    }
    if (kind === 'other' && !String(other).trim()) {
        throw new Error('Name the other activity');
    }
    await eel.add_workout_session(day, kind, other, miles, minutes)();
    utils.notifyDataChanged();
}
