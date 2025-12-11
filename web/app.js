let tasks = [];
let goals = [];
let showCompleted = false;
let currentFilter = {
    priority: '',
    goal: '',
    search: ''
};

// Initialize the app
async function init() {
    // Add loading state
    showLoadingState();
    await Promise.all([loadTasks(), loadGoals()]);
    setupEventListeners();
    setupTabs();
    hideLoadingState();
    // Add smooth entrance animations
    animateElements();
}

// Show loading state
function showLoadingState() {
    const containers = ['tasksContainer', 'goalsContainer'];
    containers.forEach(id => {
        const container = document.getElementById(id);
        if (container) {
            container.innerHTML = '<div class="empty-state"><div class="loading-spinner"></div><p>Loading...</p></div>';
        }
    });
}

// Hide loading state
function hideLoadingState() {
    // Loading state will be replaced by actual content
}

// Animate elements on load
function animateElements() {
    const elements = document.querySelectorAll('.task-item, .goal-item, .category-header');
    elements.forEach((el, index) => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        setTimeout(() => {
            el.style.transition = 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)';
            el.style.opacity = '1';
            el.style.transform = 'translateY(0)';
        }, index * 50);
    });
}

// Add ripple effect to buttons
function addRippleEffect(button) {
    button.addEventListener('click', function(e) {
        const ripple = document.createElement('span');
        const rect = this.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = e.clientX - rect.left - size / 2;
        const y = e.clientY - rect.top - size / 2;
        
        ripple.style.width = ripple.style.height = size + 'px';
        ripple.style.left = x + 'px';
        ripple.style.top = y + 'px';
        ripple.classList.add('ripple');
        
        this.appendChild(ripple);
        
        setTimeout(() => {
            ripple.remove();
        }, 600);
    });
}

// Load data from Python backend
async function loadTasks() {
    try {
        tasks = await eel.get_tasks()();
        renderTasks();
        updateGoalFilter();
        updateGoalSelect();
    } catch (error) {
        console.error('Error loading tasks:', error);
    }
}

async function loadGoals() {
    try {
        goals = await eel.get_goals()();
        renderGoals();
        updateGoalSelect();
        updateGoalFilter();
    } catch (error) {
        console.error('Error loading goals:', error);
    }
}


// Setup event listeners
function setupEventListeners() {
    // Task form submission
    document.getElementById('taskForm').addEventListener('submit', handleAddTask);
    
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
    document.getElementById('goalForm').addEventListener('submit', handleAddGoal);
    
    // Search
    document.getElementById('searchInput').addEventListener('input', handleSearch);
    
    // Filters
    document.getElementById('filterPriority').addEventListener('change', handleFilterChange);
    document.getElementById('filterGoal').addEventListener('change', handleFilterChange);
    document.getElementById('showCompleted').addEventListener('click', toggleCompleted);
}

// Tab management
function setupTabs() {
    document.querySelectorAll('.tab-button').forEach(button => {
        button.addEventListener('click', () => {
            const tabName = button.getAttribute('data-tab');
            switchTab(tabName);
        });
    });
}

function switchTab(tabName) {
    // Update buttons
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    
    // Update content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${tabName}Tab`).classList.add('active');
    
    // If switching to analytics tab, load analytics data
    if (tabName === 'analytics') {
        loadAnalytics();
        setupAnalytics();
    }
}

// Handle adding a new task
async function handleAddTask(e) {
    e.preventDefault();
    
    const title = document.getElementById('taskTitle').value.trim();
    const description = document.getElementById('taskDescription').value.trim();
    const priority = document.getElementById('taskPriority').value;
    const dueDate = document.getElementById('taskDueDate').value;
    const goalSelect = document.getElementById('taskGoal');
    
    const goalId = goalSelect.value ? parseInt(goalSelect.value) : null;
    
    if (!title) {
        showErrorFeedback('Please enter a task title');
        return;
    }
    
    // Add loading state to button - find submit button correctly
    const form = document.getElementById('taskForm');
    if (!form) {
        console.error('Task form not found');
        showErrorFeedback('Form not found. Please refresh the page.');
        return;
    }
    
    const submitButton = form.querySelector('button[type="submit"]');
    if (!submitButton) {
        console.error('Submit button not found');
        showErrorFeedback('Submit button not found. Please refresh the page.');
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
        // Show success feedback
        showSuccessFeedback('Task added successfully!');
        await loadTasks();
    } catch (error) {
        console.error('Error adding task:', error);
        showErrorFeedback('Failed to add task. Please try again.');
        // Log detailed error for debugging
        console.error('Full error details:', error);
    } finally {
        submitButton.textContent = originalText;
        submitButton.disabled = false;
    }
}

// Handle adding a new goal
async function handleAddGoal(e) {
    e.preventDefault();
    
    const title = document.getElementById('goalTitle').value.trim();
    const description = document.getElementById('goalDescription').value.trim();
    
    if (!title) {
        showErrorFeedback('Please enter a goal title');
        return;
    }
    
    // Find submit button correctly - it's in the form
    const form = document.getElementById('goalForm');
    if (!form) {
        console.error('Goal form not found');
        showErrorFeedback('Form not found. Please refresh the page.');
        return;
    }
    
    const submitButton = form.querySelector('button[type="submit"]');
    if (!submitButton) {
        console.error('Submit button not found');
        showErrorFeedback('Submit button not found. Please refresh the page.');
        return;
    }
    
    // Add loading state to button
    const originalText = submitButton.textContent;
    submitButton.textContent = 'Adding...';
    submitButton.disabled = true;
    
    try {
        await eel.add_goal(title, description)();
        document.getElementById('goalForm').reset();
        showSuccessFeedback('Goal added successfully!');
        await loadGoals();
    } catch (error) {
        console.error('Error adding goal:', error);
        showErrorFeedback('Failed to add goal. Please try again.');
        // Log detailed error for debugging
        console.error('Full error details:', error);
    } finally {
        submitButton.textContent = originalText;
        submitButton.disabled = false;
    }
}

// Show success feedback
function showSuccessFeedback(message) {
    const feedback = document.createElement('div');
    feedback.className = 'feedback feedback-success';
    feedback.textContent = message;
    document.body.appendChild(feedback);
    
    setTimeout(() => {
        feedback.classList.add('show');
    }, 10);
    
    setTimeout(() => {
        feedback.classList.remove('show');
        setTimeout(() => feedback.remove(), 300);
    }, 3000);
}

// Show error feedback
function showErrorFeedback(message) {
    const feedback = document.createElement('div');
    feedback.className = 'feedback feedback-error';
    feedback.textContent = message;
    document.body.appendChild(feedback);
    
    setTimeout(() => {
        feedback.classList.add('show');
    }, 10);
    
    setTimeout(() => {
        feedback.classList.remove('show');
        setTimeout(() => feedback.remove(), 300);
    }, 3000);
}


// Handle search
function handleSearch(e) {
    currentFilter.search = e.target.value.toLowerCase();
    renderTasks();
}

// Handle filter changes
function handleFilterChange() {
    currentFilter.priority = document.getElementById('filterPriority').value;
    currentFilter.goal = document.getElementById('filterGoal').value;
    renderTasks();
}

// Toggle showing completed tasks
function toggleCompleted() {
    showCompleted = !showCompleted;
    const btn = document.getElementById('showCompleted');
    btn.textContent = showCompleted ? 'Hide Completed' : 'Show Completed';
    renderTasks();
}

// Toggle task completion
async function toggleTask(taskId) {
    try {
        await eel.toggle_task(taskId)();
        await loadTasks();
        await loadGoals(); // Update goal progress
    } catch (error) {
        console.error('Error toggling task:', error);
    }
}

// Delete task
async function deleteTask(taskId) {
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

// Edit task
async function editTask(taskId) {
    const task = tasks.find(t => t.id === taskId);
    if (!task) return;
    
    // Populate form with task data
    document.getElementById('taskTitle').value = task.title;
    document.getElementById('taskDescription').value = task.description || '';
    document.getElementById('taskPriority').value = task.priority;
    document.getElementById('taskDueDate').value = task.due_date || '';
    document.getElementById('taskGoal').value = task.goal_id || '';
    
    // Switch to tasks tab and scroll to form
    switchTab('tasks');
    document.querySelector('.task-form').scrollIntoView({ behavior: 'smooth' });
    
    // Delete the old task
    await deleteTask(taskId);
}

// Render tasks organized by category, then priority
function renderTasks() {
    const container = document.getElementById('tasksContainer');
    
    // Filter tasks
    let filteredTasks = tasks;
    
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
    
    // Render
    if (filteredTasks.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <h3>No tasks found</h3>
                <p>${tasks.length === 0 ? 'Add your first task above!' : 'Try adjusting your filters.'}</p>
            </div>
        `;
        return;
    }
    
    // Group by goal (tasks without goals go to "Misc")
    const tasksByGoal = {};
    filteredTasks.forEach(task => {
        const goalId = task.goal_id || 'Misc';
        if (!tasksByGoal[goalId]) {
            tasksByGoal[goalId] = [];
        }
        tasksByGoal[goalId].push(task);
    });
    
    // Sort tasks within each goal by priority (Now > Next > Later)
    const priorityOrder = { Now: 3, Next: 2, Later: 1 };
    Object.keys(tasksByGoal).forEach(goalId => {
        tasksByGoal[goalId].sort((a, b) => {
            // Incomplete tasks first
            if (a.completed !== b.completed) {
                return a.completed ? 1 : -1;
            }
            // Then by priority
            const priorityA = priorityOrder[a.priority] || 0;
            const priorityB = priorityOrder[b.priority] || 0;
            if (priorityA !== priorityB) {
                return priorityB - priorityA; // Higher priority first
            }
            // Then by due date
            if (a.due_date && b.due_date) {
                return new Date(a.due_date) - new Date(b.due_date);
            }
            if (a.due_date) return -1;
            if (b.due_date) return 1;
            return 0;
        });
    });
    
    // Render by goal in rows
    let html = '';
    // Sort goals by ID (or "Misc" last)
    const sortedGoalIds = Object.keys(tasksByGoal).sort((a, b) => {
        if (a === 'Misc') return 1;
        if (b === 'Misc') return -1;
        return parseInt(a) - parseInt(b);
    });
    
    sortedGoalIds.forEach(goalId => {
        const goal = goals.find(g => g.id === parseInt(goalId));
        const goalName = goal ? goal.title : 'Misc';
        html += `<div class="category-header">${escapeHtml(goalName)}</div>`;
        html += `<div class="category-tasks-row">`;
        tasksByGoal[goalId].forEach(task => {
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
            addRippleEffect(checkbox.parentElement);
        }
        if (deleteBtn) {
            deleteBtn.addEventListener('click', () => deleteTask(task.id));
            addRippleEffect(deleteBtn);
        }
        if (editBtn) {
            editBtn.addEventListener('click', () => editTask(task.id));
            addRippleEffect(editBtn);
        }
    });
    
    // Re-animate elements
    setTimeout(() => animateElements(), 100);
}

// Create HTML for a task
function createTaskHTML(task) {
    const isOverdue = task.due_date && !task.completed && new Date(task.due_date) < new Date();
    const dueDateFormatted = task.due_date ? new Date(task.due_date).toLocaleDateString() : '';
    const goal = goals.find(g => g.id === task.goal_id);
    
    return `
        <div class="task-item ${task.completed ? 'completed' : ''}">
            <div class="task-header">
                <input type="checkbox" id="checkbox-${task.id}" class="task-checkbox" ${task.completed ? 'checked' : ''}>
                <div class="task-content">
                    <div class="task-title">${escapeHtml(task.title)}</div>
                    ${task.description ? `<div class="task-description">${escapeHtml(task.description)}</div>` : ''}
                    <div class="task-meta">
                        <span class="task-badge priority-${task.priority}">${task.priority}</span>
                        ${goal ? `<span class="goal-badge">🎯 ${escapeHtml(goal.title)}</span>` : ''}
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

// Render goals
async function renderGoals() {
    const container = document.getElementById('goalsContainer');
    
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
            addRippleEffect(editBtn);
        }
        if (deleteBtn) {
            deleteBtn.addEventListener('click', () => deleteGoal(goal.id));
            addRippleEffect(deleteBtn);
        }
    });
    
    // Re-animate elements
    setTimeout(() => animateElements(), 100);
}

// Create HTML for a goal
function createGoalHTML(goal, progress) {
    return `
        <div class="goal-item">
            <div class="goal-title">${escapeHtml(goal.title)}</div>
            ${goal.description ? `<div class="goal-description">${escapeHtml(goal.description)}</div>` : ''}
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

// Edit goal
async function editGoal(goalId) {
    const goal = goals.find(g => g.id === goalId);
    if (!goal) return;
    
    document.getElementById('goalTitle').value = goal.title;
    document.getElementById('goalDescription').value = goal.description || '';
    
    document.querySelector('.goals-form').scrollIntoView({ behavior: 'smooth' });
    
    await deleteGoal(goalId);
}

// Delete goal
async function deleteGoal(goalId) {
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


// Update goal select dropdown
function updateGoalSelect() {
    const select = document.getElementById('taskGoal');
    const currentValue = select.value;
    
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

// Update goal filter dropdown
function updateGoalFilter() {
    const select = document.getElementById('filterGoal');
    const currentValue = select.value;
    
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

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Add keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + K to focus search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        document.getElementById('searchInput')?.focus();
    }
    
    // Escape to clear search
    if (e.key === 'Escape') {
        const searchInput = document.getElementById('searchInput');
        if (document.activeElement === searchInput) {
            searchInput.value = '';
            handleSearch({ target: searchInput });
        }
    }
});

// Add smooth scroll behavior
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// ============================================
// ANALYTICS FUNCTIONS
// ============================================

/**
 * Load and display analytics data
 * This function fetches comprehensive analytics from the Python backend
 * and renders them in a visually appealing format with charts and statistics
 */
async function loadAnalytics() {
    try {
        // Fetch analytics data from Python backend
        // The get_analytics() function calculates all statistics server-side
        const analytics = await eel.get_analytics()();
        
        // Render the analytics in the UI
        renderAnalytics(analytics);
    } catch (error) {
        console.error('Error loading analytics:', error);
        // Show error message to user
        const container = document.getElementById('analyticsContainer');
        container.innerHTML = `
            <div class="empty-state">
                <h3>Error Loading Analytics</h3>
                <p>Unable to load analytics data. Please try again.</p>
            </div>
        `;
    }
}

/**
 * Render analytics data in the UI
 * This function takes the analytics data structure and creates visual cards
 * for each category of statistics
 * 
 * @param {Object} analytics - The analytics data object from Python
 */
function renderAnalytics(analytics) {
    const container = document.getElementById('analyticsContainer');
    
    // If no tasks exist, show empty state
    if (!analytics || analytics.overall.total === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <h3>No Data Available</h3>
                <p>Create some tasks to see analytics!</p>
            </div>
        `;
        return;
    }
    
    let html = '';
    
    // ============================================
    // OVERALL STATISTICS CARD
    // ============================================
    // This card shows high-level completion statistics
    // Add data-card-id attribute for identification and localStorage
    html += `
        <div class="analytics-card draggable-card resizable-card" data-card-id="overall-stats">
            <div class="card-drag-handle" title="Drag to move">⋮⋮</div>
            <div class="card-resize-handle" title="Drag to resize"></div>
            <div class="analytics-card-header">
                <h3>📊 Overall Statistics</h3>
            </div>
            <div class="analytics-card-content">
                <div class="stat-grid">
                    <div class="stat-item">
                        <div class="stat-value">${analytics.overall.total}</div>
                        <div class="stat-label">Total Tasks</div>
                    </div>
                    <div class="stat-item stat-success">
                        <div class="stat-value">${analytics.overall.completed}</div>
                        <div class="stat-label">Completed</div>
                    </div>
                    <div class="stat-item stat-warning">
                        <div class="stat-value">${analytics.overall.incomplete}</div>
                        <div class="stat-label">Incomplete</div>
                    </div>
                    <div class="stat-item stat-primary">
                        <div class="stat-value">${analytics.overall.completion_percentage}%</div>
                        <div class="stat-label">Completion Rate</div>
                    </div>
                </div>
                <!-- Progress bar showing overall completion -->
                <div class="progress-bar-large">
                    <div class="progress-fill-large" style="width: ${analytics.overall.completion_percentage}%"></div>
                </div>
            </div>
        </div>
    `;
    
    // ============================================
    // GOAL STATISTICS CARD
    // ============================================
    // Shows completion rates broken down by goal
    if (analytics.by_goal && analytics.by_goal.goals && Object.keys(analytics.by_goal.goals).length > 0) {
        html += `
            <div class="analytics-card draggable-card resizable-card" data-card-id="goal-breakdown">
                <div class="card-drag-handle" title="Drag to move">⋮⋮</div>
                <div class="card-resize-handle" title="Drag to resize"></div>
                <div class="analytics-card-header">
                    <h3>🎯 Goal Breakdown</h3>
                </div>
                <div class="analytics-card-content">
        `;
        
        // Sort goals by completion percentage (highest first)
        const sortedGoals = Object.entries(analytics.by_goal.goals)
            .sort((a, b) => b[1].completion_percentage - a[1].completion_percentage);
        
        // Create a row for each goal
        sortedGoals.forEach(([goalId, stats]) => {
            html += `
                <div class="category-stat-row">
                    <div class="category-stat-header">
                        <span class="category-name">${escapeHtml(stats.goal_name)}</span>
                        <span class="category-percentage">${stats.completion_percentage}%</span>
                    </div>
                    <div class="category-stat-details">
                        <span>${stats.completed} of ${stats.total} completed</span>
                        <span>${stats.incomplete} remaining</span>
                    </div>
                    <div class="progress-bar-small">
                        <div class="progress-fill-small" style="width: ${stats.completion_percentage}%"></div>
                    </div>
                </div>
            `;
        });
        
        html += `</div></div>`;
    }
    
    // ============================================
    // PRIORITY STATISTICS CARD
    // ============================================
    // Shows how tasks are distributed and completed by priority level
    html += `
        <div class="analytics-card draggable-card resizable-card" data-card-id="priority-analysis">
            <div class="card-drag-handle" title="Drag to move">⋮⋮</div>
            <div class="card-resize-handle" title="Drag to resize"></div>
            <div class="analytics-card-header">
                <h3>⚡ Priority Analysis</h3>
            </div>
            <div class="analytics-card-content">
    `;
    
    // Display stats for each priority level (Now, Next, Later)
    const priorities = ['Now', 'Next', 'Later'];
    priorities.forEach(priority => {
        const stats = analytics.by_priority[priority];
        if (stats) {
            const priorityClass = priority === 'Now' ? 'priority-now' : priority === 'Next' ? 'priority-next' : 'priority-later';
            html += `
                <div class="priority-stat-row ${priorityClass}">
                    <div class="priority-stat-header">
                        <span class="priority-name">${priority}</span>
                        <span class="priority-count">${stats.total} tasks</span>
                    </div>
                    <div class="priority-stat-details">
                        <span>✅ ${stats.completed} completed</span>
                        <span>⏳ ${stats.incomplete} incomplete</span>
                        <span class="priority-percentage">${stats.completion_percentage}%</span>
                    </div>
                    <div class="progress-bar-small">
                        <div class="progress-fill-small" style="width: ${stats.completion_percentage}%"></div>
                    </div>
                </div>
            `;
        }
    });
    
    html += `</div></div>`;
    
    // ============================================
    // GOAL STATISTICS CARD
    // ============================================
    // Shows progress for each goal and goal-related metrics
    if (analytics.by_goal.total_goals > 0) {
        html += `
            <div class="analytics-card draggable-card resizable-card" data-card-id="goal-progress">
                <div class="card-drag-handle" title="Drag to move">⋮⋮</div>
                <div class="card-resize-handle" title="Drag to resize"></div>
                <div class="analytics-card-header">
                    <h3>🎯 Goal Progress</h3>
                </div>
                <div class="analytics-card-content">
                    <div class="goal-stats-summary">
                        <div class="goal-stat-summary-item">
                            <span class="summary-label">Total Goals:</span>
                            <span class="summary-value">${analytics.by_goal.total_goals}</span>
                        </div>
                        <div class="goal-stat-summary-item">
                            <span class="summary-label">Tasks with Goals:</span>
                            <span class="summary-value">${analytics.by_goal.tasks_with_goals}</span>
                        </div>
                        <div class="goal-stat-summary-item">
                            <span class="summary-label">Tasks without Goals:</span>
                            <span class="summary-value">${analytics.by_goal.tasks_without_goals}</span>
                        </div>
                    </div>
        `;
        
        // Display progress for each goal
        Object.values(analytics.by_goal.goals).forEach(goalStat => {
            html += `
                <div class="goal-stat-row">
                    <div class="goal-stat-header">
                        <span class="goal-name">${escapeHtml(goalStat.goal_name)}</span>
                        <span class="goal-percentage">${goalStat.completion_percentage}%</span>
                    </div>
                    <div class="goal-stat-details">
                        <span>${goalStat.completed} of ${goalStat.total} tasks completed</span>
                    </div>
                    <div class="progress-bar-small">
                        <div class="progress-fill-small" style="width: ${goalStat.completion_percentage}%"></div>
                    </div>
                </div>
            `;
        });
        
        html += `</div></div>`;
    }
    
    // ============================================
    // TIME-BASED STATISTICS CARD
    // ============================================
    // Shows time-related metrics like overdue tasks, completion times, etc.
    html += `
        <div class="analytics-card draggable-card resizable-card" data-card-id="time-analysis">
            <div class="card-drag-handle" title="Drag to move">⋮⋮</div>
            <div class="card-resize-handle" title="Drag to resize"></div>
            <div class="analytics-card-header">
                <h3>⏰ Time Analysis</h3>
            </div>
            <div class="analytics-card-content">
                <div class="time-stats-grid">
                    <div class="time-stat-item ${analytics.time_stats.overdue_count > 0 ? 'stat-danger' : ''}">
                        <div class="time-stat-icon">🚨</div>
                        <div class="time-stat-value">${analytics.time_stats.overdue_count}</div>
                        <div class="time-stat-label">Overdue Tasks</div>
                    </div>
                    <div class="time-stat-item ${analytics.time_stats.due_soon_count > 0 ? 'stat-warning' : ''}">
                        <div class="time-stat-icon">⏳</div>
                        <div class="time-stat-value">${analytics.time_stats.due_soon_count}</div>
                        <div class="time-stat-label">Due Soon (7 days)</div>
                    </div>
                    <div class="time-stat-item stat-success">
                        <div class="time-stat-icon">✅</div>
                        <div class="time-stat-value">${analytics.time_stats.completed_today}</div>
                        <div class="time-stat-label">Completed Today</div>
                    </div>
                    <div class="time-stat-item stat-primary">
                        <div class="time-stat-icon">➕</div>
                        <div class="time-stat-value">${analytics.time_stats.created_today}</div>
                        <div class="time-stat-label">Created Today</div>
                    </div>
                    <div class="time-stat-item">
                        <div class="time-stat-icon">📅</div>
                        <div class="time-stat-value">${analytics.time_stats.avg_completion_days}</div>
                        <div class="time-stat-label">Avg Days to Complete</div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // ============================================
    // PRODUCTIVITY METRICS CARD
    // ============================================
    // Shows insights about productivity patterns
    html += `
        <div class="analytics-card draggable-card resizable-card" data-card-id="productivity-insights">
            <div class="card-drag-handle" title="Drag to move">⋮⋮</div>
            <div class="card-resize-handle" title="Drag to resize"></div>
            <div class="analytics-card-header">
                <h3>🚀 Productivity Insights</h3>
            </div>
            <div class="analytics-card-content">
    `;
    
    // Most productive goal
    if (analytics.productivity.most_productive_goal) {
        html += `
            <div class="insight-item">
                <div class="insight-icon">🏆</div>
                <div class="insight-content">
                    <div class="insight-title">Most Productive Goal</div>
                    <div class="insight-value">${escapeHtml(analytics.productivity.most_productive_goal)}</div>
                    <div class="insight-detail">${analytics.productivity.most_productive_completion_rate}% completion rate</div>
                </div>
            </div>
        `;
    }
    
    // Goal with most tasks
    if (analytics.productivity.goal_with_most_tasks) {
        html += `
            <div class="insight-item">
                <div class="insight-icon">📊</div>
                <div class="insight-content">
                    <div class="insight-title">Most Active Goal</div>
                    <div class="insight-value">${escapeHtml(analytics.productivity.goal_with_most_tasks)}</div>
                    <div class="insight-detail">${analytics.productivity.max_tasks_in_goal} tasks</div>
                </div>
            </div>
        `;
    }
    
    // Goal distribution
    if (analytics.productivity.goal_distribution && Object.keys(analytics.productivity.goal_distribution).length > 0) {
        html += `
            <div class="insight-item">
                <div class="insight-icon">📈</div>
                <div class="insight-content">
                    <div class="insight-title">Task Distribution</div>
                    <div class="distribution-list">
        `;
        
        // Sort by percentage and show top goals
        const sortedDist = Object.entries(analytics.productivity.goal_distribution)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 5); // Show top 5
        
        sortedDist.forEach(([goalName, percentage]) => {
            html += `
                <div class="distribution-item">
                    <span class="dist-category">${escapeHtml(goalName)}</span>
                    <span class="dist-percentage">${percentage}%</span>
                </div>
            `;
        });
        
        html += `</div></div></div>`;
    }
    
    html += `</div></div>`;
    
    // Insert all HTML into the container
    container.innerHTML = html;
    
    // ============================================
    // LOAD SAVED POSITIONS AND SIZES
    // ============================================
    // After rendering, restore saved positions and sizes from localStorage
    loadCardPositions();
    
    // ============================================
    // INITIALIZE DRAG AND RESIZE FUNCTIONALITY
    // ============================================
    // Set up event listeners for dragging and resizing cards
    initializeDragAndResize();
}

// ============================================
// ANALYTICS EVENT LISTENERS
// ============================================

/**
 * Setup analytics tab functionality
 * This is called when the analytics tab is opened
 */
function setupAnalytics() {
    // Add event listener for refresh button
    const refreshBtn = document.getElementById('refreshAnalytics');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', async () => {
            // Show loading state
            refreshBtn.textContent = 'Refreshing...';
            refreshBtn.disabled = true;
            
            // Reload analytics
            await loadAnalytics();
            
            // Restore button
            refreshBtn.textContent = 'Refresh Data';
            refreshBtn.disabled = false;
        });
    }
    
    // Add event listener for reset layout button
    const resetBtn = document.getElementById('resetCardLayout');
    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            // Confirm reset action
            if (confirm('Reset all card positions and sizes to default? This cannot be undone.')) {
                // Clear saved positions and sizes from localStorage
                localStorage.removeItem('analyticsCardPositions');
                localStorage.removeItem('analyticsCardSizes');
                
                // Reload analytics to apply default layout
                loadAnalytics();
                
                // Show feedback
                showSuccessFeedback('Layout reset to default');
            }
        });
    }
}

// ============================================
// DRAG AND RESIZE FUNCTIONALITY
// ============================================

/**
 * Initialize drag and resize functionality for analytics cards
 * This function sets up event listeners for dragging cards around
 * and resizing them to custom dimensions
 */
function initializeDragAndResize() {
    // Get all draggable cards
    const cards = document.querySelectorAll('.draggable-card');
    
    cards.forEach(card => {
        // Get the drag handle (the element you click to drag)
        const dragHandle = card.querySelector('.card-drag-handle');
        
        if (dragHandle) {
            // Make the drag handle cursor indicate it's draggable
            dragHandle.style.cursor = 'move';
            
            // Add mousedown event to start dragging
            dragHandle.addEventListener('mousedown', (e) => {
                startDragging(e, card);
            });
        }
        
        // Get the resize handle (the element you drag to resize)
        const resizeHandle = card.querySelector('.card-resize-handle');
        
        if (resizeHandle) {
            // Make the resize handle cursor indicate it's resizable
            resizeHandle.style.cursor = 'nwse-resize';
            
            // Add mousedown event to start resizing
            resizeHandle.addEventListener('mousedown', (e) => {
                startResizing(e, card);
            });
        }
    });
}

/**
 * Start dragging a card
 * This function is called when the user clicks and holds on a card's drag handle
 * 
 * @param {MouseEvent} e - The mouse event
 * @param {HTMLElement} card - The card element being dragged
 */
function startDragging(e, card) {
    // Prevent default behavior
    e.preventDefault();
    
    // Get the card's current position
    const rect = card.getBoundingClientRect();
    const container = document.getElementById('analyticsContainer');
    const containerRect = container.getBoundingClientRect();
    
    // Calculate the offset between mouse position and card position
    // This ensures the card doesn't jump when you start dragging
    const offsetX = e.clientX - rect.left;
    const offsetY = e.clientY - rect.top;
    
    // Add visual feedback - make card semi-transparent and raise z-index
    card.style.opacity = '0.8';
    card.style.zIndex = '1000';
    card.style.cursor = 'move';
    
    /**
     * Handle mouse movement while dragging
     * This function updates the card's position as the mouse moves
     */
    function handleMouseMove(e) {
        // Calculate new position relative to container
        const newX = e.clientX - containerRect.left - offsetX;
        const newY = e.clientY - containerRect.top - offsetY;
        
        // Constrain card within container bounds
        const maxX = containerRect.width - rect.width;
        const maxY = containerRect.height - rect.height;
        
        // Clamp values to keep card inside container
        const clampedX = Math.max(0, Math.min(newX, maxX));
        const clampedY = Math.max(0, Math.min(newY, maxY));
        
        // Update card position using absolute positioning
        card.style.position = 'absolute';
        card.style.left = clampedX + 'px';
        card.style.top = clampedY + 'px';
        card.style.margin = '0'; // Remove margin when using absolute positioning
    }
    
    /**
     * Handle mouse release - stop dragging
     * This function is called when the user releases the mouse button
     */
    function handleMouseUp() {
        // Remove event listeners
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
        
        // Restore visual feedback
        card.style.opacity = '1';
        card.style.cursor = 'default';
        
        // Save the new position to localStorage
        saveCardPosition(card);
    }
    
    // Add event listeners for mouse movement and release
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
}

/**
 * Start resizing a card
 * This function is called when the user clicks and holds on a card's resize handle
 * 
 * @param {MouseEvent} e - The mouse event
 * @param {HTMLElement} card - The card element being resized
 */
function startResizing(e, card) {
    // Prevent default behavior
    e.preventDefault();
    e.stopPropagation(); // Prevent triggering drag
    
    // Get the card's current dimensions and position
    const rect = card.getBoundingClientRect();
    const container = document.getElementById('analyticsContainer');
    const containerRect = container.getBoundingClientRect();
    
    // Store initial dimensions
    const startWidth = rect.width;
    const startHeight = rect.height;
    const startX = e.clientX;
    const startY = e.clientY;
    
    // Set minimum and maximum sizes
    const minWidth = 300;  // Minimum card width in pixels
    const minHeight = 200; // Minimum card height in pixels
    const maxWidth = containerRect.width - 20;  // Maximum width (with padding)
    const maxHeight = containerRect.height - 20; // Maximum height (with padding)
    
    // Add visual feedback
    card.style.opacity = '0.8';
    card.style.zIndex = '1000';
    
    /**
     * Handle mouse movement while resizing
     * This function updates the card's size as the mouse moves
     */
    function handleMouseMove(e) {
        // Calculate how much the mouse has moved
        const deltaX = e.clientX - startX;
        const deltaY = e.clientY - startY;
        
        // Calculate new dimensions
        let newWidth = startWidth + deltaX;
        let newHeight = startHeight + deltaY;
        
        // Constrain to minimum and maximum sizes
        newWidth = Math.max(minWidth, Math.min(newWidth, maxWidth));
        newHeight = Math.max(minHeight, Math.min(newHeight, maxHeight));
        
        // Update card size
        card.style.width = newWidth + 'px';
        card.style.height = 'auto'; // Allow height to adjust naturally
        card.style.minHeight = newHeight + 'px';
    }
    
    /**
     * Handle mouse release - stop resizing
     * This function is called when the user releases the mouse button
     */
    function handleMouseUp() {
        // Remove event listeners
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
        
        // Restore visual feedback
        card.style.opacity = '1';
        
        // Save the new size to localStorage
        saveCardSize(card);
    }
    
    // Add event listeners for mouse movement and release
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
}

/**
 * Save card position to localStorage
 * This function stores the card's position so it can be restored later
 * 
 * @param {HTMLElement} card - The card element
 */
function saveCardPosition(card) {
    // Get the card's unique ID
    const cardId = card.getAttribute('data-card-id');
    if (!cardId) return;
    
    // Get current position
    const left = card.style.left;
    const top = card.style.top;
    
    // Load existing saved positions or create new object
    const savedPositions = JSON.parse(localStorage.getItem('analyticsCardPositions') || '{}');
    
    // Update position for this card
    if (!savedPositions[cardId]) {
        savedPositions[cardId] = {};
    }
    savedPositions[cardId].left = left;
    savedPositions[cardId].top = top;
    
    // Save to localStorage
    localStorage.setItem('analyticsCardPositions', JSON.stringify(savedPositions));
}

/**
 * Save card size to localStorage
 * This function stores the card's size so it can be restored later
 * 
 * @param {HTMLElement} card - The card element
 */
function saveCardSize(card) {
    // Get the card's unique ID
    const cardId = card.getAttribute('data-card-id');
    if (!cardId) return;
    
    // Get current size
    const width = card.style.width;
    const minHeight = card.style.minHeight;
    
    // Load existing saved sizes or create new object
    const savedSizes = JSON.parse(localStorage.getItem('analyticsCardSizes') || '{}');
    
    // Update size for this card
    if (!savedSizes[cardId]) {
        savedSizes[cardId] = {};
    }
    savedSizes[cardId].width = width;
    savedSizes[cardId].minHeight = minHeight;
    
    // Save to localStorage
    localStorage.setItem('analyticsCardSizes', JSON.stringify(savedSizes));
}

/**
 * Load saved card positions and sizes from localStorage
 * This function restores cards to their previously saved positions and sizes
 */
function loadCardPositions() {
    // Load saved positions
    const savedPositions = JSON.parse(localStorage.getItem('analyticsCardPositions') || '{}');
    
    // Load saved sizes
    const savedSizes = JSON.parse(localStorage.getItem('analyticsCardSizes') || '{}');
    
    // Apply saved positions and sizes to each card
    document.querySelectorAll('.draggable-card').forEach(card => {
        const cardId = card.getAttribute('data-card-id');
        if (!cardId) return;
        
        // Apply saved position if it exists
        if (savedPositions[cardId]) {
            card.style.position = 'absolute';
            card.style.left = savedPositions[cardId].left || '';
            card.style.top = savedPositions[cardId].top || '';
            card.style.margin = '0';
        }
        
        // Apply saved size if it exists
        if (savedSizes[cardId]) {
            card.style.width = savedSizes[cardId].width || '';
            card.style.minHeight = savedSizes[cardId].minHeight || '';
        }
    });
}

// Initialize when page loads
init();
