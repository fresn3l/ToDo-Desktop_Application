/**
 * Main Application Entry Point
 * 
 * This is the main initialization file that coordinates all modules.
 * It imports and initializes all feature modules and sets up the application.
 */

// Import all modules
import * as state from './js/state.js';
import * as utils from './js/utils.js';
import * as ui from './js/ui.js';

import { loadTasks, renderTasks, updateGoalSelect, updateGoalFilter } from './js/tasks.js';
import { loadGoals, renderGoals } from './js/goals.js';
import { setupTabs, switchTab } from './js/tabs.js';
import { setupEventListeners } from './js/events.js';
import { setupJournal } from './js/journal.js';
import { setupNotificationSettings } from './js/notifications.js';

// ============================================
// INITIALIZATION
// ============================================

/**
 * Initialize the application
 * 
 * This function:
 * 1. Sets up all event listeners
 * 2. Sets up tab navigation
 * 3. Sets up journal functionality
 * 4. Sets up notification settings
 * 5. Loads initial data (tasks and goals)
 * 6. Renders initial UI
 */
async function init() {
    try {
        console.log('Starting initialization...');
        
        // Wait a bit to ensure DOM is fully ready
        await new Promise(resolve => setTimeout(resolve, 200));
        
        console.log('Setting up event listeners...');
        // Setup event listeners first
        setupEventListeners();
        
        console.log('Setting up tabs...');
        // Setup tab navigation
        setupTabs();
        
        console.log('Setting up journal...');
        // Setup journal
        setupJournal();
        
        console.log('Setting up notification settings...');
        // Setup notification settings
        setupNotificationSettings();
        
        console.log('Loading initial data...');
        // Load initial data
        await Promise.all([
            loadTasks(),
            loadGoals()
        ]);
        
        console.log('Updating goal dropdowns...');
        // Update goal dropdowns after both tasks and goals are loaded
        updateGoalSelect();
        updateGoalFilter();
        
        console.log('Rendering tasks and goals...');
        // Ensure tasks and goals are rendered
        renderTasks();
        await renderGoals();
        
        console.log('Switching to tasks tab...');
        // Switch to tasks tab by default
        await switchTab('tasks');
        
        console.log('Initialization complete');
        
        // Animate elements on load
        setTimeout(() => {
            if (ui && ui.animateElements) {
                ui.animateElements();
            }
        }, 100);
        
    } catch (error) {
        console.error('Error initializing application:', error);
        console.error('Stack trace:', error.stack);
        if (utils && utils.showErrorFeedback) {
            utils.showErrorFeedback('Failed to initialize application. Please refresh the page.');
        } else {
            alert('Failed to initialize application. Please check the console for errors.');
        }
    }
}

// Wait for eel to be available before initializing
function waitForEel() {
    return new Promise((resolve) => {
        if (typeof eel !== 'undefined' && eel.init) {
            resolve();
        } else {
            let attempts = 0;
            const checkEel = setInterval(() => {
                attempts++;
                if (typeof eel !== 'undefined' && eel.init) {
                    clearInterval(checkEel);
                    resolve();
                } else if (attempts > 50) {
                    console.warn('Eel not available after 5 seconds, proceeding anyway');
                    clearInterval(checkEel);
                    resolve();
                }
            }, 100);
        }
    });
}

// Initialize when DOM is ready
async function startApp() {
    await waitForEel();
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        // Small delay to ensure all modules are loaded
        setTimeout(init, 50);
    }
}

startApp();

// Export functions that need to be called from other modules
// Using window to avoid circular dependencies between modules
window.switchTab = switchTab;
window.loadGoals = loadGoals;
window.loadTasks = loadTasks;
window.updateGoalSelect = updateGoalSelect;
window.updateGoalFilter = updateGoalFilter;

