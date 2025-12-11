/**
 * Goals Module
 * 
 * Handles all goal-related operations: loading, rendering, creating, updating, deleting.
 */

import * as state from './state.js';
import * as ui from './ui.js';
import * as utils from './utils.js';
import { loadTasks, renderTasks } from './tasks.js';

/**
 * Load goals from Python backend
 */
export async function loadGoals() {
    try {
        state.setGoals(await eel.get_goals()());
        await renderGoals();
        updateGoalSelect();
        updateGoalFilter();
    } catch (error) {
        console.error('Error loading goals:', error);
    }
}

/**
 * Render goals with progress
 */
export async function renderGoals() {
    const container = document.getElementById('goalsContainer');
    
    if (state.goals.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <h3>No goals yet</h3>
                <p>Create your first goal above!</p>
            </div>
        `;
        return;
    }
    
    let html = '';
    for (const goal of state.goals) {
        const progress = await eel.get_goal_progress(goal.id)();
        html += createGoalHTML(goal, progress);
    }
    
    container.innerHTML = html;
    
    // Add event listeners
    state.goals.forEach(goal => {
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
    
    // Re-animate elements
    setTimeout(() => ui.animateElements(), 100);
}

/**
 * Create HTML for a goal
 */
function createGoalHTML(goal, progress) {
    return `
        <div class="goal-item">
            <div class="goal-title">${utils.escapeHtml(goal.title)}</div>
            ${goal.description ? `<div class="goal-description">${utils.escapeHtml(goal.description)}</div>` : ''}
            <div class="goal-progress">
                <div class="progress-text">${progress.completed} of ${progress.total} tasks completed</div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${progress.percentage}%"></div>
                </div>
                <div class="progress-text">${Math.round(progress.percentage)}% complete</div>
            </div>
            <div class="goal-actions">
                <button class="btn-edit" id="edit-goal-${goal.id}">Edit</button>
                <button class="btn-delete" id="delete-goal-${goal.id}">Delete</button>
            </div>
        </div>
    `;
}

/**
 * Handle adding a new goal
 */
export async function handleAddGoal(e) {
    e.preventDefault();
    
    const title = document.getElementById('goalTitle').value.trim();
    const description = document.getElementById('goalDescription').value.trim();
    
    if (!title) {
        ui.showErrorFeedback('Please enter a goal title');
        return;
    }
    
    const form = document.getElementById('goalForm');
    if (!form) {
        console.error('Goal form not found');
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
        await eel.add_goal(title, description)();
        document.getElementById('goalForm').reset();
        ui.showSuccessFeedback('Goal added successfully!');
        await loadGoals();
    } catch (error) {
        console.error('Error adding goal:', error);
        ui.showErrorFeedback('Failed to add goal. Please try again.');
    } finally {
        submitButton.textContent = originalText;
        submitButton.disabled = false;
    }
}

/**
 * Edit goal
 */
export async function editGoal(goalId) {
    const goal = state.goals.find(g => g.id === goalId);
    if (!goal) return;
    
    document.getElementById('goalTitle').value = goal.title;
    document.getElementById('goalDescription').value = goal.description || '';
    
    document.querySelector('.goals-form').scrollIntoView({ behavior: 'smooth' });
    
    await deleteGoal(goalId);
}

/**
 * Delete goal
 */
export async function deleteGoal(goalId) {
    if (!confirm('Are you sure you want to delete this goal? Tasks linked to this goal will be unlinked.')) return;
    
    try {
        await eel.delete_goal(goalId)();
        await loadGoals();
        await loadTasks();
    } catch (error) {
        console.error('Error deleting goal:', error);
        alert('Failed to delete goal. Please try again.');
    }
}

/**
 * Update goal select dropdown in task form
 */
export function updateGoalSelect() {
    const select = document.getElementById('taskGoal');
    if (!select) return;
    
    const currentValue = select.value;
    
    select.innerHTML = '<option value="">No Goal (Misc)</option>';
    
    state.goals.forEach(goal => {
        const option = document.createElement('option');
        option.value = goal.id;
        option.textContent = goal.title;
        select.appendChild(option);
    });
    
    if (currentValue && state.goals.find(g => g.id === parseInt(currentValue))) {
        select.value = currentValue;
    }
}

/**
 * Update goal filter dropdown
 */
export function updateGoalFilter() {
    const select = document.getElementById('filterGoal');
    if (!select) return;
    
    const currentValue = select.value;
    
    select.innerHTML = '<option value="">All Goals</option>';
    
    state.goals.forEach(goal => {
        const option = document.createElement('option');
        option.value = goal.id;
        option.textContent = goal.title;
        select.appendChild(option);
    });
    
    if (currentValue && state.goals.find(g => g.id === parseInt(currentValue))) {
        select.value = currentValue;
    }
}

