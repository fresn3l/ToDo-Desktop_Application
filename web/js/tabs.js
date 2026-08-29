/**
 * Tab navigation — journal, workout, to do, all work, analytics, timeline, settings.
 */

import { loadPastEntries, exitJournalFocus } from './journal.js';
import { onAnalyticsTabShown } from './analytics.js';
import { onTimelineTabShown } from './timeline.js';
import { onSettingsTabShown } from './settings.js';
import { onTodoTabShown } from './todo.js';
import { onAllWorkTabShown } from './all_work.js';
import { onWorkoutTabShown } from './workouts.js';

const ID_MAP = {
    journal: 'journalTab',
    workout: 'workoutTab',
    todo: 'todoTab',
    allwork: 'allWorkTab',
    analytics: 'analyticsTab',
    timeline: 'timelineTab',
    settings: 'settingsTab',
};

const LABELS = {
    journal: 'Journal',
    workout: 'Workout',
    todo: 'To Do',
    allwork: 'All Work',
    analytics: 'Analytics',
    timeline: 'Timeline',
    settings: 'Settings',
};

function setDocumentTitle(name) {
    document.title = `${LABELS[name] || 'Kosistenz'} · Kosistenz`;
    const crumb = document.getElementById('pageCrumb');
    if (crumb) crumb.textContent = LABELS[name] || '';
}

export function setupTabs() {
    const sidebar = document.querySelector('.app-sidebar');
    if (!sidebar) return;

    sidebar.addEventListener('click', (e) => {
        const btn = e.target.closest('.nav-item[data-tab]');
        if (!btn) return;
        const tab = btn.getAttribute('data-tab');
        if (tab) {
            switchTab(tab).catch((err) => console.error(err));
        }
    });

    document.addEventListener('keydown', (e) => {
        if (!(e.metaKey || e.ctrlKey) || e.shiftKey || e.altKey) return;
        const map = {
            1: 'journal',
            2: 'workout',
            3: 'todo',
            4: 'allwork',
            5: 'analytics',
            6: 'timeline',
            7: 'settings',
        };
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

    document.addEventListener('kosistenz:open-tab', (e) => {
        const tab = e.detail?.tab;
        if (tab) switchTab(tab).catch((err) => console.error(err));
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
    } else if (name === 'workout') {
        await onWorkoutTabShown();
    } else if (name === 'todo') {
        await onTodoTabShown();
    } else if (name === 'allwork') {
        await onAllWorkTabShown();
    } else if (name === 'analytics') {
        await onAnalyticsTabShown();
    } else if (name === 'timeline') {
        await onTimelineTabShown();
    } else if (name === 'settings') {
        onSettingsTabShown();
    }

    document.dispatchEvent(new CustomEvent('kosistenz:tab-shown', { detail: { tab: name } }));
}
