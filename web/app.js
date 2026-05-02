/**
 * Kosistenz app entry point (journal + daily checklist).
 */

import * as utils from './js/utils.js';
import { setupTabs, switchTab } from './js/tabs.js';
import { setupJournal, loadPastEntries } from './js/journal.js';
import { setupDailyChecklist } from './js/daily_checklist.js';

async function init() {
    await new Promise((resolve) => setTimeout(resolve, 100));
    setupTabs();
    setupJournal();
    await setupDailyChecklist();
    await loadPastEntries();
    await switchTab('journal');
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
