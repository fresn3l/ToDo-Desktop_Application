let habits = [];
let goals = [];
let currentFilter = {
    priority: '',
    frequency: '',
    goal: '',
    search: ''
};

// Initialize the app
async function init() {
    // Add loading state
    showLoadingState();
    await Promise.all([loadHabits(), loadGoals()]);
    setupEventListeners();
    setupTabs();
    hideLoadingState();
    // Add smooth entrance animations
    animateElements();
}

// Show loading state
function showLoadingState() {
    const containers = ['habitsContainer', 'goalsContainer'];
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
    const elements = document.querySelectorAll('.task-item, .habit-item, .goal-item, .category-header');
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
async function loadHabits() {
    try {
        habits = await eel.get_habits()();
        // Load streaks for all habits
        for (const habit of habits) {
            habit.streak = await eel.get_habit_streak(habit.id)();
        }
        renderHabits();
        updateGoalFilter();
        updateGoalSelect();
    } catch (error) {
        console.error('Error loading habits:', error);
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
    // Habit form submission
    const habitForm = document.getElementById('habitForm');
    if (habitForm) {
        habitForm.addEventListener('submit', handleAddHabit);
    }
    
    // Toggle habit form visibility
    const toggleHabitFormBtn = document.getElementById('toggleHabitForm');
    const habitFormContainer = document.getElementById('habitFormContainer');
    if (toggleHabitFormBtn && habitFormContainer) {
        toggleHabitFormBtn.addEventListener('click', () => {
            const isVisible = habitFormContainer.style.display !== 'none';
            habitFormContainer.style.display = isVisible ? 'none' : 'block';
            toggleHabitFormBtn.innerHTML = isVisible 
                ? '<span class="btn-icon">+</span> Add New Habit'
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
    const filterFrequency = document.getElementById('filterFrequency');
    if (filterFrequency) {
        filterFrequency.addEventListener('change', handleFilterChange);
    }
    const filterGoal = document.getElementById('filterGoal');
    if (filterGoal) {
        filterGoal.addEventListener('change', handleFilterChange);
    }
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
    const activeButton = document.querySelector(`[data-tab="${tabName}"]`);
    if (activeButton) {
        activeButton.classList.add('active');
    }
    
    // Update content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    const activeTab = document.getElementById(`${tabName}Tab`);
    if (activeTab) {
        activeTab.classList.add('active');
    }
    
    // If switching to analytics tab, load analytics data
    if (tabName === 'analytics') {
        loadAnalytics();
        setupAnalytics();
    }
}

// Handle adding a new habit
async function handleAddHabit(e) {
    e.preventDefault();
    
    const title = document.getElementById('habitTitle').value.trim();
    const description = document.getElementById('habitDescription').value.trim();
    const priority = document.getElementById('habitPriority').value;
    const frequency = document.getElementById('habitFrequency').value;
    const goalSelect = document.getElementById('habitGoal');
    
    const goalId = goalSelect.value ? parseInt(goalSelect.value) : null;
    
    if (!title) {
        showErrorFeedback('Please enter a habit name');
        return;
    }
    
    const form = document.getElementById('habitForm');
    if (!form) {
        console.error('Habit form not found');
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
        await eel.add_habit(title, description, priority, frequency, goalId)();
        document.getElementById('habitForm').reset();
        // Hide form after successful submission
        const habitFormContainer = document.getElementById('habitFormContainer');
        const toggleHabitFormBtn = document.getElementById('toggleHabitForm');
        if (habitFormContainer) {
            habitFormContainer.style.display = 'none';
        }
        if (toggleHabitFormBtn) {
            toggleHabitFormBtn.innerHTML = '<span class="btn-icon">+</span> Add New Habit';
        }
        showSuccessFeedback('Habit added successfully!');
        await loadHabits();
    } catch (error) {
        console.error('Error adding habit:', error);
        showErrorFeedback('Failed to add habit. Please try again.');
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
    renderHabits();
}

// Handle filter changes
function handleFilterChange() {
    const filterPriority = document.getElementById('filterPriority');
    const filterFrequency = document.getElementById('filterFrequency');
    const filterGoal = document.getElementById('filterGoal');
    
    if (filterPriority) currentFilter.priority = filterPriority.value;
    if (filterFrequency) currentFilter.frequency = filterFrequency.value;
    if (filterGoal) currentFilter.goal = filterGoal.value;
    
    renderHabits();
}

// Check in habit for today
async function checkInHabit(habitId) {
    try {
        await eel.check_in_habit(habitId)();
        await loadHabits();
        await loadGoals(); // Update goal progress
        showSuccessFeedback('Habit checked in!');
    } catch (error) {
        console.error('Error checking in habit:', error);
        showErrorFeedback('Failed to check in habit. Please try again.');
    }
}

// Uncheck habit for today
async function uncheckHabit(habitId) {
    try {
        await eel.uncheck_habit(habitId)();
        await loadHabits();
        await loadGoals(); // Update goal progress
    } catch (error) {
        console.error('Error unchecking habit:', error);
    }
}

// Delete habit
async function deleteHabit(habitId) {
    if (!confirm('Are you sure you want to delete this habit?')) return;
    
    try {
        await eel.delete_habit(habitId)();
        await loadHabits();
        await loadGoals(); // Update goal progress
    } catch (error) {
        console.error('Error deleting habit:', error);
        alert('Failed to delete habit. Please try again.');
    }
}

// Edit habit
async function editHabit(habitId) {
    const habit = habits.find(h => h.id === habitId);
    if (!habit) return;
    
    // Populate form with habit data
    document.getElementById('habitTitle').value = habit.title;
    document.getElementById('habitDescription').value = habit.description || '';
    document.getElementById('habitPriority').value = habit.priority;
    document.getElementById('habitFrequency').value = habit.frequency || 'daily';
    document.getElementById('habitGoal').value = habit.goal_id || '';
    
    // Switch to habits tab and scroll to form
    switchTab('habits');
    const habitForm = document.querySelector('.task-form');
    if (habitForm) {
        habitForm.scrollIntoView({ behavior: 'smooth' });
    }
    
    // Delete the old habit
    await deleteHabit(habitId);
}

// Render habits organized by goal, then priority
function renderHabits() {
    const container = document.getElementById('habitsContainer');
    if (!container) return;
    
    // Filter habits
    let filteredHabits = habits;
    
    // Apply search filter
    if (currentFilter.search) {
        filteredHabits = filteredHabits.filter(habit => 
            habit.title.toLowerCase().includes(currentFilter.search) ||
            (habit.description && habit.description.toLowerCase().includes(currentFilter.search))
        );
    }
    
    // Apply priority filter
    if (currentFilter.priority) {
        filteredHabits = filteredHabits.filter(habit => habit.priority === currentFilter.priority);
    }
    
    // Apply frequency filter
    if (currentFilter.frequency) {
        filteredHabits = filteredHabits.filter(habit => habit.frequency === currentFilter.frequency);
    }
    
    // Apply goal filter
    if (currentFilter.goal) {
        const goalId = parseInt(currentFilter.goal);
        filteredHabits = filteredHabits.filter(habit => habit.goal_id === goalId);
    }
    
    // Render
    if (filteredHabits.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <h3>No habits found</h3>
                <p>${habits.length === 0 ? 'Add your first habit above!' : 'Try adjusting your filters.'}</p>
            </div>
        `;
        return;
    }
    
    // Group by goal (habits without goals go to "Misc")
    const habitsByGoal = {};
    filteredHabits.forEach(habit => {
        const goalId = habit.goal_id || 'Misc';
        if (!habitsByGoal[goalId]) {
            habitsByGoal[goalId] = [];
        }
        habitsByGoal[goalId].push(habit);
    });
    
    // Sort habits within each goal by priority (Now > Next > Later)
    const priorityOrder = { Now: 3, Next: 2, Later: 1 };
    Object.keys(habitsByGoal).forEach(goalId => {
        habitsByGoal[goalId].sort((a, b) => {
            // Then by priority
            const priorityA = priorityOrder[a.priority] || 0;
            const priorityB = priorityOrder[b.priority] || 0;
            if (priorityA !== priorityB) {
                return priorityB - priorityA; // Higher priority first
            }
            // Then by streak (higher streak first)
            const streakA = a.streak || 0;
            const streakB = b.streak || 0;
            return streakB - streakA;
        });
    });
    
    // Render by goal in rows
    let html = '';
    // Sort goals by ID (or "Misc" last)
    const sortedGoalIds = Object.keys(habitsByGoal).sort((a, b) => {
        if (a === 'Misc') return 1;
        if (b === 'Misc') return -1;
        return parseInt(a) - parseInt(b);
    });
    
    sortedGoalIds.forEach(goalId => {
        const goal = goals.find(g => g.id === parseInt(goalId));
        const goalName = goal ? goal.title : 'Misc';
        html += `<div class="category-header">${escapeHtml(goalName)}</div>`;
        html += `<div class="category-tasks-row">`;
        habitsByGoal[goalId].forEach(habit => {
            html += createHabitHTML(habit);
        });
        html += `</div>`;
    });
    
    container.innerHTML = html;
    
    // Add event listeners
    filteredHabits.forEach(habit => {
        const checkInBtn = document.getElementById(`checkin-${habit.id}`);
        const deleteBtn = document.getElementById(`delete-${habit.id}`);
        const editBtn = document.getElementById(`edit-${habit.id}`);
        
        if (checkInBtn) {
            checkInBtn.addEventListener('click', () => {
                const today = new Date().toISOString().split('T')[0];
                const isCheckedIn = habit.check_ins && habit.check_ins.includes(today);
                if (isCheckedIn) {
                    uncheckHabit(habit.id);
                } else {
                    checkInHabit(habit.id);
                }
            });
            addRippleEffect(checkInBtn);
        }
        if (deleteBtn) {
            deleteBtn.addEventListener('click', () => deleteHabit(habit.id));
            addRippleEffect(deleteBtn);
        }
        if (editBtn) {
            editBtn.addEventListener('click', () => editHabit(habit.id));
            addRippleEffect(editBtn);
        }
    });
    
    // Re-animate elements
    setTimeout(() => animateElements(), 100);
}

// Create HTML for a habit
function createHabitHTML(habit) {
    const today = new Date().toISOString().split('T')[0];
    const isCheckedIn = habit.check_ins && habit.check_ins.includes(today);
    const checkIns = habit.check_ins || [];
    const streak = habit.streak || 0;
    const goal = goals.find(g => g.id === habit.goal_id);
    const totalCheckIns = checkIns.length;
    
    // Calculate last 7 days check-in status
    const last7Days = [];
    for (let i = 6; i >= 0; i--) {
        const date = new Date();
        date.setDate(date.getDate() - i);
        const dateStr = date.toISOString().split('T')[0];
        last7Days.push({
            date: dateStr,
            checked: checkIns.includes(dateStr)
        });
    }
    
    return `
        <div class="task-item habit-item">
            <div class="task-header">
                <button id="checkin-${habit.id}" class="habit-checkin-btn ${isCheckedIn ? 'checked' : ''}" title="${isCheckedIn ? 'Uncheck for today' : 'Check in for today'}">
                    ${isCheckedIn ? '✓' : '○'}
                </button>
                <div class="task-content">
                    <div class="task-title">${escapeHtml(habit.title)}</div>
                    ${habit.description ? `<div class="task-description">${escapeHtml(habit.description)}</div>` : ''}
                    <div class="task-meta">
                        <span class="task-badge priority-${habit.priority.toLowerCase()}">${habit.priority}</span>
                        <span class="task-badge frequency-badge">${habit.frequency || 'daily'}</span>
                        <span class="streak-badge">🔥 ${streak} day streak</span>
                        ${goal ? `<span class="goal-badge">🎯 ${escapeHtml(goal.title)}</span>` : ''}
                        <span class="checkin-count">${totalCheckIns} check-ins</span>
                    </div>
                    <div class="habit-week-view">
                        ${last7Days.map(day => `
                            <span class="day-indicator ${day.checked ? 'checked' : ''}" title="${day.date}">
                                ${day.checked ? '✓' : '○'}
                            </span>
                        `).join('')}
                    </div>
                    <div class="task-actions">
                        <button class="btn-edit" id="edit-${habit.id}">Edit</button>
                        <button class="btn-delete" id="delete-${habit.id}">Delete</button>
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
                    <div class="progress-text">${progress.completed} of ${progress.total} habits tracked</div>
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
    if (!confirm('Are you sure you want to delete this goal? Habits linked to this goal will be unlinked.')) return;
    
    try {
        await eel.delete_goal(goalId)();
        await loadGoals();
        await loadHabits();
    } catch (error) {
        console.error('Error deleting goal:', error);
        alert('Failed to delete goal. Please try again.');
    }
}


// Update goal select dropdown
function updateGoalSelect() {
    const select = document.getElementById('habitGoal');
    if (!select) return;
    
    const currentValue = select.value;
    
    select.innerHTML = '<option value="">No Goal (Misc)</option>';
    
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
    
    // If no habits exist, show empty state
    if (!analytics || analytics.overall.total === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <h3>No Data Available</h3>
                <p>Create some habits to see analytics!</p>
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
                        <div class="stat-label">Total Habits</div>
                    </div>
                        <div class="stat-item stat-success">
                        <div class="stat-value">${analytics.overall.completed}</div>
                        <div class="stat-label">Total Check-ins</div>
                    </div>
                    <div class="stat-item stat-warning">
                        <div class="stat-value">${analytics.overall.incomplete}</div>
                        <div class="stat-label">Active Habits</div>
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
                        <span class="priority-count">${stats.total} habits</span>
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
                            <span class="summary-label">Habits with Goals:</span>
                            <span class="summary-value">${analytics.by_goal.tasks_with_goals}</span>
                        </div>
                        <div class="goal-stat-summary-item">
                            <span class="summary-label">Habits without Goals:</span>
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
                        <span>${goalStat.completed} of ${goalStat.total} habits tracked</span>
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
                        <div class="time-stat-label">Missed Today</div>
                    </div>
                    <div class="time-stat-item ${analytics.time_stats.due_soon_count > 0 ? 'stat-warning' : ''}">
                        <div class="time-stat-icon">⏳</div>
                        <div class="time-stat-value">${analytics.time_stats.due_soon_count}</div>
                        <div class="time-stat-label">Active This Week</div>
                    </div>
                    <div class="time-stat-item stat-success">
                        <div class="time-stat-icon">✅</div>
                        <div class="time-stat-value">${analytics.time_stats.completed_today}</div>
                        <div class="time-stat-label">Checked In Today</div>
                    </div>
                    <div class="time-stat-item stat-primary">
                        <div class="time-stat-icon">➕</div>
                        <div class="time-stat-value">${analytics.time_stats.created_today}</div>
                        <div class="time-stat-label">Habits Created Today</div>
                    </div>
                    <div class="time-stat-item">
                        <div class="time-stat-icon">📅</div>
                        <div class="time-stat-value">${analytics.time_stats.avg_completion_days}</div>
                        <div class="time-stat-label">Avg Check-ins per Habit</div>
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
                    <div class="insight-detail">${analytics.productivity.max_tasks_in_goal} habits</div>
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
                    <div class="insight-title">Habit Distribution</div>
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
