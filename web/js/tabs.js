/**
 * Tab navigation — today, calendar, journal, workout, to do, goals, all work, analytics, timeline, settings.
 */

import { loadPastEntries, exitJournalFocus } from './journal.js';
import { onAnalyticsTabShown } from './analytics.js';
import { onTimelineTabShown } from './timeline.js';
import { onSettingsTabShown } from './settings.js';
import { onTodoTabShown } from './todo.js';
import { onAllWorkTabShown } from './all_work.js';
import { onWorkoutTabShown } from './workouts.js';
import { onTodayTabShown } from './today.js';
import { onCalendarTabShown } from './calendar.js';
import { onGoalsTabShown } from './goals.js';
import { notifyNativeTab } from './appearance.js';

const ID_MAP = {
    today: 'todayTab',
    calendar: 'calendarTab',
    journal: 'journalTab',
    workout: 'workoutTab',
    todo: 'todoTab',
    goals: 'goalsTab',
    allwork: 'allWorkTab',
    analytics: 'analyticsTab',
    timeline: 'timelineTab',
    settings: 'settingsTab',
};

const LABELS = {
    today: 'Today',
    calendar: 'Calendar',
    journal: 'Journal',
    workout: 'Workout',
    todo: 'To Do',
    goals: 'Goals',
    allwork: 'All Work',
    analytics: 'Analytics',
    timeline: 'Timeline',
    settings: 'Settings',
};

function setDocumentTitle(name) {
    document.title = `${LABELS[name] || 'Kosistenz'} · Kosistenz`;
    const crumb = document.getElementById('pageCrumb');
    if (crumb) crumb.textContent = LABELS[name] || '';
    notifyNativeTab(name, LABELS[name] || 'Kosistenz');
}

function openTabFromEvent(e) {
    const btn = e.target.closest?.('.nav-item[data-tab]');
    if (!btn) return;
    const tab = btn.getAttribute('data-tab');
    if (!tab) return;
    e.preventDefault();
    switchTab(tab).catch((err) => console.error(err));
}

export function setupTabs() {
    const sidebar = document.querySelector('.app-sidebar');
    if (!sidebar) return;

    // Capture phase: native WKWebView can miss bubble-phase clicks on transparent pixels.
    sidebar.addEventListener('click', openTabFromEvent, true);

    document.addEventListener('keydown', (e) => {
        if ((e.metaKey || e.ctrlKey) && e.key === ',') {
            e.preventDefault();
            switchTab('settings').catch((err) => console.error(err));
            return;
        }
        if (!(e.metaKey || e.ctrlKey) || e.shiftKey || e.altKey) return;
        const map = {
            1: 'today',
            2: 'calendar',
            3: 'journal',
            4: 'workout',
            5: 'todo',
            6: 'goals',
            7: 'allwork',
            8: 'analytics',
            9: 'timeline',
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
    document.documentElement.setAttribute('data-page', name);

    if (name !== 'journal') {
        exitJournalFocus();
    }

    try {
        if (name === 'today') {
            await onTodayTabShown();
        } else if (name === 'calendar') {
            await onCalendarTabShown();
        } else if (name === 'journal') {
            await loadPastEntries();
        } else if (name === 'workout') {
            await onWorkoutTabShown();
        } else if (name === 'todo') {
            await onTodoTabShown();
        } else if (name === 'goals') {
            await onGoalsTabShown();
        } else if (name === 'allwork') {
            await onAllWorkTabShown();
        } else if (name === 'analytics') {
            await onAnalyticsTabShown();
        } else if (name === 'timeline') {
            await onTimelineTabShown();
        } else if (name === 'settings') {
            onSettingsTabShown();
        }
    } catch (err) {
        console.error(err);
    }

    document.dispatchEvent(new CustomEvent('kosistenz:tab-shown', { detail: { tab: name } }));
}
