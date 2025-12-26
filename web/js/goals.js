/**
 * Goals Module
 * 
 * Handles all goal-related operations including:
 * - Loading goals from backend
 * - Creating, updating, deleting goals
 * - Rendering goals with progress
 * - Goal form handling
 */

import * as state from './state.js';
import * as utils from './utils.js';
import * as ui from './ui.js';

// ============================================
// GOAL DATA LOADING
// ============================================

/**
 * Load all goals from the Python backend
 */
export async function loadGoals() {
    try {
        if (typeof eel !== 'undefined' && eel.get_goals) {
            const goals = await eel.get_goals()();
            state.setGoals(goals || []);
        } else {
            state.setGoals([]);
        }
        
        await renderGoals();
        if (window.updateGoalSelect) window.updateGoalSelect();
        if (window.updateGoalFilter) window.updateGoalFilter();
    } catch (error) {
        console.error('Error loading goals:', error);
        // Still render with empty goals if loading fails
        state.setGoals([]);
        renderGoals().catch(err => console.error('Error rendering goals:', err));
    }
}

// ============================================
// GOAL CRUD OPERATIONS
// ============================================

/**
 * Handle adding or updating a goal
 */
export async function handleAddGoal(e) {
    e.preventDefault();
    
    const title = document.getElementById('goalTitle').value.trim();
    const description = document.getElementById('goalDescription').value.trim();
    const timeGoalInput = document.getElementById('goalTimeGoal');
    const timeGoal = timeGoalInput && timeGoalInput.value ? parseFloat(timeGoalInput.value) : null;
    
    if (!title) {
        utils.showErrorFeedback('Please enter a goal title');
        return;
    }
    
    if (timeGoal !== null && (isNaN(timeGoal) || timeGoal <= 0)) {
        utils.showErrorFeedback('Time goal must be a positive number');
        return;
    }
    
    const form = document.getElementById('goalForm');
    if (!form) {
        utils.showErrorFeedback('Form not found. Please refresh the page.');
        return;
    }
    
    const submitButton = form.querySelector('button[type="submit"]');
    if (!submitButton) {
        utils.showErrorFeedback('Submit button not found. Please refresh the page.');
        return;
    }
    
    const originalText = submitButton.textContent;
    submitButton.textContent = 'Adding...';
    submitButton.disabled = true;
    
    try {
        const isEditMode = state.getEditingGoalId() !== null;
        const goalId = isEditMode ? state.getEditingGoalId() : null;
        
        if (isEditMode) {
            const result = await eel.update_goal(goalId, title, description, timeGoal)();
            if (!result) {
                throw new Error('Goal update failed - goal not found');
            }
            state.clearEditingGoalId();
            utils.showSuccessFeedback('Goal updated successfully!');
        } else {
            await eel.add_goal(title, description, timeGoal)();
            utils.showSuccessFeedback('Goal added successfully!');
        }
        
        document.getElementById('goalForm').reset();
        
        const formTitle = document.querySelector('.goals-form h2');
        const submitBtn = document.querySelector('#goalForm button[type="submit"]');
        if (formTitle) {
            formTitle.textContent = 'Add New Goal';
        }
        if (submitBtn) {
            submitBtn.textContent = 'Add Goal';
        }
        
        await loadGoals();
    } catch (error) {
        console.error('Error adding goal:', error);
        utils.showErrorFeedback('Failed to add goal. Please try again.');
    } finally {
        submitButton.textContent = originalText;
        submitButton.disabled = false;
    }
}

/**
 * Edit a goal by populating the form
 */
export function editGoal(goalId) {
    const goals = state.getGoals();
    const goal = goals.find(g => g.id === goalId);
    if (!goal) return;
    
    state.setEditingGoalId(goalId);
    
    document.getElementById('goalTitle').value = goal.title;
    document.getElementById('goalDescription').value = goal.description || '';
    
    const timeGoalInput = document.getElementById('goalTimeGoal');
    if (timeGoalInput) {
        timeGoalInput.value = goal.time_goal || '';
    }
    
    const formTitle = document.querySelector('.goals-form h2');
    const submitButton = document.querySelector('#goalForm button[type="submit"]');
    if (formTitle) {
        formTitle.textContent = 'Edit Goal';
    }
    if (submitButton) {
        submitButton.textContent = 'Update Goal';
    }
    
    document.querySelector('.goals-form').scrollIntoView({ behavior: 'smooth' });
}

/**
 * Delete a goal
 */
export async function deleteGoal(goalId) {
    if (!confirm('Are you sure you want to delete this goal? Tasks linked to this goal will be unlinked.')) return;
    
    try {
        await eel.delete_goal(goalId)();
        await loadGoals();
        if (window.loadTasks) {
            await window.loadTasks();
        }
    } catch (error) {
        console.error('Error deleting goal:', error);
        alert('Failed to delete goal. Please try again.');
    }
}

// ============================================
// GOAL RENDERING
// ============================================

/**
 * Render goals with progress
 */
export async function renderGoals() {
    const container = document.getElementById('goalsContainer');
    if (!container) return;
    
    const goals = state.getGoals();
    
    if (goals.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <h3>No goals yet</h3>
                <p>Create your first goal above!</p>
            </div>
        `;
        return;
    }
    
    let html = '';
    for (const goal of goals) {
        const progress = await eel.get_goal_progress(goal.id)();
        html += createGoalHTML(goal, progress);
    }
    
    container.innerHTML = html;
    
    // Add event listeners
    goals.forEach(goal => {
        const editBtn = document.getElementById(`edit-goal-${goal.id}`);
        const deleteBtn = document.getElementById(`delete-goal-${goal.id}`);
        
        if (editBtn) {
            editBtn.addEventListener('click', () => editGoal(goal.id));
            ui.addRippleEffect(editBtn);
        }
        if (deleteBtn) {
            deleteBtn.addEventListener('click', () => deleteGoal(goal.id));
            ui.addRippleEffect(deleteBtn);
        }
    });
    
    setTimeout(() => ui.animateElements(), 100);
}

/**
 * Create HTML for a goal
 */
function createGoalHTML(goal, progress) {
    let progressText = '';
    if (progress.total === 0) {
        progressText = 'No items linked';
    } else {
        const parts = [];
        if (progress.tasks_total > 0) {
            parts.push(`${progress.tasks_completed}/${progress.tasks_total} tasks`);
        }
        if (progress.habits_total > 0) {
            parts.push(`${progress.habits_completed}/${progress.habits_total} habits`);
        }
        progressText = parts.join(' • ') + ` (${progress.completed}/${progress.total} total)`;
    }
    
    let timeProgressHTML = '';
    if (progress.time_goal && progress.time_goal > 0) {
        const timePercentage = progress.time_percentage || 0;
        const timeSpent = progress.time_spent || 0;
        timeProgressHTML = `
            <div class="goal-time-progress">
                <div class="time-progress-header">
                    <span class="time-progress-label">Time Progress:</span>
                    <span class="time-progress-stats">${timeSpent.toFixed(1)}h / ${progress.time_goal.toFixed(1)}h</span>
                </div>
                <div class="progress-bar time-progress-bar">
                    <div class="progress-fill time-progress-fill" style="width: ${Math.min(timePercentage, 100)}%"></div>
                </div>
                <div class="time-progress-percentage">${Math.round(timePercentage)}% of time goal</div>
            </div>
        `;
    }
    
    return `
        <div class="goal-item">
            <div class="goal-title">${utils.escapeHtml(goal.title)}</div>
            ${goal.description ? `<div class="goal-description">${utils.escapeHtml(goal.description)}</div>` : ''}
            <div class="goal-progress">
                <div class="progress-text">${progressText}</div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${progress.percentage}%"></div>
                </div>
                <div class="progress-text">${Math.round(progress.percentage)}% complete</div>
            </div>
            ${timeProgressHTML}
            <div class="goal-actions">
                <button class="btn-edit" id="edit-goal-${goal.id}">Edit</button>
                <button class="btn-delete" id="delete-goal-${goal.id}">Delete</button>
            </div>
        </div>
    `;
}
