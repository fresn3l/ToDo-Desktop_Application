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
        // Setup event listeners first
        setupEventListeners();
        
        // Setup tab navigation
        setupTabs();
        
        // Setup journal
        setupJournal();
        
        // Setup notification settings
        setupNotificationSettings();
        
        // Load initial data
        await Promise.all([
            loadTasks(),
            loadGoals()
        ]);
        
        // Update goal dropdowns after both tasks and goals are loaded
        updateGoalSelect();
        updateGoalFilter();
        
        // Switch to tasks tab by default
        switchTab('tasks');
        
        // Animate elements on load
        setTimeout(() => ui.animateElements(), 100);
        
    } catch (error) {
        console.error('Error initializing application:', error);
        utils.showErrorFeedback('Failed to initialize application. Please refresh the page.');
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

// Make switchTab available globally for tasks.js
window.switchTab = switchTab;

// Make loadGoals and loadTasks available globally to avoid circular dependencies
window.loadGoals = loadGoals;
window.loadTasks = loadTasks;
window.updateGoalSelect = updateGoalSelect;
window.updateGoalFilter = updateGoalFilter;

