/**
 * Events Module
 * 
 * Sets up all event listeners for user interactions
 */

import { handleAddTask, handleSearch, handleSortChange, handleFilterChange, toggleCompleted, updateGoalSelect, updateGoalFilter } from './tasks.js';
import { handleAddGoal } from './goals.js';
import * as state from './state.js';

// ============================================
// EVENT LISTENER SETUP
// ============================================

/**
 * Set up all event listeners for user interactions
 */
export function setupEventListeners() {
    // Task form submission
    const taskForm = document.getElementById('taskForm');
    if (taskForm) {
        taskForm.addEventListener('submit', handleAddTask);
    }
    
    // Toggle task form visibility
    const toggleTaskFormBtn = document.getElementById('toggleTaskForm');
    const taskFormContainer = document.getElementById('taskFormContainer');
    if (toggleTaskFormBtn && taskFormContainer) {
        toggleTaskFormBtn.addEventListener('click', () => {
            const isVisible = taskFormContainer.style.display !== 'none';
            
            if (isVisible) {
                state.clearEditingTaskId();
                document.getElementById('taskForm').reset();
                
                const formTitle = taskFormContainer.querySelector('h2');
                const submitButton = document.querySelector('#taskForm button[type="submit"]');
                if (formTitle) {
                    formTitle.textContent = 'Add New Task';
                }
                if (submitButton) {
                    submitButton.textContent = 'Add Task';
                }
            }
            
            taskFormContainer.style.display = isVisible ? 'none' : 'block';
            toggleTaskFormBtn.innerHTML = isVisible 
                ? '<span class="btn-icon">+</span> Add New Task'
                : '<span class="btn-icon">−</span> Cancel';
        });
    }
    
    // Goal form submission
    const goalForm = document.getElementById('goalForm');
    if (goalForm) {
        goalForm.addEventListener('submit', handleAddGoal);
    }
    
    // Search input
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', handleSearch);
    }
    
    // Filter dropdowns
    const filterPriority = document.getElementById('filterPriority');
    if (filterPriority) {
        filterPriority.addEventListener('change', handleFilterChange);
    }
    
    const filterGoal = document.getElementById('filterGoal');
    if (filterGoal) {
        filterGoal.addEventListener('change', handleFilterChange);
    }
    
    // Sort dropdown
    const sortTasks = document.getElementById('sortTasks');
    if (sortTasks) {
        sortTasks.addEventListener('change', handleSortChange);
    }
    
    // Show/hide completed tasks toggle button
    const showCompletedBtn = document.getElementById('showCompleted');
    if (showCompletedBtn) {
        showCompletedBtn.addEventListener('click', toggleCompleted);
    }
}
