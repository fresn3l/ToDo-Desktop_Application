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
    eveningAsk: 'What still matters tonight?',
    noEvents: 'Clear clock.',
    nothingDated: 'Nothing for today.',
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
    clunyOff: 'Off', // Glance Cluny is the health line when the brain is down
    noBrief: 'No brief yet',
    writeIntention: 'Write an intention',
    writeRecap: 'Write a recap',
    unscheduled: 'unscheduled',
    done: 'Done',
    plus15: '+15',
    park: 'Park',
    skip: 'Skip',
    doToday: 'Do today',
    logWorkout: 'Log',
    now: 'Now',
    next: 'Next',
    gap: 'Gap',
    clearClock: 'Clear clock.',
    nothingDue: 'Nothing due this week.',
    allPlaced: 'Nothing to place.',
    addLine: 'Add a line',
    zeroMinutes: '0 min this week',
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

export function minutesLabel(n) {
    const mins = Math.max(0, Number(n) || 0);
    if (mins < 60) return `${mins} min`;
    const hours = Math.floor(mins / 60);
    const rem = mins % 60;
    if (!rem) return hours === 1 ? '1 hr' : `${hours} hr`;
    return `${hours}h ${rem}m`;
}

export function waitingLine(n) {
    const count = Number(n) || 0;
    if (count === 1) return '1 unscheduled';
    return `${count} unscheduled`;
}
