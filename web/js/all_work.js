/**
 * All Work — undated backlog. Assign to today, tomorrow, or leave for later.
 */

import * as utils from './utils.js';
import { tomorrowISO } from './work.js';

export async function refreshAllWork() {
    const list = document.getElementById('allWorkList');
    const summary = document.getElementById('allWorkSummary');
    if (!list) return;
    try {
        const items = await eel.list_backlog()();
        if (summary) {
            summary.textContent = items.length
                ? `${items.length} waiting to be dated`
                : 'Empty — add work for later';
        }
        if (!items.length) {
            list.innerHTML = `
                <div class="empty-state">
                    <h3>Nothing parked in All Work</h3>
                    <p>Capture tasks here. Tonight, assign some to tomorrow or leave them for later.</p>
                </div>`;
            return;
        }
        list.innerHTML = items
            .map(
                (item) => `
                <article class="work-item" data-id="${utils.escapeHtml(item.id)}">
                    <div class="work-item-main">
                        <h3>${utils.escapeHtml(item.title)}</h3>
                        <p class="work-meta">${item.due_at ? `Due ${utils.escapeHtml(String(item.due_at).slice(0, 16).replace('T', ' '))}` : 'Not dated yet'}${item.estimate_minutes ? ` · ${item.estimate_minutes} min` : ''}</p>
                    </div>
                    <div class="work-item-actions">
                        <button type="button" class="btn-primary" data-act="today">Today</button>
                        <button type="button" class="btn-secondary" data-act="tomorrow">Tomorrow</button>
                        <button type="button" class="btn-ghost" data-act="delete">Delete</button>
                    </div>
                </article>`,
            )
            .join('');
        list.querySelectorAll('.work-item').forEach((row) => {
            const id = row.getAttribute('data-id');
            row.querySelectorAll('[data-act]').forEach((btn) => {
                btn.addEventListener('click', async () => {
                    const act = btn.getAttribute('data-act');
                    try {
                        if (act === 'today') {
                            await eel.assign_work_item(id, utils.localISODate())();
                            utils.showSuccessFeedback('Moved to today’s To Do.');
                        } else if (act === 'tomorrow') {
                            await eel.assign_work_item(id, tomorrowISO())();
                            utils.showSuccessFeedback('Queued for tomorrow.');
                        } else if (act === 'delete') {
                            await eel.delete_work_item(id)();
                        }
                        utils.notifyDataChanged();
                        await refreshAllWork();
                    } catch (e) {
                        utils.showErrorFeedback('Could not update that item.');
                    }
                });
            });
        });
    } catch (e) {
        console.error(e);
        list.innerHTML = '<p class="checklist-error">Could not load All Work.</p>';
    }
}

async function addBacklogTask() {
    const input = document.getElementById('allWorkNewTitle');
    const title = (input?.value || '').trim();
    if (!title) {
        utils.showErrorFeedback('Name the work first.');
        return;
    }
    try {
        await eel.create_work_item(
            title,
            '',
            '',
            'backlog',
            null,
            document.getElementById('allWorkNewDue')?.value || '',
            document.getElementById('allWorkNewEstimate')?.value || '',
        )();
        if (input) input.value = '';
        const est = document.getElementById('allWorkNewEstimate');
        const dueEl = document.getElementById('allWorkNewDue');
        if (est) est.value = '';
        if (dueEl) dueEl.value = '';
        utils.showSuccessFeedback('Saved in All Work.');
        utils.notifyDataChanged();
        await refreshAllWork();
        input?.focus();
    } catch (e) {
        utils.showErrorFeedback('Could not add that item.');
    }
}

export function setupAllWork() {
    document.getElementById('allWorkAddBtn')?.addEventListener('click', () => {
        void addBacklogTask();
    });
    document.getElementById('allWorkNewTitle')?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            void addBacklogTask();
        }
    });
    document.addEventListener('kosistenz:data-changed', () => {
        if (document.getElementById('allWorkTab')?.classList.contains('active')) {
            void refreshAllWork();
        }
    });
}

export async function onAllWorkTabShown() {
    await refreshAllWork();
}
