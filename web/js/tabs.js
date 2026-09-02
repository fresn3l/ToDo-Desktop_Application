/**
 * Tab navigation — Home, Calendar, Settings.
 */

import { exitJournalFocus } from './journal.js';
import { onSettingsTabShown } from './settings.js';
import { onCalendarTabShown } from './calendar.js';
import { onHomeTabShown, clearHomePageColors, closeHomeWork } from './home.js';
import { notifyNativeTab } from './appearance.js';

const ID_MAP = {
    home: 'homeTab',
    today: 'homeTab',
    calendar: 'calendarTab',
    settings: 'settingsTab',
};

const LABELS = {
    home: 'Home',
    today: 'Home',
    calendar: 'Calendar',
    settings: 'Settings',
};

function canonicalTab(name) {
    if (name === 'today' || name === 'journal' || name === 'workout' || name === 'todo'
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
            2: 'calendar',
            3: 'settings',
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
        if (tab) switchTab(tab).catch((err) => console.error(err));
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

    if (key !== 'home') {
        closeHomeWork(true);
        exitJournalFocus();
        clearHomePageColors();
    }

    try {
        if (key === 'home') {
            await onHomeTabShown(opts.homePageId);
        } else if (key === 'calendar') {
            await onCalendarTabShown();
        } else if (key === 'settings') {
            onSettingsTabShown();
        }
    } catch (err) {
        console.error(err);
    }

    document.dispatchEvent(new CustomEvent('kosistenz:tab-shown', { detail: { tab: key } }));
}
