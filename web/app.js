/**
 * Main Application Entry Point
 * 
 * This file initializes the application and coordinates all modules.
 * All functionality has been modularized for better maintainability.
 */

// Import all modules
import * as state from './js/state.js';
import * as ui from './js/ui.js';
import { loadTasks } from './js/tasks.js';
import { loadGoals } from './js/goals.js';
import { setupEventListeners } from './js/events.js';
import { setupTabs } from './js/tabs.js';

/**
 * Initialize the application
 */
async function init() {
    // Show loading state
    ui.showLoadingState();
    
    // Load all data in parallel
    await Promise.all([loadTasks(), loadGoals()]);
    
    // Setup UI interactions
    setupEventListeners();
    setupTabs();
    
    // Hide loading state
    ui.hideLoadingState();
    
    // Add smooth entrance animations
    ui.animateElements();
}

// Initialize when page loads
init();
