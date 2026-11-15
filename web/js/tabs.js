/**
 * Tab navigation — Today, To Do, Calendar, Settings.
 */

import { notifyNativeTab } from './appearance.js';
import { bootFeature, loadOnce, logEelError } from './lazy.js';

const ID_MAP = {
    today: 'calendarTab',
    todo: 'todoPage',
    calendar: 'calendarTab',
    settings: 'settingsTab',
};

const LABELS = {
    today: 'Today',
    todo: 'To Do',
    calendar: 'Calendar',
    settings: 'Settings',
};

function canonicalTab(name) {
    if (name === 'today') return 'calendar';
    if (name === 'work' || name === 'allwork') return 'todo';
    if (name === 'todo') return 'todo';
    return name;
}

function markNav(face) {
    document.querySelectorAll('.nav-item').forEach((b) => {
        const tab = b.getAttribute('data-tab');
        let on = false;
        if (tab === 'today') on = face === 'today';
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
    switchTab(tab).catch((err) => console.error(err));
}

async function loadTab(key) {
    return loadOnce(`tab:${key}`, async () => {
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
            2: 'todo',
            3: 'calendar',
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
    markNav(face);
    const activeId = ID_MAP[key];
    document.querySelectorAll('.tab-content').forEach((c) => {
        c.classList.toggle('active', activeId !== undefined && c.id === activeId);
    });
    setDocumentTitle(face === 'today' ? 'today' : key);
    document.documentElement.setAttribute('data-page', key);

    try {
        const mod = await loadTab(key);
        if (key === 'todo') await mod?.onTodoPageShown?.();
        else if (key === 'calendar') {
            const view = name === 'today' || opts.calView === 'day' ? 'day' : (opts.calView || 'week');
            mod?.setCalView?.(view);
            await mod?.onCalendarTabShown?.();
        }
        else if (key === 'settings') mod?.onSettingsTabShown?.();
    } catch (err) {
        logEelError(err);
    }

    document.dispatchEvent(new CustomEvent('kosistenz:tab-shown', { detail: { tab: key } }));
}
