/**
 * Tasks Module
 * 
 * Handles all task-related operations including:
 * - Loading tasks from backend
 * - Creating, updating, deleting tasks
 * - Rendering tasks with filtering and sorting
 * - Task form handling
 */

import * as state from './state.js';
import * as utils from './utils.js';
import * as ui from './ui.js';

// ============================================
// TASK DATA LOADING
// ============================================

/**
 * Load all tasks from the Python backend
 */
export async function loadTasks() {
    try {
        if (typeof eel !== 'undefined' && eel.get_tasks) {
            const tasks = await eel.get_tasks()();
            state.setTasks(tasks || []);
        } else {
            state.setTasks([]);
        }
        
        renderTasks();
        updateGoalFilter();
        updateGoalSelect();
    } catch (error) {
        console.error('Error loading tasks:', error);
        // Still render with empty tasks if loading fails
        state.setTasks([]);
        renderTasks();
    }
}

// ============================================
// TASK CRUD OPERATIONS
// ============================================

/**
 * Handle adding or updating a task
 */
export async function handleAddTask(e) {
    e.preventDefault();
    
    const title = document.getElementById('taskTitle').value.trim();
    const description = document.getElementById('taskDescription').value.trim();
    const priority = document.getElementById('taskPriority').value;
    const dueDate = document.getElementById('taskDueDate').value;
    const goalSelect = document.getElementById('taskGoal');
    const timeSpentInput = document.getElementById('taskTimeSpent');
    const recurrenceSelect = document.getElementById('taskRecurrence');
    const recurrenceEndDateInput = document.getElementById('taskRecurrenceEndDate');
    
    const goalId = goalSelect.value ? parseInt(goalSelect.value) : null;
    const timeSpent = timeSpentInput && timeSpentInput.value ? parseFloat(timeSpentInput.value) : null;
    const recurrence = recurrenceSelect.value || null;
    const recurrenceEndDate = recurrenceEndDateInput && recurrenceEndDateInput.value ? recurrenceEndDateInput.value : null;
    
    if (timeSpent !== null && (isNaN(timeSpent) || timeSpent < 0)) {
        utils.showErrorFeedback('Time spent must be a non-negative number');
        return;
    }
    
    if (!title) {
        utils.showErrorFeedback('Please enter a task title');
        return;
    }
    
    const form = document.getElementById('taskForm');
    if (!form) {
        utils.showErrorFeedback('Form not found. Please refresh the page.');
        return;
    }
    
    const submitButton = form.querySelector('button[type="submit"]');
    if (!submitButton) {
        utils.showErrorFeedback('Submit button not found. Please refresh the page.');
        return;
    }
    
    const isEditMode = state.getEditingTaskId() !== null;
    const taskId = isEditMode ? state.getEditingTaskId() : null;
    
    const originalText = submitButton.textContent;
    submitButton.textContent = isEditMode ? 'Updating...' : 'Adding...';
    submitButton.disabled = true;
    
    try {
        if (isEditMode) {
            const result = await eel.update_task(taskId, title, description, priority, dueDate, goalId, timeSpent, recurrence, recurrenceEndDate)();
            if (!result) {
                throw new Error('Task update failed - task not found');
            }
            state.clearEditingTaskId();
            utils.showSuccessFeedback('Task updated successfully!');
        } else {
            await eel.add_task(title, description, priority, dueDate, goalId, timeSpent, recurrence, recurrenceEndDate)();
            utils.showSuccessFeedback('Task added successfully!');
        }
        
        document.getElementById('taskForm').reset();
        
        const formContainer = document.getElementById('taskFormContainer');
        const formTitle = formContainer ? formContainer.querySelector('h2') : null;
        if (formTitle) {
            formTitle.textContent = 'Add New Task';
        }
        submitButton.textContent = 'Add Task';
        
        const toggleTaskFormBtn = document.getElementById('toggleTaskForm');
        if (formContainer) {
            formContainer.style.display = 'none';
        }
        if (toggleTaskFormBtn) {
            toggleTaskFormBtn.innerHTML = '<span class="btn-icon">+</span> Add New Task';
        }
        
        await loadTasks();
        if (window.loadGoals) {
            await window.loadGoals();
        }
    } catch (error) {
        console.error(`Error ${isEditMode ? 'updating' : 'adding'} task:`, error);
        utils.showErrorFeedback(`Failed to ${isEditMode ? 'update' : 'add'} task. Please try again.`);
    } finally {
        submitButton.textContent = originalText;
        submitButton.disabled = false;
    }
}

/**
 * Toggle task completion status
 */
export async function toggleTask(taskId) {
    try {
        if (!taskId || isNaN(taskId)) {
            console.error('Invalid task ID:', taskId);
            return false;
        }
        
        const result = await eel.toggle_task(taskId)();
        
        if (!result) {
            console.error('Task not found or toggle failed for ID:', taskId);
            utils.showErrorFeedback('Failed to toggle task. Please try again.');
            return false;
        }
        
        await loadTasks();
        if (window.loadGoals) {
            await window.loadGoals();
        }
        return true;
    } catch (error) {
        console.error('Error toggling task:', error);
        utils.showErrorFeedback('Failed to toggle task. Please try again.');
        return false;
    }
}

/**
 * Delete a task
 */
export async function deleteTask(taskId) {
    if (!confirm('Are you sure you want to delete this task?')) return;
    
    try {
        await eel.delete_task(taskId)();
        await loadTasks();
        // loadGoals will be called from main app.js
    } catch (error) {
        console.error('Error deleting task:', error);
        alert('Failed to delete task. Please try again.');
    }
}

/**
 * Edit a task by populating the form
 */
export function editTask(taskId) {
    const tasks = state.getTasks();
    const task = tasks.find(t => t.id === taskId);
    if (!task) {
        utils.showErrorFeedback('Task not found. Please refresh the page.');
        return;
    }
    
    state.setEditingTaskId(taskId);
    
    document.getElementById('taskTitle').value = task.title;
    document.getElementById('taskDescription').value = task.description || '';
    document.getElementById('taskPriority').value = task.priority;
    document.getElementById('taskDueDate').value = task.due_date || '';
    
    const goalSelect = document.getElementById('taskGoal');
    if (goalSelect) {
        goalSelect.value = task.goal_id || '';
    }
    
    const timeSpentInput = document.getElementById('taskTimeSpent');
    if (timeSpentInput) {
        timeSpentInput.value = task.time_spent || '';
    }
    
    // Populate recurrence fields
    const recurrenceSelect = document.getElementById('taskRecurrence');
    const recurrenceEndDateInput = document.getElementById('taskRecurrenceEndDate');
    const recurrenceEndDateGroup = document.getElementById('recurrenceEndDateGroup');
    
    if (recurrenceSelect) {
        // For editing, check if this is a template or instance
        // If it's an instance, we need to find the template to get recurrence settings
        let recurrenceValue = task.recurrence || '';
        let recurrenceEndDateValue = task.recurrence_end_date || '';
        
        // If this is an instance (not a template), find the template
        if (!task.is_recurring_template && task.parent_task_id) {
            const tasks = state.getTasks();
            const template = tasks.find(t => t.id === task.parent_task_id && t.is_recurring_template);
            if (template) {
                recurrenceValue = template.recurrence || '';
                recurrenceEndDateValue = template.recurrence_end_date || '';
            }
        }
        
        recurrenceSelect.value = recurrenceValue;
        
        // Show/hide recurrence end date group based on recurrence selection
        if (recurrenceSelect.value) {
            if (recurrenceEndDateGroup) {
                recurrenceEndDateGroup.style.display = 'block';
            }
        } else {
            if (recurrenceEndDateGroup) {
                recurrenceEndDateGroup.style.display = 'none';
            }
        }
    }
    
    if (recurrenceEndDateInput) {
        // Get recurrence end date from template if this is an instance
        let recurrenceEndDateValue = task.recurrence_end_date || '';
        if (!task.is_recurring_template && task.parent_task_id) {
            const tasks = state.getTasks();
            const template = tasks.find(t => t.id === task.parent_task_id && t.is_recurring_template);
            if (template) {
                recurrenceEndDateValue = template.recurrence_end_date || '';
            }
        }
        recurrenceEndDateInput.value = recurrenceEndDateValue;
    }
    
    const formContainer = document.getElementById('taskFormContainer');
    const formTitle = formContainer ? formContainer.querySelector('h2') : null;
    if (formTitle) {
        formTitle.textContent = 'Edit Task';
    }
    
    const submitButton = document.querySelector('#taskForm button[type="submit"]');
    if (submitButton) {
        submitButton.textContent = 'Update Task';
    }
    
    if (formContainer) {
        formContainer.style.display = 'block';
    }
    
    const toggleTaskFormBtn = document.getElementById('toggleTaskForm');
    if (toggleTaskFormBtn) {
        toggleTaskFormBtn.innerHTML = '<span class="btn-icon">−</span> Cancel';
    }
    
    // Switch to tasks tab
    if (window.switchTab) {
        window.switchTab('tasks');
    }
    
    setTimeout(() => {
        const taskForm = document.querySelector('.task-form');
        if (taskForm) {
            taskForm.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }, 100);
}

// ============================================
// TASK RENDERING
// ============================================

/**
 * Render tasks with filtering and sorting
 */
export function renderTasks() {
    const container = document.getElementById('tasksContainer');
    if (!container) {
        console.warn('Tasks container not found');
        return;
    }
    
    const tasks = state.getTasks();
    const currentFilter = state.getCurrentFilter();
    const currentSort = state.getCurrentSort();
    const showCompleted = state.getShowCompleted();
    const goals = state.getGoals();
    
    console.log('Rendering tasks:', tasks.length, 'total tasks');
    
    let filteredTasks = [...tasks];
    
    // Apply search filter
    if (currentFilter.search) {
        filteredTasks = filteredTasks.filter(task => 
            task.title.toLowerCase().includes(currentFilter.search) ||
            (task.description && task.description.toLowerCase().includes(currentFilter.search))
        );
    }
    
    // Apply priority filter
    if (currentFilter.priority) {
        filteredTasks = filteredTasks.filter(task => task.priority === currentFilter.priority);
    }
    
    // Apply goal filter
    if (currentFilter.goal) {
        const goalId = parseInt(currentFilter.goal);
        filteredTasks = filteredTasks.filter(task => task.goal_id === goalId);
    }
    
    // Filter completed tasks
    if (!showCompleted) {
        filteredTasks = filteredTasks.filter(task => !task.completed);
    }
    
    // Filter out not_completed tasks (tasks that missed deadline by >24 hours)
    filteredTasks = filteredTasks.filter(task => !task.not_completed);
    
    console.log('After filtering:', filteredTasks.length, 'tasks to display');
    
    // Apply sort-specific filters
    if (currentSort === 'due-today') {
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const tomorrow = new Date(today);
        tomorrow.setDate(tomorrow.getDate() + 1);
        
        filteredTasks = filteredTasks.filter(task => {
            if (!task.due_date) return false;
            const dueDate = new Date(task.due_date);
            dueDate.setHours(0, 0, 0, 0);
            return dueDate >= today && dueDate < tomorrow;
        });
    } else if (currentSort === 'due-week') {
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const weekFromNow = new Date(today);
        weekFromNow.setDate(weekFromNow.getDate() + 7);
        
        filteredTasks = filteredTasks.filter(task => {
            if (!task.due_date) return false;
            const dueDate = new Date(task.due_date);
            dueDate.setHours(0, 0, 0, 0);
            return dueDate >= today && dueDate <= weekFromNow;
        });
    }
    
    // Render
    if (filteredTasks.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <h3>No tasks found</h3>
                <p>${tasks.length === 0 ? 'Add your first task above!' : 'Try adjusting your filters or sort options.'}</p>
            </div>
        `;
        return;
    }
    
    let html = '';
    
    if (currentSort === 'category') {
    const tasksByGoal = {};
    filteredTasks.forEach(task => {
            const goalId = task.goal_id || 'Misc';
        if (!tasksByGoal[goalId]) {
            tasksByGoal[goalId] = [];
        }
        tasksByGoal[goalId].push(task);
    });
    
        const priorityOrder = { Now: 3, Next: 2, Later: 1 };
        Object.keys(tasksByGoal).forEach(goalId => {
            tasksByGoal[goalId].sort((a, b) => {
                if (a.completed !== b.completed) {
                    return a.completed ? 1 : -1;
                }
                const priorityA = priorityOrder[a.priority] || 0;
                const priorityB = priorityOrder[b.priority] || 0;
                if (priorityA !== priorityB) {
                    return priorityB - priorityA;
                }
                if (a.due_date && b.due_date) {
                    return new Date(a.due_date) - new Date(b.due_date);
                }
                if (a.due_date) return -1;
                if (b.due_date) return 1;
                return 0;
            });
        });
        
        const sortedGoalIds = Object.keys(tasksByGoal).sort((a, b) => {
        if (a === 'Misc') return 1;
        if (b === 'Misc') return -1;
        return parseInt(a) - parseInt(b);
    });
    
        sortedGoalIds.forEach(goalId => {
            const goal = goals.find(g => g.id === parseInt(goalId));
        const goalName = goal ? goal.title : 'Misc';
        html += `<div class="category-header">${utils.escapeHtml(goalName)}</div>`;
        html += `<div class="category-tasks-row">`;
            tasksByGoal[goalId].forEach(task => {
                html += createTaskHTML(task, goals);
            });
            html += `</div>`;
        });
    } else if (currentSort === 'due-date' || currentSort === 'due-today' || currentSort === 'due-week') {
        const sortedTasks = [...filteredTasks].sort((a, b) => {
            if (a.completed !== b.completed) {
                return a.completed ? 1 : -1;
            }
            if (a.due_date && b.due_date) {
                return new Date(a.due_date) - new Date(b.due_date);
            }
            if (a.due_date) return -1;
            if (b.due_date) return 1;
            const priorityOrder = { Now: 3, Next: 2, Later: 1 };
            const priorityA = priorityOrder[a.priority] || 0;
            const priorityB = priorityOrder[b.priority] || 0;
            return priorityB - priorityA;
        });
        
        const tasksByDate = {};
        sortedTasks.forEach(task => {
            let dateKey = 'No Due Date';
            if (task.due_date) {
                const dueDate = new Date(task.due_date);
                const today = new Date();
                today.setHours(0, 0, 0, 0);
                const tomorrow = new Date(today);
                tomorrow.setDate(tomorrow.getDate() + 1);
                const weekFromNow = new Date(today);
                weekFromNow.setDate(weekFromNow.getDate() + 7);
                
                dueDate.setHours(0, 0, 0, 0);
                
                if (dueDate < today) {
                    dateKey = 'Overdue';
                } else if (dueDate >= today && dueDate < tomorrow) {
                    dateKey = 'Due Today';
                } else if (dueDate >= tomorrow && dueDate <= weekFromNow) {
                    dateKey = 'Due This Week';
                } else {
                    dateKey = dueDate.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
                }
            }
            
            if (!tasksByDate[dateKey]) {
                tasksByDate[dateKey] = [];
            }
            tasksByDate[dateKey].push(task);
        });
        
        const dateOrder = ['Overdue', 'Due Today', 'Due This Week', 'No Due Date'];
        const sortedDateKeys = Object.keys(tasksByDate).sort((a, b) => {
            const aIndex = dateOrder.indexOf(a);
            const bIndex = dateOrder.indexOf(b);
            if (aIndex !== -1 && bIndex !== -1) return aIndex - bIndex;
            if (aIndex !== -1) return -1;
            if (bIndex !== -1) return 1;
            return a.localeCompare(b);
        });
        
        sortedDateKeys.forEach(dateKey => {
            html += `<div class="category-header">${utils.escapeHtml(dateKey)}</div>`;
            html += `<div class="category-tasks-row">`;
            tasksByDate[dateKey].forEach(task => {
                html += createTaskHTML(task, goals);
        });
        html += `</div>`;
    });
    } else if (currentSort === 'priority') {
        const priorityOrder = { Now: 3, Next: 2, Later: 1 };
        const sortedTasks = [...filteredTasks].sort((a, b) => {
            if (a.completed !== b.completed) {
                return a.completed ? 1 : -1;
            }
            const priorityA = priorityOrder[a.priority] || 0;
            const priorityB = priorityOrder[b.priority] || 0;
            if (priorityA !== priorityB) {
                return priorityB - priorityA;
            }
            if (a.due_date && b.due_date) {
                return new Date(a.due_date) - new Date(b.due_date);
            }
            if (a.due_date) return -1;
            if (b.due_date) return 1;
            return 0;
        });
        
        const tasksByPriority = {};
        sortedTasks.forEach(task => {
            const priority = task.priority || 'Later';
            if (!tasksByPriority[priority]) {
                tasksByPriority[priority] = [];
            }
            tasksByPriority[priority].push(task);
        });
        
        const priorityOrderKeys = ['Now', 'Next', 'Later'];
        priorityOrderKeys.forEach(priority => {
            if (tasksByPriority[priority] && tasksByPriority[priority].length > 0) {
                html += `<div class="category-header">${utils.escapeHtml(priority)} Priority</div>`;
                html += `<div class="category-tasks-row">`;
                tasksByPriority[priority].forEach(task => {
                    html += createTaskHTML(task, goals);
                });
                html += `</div>`;
            }
        });
    }
    
    container.innerHTML = html;
    
    // Event delegation for checkboxes and buttons
    if (container._taskChangeHandler) {
        container.removeEventListener('change', container._taskChangeHandler);
    }
    if (container._taskClickHandler) {
        container.removeEventListener('click', container._taskClickHandler);
    }
    
    container._taskChangeHandler = async (e) => {
        if (e.target && e.target.classList.contains('task-checkbox')) {
            e.stopPropagation();
            e.preventDefault();
            
            const taskId = parseInt(e.target.id.replace('checkbox-', ''));
            if (taskId && !isNaN(taskId)) {
                const intendedState = e.target.checked;
                e.target.disabled = true;
                
                try {
                    const success = await toggleTask(taskId);
                    if (!success) {
                        e.target.checked = !intendedState;
                    }
                } catch (error) {
                    e.target.checked = !intendedState;
                    console.error('Error toggling task:', error);
                } finally {
                    e.target.disabled = false;
                }
            }
        }
    };
    
    container._taskClickHandler = async (e) => {
        if (e.target && e.target.id) {
            const id = e.target.id;
            
            if (id.startsWith('delete-')) {
                const taskId = parseInt(id.replace('delete-', ''));
                if (taskId && !isNaN(taskId)) {
                    await deleteTask(taskId);
                }
            }
            
            if (id.startsWith('edit-')) {
                const taskId = parseInt(id.replace('edit-', ''));
                if (taskId && !isNaN(taskId)) {
                    editTask(taskId);
                }
            }
        }
    };
    
    container.addEventListener('change', container._taskChangeHandler);
    container.addEventListener('click', container._taskClickHandler);
    
    // Add ripple effects
    filteredTasks.forEach(task => {
        const checkbox = document.getElementById(`checkbox-${task.id}`);
        const deleteBtn = document.getElementById(`delete-${task.id}`);
        const editBtn = document.getElementById(`edit-${task.id}`);
        
        if (checkbox) {
            ui.addRippleEffect(checkbox.parentElement);
        }
        if (deleteBtn) {
            ui.addRippleEffect(deleteBtn);
        }
        if (editBtn) {
            ui.addRippleEffect(editBtn);
        }
    });
    
    setTimeout(() => {
        const elements = document.querySelectorAll('.task-item, .category-header');
        elements.forEach((el, index) => {
            el.style.opacity = '0';
            el.style.transform = 'translateY(20px)';
            setTimeout(() => {
                el.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                el.style.opacity = '1';
                el.style.transform = 'translateY(0)';
            }, index * 50);
        });
    }, 100);
}

/**
 * Create HTML for a task
 */
function createTaskHTML(task, goals) {
    const isOverdue = task.due_date && !task.completed && new Date(task.due_date) < new Date();
    const dueDateFormatted = task.due_date ? new Date(task.due_date).toLocaleDateString() : '';
    const goal = goals.find(g => g.id === task.goal_id);
    const isRecurring = task.recurrence && task.recurrence !== '';
    const recurrenceLabel = isRecurring ? {
        'daily': '🔄 Daily',
        'weekly': '🔄 Weekly',
        'monthly': '🔄 Monthly',
        'yearly': '🔄 Yearly'
    }[task.recurrence] || '🔄 Recurring' : '';
    
    return `
        <div class="task-item ${task.completed ? 'completed' : ''}">
            <div class="task-header">
                <input type="checkbox" id="checkbox-${task.id}" class="task-checkbox" ${task.completed ? 'checked' : ''}>
                <div class="task-content">
                    <div class="task-title">${utils.escapeHtml(task.title)}</div>
                    ${task.description ? `<div class="task-description">${utils.escapeHtml(task.description)}</div>` : ''}
                    <div class="task-meta">
                        <span class="task-badge priority-${task.priority}">${task.priority}</span>
                        ${goal ? `<span class="goal-badge">🎯 ${utils.escapeHtml(goal.title)}</span>` : ''}
                        ${isRecurring ? `<span class="recurrence-badge">${recurrenceLabel}</span>` : ''}
                        ${task.due_date ? `<span class="due-date ${isOverdue ? 'overdue' : ''}">📅 ${dueDateFormatted}${isOverdue ? ' (Overdue!)' : ''}</span>` : ''}
                    </div>
                    <div class="task-actions">
                        <button class="btn-edit" id="edit-${task.id}">Edit</button>
                        <button class="btn-delete" id="delete-${task.id}">Delete</button>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// ============================================
// FILTERING AND SORTING
// ============================================

/**
 * Handle search input changes
 */
export function handleSearch(e) {
    state.setCurrentFilter({ search: e.target.value.toLowerCase() });
    renderTasks();
}

/**
 * Handle sort dropdown changes
 */
export function handleSortChange() {
    const sortSelect = document.getElementById('sortTasks');
    if (sortSelect) {
        state.setCurrentSort(sortSelect.value);
        renderTasks();
    }
}

/**
 * Handle filter dropdown changes
 */
export function handleFilterChange() {
    const prioritySelect = document.getElementById('filterPriority');
    const goalSelect = document.getElementById('filterGoal');
    
    const filter = {};
    if (prioritySelect) {
        filter.priority = prioritySelect.value;
    }
    if (goalSelect) {
        filter.goal = goalSelect.value;
    }
    
    state.setCurrentFilter(filter);
    renderTasks();
}

/**
 * Toggle visibility of completed tasks
 */
export function toggleCompleted() {
    state.setShowCompleted(!state.getShowCompleted());
    
    const btn = document.getElementById('showCompleted');
    if (btn) {
        btn.textContent = state.getShowCompleted() ? 'Hide Completed' : 'Show Completed';
    }
    
    renderTasks();
}

/**
 * Update goal select dropdown in task form
 */
export function updateGoalSelect() {
    const select = document.getElementById('taskGoal');
    if (!select) return;
    
    const currentValue = select.value;
    const goals = state.getGoals();
    
    select.innerHTML = '<option value="">No Goal</option>';
    
    goals.forEach(goal => {
        const option = document.createElement('option');
        option.value = goal.id;
        option.textContent = goal.title;
        select.appendChild(option);
    });
    
    if (currentValue && goals.find(g => g.id === parseInt(currentValue))) {
        select.value = currentValue;
    }
}

/**
 * Update goal filter dropdown in filter controls
 */
export function updateGoalFilter() {
    const select = document.getElementById('filterGoal');
    if (!select) return;
    
    const currentValue = select.value;
    const goals = state.getGoals();
    
    select.innerHTML = '<option value="">All Goals</option>';
    
    goals.forEach(goal => {
        const option = document.createElement('option');
        option.value = goal.id;
        option.textContent = goal.title;
        select.appendChild(option);
    });
    
    if (currentValue && goals.find(g => g.id === parseInt(currentValue))) {
        select.value = currentValue;
    }
}
