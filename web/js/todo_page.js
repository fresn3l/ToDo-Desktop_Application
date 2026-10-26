/**
 * To Do tab — one tall list. Today stays on the Today tab.
 * Sometime this week has no weekday. After that Monday it waits in Review.
 */

import * as utils from './utils.js';
import { callEel } from './lazy.js';

let bound = false;
let page = null;
let review = false;
let dragId = '';

const GROUPS = [
    { id: 'this_week', bucket: 'week', title: 'This week' },
    { id: 'later', bucket: 'later', title: 'Later' },
    { id: 'no_day', bucket: 'none', title: 'No day' },
];

export function setupTodoPage() {
    if (bound) return;
    bound = true;
    document.getElementById('todoReviewBtn')?.addEventListener('click', () => {
        review = !review;
        paint();
    });
    document.getElementById('todoPageWeek')?.addEventListener('click', () => {
        void add('week');
    });
    document.getElementById('todoPageToday')?.addEventListener('click', () => {
        void add('today');
    });
    document.getElementById('todoPagePark')?.addEventListener('click', () => {
        void add('none');
    });
    document.getElementById('todoPageTitle')?.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            void add('week');
        }
    });
    const tile = document.getElementById('todoPageTile');
    tile?.addEventListener('click', (event) => {
        const btn = event.target.closest('button[data-act]');
        if (!btn || !tile.contains(btn)) return;
        event.preventDefault();
        void onAct(btn);
    });
    tile?.addEventListener('dragstart', (event) => {
        const handle = event.target.closest?.('.todo-row-copy');
        if (!handle) return;
        dragId = handle.getAttribute('data-id') || '';
        event.dataTransfer?.setData('text/plain', dragId);
        if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move';
    });
    tile?.addEventListener('dragover', (event) => {
        if (!dragId || !event.target.closest?.('[data-drop]')) return;
        event.preventDefault();
        tile.querySelectorAll('.is-drop').forEach((el) => el.classList.remove('is-drop'));
        event.target.closest('[data-drop]')?.classList.add('is-drop');
    });
    tile?.addEventListener('dragleave', (event) => {
        event.target.closest?.('[data-drop]')?.classList.remove('is-drop');
    });
    tile?.addEventListener('drop', (event) => {
        const zone = event.target.closest?.('[data-drop]');
        tile.querySelectorAll('.is-drop').forEach((el) => el.classList.remove('is-drop'));
        if (!zone || !dragId) return;
        event.preventDefault();
        const id = dragId;
        dragId = '';
        void onDrop(id, zone);
    });
}

export async function onTodoPageShown() {
    review = false;
    await reload();
    document.getElementById('todoPageTitle')?.focus();
}

async function reload() {
    try {
        page = await callEel('get_todo_page');
        paint();
    } catch (err) {
        utils.showErrorFeedback(err?.message || 'Could not load To Do.');
    }
}

async function add(bucket) {
    const input = document.getElementById('todoPageTitle');
    const title = input?.value || '';
    if (!title.trim()) return;
    try {
        page = await callEel('add_todo_bucket', title, bucket, '');
        if (input) input.value = '';
        paint();
    } catch (err) {
        utils.showErrorFeedback(err?.message || 'Could not add that.');
    }
}

async function onAct(btn) {
    const id = btn.getAttribute('data-id') || '';
    const act = btn.getAttribute('data-act') || '';
    try {
        if (act === 'done') await callEel('finish_work_item', id);
        else if (act === 'delete') await callEel('delete_work_item', id, 'occurrence');
        else if (act === 'today') page = await callEel('place_work_bucket', id, 'today', '');
        else if (act === 'week') page = await callEel('place_work_bucket', id, 'week', '');
        else if (act === 'later') page = await callEel('place_work_bucket', id, 'later', '');
        else if (act === 'none') page = await callEel('place_work_bucket', id, 'none', '');
        else if (act === 'day') page = await callEel('place_work_bucket', id, 'date', btn.getAttribute('data-day') || '');
        else return;
        if (act === 'done' || act === 'delete') page = await callEel('get_todo_page');
        if (review && !(page?.review || []).length) review = false;
        paint();
    } catch (err) {
        utils.showErrorFeedback(err?.message || 'Could not update that.');
    }
}

function findItem(id) {
    if (!page) return null;
    const lists = [page.this_week, page.later, page.no_day, page.review];
    for (const list of lists) {
        const hit = (list || []).find((item) => item.id === id);
        if (hit) return hit;
    }
    return null;
}

function groupOf(item) {
    if (!item || !page) return '';
    if ((page.review || []).some((row) => row.id === item.id)) return 'review';
    if ((page.this_week || []).some((row) => row.id === item.id)) return 'this_week';
    if ((page.later || []).some((row) => row.id === item.id)) return 'later';
    if ((page.no_day || []).some((row) => row.id === item.id)) return 'no_day';
    return '';
}

async function onDrop(id, zone) {
    const drop = zone.getAttribute('data-drop') || '';
    const item = findItem(id);
    const source = groupOf(item);
    try {
        if (drop === 'day') {
            page = await callEel('place_work_bucket', id, 'date', zone.getAttribute('data-day') || '');
        } else if (drop === 'row') {
            const targetGroup = zone.getAttribute('data-group') || '';
            if (targetGroup && targetGroup === source) {
                page = await callEel('reorder_work_items', orderAfterDrop(source, id, zone.getAttribute('data-id') || ''));
            } else {
                const bucket = GROUPS.find((group) => group.id === targetGroup)?.bucket || 'none';
                page = await callEel('place_work_bucket', id, bucket, '');
            }
        } else {
            const bucket = zone.getAttribute('data-bucket') || 'none';
            page = await callEel('place_work_bucket', id, bucket, '');
        }
        paint();
    } catch (err) {
        utils.showErrorFeedback(err?.message || 'Could not move that.');
    }
}

function orderAfterDrop(groupId, drag, targetId) {
    const list = (page?.[groupId] || []).map((item) => item.id).filter((id) => id !== drag);
    const index = list.indexOf(targetId);
    if (index < 0) list.push(drag);
    else list.splice(index, 0, drag);
    return list;
}

function paint() {
    const tile = document.getElementById('todoPageTile');
    const reviewBtn = document.getElementById('todoReviewBtn');
    if (!tile || !page) return;
    const count = Number(page.review_count || (page.review || []).length || 0);
    if (reviewBtn) {
        reviewBtn.textContent = count ? `Review ${count}` : 'Review';
        reviewBtn.classList.toggle('is-selected', review);
    }
    if (review) {
        tile.innerHTML = reviewHtml();
        return;
    }
    tile.innerHTML = GROUPS.map((group) => groupHtml(group)).join('');
}

function reviewHtml() {
    const rows = page.review || [];
    if (!rows.length) {
        return '<p class="todo-empty">Nothing left to place.</p>';
    }
    const days = page.weekdays || [];
    return `
        <section>
            <h2>Place these</h2>
            <p class="todo-empty">Last week’s undated to-dos. They stay here until you place them.</p>
            ${rows.map((item) => reviewRow(item, days)).join('')}
        </section>
    `;
}

function reviewRow(item, days) {
    const id = utils.escapeHtml(item.id || '');
    const dayButtons = days.map((day) =>
        `<button type="button" class="btn-ghost" data-act="day" data-id="${id}" data-day="${utils.escapeHtml(day.date)}">${utils.escapeHtml(day.label)}</button>`
    ).join('');
    return `<div class="todo-row">
        <div class="todo-row-copy"><strong>${utils.escapeHtml(item.title || '')}</strong><span>Sometime last week</span></div>
        <div class="todo-review-actions">
            <button type="button" class="btn-ghost" data-act="week" data-id="${id}">This week</button>
            ${dayButtons}
            <button type="button" class="btn-ghost" data-act="later" data-id="${id}">Later</button>
            <button type="button" class="btn-ghost" data-act="done" data-id="${id}">Done</button>
        </div>
    </div>`;
}

function groupHtml(group) {
    const rows = page[group.id] || [];
    const days = group.id === 'this_week'
        ? (page.weekdays || []).map((day) =>
            `<button type="button" class="work-day-chip todo-day-chip" data-drop="day" data-day="${utils.escapeHtml(day.date)}">${utils.escapeHtml(day.label)}</button>`
        ).join('')
        : '';
    const body = rows.length
        ? rows.map((item) => rowHtml(item, group.id)).join('')
        : '<p class="todo-empty">Drop here.</p>';
    return `<section data-drop="bucket" data-bucket="${group.bucket}">
        <div class="todo-group-head">
            <h2>${group.title}</h2>
            ${days}
        </div>
        ${body}
    </section>`;
}

function rowHtml(item, groupId) {
    const id = utils.escapeHtml(item.id || '');
    return `<div class="todo-row" data-drop="row" data-group="${groupId}" data-id="${utils.escapeHtml(item.id || '')}">
        <button type="button" class="todo-row-copy" draggable="true" data-id="${id}">
            <strong>${utils.escapeHtml(item.title || '')}</strong>
            <span>${utils.escapeHtml(meta(item))}</span>
        </button>
        <button type="button" class="btn-ghost" data-act="done" data-id="${id}">Done</button>
        <button type="button" class="btn-ghost" data-act="today" data-id="${id}">Today</button>
        <button type="button" class="btn-ghost" data-act="delete" data-id="${id}">Delete</button>
    </div>`;
}

function meta(item) {
    const scheduled = String(item.scheduled_date || '').slice(0, 10);
    if (scheduled) {
        const hit = (page.weekdays || []).find((day) => day.date === scheduled);
        return hit ? hit.label : scheduled;
    }
    if (item.horizon === 'week') return 'Sometime this week';
    if (item.horizon === 'later') return 'Later';
    return 'No day';
}
