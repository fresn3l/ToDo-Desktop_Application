/**
 * State Management Module
 * 
 * Centralized state management for the application.
 * This module exports the global state variables that are shared across modules.
 */

// Global application state
export let tasks = [];
export let goals = [];
export let showCompleted = false;
export let currentFilter = {
    priority: '',
    goal: '',
    search: ''
};

/**
 * Update tasks array
 */
export function setTasks(newTasks) {
    tasks = newTasks;
}

/**
 * Update goals array
 */
export function setGoals(newGoals) {
    goals = newGoals;
}

/**
 * Toggle showCompleted flag
 */
export function toggleShowCompleted() {
    showCompleted = !showCompleted;
    return showCompleted;
}

/**
 * Update filter values
 */
export function updateFilter(filterName, value) {
    currentFilter[filterName] = value;
}

/**
 * Get current filter
 */
export function getFilter() {
    return { ...currentFilter };
}

