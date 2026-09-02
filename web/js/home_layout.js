/**
 * Home grid helpers — snap, overlap, allowed sizes.
 * Mutations persist through the Python store; this is for edit-mode preview.
 */

export const GRID_COLUMNS = 4;

export const WIDGET_CATALOG = {
    todo: { label: 'To Do', sizes: [[2, 1], [2, 2], [2, 3], [4, 2], [4, 3], [4, 4]], default: [2, 2], source: 'todoTab' },
    today_calendar: { label: 'Today', sizes: [[1, 1], [2, 1], [2, 2], [2, 3], [4, 2]], default: [2, 2], source: 'todayCalendarSource' },
    workout: { label: 'Workout', sizes: [[2, 1], [2, 2], [2, 3], [4, 2], [4, 3], [4, 4]], default: [2, 2], source: 'workoutTab' },
    goals: { label: 'Goals', sizes: [[2, 1], [2, 2], [2, 3], [4, 2], [4, 3], [4, 4]], default: [2, 2], source: 'goalsTab' },
    allwork: { label: 'All Work', sizes: [[2, 1], [2, 2], [2, 3], [4, 2], [4, 3]], default: [2, 2], source: 'allWorkTab' },
    analytics: { label: 'Analytics', sizes: [[2, 2], [2, 3], [4, 2], [4, 3], [4, 4]], default: [2, 2], source: 'analyticsTab' },
    timeline: { label: 'Timeline', sizes: [[2, 2], [2, 3], [4, 2], [4, 3], [4, 4]], default: [2, 2], source: 'timelineTab' },
    weather: { label: 'Weather', sizes: [[1, 1], [2, 1], [1, 2], [2, 2], [2, 3], [4, 2], [4, 3]], default: [2, 1], source: 'weatherSource' },
    focus: { label: 'Focus', sizes: [[1, 1], [2, 1], [2, 2], [4, 1], [4, 2]], default: [2, 1], source: 'focusSource' },
    countdown: { label: 'Countdown', sizes: [[1, 1], [2, 1], [1, 2], [2, 2], [2, 3], [4, 2]], default: [2, 1], source: 'countdownSource' },
    habits: { label: 'Habits', sizes: [[1, 1], [2, 1], [1, 2], [2, 2], [2, 3], [4, 2]], default: [2, 2], source: 'habitsSource' },
    heatmap: { label: 'Heatmap', sizes: [[2, 1], [4, 1], [2, 2], [4, 2], [4, 3]], default: [4, 1], source: 'heatmapSource' },
    day_brief: { label: 'Day', sizes: [[2, 1], [2, 2], [2, 3], [4, 2], [4, 3], [4, 4]], default: [2, 2], source: 'dayBriefSource' },
    counters: { label: 'Counters', sizes: [[1, 1], [2, 1], [2, 2], [4, 2], [4, 3]], default: [2, 1], source: 'countersSource' },
    reading: { label: 'Reading', sizes: [[1, 1], [2, 1], [2, 2], [2, 3], [4, 2]], default: [2, 1], source: 'readingSource' },
    word: { label: 'Word', sizes: [[1, 1], [2, 1], [1, 2], [2, 2], [2, 3], [4, 2]], default: [1, 1], source: 'wordTab' },
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
    const gap = parseCssPx(styles.columnGap || styles.gap, 12);
    const colW = (rect.width - gap * (GRID_COLUMNS - 1)) / GRID_COLUMNS;
    const rowH = parseCssPx(styles.gridAutoRows, 92);
    const x = Math.max(0, Math.min(GRID_COLUMNS - 1, Math.floor((clientX - rect.left) / (colW + gap))));
    const y = Math.max(0, Math.floor((clientY - rect.top) / (rowH + gap)));
    return { x, y };
}

function parseCssPx(value, fallback) {
    const raw = String(value || '').trim();
    const n = parseFloat(raw);
    if (!Number.isFinite(n) || n <= 0) return fallback;
    if (raw.endsWith('rem')) return n * 16;
    return n;
}

export function canPlace(occupied, widget, x, y, w = widget.w, h = widget.h) {
    const trial = { ...widget, x, y, w, h };
    if (trial.x < 0 || trial.y < 0 || trial.x + trial.w > GRID_COLUMNS) return false;
    if (trial.w < 1 || trial.h < 1) return false;
    return (occupied || []).every((other) => other.id === widget.id || !boxesOverlap(trial, other));
}

export function allowedSizes(kind) {
    return (WIDGET_CATALOG[kind]?.sizes || []).map((size) => [...size]);
}

export function pickResize(kind, widget, wantW, wantH, occupied, axis = 'both') {
    const sizes = allowedSizes(kind);
    if (!sizes.length) return { w: widget.w, h: widget.h };
    const scored = sizes
        .map(([w, h]) => {
            let dist;
            if (axis === 'x') dist = Math.abs(w - wantW) * 4 + Math.abs(h - widget.h);
            else if (axis === 'y') dist = Math.abs(h - wantH) * 4 + Math.abs(w - widget.w);
            else dist = Math.abs(w - wantW) + Math.abs(h - wantH);
            return { w, h, dist, area: w * h };
        })
        .sort((a, b) => a.dist - b.dist || a.area - b.area || a.w - b.w);
    for (const size of scored) {
        if (canPlace(occupied, widget, widget.x, widget.y, size.w, size.h)) {
            return { w: size.w, h: size.h };
        }
    }
    return { w: widget.w, h: widget.h };
}

export function pageById(layout, pageId) {
    return (layout?.pages || []).find((page) => page.id === pageId) || null;
}

export function kindsOnPage(page) {
    return new Set((page?.widgets || []).map((item) => item.kind));
}

export function isFirstHomePage(layout, page) {
    return !!(layout?.pages?.[0] && page && layout.pages[0].id === page.id);
}

export function widgetRegion(widget, firstPage) {
    if (!firstPage) return 'below';
    return widget?.region === 'above' ? 'above' : 'below';
}

export function widgetsInRegion(page, region, firstPage) {
    return (page?.widgets || []).filter((item) => widgetRegion(item, firstPage) === region);
}
