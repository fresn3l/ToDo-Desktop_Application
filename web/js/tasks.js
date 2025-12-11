/**
 * Tasks Module
 * 
 * Handles all task-related operations: loading, rendering, creating, updating, deleting.
 */

import * as state from './state.js';
import * as ui from './ui.js';
import * as utils from './utils.js';
import { loadGoals, updateGoalSelect, updateGoalFilter } from './goals.js';

/**
 * Load tasks from Python backend
 */
export async function loadTasks() {
    try {
        state.setTasks(await eel.get_tasks()());
        renderTasks();
        updateGoalFilter();
        updateGoalSelect();
    } catch (error) {
        console.error('Error loading tasks:', error);
    }
}

/**
 * Render tasks organized by goal, then priority
 */
export function renderTasks() {
    const container = document.getElementById('tasksContainer');
    
    // Filter tasks
    let filteredTasks = [...state.tasks];
    const filter = state.getFilter();
    
    // Apply search filter
    if (filter.search) {
        filteredTasks = filteredTasks.filter(task => 
            task.title.toLowerCase().includes(filter.search) ||
            (task.description && task.description.toLowerCase().includes(filter.search))
        );
    }
    
    // Apply priority filter
    if (filter.priority) {
        filteredTasks = filteredTasks.filter(task => task.priority === filter.priority);
    }
    
    // Apply goal filter
    if (filter.goal) {
        const goalId = parseInt(filter.goal);
        filteredTasks = filteredTasks.filter(task => task.goal_id === goalId);
    }
    
    // Filter completed tasks
    if (!state.showCompleted) {
        filteredTasks = filteredTasks.filter(task => !task.completed);
    }
    
    // Sort: incomplete first, then by goal, then by priority, then by due date
    filteredTasks.sort((a, b) => {
        if (a.completed !== b.completed) {
            return a.completed ? 1 : -1;
        }
        // Sort by goal (tasks without goal last, then by goal ID)
        const goalA = a.goal_id === null ? 'Misc' : String(a.goal_id);
        const goalB = b.goal_id === null ? 'Misc' : String(b.goal_id);
        if (goalA !== goalB) {
            if (goalA === 'Misc') return 1;
            if (goalB === 'Misc') return -1;
            return parseInt(goalA) - parseInt(goalB);
        }
        // Sort by priority within goal
        const priorityA = utils.PRIORITY_ORDER[a.priority] || 0;
        const priorityB = utils.PRIORITY_ORDER[b.priority] || 0;
        if (priorityA !== priorityB) {
            return priorityB - priorityA; // Higher priority first
        }
        // Sort by due date
        if (a.due_date && b.due_date) {
            return new Date(a.due_date) - new Date(b.due_date);
        }
        if (a.due_date) return -1;
        if (b.due_date) return 1;
        return 0;
    });
    
    // Render
    if (filteredTasks.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <h3>No tasks found</h3>
                <p>${state.tasks.length === 0 ? 'Add your first task above!' : 'Try adjusting your filters.'}</p>
            </div>
        `;
        return;
    }
    
    // Group by goal
    const tasksByGoal = {};
    filteredTasks.forEach(task => {
        const goalId = task.goal_id === null ? 'Misc' : String(task.goal_id);
        if (!tasksByGoal[goalId]) {
            tasksByGoal[goalId] = [];
        }
        tasksByGoal[goalId].push(task);
    });
    
    let html = '';
    const sortedGoalKeys = Object.keys(tasksByGoal).sort((a, b) => {
        if (a === 'Misc') return 1;
        if (b === 'Misc') return -1;
        return parseInt(a) - parseInt(b);
    });
    
    sortedGoalKeys.forEach(goalKey => {
        const goal = state.goals.find(g => String(g.id) === goalKey);
        const goalName = goal ? goal.title : 'Misc';
        html += `<div class="category-header">${utils.escapeHtml(goalName)}</div>`;
        html += `<div class="category-tasks-row">`;
        tasksByGoal[goalKey].forEach(task => {
            html += createTaskHTML(task);
        });
        html += `</div>`;
    });
    
    container.innerHTML = html;
    
    // Add event listeners
    filteredTasks.forEach(task => {
        const checkbox = document.getElementById(`checkbox-${task.id}`);
        const deleteBtn = document.getElementById(`delete-${task.id}`);
        const editBtn = document.getElementById(`edit-${task.id}`);
        
        if (checkbox) {
            checkbox.addEventListener('change', () => toggleTask(task.id));
            ui.addRippleEffect(checkbox.parentElement);
        }
        if (deleteBtn) {
            deleteBtn.addEventListener('click', () => deleteTask(task.id));
            ui.addRippleEffect(deleteBtn);
        }
        if (editBtn) {
            editBtn.addEventListener('click', () => editTask(task.id));
            ui.addRippleEffect(editBtn);
        }
    });
    
    // Re-animate elements
    setTimeout(() => ui.animateElements(), 100);
}

/**
 * Create HTML for a task
 */
function createTaskHTML(task) {
    const isOverdue = utils.isOverdue(task.due_date, task.completed);
    const dueDateFormatted = utils.formatDate(task.due_date);
    const goal = state.goals.find(g => g.id === task.goal_id);
    
    return `
        <div class="task-item ${task.completed ? 'completed' : ''}">
            <div class="task-header">
                <input type="checkbox" id="checkbox-${task.id}" class="task-checkbox" ${task.completed ? 'checked' : ''}>
                <div class="task-content">
                    <div class="task-title">${utils.escapeHtml(task.title)}</div>
                    ${task.description ? `<div class="task-description">${utils.escapeHtml(task.description)}</div>` : ''}
                    <div class="task-meta">
                        <span class="task-badge priority-${task.priority.toLowerCase()}">${task.priority}</span>
                        ${goal ? `<span class="goal-badge">🎯 ${utils.escapeHtml(goal.title)}</span>` : ''}
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

/**
 * Handle adding a new task
 */
export async function handleAddTask(e) {
    e.preventDefault();
    
    const title = document.getElementById('taskTitle').value.trim();
    const description = document.getElementById('taskDescription').value.trim();
    const priority = document.getElementById('taskPriority').value;
    const dueDate = document.getElementById('taskDueDate').value;
    const goalSelect = document.getElementById('taskGoal');
    
    const goalId = goalSelect.value ? parseInt(goalSelect.value) : null;
    
    if (!title) {
        ui.showErrorFeedback('Please enter a task title');
        return;
    }
    
    const form = document.getElementById('taskForm');
    if (!form) {
        console.error('Task form not found');
        ui.showErrorFeedback('Form not found. Please refresh the page.');
        return;
    }
    
    const submitButton = form.querySelector('button[type="submit"]');
    if (!submitButton) {
        console.error('Submit button not found');
        ui.showErrorFeedback('Submit button not found. Please refresh the page.');
        return;
    }
    
    const originalText = submitButton.textContent;
    submitButton.textContent = 'Adding...';
    submitButton.disabled = true;
    
    try {
        await eel.add_task(title, description, priority, dueDate, goalId)();
        document.getElementById('taskForm').reset();
        // Hide form after successful submission
        const taskFormContainer = document.getElementById('taskFormContainer');
        const toggleTaskFormBtn = document.getElementById('toggleTaskForm');
        if (taskFormContainer) {
            taskFormContainer.style.display = 'none';
        }
        if (toggleTaskFormBtn) {
            toggleTaskFormBtn.innerHTML = '<span class="btn-icon">+</span> Add New Task';
        }
        ui.showSuccessFeedback('Task added successfully!');
        await loadTasks();
    } catch (error) {
        console.error('Error adding task:', error);
        ui.showErrorFeedback('Failed to add task. Please try again.');
    } finally {
        submitButton.textContent = originalText;
        submitButton.disabled = false;
    }
}

/**
 * Toggle task completion
 */
export async function toggleTask(taskId) {
    try {
        await eel.toggle_task(taskId)();
        await loadTasks();
        await loadGoals(); // Update goal progress
    } catch (error) {
        console.error('Error toggling task:', error);
    }
}

/**
 * Delete task
 */
export async function deleteTask(taskId) {
    if (!confirm('Are you sure you want to delete this task?')) return;
    
    try {
        await eel.delete_task(taskId)();
        await loadTasks();
        await loadGoals(); // Update goal progress
    } catch (error) {
        console.error('Error deleting task:', error);
        alert('Failed to delete task. Please try again.');
    }
}

/**
 * Edit task
 */
export async function editTask(taskId) {
    const task = state.tasks.find(t => t.id === taskId);
    if (!task) return;
    
    // Populate form with task data
    document.getElementById('taskTitle').value = task.title;
    document.getElementById('taskDescription').value = task.description || '';
    document.getElementById('taskPriority').value = task.priority;
    document.getElementById('taskDueDate').value = task.due_date || '';
    document.getElementById('taskGoal').value = task.goal_id || '';
    
    // Switch to tasks tab and scroll to form
    const { switchTab } = await import('./tabs.js');
    switchTab('tasks');
    document.querySelector('.task-form').scrollIntoView({ behavior: 'smooth' });
    
    // Delete the old task
    await deleteTask(taskId);
}

/**
 * Handle search input
 */
export function handleSearch(e) {
    state.updateFilter('search', e.target.value.toLowerCase());
    renderTasks();
}

/**
 * Handle filter changes
 */
export function handleFilterChange() {
    state.updateFilter('priority', document.getElementById('filterPriority').value);
    state.updateFilter('goal', document.getElementById('filterGoal').value);
    renderTasks();
}

/**
 * Toggle showing completed tasks
 */
export function toggleCompleted() {
    const isShowing = state.toggleShowCompleted();
    const btn = document.getElementById('showCompleted');
    if (btn) {
        btn.textContent = isShowing ? 'Hide Completed' : 'Show Completed';
    }
    renderTasks();
}

