/**
 * State Management Module
 * 
 * Manages global application state including tasks, goals, filters, and UI state.
 * This module provides a centralized state store for the application.
 */

// ============================================
// GLOBAL STATE VARIABLES
// ============================================

/**
 * Array of all tasks loaded from the backend
 * Each task object contains: id, title, description, priority, due_date, 
 * completed, goal_id, created_at, completed_at, time_spent, not_completed
 */
let tasks = [];

/**
 * Array of all goals loaded from the backend
 * Each goal object contains: id, title, description, created_at, time_goal
 */
let goals = [];

/**
 * Boolean flag to control visibility of completed tasks
 * false = hide completed tasks, true = show completed tasks
 */
let showCompleted = false;

/**
 * Filter object containing current filter settings
 * Used to filter tasks by priority, goal, and search text
 */
let currentFilter = {
    priority: '',  // Filter by priority: 'Now', 'Next', 'Later', or '' for all
    goal: '',      // Filter by goal ID or '' for all goals
    search: ''      // Search text to filter task titles/descriptions
};

/**
 * Current sort mode for tasks
 * Options: 'category', 'due-date', 'due-today', 'due-week', 'priority'
 */
let currentSort = 'category';

/**
 * Currently editing task ID (if any)
 */
let editingTaskId = null;

/**
 * Currently editing goal ID (if any)
 */
let editingGoalId = null;

// ============================================
// STATE GETTERS
// ============================================

export function getTasks() {
    return tasks;
}

export function getGoals() {
    return goals;
}

export function getShowCompleted() {
    return showCompleted;
}

export function getCurrentFilter() {
    return currentFilter;
}

export function getCurrentSort() {
    return currentSort;
}

// ============================================
// STATE SETTERS
// ============================================

export function setTasks(newTasks) {
    tasks = newTasks;
}

export function setGoals(newGoals) {
    goals = newGoals;
}

export function setShowCompleted(value) {
    showCompleted = value;
}

export function setCurrentFilter(filter) {
    currentFilter = { ...currentFilter, ...filter };
}

export function setCurrentSort(sort) {
    currentSort = sort;
}

export function getEditingTaskId() {
    return editingTaskId;
}

export function setEditingTaskId(id) {
    editingTaskId = id;
}

export function clearEditingTaskId() {
    editingTaskId = null;
}

export function getEditingGoalId() {
    return editingGoalId;
}

export function setEditingGoalId(id) {
    editingGoalId = id;
}

export function clearEditingGoalId() {
    editingGoalId = null;
}

// ============================================
// STATE RESET
// ============================================

export function resetState() {
    tasks = [];
    goals = [];
    showCompleted = false;
    currentFilter = {
        priority: '',
        goal: '',
        search: ''
    };
    currentSort = 'category';
    editingTaskId = null;
    editingGoalId = null;
}
