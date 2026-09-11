/**
 * Tab navigation — Home, Journal, Calendar, Settings.
 * Non-Home screens load their JS and Python on first visit.
 */

import { onHomeTabShown, clearHomePageColors, closeHomeWork } from './home.js';
import { notifyNativeTab } from './appearance.js';
import { bootFeature, loadOnce } from './lazy.js';

const ID_MAP = {
    home: 'homeTab',
    today: 'homeTab',
    journal: 'journalTab',
    calendar: 'calendarTab',
    brain: 'brainTab',
    library: 'libraryTab',
    settings: 'settingsTab',
};

const LABELS = {
    home: 'Home',
    today: 'Home',
    journal: 'Journal',
    calendar: 'Calendar',
    brain: 'Brain',
    library: 'Library',
    settings: 'Settings',
};

function canonicalTab(name) {
    if (name === 'today' || name === 'workout' || name === 'todo'
        || name === 'goals' || name === 'allwork' || name === 'analytics' || name === 'timeline'
        || name === 'checklist' || name === 'word') {
        return 'home';
    }
    return name;
}

function setDocumentTitle(name) {
    const key = canonicalTab(name);
    document.title = `${LABELS[key] || 'Kosistenz'} · Kosistenz`;
    const crumb = document.getElementById('pageCrumb');
    if (crumb) crumb.textContent = LABELS[key] || '';
    notifyNativeTab(key, LABELS[key] || 'Kosistenz');
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
            1: 'home',
            2: 'journal',
            3: 'calendar',
            4: 'brain',
            5: 'library',
        };
        const tab = map[e.key];
        if (!tab) return;
        e.preventDefault();
        switchTab(tab).catch((err) => console.error(err));
    });

    document.addEventListener('kosistenz:open-day', () => {
        switchTab('home').catch((err) => console.error(err));
    });

    document.addEventListener('kosistenz:open-tab', (e) => {
        const tab = e.detail?.tab;
        if (tab) switchTab(tab, e.detail || {}).catch((err) => console.error(err));
    });
}

export async function switchTab(name, opts = {}) {
    const key = canonicalTab(name);
    if (opts.homePageId) {
        document.documentElement.setAttribute('data-home-page', opts.homePageId);
    }
    const homePage = document.documentElement.getAttribute('data-home-page');
    document.querySelectorAll('.nav-item').forEach((b) => {
        const pageId = b.getAttribute('data-home-page');
        const on = pageId
            ? key === 'home' && pageId === homePage
            : b.getAttribute('data-tab') === key;
        b.classList.toggle('active', on);
        b.setAttribute('aria-current', on ? 'page' : 'false');
    });
    const activeId = ID_MAP[key];
    document.querySelectorAll('.tab-content').forEach((c) => {
        c.classList.toggle('active', activeId !== undefined && c.id === activeId);
    });
    setDocumentTitle(key);
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
            if (key === 'journal') await mod?.loadPastEntries?.();
            else if (key === 'calendar') await mod?.onCalendarTabShown?.();
            else if (key === 'brain') await mod?.onBrainTabShown?.();
            else if (key === 'library') await mod?.onLibraryTabShown?.();
            else if (key === 'settings') mod?.onSettingsTabShown?.();
        }
    } catch (err) {
        console.error(err);
    }

    document.dispatchEvent(new CustomEvent('kosistenz:tab-shown', { detail: { tab: key } }));
}
