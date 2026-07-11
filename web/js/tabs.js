/**
 * Tab navigation — journal and daily checklist.
 */

import { loadPastEntries } from './journal.js';
import { onChecklistTabShown } from './daily_checklist.js';
import { onReviewTabShown } from './review.js';
import { onTimelineTabShown, setupTimeline } from './timeline.js';

export function setupTabs() {
    const container = document.querySelector('.tabs');
    if (!container) return;

    container.addEventListener('click', (e) => {
        const btn = e.target.closest('.tab-button');
        if (!btn) return;
        const tab = btn.getAttribute('data-tab');
        if (tab) {
            switchTab(tab).catch((err) => console.error(err));
        }
    });
}

export async function switchTab(name) {
    document.querySelectorAll('.tab-button').forEach((b) => {
        b.classList.toggle('active', b.getAttribute('data-tab') === name);
    });
    const idMap = { journal: 'journalTab', checklist: 'checklistTab', review: 'reviewTab', timeline: 'timelineTab' };
    const activeId = idMap[name];
    document.querySelectorAll('.tab-content').forEach((c) => {
        c.classList.toggle('active', activeId !== undefined && c.id === activeId);
    });

    if (name === 'journal') {
        await loadPastEntries();
    } else if (name === 'checklist') {
        await onChecklistTabShown();
    } else if (name === 'review') {
        await onReviewTabShown();
    } else if (name === 'timeline') {
        await onTimelineTabShown();
    }
}
