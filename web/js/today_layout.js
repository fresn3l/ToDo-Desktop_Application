/**
 * Today dashboard layout — module order and board placement.
 */

export const TODAY_MODULES = [
    { id: 'todo', label: 'To Do' },
    { id: 'workout', label: 'Workout' },
    { id: 'journal', label: 'Journal' },
];

const IDS = TODAY_MODULES.map((m) => m.id);

export function parseTodayOrder(raw) {
    const parts = String(raw || '')
        .split(',')
        .map((s) => s.trim())
        .filter((id) => IDS.includes(id));
    const order = [];
    parts.forEach((id) => {
        if (!order.includes(id)) order.push(id);
    });
    IDS.forEach((id) => {
        if (!order.includes(id)) order.push(id);
    });
    return order;
}

export function applyTodayOrder(raw) {
    parseTodayOrder(raw).forEach((id, index) => {
        const el = document.querySelector(`.today-card[data-module="${id}"]`);
        if (el) el.style.order = String(index);
    });
}

export function moveTodayModule(order, moduleId, direction) {
    const next = parseTodayOrder(order);
    const i = next.indexOf(moduleId);
    if (i < 0) return next;
    const j = direction === 'up' ? i - 1 : i + 1;
    if (j < 0 || j >= next.length) return next;
    const swap = next[i];
    next[i] = next[j];
    next[j] = swap;
    return next;
}

export function renderTodayOrderList(listEl, raw) {
    if (!listEl) return;
    const order = parseTodayOrder(raw);
    listEl.innerHTML = order
        .map((id, index) => {
            const label = TODAY_MODULES.find((m) => m.id === id)?.label || id;
            const upOff = index === 0 ? ' disabled' : '';
            const downOff = index === order.length - 1 ? ' disabled' : '';
            return `<li class="today-order-row" data-module="${id}">
                <span>${label}</span>
                <span class="today-order-moves">
                    <button type="button" class="btn-ghost today-order-btn" data-move="up"${upOff} aria-label="Move ${label} up">Up</button>
                    <button type="button" class="btn-ghost today-order-btn" data-move="down"${downOff} aria-label="Move ${label} down">Down</button>
                </span>
            </li>`;
        })
        .join('');
}
