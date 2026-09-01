/**
 * Home grid helpers — snap, overlap, allowed sizes.
 * Mutations persist through the Python store; this is for edit-mode preview.
 */

export const GRID_COLUMNS = 4;

export const WIDGET_CATALOG = {
    todo: { label: 'To Do', sizes: [[2, 2], [2, 3], [4, 2], [4, 4]], default: [2, 3], source: 'todoTab' },
    today_calendar: { label: 'Today', sizes: [[2, 2], [2, 3], [4, 2]], default: [2, 2], source: 'todayCalendarSource' },
    workout: { label: 'Workout', sizes: [[2, 2], [2, 3], [4, 3], [4, 4]], default: [2, 2], source: 'workoutTab' },
    journal: { label: 'Journal', sizes: [[2, 2], [4, 2], [4, 4]], default: [2, 2], source: 'journalTab' },
    goals: { label: 'Goals', sizes: [[2, 2], [4, 3], [4, 4]], default: [4, 3], source: 'goalsTab' },
    allwork: { label: 'All Work', sizes: [[2, 2], [2, 3], [4, 2]], default: [2, 2], source: 'allWorkTab' },
    analytics: { label: 'Analytics', sizes: [[4, 3], [4, 4]], default: [4, 3], source: 'analyticsTab' },
    timeline: { label: 'Timeline', sizes: [[4, 2], [4, 3], [4, 4]], default: [4, 3], source: 'timelineTab' },
    weather: { label: 'Weather', sizes: [[2, 2], [2, 3], [4, 2], [4, 3]], default: [2, 3], source: 'weatherSource' },
    focus: { label: 'Focus', sizes: [[2, 2], [4, 2]], default: [2, 2], source: 'focusSource' },
    countdown: { label: 'Countdown', sizes: [[2, 2], [2, 3], [4, 2]], default: [2, 2], source: 'countdownSource' },
    habits: { label: 'Habits', sizes: [[2, 2], [2, 3], [4, 2]], default: [2, 3], source: 'habitsSource' },
    heatmap: { label: 'Heatmap', sizes: [[4, 2], [4, 3]], default: [4, 2], source: 'heatmapSource' },
    day_brief: { label: 'Day', sizes: [[2, 3], [4, 3], [4, 4]], default: [2, 3], source: 'dayBriefSource' },
    counters: { label: 'Counters', sizes: [[2, 2], [2, 3], [4, 2], [4, 3]], default: [2, 2], source: 'countersSource' },
    reading: { label: 'Reading', sizes: [[2, 2], [2, 3], [4, 2]], default: [2, 2], source: 'readingSource' },
};

export function catalogList() {
    return Object.entries(WIDGET_CATALOG).map(([kind, spec]) => ({ kind, ...spec }));
}

export function boxesOverlap(a, b) {
    return !(
        a.x + a.w <= b.x
        || b.x + b.w <= a.x
        || a.y + a.h <= b.y
        || b.y + b.h <= a.y
    );
}

export function firstFit(occupied, w, h, ignoreId) {
    const others = (occupied || []).filter((box) => box.id !== ignoreId);
    for (let y = 0; y < 32; y += 1) {
        for (let x = 0; x <= GRID_COLUMNS - w; x += 1) {
            const trial = { x, y, w, h };
            if (others.every((other) => !boxesOverlap(trial, other))) {
                return { x, y };
            }
        }
    }
    return null;
}

export function snapCell(clientX, clientY, gridEl) {
    if (!gridEl) return { x: 0, y: 0 };
    const rect = gridEl.getBoundingClientRect();
    const styles = window.getComputedStyle(gridEl);
    const gap = parseFloat(styles.columnGap || styles.gap || '12') || 12;
    const colW = (rect.width - gap * (GRID_COLUMNS - 1)) / GRID_COLUMNS;
    const rowH = parseFloat(styles.gridAutoRows) || 136;
    const x = Math.max(0, Math.min(GRID_COLUMNS - 1, Math.floor((clientX - rect.left) / (colW + gap))));
    const y = Math.max(0, Math.floor((clientY - rect.top) / (rowH + gap)));
    return { x, y };
}

export function canPlace(occupied, widget, x, y) {
    const trial = { ...widget, x, y };
    if (trial.x < 0 || trial.y < 0 || trial.x + trial.w > GRID_COLUMNS) return false;
    return (occupied || []).every((other) => other.id === widget.id || !boxesOverlap(trial, other));
}

export function pageById(layout, pageId) {
    return (layout?.pages || []).find((page) => page.id === pageId) || null;
}

export function kindsOnPage(page) {
    return new Set((page?.widgets || []).map((item) => item.kind));
}
