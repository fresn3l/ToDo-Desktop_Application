/**
 * Tab navigation — Home, Journal, Calendar, Analytics, Settings.
 * Non-Home screens load their JS and Python on first visit.
 */

import { onHomeTabShown, clearHomePageColors, closeHomeWork } from './home.js';
import { notifyNativeTab } from './appearance.js';
import { bootFeature, loadOnce, logEelError } from './lazy.js';

const ID_MAP = {
    home: 'homeTab',
    today: 'calendarTab',
    journal: 'journalTab',
    notes: 'notesTab',
    todo: 'todoPage',
    calendar: 'calendarTab',
    analytics: 'analyticsTab',
    brain: 'brainTab',
    library: 'libraryTab',
    settings: 'settingsTab',
};

const LABELS = {
    home: 'Home',
    today: 'Today',
    journal: 'Journal',
    notes: 'Notes',
    todo: 'To Do',
    calendar: 'Calendar',
    analytics: 'Analytics',
    brain: 'Brain',
    library: 'Library',
    settings: 'Settings',
};

function canonicalTab(name) {
    if (name === 'today') return 'calendar';
    if (name === 'work' || name === 'allwork') {
        return 'calendar';
    }
    if (name === 'todo') return 'todo';
    if (name === 'workout'
        || name === 'goals' || name === 'timeline'
        || name === 'checklist' || name === 'word') {
        return 'home';
    }
    return name;
}

function markNav(face) {
    const homePage = document.documentElement.getAttribute('data-home-page');
    document.querySelectorAll('.nav-item').forEach((b) => {
        const pageId = b.getAttribute('data-home-page');
        const tab = b.getAttribute('data-tab');
        let on = false;
        if (pageId) on = face === 'home' && pageId === homePage;
        else if (tab === 'today') on = face === 'today';
        else if (tab === 'calendar') on = face === 'calendar';
        else on = tab === face;
        b.classList.toggle('active', on);
        b.setAttribute('aria-current', on ? 'page' : 'false');
    });
}

function setDocumentTitle(name) {
    const key = canonicalTab(name);
    const label = LABELS[name] || LABELS[key] || 'Kosistenz';
    document.title = `${label} · Kosistenz`;
    notifyNativeTab(key, label);
}

function openTabFromEvent(e) {
    const btn = e.target.closest?.('.nav-item[data-tab]');
    if (!btn) return;
    const tab = btn.getAttribute('data-tab');
    if (!tab) return;
    e.preventDefault();
    const pageId = btn.getAttribute('data-home-page');
    switchTab(tab, pageId ? { homePageId: pageId } : {}).catch((err) => console.error(err));
}

let journalApi = null;

async function loadTab(key) {
    return loadOnce(`tab:${key}`, async () => {
        if (key === 'journal') {
            await bootFeature('journal');
            const mod = await import('./journal.js');
            mod.setupJournal();
            journalApi = mod;
            return mod;
        }
        if (key === 'notes') {
            await bootFeature('notes');
            const mod = await import('./notes.js');
            mod.setupNotes();
            return mod;
        }
        if (key === 'todo') {
            await bootFeature('todo');
            const mod = await import('./todo_page.js');
            mod.setupTodoPage();
            return mod;
        }
        if (key === 'calendar') {
            await bootFeature('calendar');
            const mod = await import('./calendar.js');
            mod.setupCalendar();
            return mod;
        }
        if (key === 'brain') {
            await bootFeature('brain');
            const mod = await import('./brain.js');
            mod.setupBrain();
            return mod;
        }
        if (key === 'library') {
            await bootFeature('library');
            const mod = await import('./library.js');
            mod.setupLibrary();
            return mod;
        }
        if (key === 'analytics') {
            await bootFeature('analytics');
            const mod = await import('./analytics.js');
            mod.setupAnalytics();
            return mod;
        }
        if (key === 'settings') {
            const mod = await import('./settings.js');
            mod.setupSettings();
            return mod;
        }
        return null;
    });
}

export function setupTabs() {
    const sidebar = document.querySelector('.app-sidebar');
    if (!sidebar) return;

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
        };
        const tab = map[e.key];
        if (!tab) return;
        e.preventDefault();
        switchTab(tab).catch((err) => console.error(err));
    });

    document.addEventListener('kosistenz:open-day', () => {
        switchTab('today').catch((err) => console.error(err));
    });

    document.addEventListener('click', (e) => {
        const btn = e.target.closest?.('[data-open-tab]');
        if (!btn) return;
        const tab = btn.getAttribute('data-open-tab');
        if (!tab) return;
        e.preventDefault();
        switchTab(tab).catch((err) => console.error(err));
    });

    document.addEventListener('kosistenz:cal-view', (e) => {
        const view = e.detail?.view;
        if (document.documentElement.getAttribute('data-page') !== 'calendar') return;
        markNav(view === 'day' ? 'today' : 'calendar');
    });

    document.addEventListener('kosistenz:open-tab', (e) => {
        const tab = e.detail?.tab;
        if (tab) switchTab(tab, e.detail || {}).catch((err) => console.error(err));
    });
}

export async function switchTab(name, opts = {}) {
    const key = canonicalTab(name);
    const face = name === 'today' || opts.calView === 'day'
        ? 'today'
        : (name === 'calendar' ? 'calendar' : key);
    if (opts.homePageId) {
        document.documentElement.setAttribute('data-home-page', opts.homePageId);
    }
    markNav(face);
    const activeId = ID_MAP[key];
    document.querySelectorAll('.tab-content').forEach((c) => {
        c.classList.toggle('active', activeId !== undefined && c.id === activeId);
    });
    setDocumentTitle(face === 'today' ? 'today' : key);
    document.documentElement.setAttribute('data-page', key);

    if (key !== 'journal') {
        journalApi?.exitJournalFocus?.();
    }
    if (key !== 'home') {
        closeHomeWork(true);
        clearHomePageColors();
    }

    try {
        if (key === 'home') {
            await onHomeTabShown(opts.homePageId);
        } else {
            const mod = await loadTab(key);
            if (key === 'journal') void mod?.loadPastEntries?.();
            else if (key === 'notes') void mod?.loadNotes?.();
            else if (key === 'todo') await mod?.onTodoPageShown?.();
            else if (key === 'calendar') {
                const view = name === 'today' || opts.calView === 'day' ? 'day' : (opts.calView || 'week');
                mod?.setCalView?.(view);
                await mod?.onCalendarTabShown?.();
            }
            else if (key === 'analytics') await mod?.onAnalyticsTabShown?.();
            else if (key === 'brain') await mod?.onBrainTabShown?.();
            else if (key === 'library') await mod?.onLibraryTabShown?.();
            else if (key === 'settings') mod?.onSettingsTabShown?.();
        }
    } catch (err) {
        logEelError(err);
    }

    document.dispatchEvent(new CustomEvent('kosistenz:tab-shown', { detail: { tab: key } }));
}
