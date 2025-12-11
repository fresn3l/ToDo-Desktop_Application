/**
 * Events Module
 * 
 * Sets up all event listeners for the application.
 */

import { handleAddTask, handleSearch, handleFilterChange, toggleCompleted } from './tasks.js';
import { handleAddGoal } from './goals.js';

/**
 * Setup all event listeners
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
    
    // Search
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', handleSearch);
    }
    
    // Filters
    const filterPriority = document.getElementById('filterPriority');
    if (filterPriority) {
        filterPriority.addEventListener('change', handleFilterChange);
    }
    
    const filterGoal = document.getElementById('filterGoal');
    if (filterGoal) {
        filterGoal.addEventListener('change', handleFilterChange);
    }
    
    const showCompleted = document.getElementById('showCompleted');
    if (showCompleted) {
        showCompleted.addEventListener('click', toggleCompleted);
    }
    
    // Keyboard shortcuts
    setupKeyboardShortcuts();
}

/**
 * Setup keyboard shortcuts
 */
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + K to focus search
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const searchInput = document.getElementById('searchInput');
            if (searchInput) {
                searchInput.focus();
            }
        }
        
        // Escape to clear search
        if (e.key === 'Escape') {
            const searchInput = document.getElementById('searchInput');
            if (document.activeElement === searchInput && searchInput) {
                searchInput.value = '';
                handleSearch({ target: searchInput });
            }
        }
    });
}

