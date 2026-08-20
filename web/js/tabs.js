/**
 * Tab navigation — journal, checklist, review, timeline, settings.
 */

import { loadPastEntries, exitJournalFocus } from './journal.js';
import { onChecklistTabShown } from './daily_checklist.js';
import { onReviewTabShown } from './review.js';
import { onTimelineTabShown } from './timeline.js';
import { onSettingsTabShown } from './settings.js';

const ID_MAP = {
    journal: 'journalTab',
    checklist: 'checklistTab',
    review: 'reviewTab',
    timeline: 'timelineTab',
    settings: 'settingsTab',
};

const LABELS = {
    journal: 'Journal',
    checklist: 'Checklist',
    review: 'Review',
    timeline: 'Timeline',
    settings: 'Settings',
};

function setDocumentTitle(name) {
    document.title = `${LABELS[name] || 'Kosistenz'} · Kosistenz`;
    const crumb = document.getElementById('pageCrumb');
    if (crumb) crumb.textContent = LABELS[name] || '';
}

export function setupTabs() {
    const nav = document.querySelector('.app-nav');
    if (!nav) return;

    nav.addEventListener('click', (e) => {
        const btn = e.target.closest('.nav-item');
        if (!btn) return;
        const tab = btn.getAttribute('data-tab');
        if (tab) {
            switchTab(tab).catch((err) => console.error(err));
        }
    });

    document.addEventListener('keydown', (e) => {
        if (!(e.metaKey || e.ctrlKey) || e.shiftKey || e.altKey) return;
        const map = { 1: 'journal', 2: 'checklist', 3: 'review', 4: 'timeline', 5: 'settings' };
        const tab = map[e.key];
        if (!tab) return;
        e.preventDefault();
        switchTab(tab).catch((err) => console.error(err));
    });

    document.addEventListener('kosistenz:open-day', (e) => {
        const date = e.detail?.date;
        if (!date) return;
        const picker = document.getElementById('timelineDate');
        if (picker) picker.value = date;
        switchTab('timeline').catch((err) => console.error(err));
    });
}

export async function switchTab(name) {
    document.querySelectorAll('.nav-item').forEach((b) => {
        const on = b.getAttribute('data-tab') === name;
        b.classList.toggle('active', on);
        b.setAttribute('aria-current', on ? 'page' : 'false');
    });
    const activeId = ID_MAP[name];
    document.querySelectorAll('.tab-content').forEach((c) => {
        c.classList.toggle('active', activeId !== undefined && c.id === activeId);
    });
    setDocumentTitle(name);

    if (name !== 'journal') {
        exitJournalFocus();
    }

    if (name === 'journal') {
        await loadPastEntries();
    } else if (name === 'checklist') {
        await onChecklistTabShown();
    } else if (name === 'review') {
        await onReviewTabShown();
    } else if (name === 'timeline') {
        await onTimelineTabShown();
    } else if (name === 'settings') {
        onSettingsTabShown();
    }
}
