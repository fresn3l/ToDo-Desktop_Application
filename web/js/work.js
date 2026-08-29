/**
 * Shared helpers for To Do / All Work.
 */

import * as utils from './utils.js';

export function formatDuration(seconds) {
    const total = Math.max(0, Math.floor(Number(seconds) || 0));
    const hours = Math.floor(total / 3600);
    const minutes = Math.floor((total % 3600) / 60);
    const secs = total % 60;
    if (hours > 0) {
        return `${hours}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    }
    return `${minutes}:${String(secs).padStart(2, '0')}`;
}

export function tomorrowISO() {
    const d = new Date();
    d.setDate(d.getDate() + 1);
    return utils.localISODate(d);
}

export function liveSeconds(item) {
    const stored = Number(item?.stored_duration_seconds ?? item?.duration_seconds) || 0;
    if (item?.status !== 'active' || !item.active_started_at) {
        return Number(item?.duration_seconds) || stored;
    }
    const start = new Date(item.active_started_at).getTime();
    if (Number.isNaN(start)) return stored;
    return stored + Math.max(0, Math.floor((Date.now() - start) / 1000));
}

export async function mountWorkPlanner(container, { targetDate }) {
    if (!container) {
        return { getPlan: () => ({ created_titles: [], assign_ids: [], tomorrow: targetDate }) };
    }

    const state = {
        drafts: [],
        selected: new Set(),
        backlog: [],
        already: [],
    };

    async function load() {
        const [backlog, already] = await Promise.all([
            eel.list_backlog()(),
            eel.list_work_for_date(targetDate)(),
        ]);
        state.backlog = backlog || [];
        state.already = already || [];
        render();
    }

    function getPlan() {
        return {
            created_titles: state.drafts.map((t) => t.trim()).filter(Boolean),
            assign_ids: [...state.selected],
            tomorrow: targetDate,
        };
    }

    function render() {
        const draftRows = state.drafts
            .map(
                (title, idx) => `
                <li class="work-draft">
                    <span>${utils.escapeHtml(title)}</span>
                    <button type="button" class="btn-ghost work-mini" data-drop-draft="${idx}">Remove</button>
                </li>`,
            )
            .join('');

        const backlogRows = state.backlog.length
            ? state.backlog
                  .map((item) => {
                      const checked = state.selected.has(item.id) ? 'checked' : '';
                      return `
                        <label class="work-pick">
                            <input type="checkbox" data-assign-id="${utils.escapeHtml(item.id)}" ${checked}>
                            <span>${utils.escapeHtml(item.title)}</span>
                        </label>`;
                  })
                  .join('')
            : '<p class="checklist-empty">All Work is empty. New tasks below go straight to tomorrow.</p>';

        const alreadyRows = state.already.length
            ? `<ul class="work-already">${state.already
                  .map((item) => `<li>${utils.escapeHtml(item.title)}</li>`)
                  .join('')}</ul>`
            : '';

        container.innerHTML = `
            <p class="panel-sub work-planner-lead">
                These land on <strong>tomorrow’s To Do</strong> (${utils.escapeHtml(targetDate)}).
                Anything you leave unchecked stays in All Work.
            </p>
            ${alreadyRows ? `<div class="work-already-wrap"><p class="checklist-field-label">Already on tomorrow</p>${alreadyRows}</div>` : ''}
            <div class="work-add-row">
                <input type="text" class="checklist-text-input" id="workPlannerInput" placeholder="Pay electricity bill" autocomplete="off">
                <button type="button" class="btn-secondary" id="workPlannerAdd">Add</button>
            </div>
            ${draftRows ? `<ul class="work-draft-list">${draftRows}</ul>` : ''}
            <p class="checklist-field-label">From All Work</p>
            <div class="work-pick-list">${backlogRows}</div>
        `;

        const input = container.querySelector('#workPlannerInput');
        const add = () => {
            const title = (input?.value || '').trim();
            if (!title) return;
            state.drafts.push(title);
            if (input) input.value = '';
            render();
            container.querySelector('#workPlannerInput')?.focus();
        };
        container.querySelector('#workPlannerAdd')?.addEventListener('click', add);
        input?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                add();
            }
        });
        container.querySelectorAll('[data-drop-draft]').forEach((btn) => {
            btn.addEventListener('click', () => {
                state.drafts.splice(Number(btn.getAttribute('data-drop-draft')), 1);
                render();
            });
        });
        container.querySelectorAll('[data-assign-id]').forEach((box) => {
            box.addEventListener('change', () => {
                const id = box.getAttribute('data-assign-id');
                if (box.checked) state.selected.add(id);
                else state.selected.delete(id);
            });
        });
    }

    await load();
    return { getPlan };
}
