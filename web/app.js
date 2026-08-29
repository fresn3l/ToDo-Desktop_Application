/**
 * Kosistenz app entry point (journal, workout, work).
 */

import * as utils from './js/utils.js';
import { initAppearance } from './js/appearance.js';
import { setupTabs, switchTab } from './js/tabs.js';
import { setupJournal } from './js/journal.js';
import { setupAnalytics } from './js/analytics.js';
import { setupTimeline } from './js/timeline.js';
import { setupSettings } from './js/settings.js';
import { setupToday } from './js/today.js';
import { setupTodo } from './js/todo.js';
import { setupAllWork } from './js/all_work.js';
import { setupWorkouts } from './js/workouts.js';

async function init() {
    await new Promise((resolve) => setTimeout(resolve, 100));
    await initAppearance();
    setupTabs();
    setupSettings();
    setupToday();
    setupTodo();
    setupAllWork();
    setupWorkouts();
    setupJournal();
    setupAnalytics();
    setupTimeline();
    await switchTab('journal');
}

function markNativeShell() {
    const native = typeof window.pywebview !== 'undefined'
        || window.kosistenzNative === true
        || document.documentElement.classList.contains('native-shell');
    if (!native) return;
    document.documentElement.classList.add('native-shell');
    if (document.body.dataset.nativeMenu === '1') return;
    document.body.dataset.nativeMenu = '1';
    document.addEventListener('contextmenu', (e) => {
        if (!e.target.closest('input, textarea, select, [contenteditable="true"]')) {
            e.preventDefault();
        }
    });
}

function waitForEel() {
    return new Promise((resolve) => {
        if (typeof eel !== 'undefined' && eel.init) {
            resolve();
            return;
        }
        let attempts = 0;
        const checkEel = setInterval(() => {
            attempts++;
            if (typeof eel !== 'undefined' && eel.init) {
                clearInterval(checkEel);
                resolve();
            } else if (attempts > 50) {
                clearInterval(checkEel);
                resolve();
            }
        }, 100);
    });
}

async function startApp() {
    markNativeShell();
    window.addEventListener('pywebviewready', markNativeShell);
    await waitForEel();
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => init().catch(handleInitError));
    } else {
        setTimeout(() => init().catch(handleInitError), 50);
    }
}

function handleInitError(error) {
    console.error(error);
    if (utils.showErrorFeedback) {
        utils.showErrorFeedback('Failed to start the app. Refresh and try again.');
    }
}

startApp();
