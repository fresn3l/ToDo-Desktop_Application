/**
 * Notes — storage, or one focus span.
 */

import * as utils from './utils.js';
import { callEel } from './lazy.js';

let notes = [];
let spans = [];
let currentId = '';

export function setupNotes() {
    document.getElementById('notesNewBtn')?.addEventListener('click', () => {
        currentId = '';
        const title = document.getElementById('notesTitle');
        const body = document.getElementById('notesBody');
        const pick = document.getElementById('notesFocusPick');
        if (title) title.value = '';
        if (body) body.value = '';
        if (pick) pick.value = '';
        title?.focus();
        paintList();
    });
    document.getElementById('notesSaveBtn')?.addEventListener('click', () => {
        void saveCurrent();
    });
    document.getElementById('notesDetachBtn')?.addEventListener('click', () => {
        void detachCurrent();
    });
    document.getElementById('notesDeleteBtn')?.addEventListener('click', () => {
        void deleteCurrent();
    });
    void loadNotes();
}

export async function loadNotes() {
    try {
        const [rows, holds] = await Promise.all([callEel('list_notes'), callEel('list_focus_spans')]);
        notes = rows || [];
        spans = holds || [];
        const current = notes.find((row) => row.id === currentId);
        if (currentId && !current) {
            currentId = '';
        }
        fillFocusPick(current?.focus_id);
        if (currentId) {
            fillEditor(current);
        }
        paintList();
    } catch (err) {
        utils.showErrorFeedback(err?.message || 'Could not load notes.');
    }
}

function fillFocusPick(extraId) {
    const pick = document.getElementById('notesFocusPick');
    if (!pick) return;
    const selected = extraId || pick.value;
    const known = new Set(spans.map((row) => row.id));
    const options = ['<option value="">In storage</option>'].concat(
        spans.map((row) => {
            const when = row.weekday ? `${row.weekday} · ${row.title || 'Focus'}` : (row.title || 'Focus');
            return `<option value="${utils.escapeHtml(row.id || '')}">${utils.escapeHtml(when)}</option>`;
        }),
    );
    if (selected && !known.has(selected)) {
        options.push(`<option value="${utils.escapeHtml(selected)}">On the clock</option>`);
    }
    pick.innerHTML = options.join('');
    if (selected && [...pick.options].some((opt) => opt.value === selected)) {
        pick.value = selected;
    }
}

function spanLabel(focusId) {
    const hit = spans.find((row) => row.id === focusId);
    if (!hit) return 'On the clock';
    return hit.weekday ? `${hit.weekday} · ${hit.title}` : hit.title || 'Focus';
}

function paintList() {
    const host = document.getElementById('notesList');
    if (!host) return;
    const storage = notes.filter((row) => !row.focus_id);
    const pinned = notes.filter((row) => row.focus_id);
    const groups = [
        { title: 'Storage', rows: storage },
        { title: 'On a focus span', rows: pinned },
    ];
    host.innerHTML = groups
        .map((group) => {
            if (!group.rows.length) {
                return `<h3 class="cal-work-group">${group.title}</h3><p class="empty-state empty-state--line">${group.title === 'Storage' ? 'Nothing in storage.' : 'No notes on a span.'}</p>`;
            }
            return `<h3 class="cal-work-group">${group.title}</h3>${group.rows
                .map((row) => {
                    const selected = row.id === currentId ? ' is-selected' : '';
                    const sub = row.focus_id ? spanLabel(row.focus_id) : 'In storage';
                    return `<button type="button" class="notes-row${selected}" data-id="${utils.escapeHtml(row.id)}">
                        <strong>${utils.escapeHtml(row.title || 'Note')}</strong>
                        <span>${utils.escapeHtml(sub)}</span>
                    </button>`;
                })
                .join('')}`;
        })
        .join('');
    host.querySelectorAll('.notes-row').forEach((btn) => {
        btn.addEventListener('click', () => {
            currentId = btn.getAttribute('data-id') || '';
            fillEditor(notes.find((row) => row.id === currentId));
            paintList();
        });
    });
}

function fillEditor(row) {
    const title = document.getElementById('notesTitle');
    const body = document.getElementById('notesBody');
    const pick = document.getElementById('notesFocusPick');
    if (title) title.value = row?.title || '';
    if (body) body.value = row?.body || '';
    if (pick) pick.value = row?.focus_id || '';
}

async function saveCurrent() {
    const title = document.getElementById('notesTitle')?.value || '';
    const body = document.getElementById('notesBody')?.value || '';
    const focus = document.getElementById('notesFocusPick')?.value || '';
    try {
        const saved = await callEel('save_note', title, body, currentId, focus);
        currentId = saved.id;
        utils.notifyDataChanged('notes');
        await loadNotes();
        utils.showSuccessFeedback(focus ? 'Saved on that span.' : 'Saved in storage.');
    } catch (err) {
        utils.showErrorFeedback(err?.message || 'Could not save that note.');
    }
}

async function detachCurrent() {
    if (!currentId) {
        const pick = document.getElementById('notesFocusPick');
        if (pick) pick.value = '';
        return;
    }
    try {
        await callEel('detach_note', currentId);
        utils.notifyDataChanged('notes');
        await loadNotes();
        utils.showSuccessFeedback('Back in storage.');
    } catch (err) {
        utils.showErrorFeedback(err?.message || 'Could not move that into storage.');
    }
}

async function deleteCurrent() {
    if (!currentId) {
        fillEditor(null);
        return;
    }
    const ok = await utils.askConfirm({
        title: 'Delete this note?',
        message: 'It leaves storage and any focus span.',
        ok: 'Delete',
        danger: true,
    });
    if (!ok) return;
    try {
        await callEel('delete_note', currentId);
        currentId = '';
        fillEditor(null);
        utils.notifyDataChanged('notes');
        await loadNotes();
    } catch (err) {
        utils.showErrorFeedback(err?.message || 'Could not delete that note.');
    }
}
