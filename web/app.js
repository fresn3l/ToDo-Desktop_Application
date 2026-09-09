/**
 * Kosistenz app entry point — Home first, other screens on demand.
 */

import * as utils from './js/utils.js';
import { initAppearance } from './js/appearance.js';
import { setupTabs, switchTab } from './js/tabs.js';
import { setupHome } from './js/home.js';

async function init() {
    await initAppearance();
    setupTabs();
    setupHome();
    document.addEventListener('kosistenz:command', (e) => {
        const action = e.detail?.action;
        if (action === 'journal-new') {
            switchTab('journal')
                .then(async () => {
                    const { beginNewJournalEntry } = await import('./js/journal.js');
                    beginNewJournalEntry(e.detail?.text || '');
                })
                .catch((err) => console.error(err));
            return;
        }
        if (action === 'open-tab' && e.detail?.tab) {
            switchTab(e.detail.tab).catch((err) => console.error(err));
        }
    });
    await switchTab('home');
    void pullPhoneOnOpen();
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible') {
            void pullPhoneOnOpen();
        }
    });
}

async function pullPhoneOnOpen() {
    if (typeof eel === 'undefined' || !eel.maybe_pull_icloud_on_open) return;
    try {
        const result = await eel.maybe_pull_icloud_on_open()();
        if (result && !result.skipped) {
            utils.notifyDataChanged();
        }
    } catch (_) {
        /* pack missing or Cluny-unrelated — Today still works */
    }
}

window.kosistenzPullPhone = pullPhoneOnOpen;

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
        init().catch(handleInitError);
    }
}

function handleInitError(error) {
    console.error(error);
    if (utils.showErrorFeedback) {
        utils.showErrorFeedback('Failed to start the app. Refresh and try again.');
    }
}

startApp();
