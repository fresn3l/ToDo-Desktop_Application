/**
 * Home glance microcopy. Edit strings here, not inline in tile HTML.
 */

export const copy = {
    openSettings: 'Open Settings',
    open: 'Open',
    setPlace: 'Set a place',
    addPlace: 'Add a place',
    add: 'Add',
    start: 'Start',
    finish: 'Finish',
    kept: 'Kept',
    tick: 'Tick',
    whatsOn: 'What’s on today?',
    freeTime: 'Free time',
    noEvents: 'No events today.',
    nothingDated: 'Nothing dated yet.',
    allFinished: 'All finished.',
    noHabits: 'No habits yet.',
    noCounters: 'No counters yet.',
    noFocus: 'No focus yet.',
    noDates: 'No dates yet.',
    noBook: 'No book yet.',
    noGoals: 'No goals yet.',
    backlogClear: 'Nothing unscheduled.',
    noActivity: 'No activity yet.',
    noStreak: 'No streak yet.',
    nothingLogged: 'Nothing logged.',
    noForecast: 'No forecast yet.',
    couldNotLoad: 'Could not load.',
    noWord: 'No word yet.',
    clunyOff: 'Journal and timer still available.',
    unscheduled: 'unscheduled',
    usedTonight: 'Used tonight.',
    heldToday: 'Held for today.',
    loading: 'Loading…',
};

export function eventsToday(n) {
    const count = Number(n) || 0;
    if (count <= 0) return copy.noEvents;
    if (count === 1) return '1 event today.';
    return `${count} events today.`;
}

export function moreCount(n) {
    const count = Number(n) || 0;
    if (count <= 0) return '';
    return `+${count} more`;
}

export function countLabel(base, n) {
    if (n == null || n === '') return base;
    return `${base} · ${n}`;
}

export function waitingLine(n) {
    const count = Number(n) || 0;
    if (count === 1) return '1 unscheduled';
    return `${count} unscheduled`;
}
