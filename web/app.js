/* ============================================
   TO-DO APPLICATION - MAIN JAVASCRIPT FILE
   ============================================
   
   This file contains all frontend JavaScript logic for the ToDo application.
   It handles:
   - Task management (CRUD operations)
   - Goal management (CRUD operations)
   - Journal functionality with timer
   - Analytics display
   - UI interactions and event handling
   - Data synchronization with Python backend via Eel
   
   Architecture:
   - State management: Global variables for tasks, goals, filters
   - Event-driven: Uses event delegation for dynamic content
   - Async operations: All backend calls are async/await
   - Modular functions: Each feature has dedicated functions
   ============================================ */

/* ============================================
   GLOBAL STATE VARIABLES
   ============================================ */

/**
 * Array of all tasks loaded from the backend
 * Each task object contains: id, title, description, priority, due_date, 
 * completed, goal_id, created_at, completed_at
 */
let tasks = [];

/**
 * Array of all goals loaded from the backend
 * Each goal object contains: id, title, description, created_at
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

/* ============================================
   APPLICATION INITIALIZATION
   ============================================ */

/**
 * Initialize the application
 * This is the main entry point called when the page loads.
 * 
 * Flow:
 * 1. Show loading indicators
 * 2. Load initial data (tasks and goals) from backend
 * 3. Set up event listeners for user interactions
 * 4. Initialize tab switching functionality
 * 5. Initialize journal functionality
 * 6. Hide loading indicators
 * 7. Animate elements for smooth entrance
 * 
 * @async
 */
async function init() {
    // Show loading state to provide user feedback
    showLoadingState();
    
    // Load data from backend in parallel for better performance
    await Promise.all([loadTasks(), loadGoals()]);
    
    // Set up all event listeners for user interactions
    setupEventListeners();
    
    // Initialize tab navigation system
    setupTabs();
    
    // Initialize journal timer and entry functionality
    setupJournal();
    
    // Initialize notification settings
    setupNotificationSettings();
    
    // Hide loading indicators now that data is loaded
    hideLoadingState();
    
    // Add smooth entrance animations for better UX
    animateElements();
}

/* ============================================
   UI UTILITY FUNCTIONS
   ============================================ */

/**
 * Display loading indicators in specified containers
 * Shows a spinner and "Loading..." text while data is being fetched
 * 
 * Containers updated:
 * - tasksContainer: Shows loading state for tasks
 * - goalsContainer: Shows loading state for goals
 */
function showLoadingState() {
    const containers = ['tasksContainer', 'goalsContainer'];
    containers.forEach(id => {
        const container = document.getElementById(id);
        if (container) {
            container.innerHTML = '<div class="empty-state"><div class="loading-spinner"></div><p>Loading...</p></div>';
        }
    });
}

/**
 * Hide loading indicators
 * Loading state is automatically replaced when actual content is rendered
 * This function exists for consistency and potential future use
 */
function hideLoadingState() {
    // Loading state will be replaced by actual content when render functions are called
}

/**
 * Animate elements on page load for smooth entrance effect
 * 
 * Animation sequence:
 * 1. Elements start invisible and slightly below their final position
 * 2. Each element fades in and slides up with a staggered delay
 * 3. Creates a cascading entrance effect
 * 
 * Elements animated:
 * - .task-item: Individual task cards
 * - .goal-item: Individual goal cards
 * - .category-header: Category/group headers
 * 
 * @param {number} index - Delay multiplier (50ms per index for stagger effect)
 */
function animateElements() {
    const elements = document.querySelectorAll('.task-item, .goal-item, .category-header');
    elements.forEach((el, index) => {
        // Start invisible and below final position
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        
        // Animate after a staggered delay
        setTimeout(() => {
            el.style.transition = 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)';
            el.style.opacity = '1';
            el.style.transform = 'translateY(0)';
        }, index * 50); // 50ms delay between each element
    });
}

/**
 * Add ripple effect to buttons for visual feedback
 * 
 * Creates a Material Design-style ripple animation when button is clicked.
 * The ripple expands from the click point and fades out.
 * 
 * @param {HTMLElement} button - The button element to add ripple effect to
 * 
 * How it works:
 * 1. Creates a span element for the ripple
 * 2. Calculates size based on button dimensions (ensures full coverage)
 * 3. Positions ripple at click coordinates
 * 4. Adds ripple class for styling
 * 5. Removes ripple after animation completes (600ms)
 */
function addRippleEffect(button) {
    button.addEventListener('click', function(e) {
        // Create ripple element
        const ripple = document.createElement('span');
        
        // Get button position and dimensions
        const rect = this.getBoundingClientRect();
        
        // Calculate ripple size (largest dimension to ensure full coverage)
        const size = Math.max(rect.width, rect.height);
        
        // Calculate position relative to button (centered on click point)
        const x = e.clientX - rect.left - size / 2;
        const y = e.clientY - rect.top - size / 2;
        
        // Set ripple dimensions and position
        ripple.style.width = ripple.style.height = size + 'px';
        ripple.style.left = x + 'px';
        ripple.style.top = y + 'px';
        ripple.classList.add('ripple');
        
        // Add ripple to button
        this.appendChild(ripple);
        
        // Remove ripple after animation completes
        setTimeout(() => {
            ripple.remove();
        }, 600);
    });
}

/* ============================================
   DATA LOADING FUNCTIONS
   ============================================ */

/**
 * Load all tasks from the Python backend
 * 
 * Flow:
 * 1. Call Python backend function get_tasks() via Eel
 * 2. Store tasks in global tasks array
 * 3. Re-render tasks in the UI
 * 4. Update goal filter dropdown (tasks may have changed goal assignments)
 * 5. Update goal select dropdown (for task creation form)
 * 
 * Error handling:
 * - Logs errors to console for debugging
 * - UI will show empty state if tasks fail to load
 * 
 * @async
 * @throws {Error} If backend call fails
 */
async function loadTasks() {
    try {
        // Fetch tasks from Python backend via Eel
        tasks = await eel.get_tasks()();
        
        // Update UI with loaded tasks
        renderTasks();
        
        // Update filter dropdowns (tasks may have new goal assignments)
        updateGoalFilter();
        updateGoalSelect();
    } catch (error) {
        console.error('Error loading tasks:', error);
        // Error is logged but doesn't crash the app
        // UI will show empty state or previous data
    }
}

/**
 * Load all goals from the Python backend
 * 
 * Flow:
 * 1. Call Python backend function get_goals() via Eel
 * 2. Store goals in global goals array
 * 3. Re-render goals in the UI
 * 4. Update goal select dropdown (for task creation form)
 * 5. Update goal filter dropdown (for task filtering)
 * 
 * Error handling:
 * - Logs errors to console for debugging
 * - UI will show empty state if goals fail to load
 * 
 * @async
 * @throws {Error} If backend call fails
 */
async function loadGoals() {
    try {
        // Fetch goals from Python backend via Eel
        goals = await eel.get_goals()();
        
        // Update UI with loaded goals
        renderGoals();
        
        // Update dropdowns that depend on goals
        updateGoalSelect();  // For task creation form
        updateGoalFilter();  // For task filtering
    } catch (error) {
        console.error('Error loading goals:', error);
        // Error is logged but doesn't crash the app
        // UI will show empty state or previous data
    }
}


/* ============================================
   EVENT LISTENER SETUP
   ============================================ */

/**
 * Set up all event listeners for user interactions
 * 
 * This function attaches event handlers to:
 * - Form submissions (task and goal creation)
 * - UI toggles (task form visibility)
 * - Search input (real-time filtering)
 * - Filter dropdowns (priority and goal filtering)
 * - Completed tasks toggle button
 * 
 * Called once during app initialization.
 * All event listeners are attached to static elements that exist on page load.
 */
function setupEventListeners() {
    // Task form submission - handles new task creation
    const taskForm = document.getElementById('taskForm');
    if (taskForm) {
        taskForm.addEventListener('submit', handleAddTask);
    }
    
    // Toggle task form visibility - show/hide the task creation form
    const toggleTaskFormBtn = document.getElementById('toggleTaskForm');
    const taskFormContainer = document.getElementById('taskFormContainer');
    if (toggleTaskFormBtn && taskFormContainer) {
        toggleTaskFormBtn.addEventListener('click', () => {
            const isVisible = taskFormContainer.style.display !== 'none';
            
            if (isVisible) {
                // Hiding form - reset to add mode and clear any edit state
                window.editingTaskId = undefined;
                document.getElementById('taskForm').reset();
                
                // Reset form title and button text
                const formTitle = taskFormContainer.querySelector('h2');
                const submitButton = document.querySelector('#taskForm button[type="submit"]');
                if (formTitle) {
                    formTitle.textContent = 'Add New Task';
                }
                if (submitButton) {
                    submitButton.textContent = 'Add Task';
                }
            }
            
            // Toggle visibility
            taskFormContainer.style.display = isVisible ? 'none' : 'block';
            // Update button text and icon
            toggleTaskFormBtn.innerHTML = isVisible 
                ? '<span class="btn-icon">+</span> Add New Task'
                : '<span class="btn-icon">−</span> Cancel';
        });
    }
    
    // Goal form submission - handles new goal creation
    const goalForm = document.getElementById('goalForm');
    if (goalForm) {
        goalForm.addEventListener('submit', handleAddGoal);
    }
    
    // Search input - real-time text search as user types
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', handleSearch);
    }
    
    // Filter dropdowns - filter tasks by priority or goal
    const filterPriority = document.getElementById('filterPriority');
    if (filterPriority) {
        filterPriority.addEventListener('change', handleFilterChange);
    }
    
    const filterGoal = document.getElementById('filterGoal');
    if (filterGoal) {
        filterGoal.addEventListener('change', handleFilterChange);
    }
    
    // Sort dropdown - change how tasks are sorted/displayed
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

/* ============================================
   TAB NAVIGATION SYSTEM
   ============================================ */

/**
 * Initialize tab navigation system
 * 
 * Sets up click handlers for all tab buttons.
 * When a tab button is clicked, it calls switchTab() to change the active tab.
 * 
 * Tab buttons are identified by the data-tab attribute:
 * - data-tab="tasks" -> Tasks tab
 * - data-tab="goals" -> Goals tab
 * - data-tab="analytics" -> Analytics tab
 * - data-tab="journal" -> Journal tab
 */
function setupTabs() {
    document.querySelectorAll('.tab-button').forEach(button => {
        button.addEventListener('click', () => {
            const tabName = button.getAttribute('data-tab');
            if (tabName) {
                switchTab(tabName);
            }
        });
    });
}

/**
 * Switch to a different tab
 * 
 * This function handles tab switching by:
 * 1. Updating tab button active states (visual indication)
 * 2. Showing/hiding tab content panels
 * 3. Loading tab-specific data if needed (analytics, journal)
 * 
 * @param {string} tabName - Name of the tab to switch to ('tasks', 'goals', 'analytics', 'journal')
 * 
 * Special handling:
 * - Analytics tab: Loads analytics data and sets up drag/resize functionality
 * - Journal tab: Loads past journal entries from last 30 days
 */
function switchTab(tabName) {
    // Update tab button active states
    // Remove 'active' class from all buttons
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });
    // Add 'active' class to clicked button
    const activeButton = document.querySelector(`[data-tab="${tabName}"]`);
    if (activeButton) {
        activeButton.classList.add('active');
    }
    
    // Update tab content visibility
    // Hide all tab content panels
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    // Show selected tab content
    const activeTab = document.getElementById(`${tabName}Tab`);
    if (activeTab) {
        activeTab.classList.add('active');
    }
    
    // Load tab-specific data if needed
    if (tabName === 'analytics') {
        // Analytics tab requires data loading and drag/resize setup
        loadAnalytics();
        setupAnalytics();
    } else if (tabName === 'journal') {
        // Journal tab loads past entries when opened
        loadPastEntries();
    } else if (tabName === 'settings') {
        // Settings tab loads current notification settings
        loadNotificationSettings();
    }
}

/* ============================================
   TASK MANAGEMENT FUNCTIONS
   ============================================ */

/**
 * Handle adding a new task to the system
 * 
 * This function processes the task creation form submission:
 * 1. Validates input (title is required)
 * 2. Extracts form values (title, description, priority, due date, goal)
 * 3. Shows loading state on submit button
 * 4. Calls Python backend to save the task
 * 5. Resets form and hides it on success
 * 6. Reloads tasks to show the new task
 * 7. Provides user feedback (success/error messages)
 * 
 * Form fields:
 * - taskTitle: Required task title
 * - taskDescription: Optional task description
 * - taskPriority: Priority level ('Now', 'Next', 'Later')
 * - taskDueDate: Optional due date (ISO format)
 * - taskGoal: Optional goal ID to link task to a goal
 * 
 * @param {Event} e - Form submission event
 * @async
 */
async function handleAddTask(e) {
    // Prevent default form submission (page reload)
    e.preventDefault();
    
    // Extract form values
    const title = document.getElementById('taskTitle').value.trim();
    const description = document.getElementById('taskDescription').value.trim();
    const priority = document.getElementById('taskPriority').value;
    const dueDate = document.getElementById('taskDueDate').value;
    const goalSelect = document.getElementById('taskGoal');
    const timeSpentInput = document.getElementById('taskTimeSpent');
    
    // Parse goal ID (convert string to integer, or null if no goal selected)
    const goalId = goalSelect.value ? parseInt(goalSelect.value) : null;
    
    // Parse time spent (convert to float, or null if not provided)
    const timeSpent = timeSpentInput && timeSpentInput.value ? parseFloat(timeSpentInput.value) : null;
    
    // Validate time spent if provided
    if (timeSpent !== null && (isNaN(timeSpent) || timeSpent < 0)) {
        showErrorFeedback('Time spent must be a non-negative number');
        return;
    }
    
    // Validate required fields
    if (!title) {
        showErrorFeedback('Please enter a task title');
        return;
    }
    
    // Find form and submit button for loading state
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
    
    // Check if we're in edit mode (editing an existing task)
    const isEditMode = window.editingTaskId !== undefined && window.editingTaskId !== null;
    const taskId = isEditMode ? window.editingTaskId : null;
    
    // Show loading state on button
    const originalText = submitButton.textContent;
    submitButton.textContent = isEditMode ? 'Updating...' : 'Adding...';
    submitButton.disabled = true;
    
    try {
        if (isEditMode) {
            // Update existing task
            const result = await eel.update_task(taskId, title, description, priority, dueDate, goalId, timeSpent)();
            
            if (!result) {
                throw new Error('Task update failed - task not found');
            }
            
            // Clear edit mode
            window.editingTaskId = undefined;
            
            // Show success message
            showSuccessFeedback('Task updated successfully!');
        } else {
            // Create new task
            await eel.add_task(title, description, priority, dueDate, goalId, timeSpent)();
            
            // Show success message
            showSuccessFeedback('Task added successfully!');
        }
        
        // Reset form to clear all fields
        document.getElementById('taskForm').reset();
        
        // Reset form title and button text to add mode
        const formContainer = document.getElementById('taskFormContainer');
        const formTitle = formContainer ? formContainer.querySelector('h2') : null;
        if (formTitle) {
            formTitle.textContent = 'Add New Task';
        }
        submitButton.textContent = 'Add Task';
        
        // Hide form after successful submission
        const toggleTaskFormBtn = document.getElementById('toggleTaskForm');
        if (taskFormContainer) {
            taskFormContainer.style.display = 'none';
        }
        if (toggleTaskFormBtn) {
            toggleTaskFormBtn.innerHTML = '<span class="btn-icon">+</span> Add New Task';
        }
        
        // Reload tasks to display the updated/new task
        await loadTasks();
        // Also reload goals to update progress if task was linked to a goal
        await loadGoals();
    } catch (error) {
        // Handle errors gracefully
        console.error(`Error ${isEditMode ? 'updating' : 'adding'} task:`, error);
        showErrorFeedback(`Failed to ${isEditMode ? 'update' : 'add'} task. Please try again.`);
        // Log detailed error for debugging
        console.error('Full error details:', error);
    } finally {
        // Always restore button state, even if there was an error
        submitButton.textContent = originalText;
        submitButton.disabled = false;
    }
}

// Handle adding a new goal
async function handleAddGoal(e) {
    e.preventDefault();
    
    const title = document.getElementById('goalTitle').value.trim();
    const description = document.getElementById('goalDescription').value.trim();
    const timeGoalInput = document.getElementById('goalTimeGoal');
    const timeGoal = timeGoalInput && timeGoalInput.value ? parseFloat(timeGoalInput.value) : null;
    
    if (!title) {
        showErrorFeedback('Please enter a goal title');
        return;
    }
    
    // Validate time goal if provided
    if (timeGoal !== null && (isNaN(timeGoal) || timeGoal <= 0)) {
        showErrorFeedback('Time goal must be a positive number');
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
        // Check if we're in edit mode
        const isEditMode = window.editingGoalId !== undefined && window.editingGoalId !== null;
        const goalId = isEditMode ? window.editingGoalId : null;
        
        if (isEditMode) {
            // Update existing goal
            const result = await eel.update_goal(goalId, title, description, timeGoal)();
            if (!result) {
                throw new Error('Goal update failed - goal not found');
            }
            window.editingGoalId = undefined;
            showSuccessFeedback('Goal updated successfully!');
        } else {
            // Create new goal
            await eel.add_goal(title, description, timeGoal)();
            showSuccessFeedback('Goal added successfully!');
        }
        
        document.getElementById('goalForm').reset();
        
        // Reset form title and button text
        const formTitle = document.querySelector('.goals-form h2');
        const submitButton = document.querySelector('#goalForm button[type="submit"]');
        if (formTitle) {
            formTitle.textContent = 'Add New Goal';
        }
        if (submitButton) {
            submitButton.textContent = 'Add Goal';
        }
        
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

/* ============================================
   USER FEEDBACK FUNCTIONS
   ============================================ */

/**
 * Display a success notification to the user
 * 
 * Creates a temporary notification that appears at the top of the screen,
 * fades in, displays for 3 seconds, then fades out and removes itself.
 * 
 * Visual feedback:
 * - Green background (success color)
 * - Slides down from top
 * - Auto-dismisses after 3 seconds
 * 
 * @param {string} message - Success message to display
 * 
 * Animation timeline:
 * - 10ms: Add 'show' class for fade-in animation
 * - 3000ms: Remove 'show' class for fade-out
 * - 3300ms: Remove element from DOM
 */
function showSuccessFeedback(message) {
    // Create feedback element
    const feedback = document.createElement('div');
    feedback.className = 'feedback feedback-success';
    feedback.textContent = message;
    
    // Add to page
    document.body.appendChild(feedback);
    
    // Trigger fade-in animation
    setTimeout(() => {
        feedback.classList.add('show');
    }, 10);
    
    // Auto-dismiss after 3 seconds
    setTimeout(() => {
        feedback.classList.remove('show');
        // Remove from DOM after fade-out animation completes
        setTimeout(() => feedback.remove(), 300);
    }, 3000);
}

/**
 * Display an error notification to the user
 * 
 * Creates a temporary notification that appears at the top of the screen,
 * fades in, displays for 3 seconds, then fades out and removes itself.
 * 
 * Visual feedback:
 * - Red background (error color)
 * - Slides down from top
 * - Auto-dismisses after 3 seconds
 * 
 * @param {string} message - Error message to display
 * 
 * Animation timeline:
 * - 10ms: Add 'show' class for fade-in animation
 * - 3000ms: Remove 'show' class for fade-out
 * - 3300ms: Remove element from DOM
 */
function showErrorFeedback(message) {
    // Create feedback element
    const feedback = document.createElement('div');
    feedback.className = 'feedback feedback-error';
    feedback.textContent = message;
    
    // Add to page
    document.body.appendChild(feedback);
    
    // Trigger fade-in animation
    setTimeout(() => {
        feedback.classList.add('show');
    }, 10);
    
    // Auto-dismiss after 3 seconds
    setTimeout(() => {
        feedback.classList.remove('show');
        // Remove from DOM after fade-out animation completes
        setTimeout(() => feedback.remove(), 300);
    }, 3000);
}

/* ============================================
   FILTERING AND SEARCH FUNCTIONS
   ============================================ */

/**
 * Handle search input changes
 * 
 * Updates the search filter as the user types and re-renders tasks.
 * Search is case-insensitive and matches against task titles and descriptions.
 * 
 * @param {Event} e - Input event from search field
 * 
 * Flow:
 * 1. Get search text from input field
 * 2. Convert to lowercase for case-insensitive matching
 * 3. Update global currentFilter.search
 * 4. Re-render tasks with new filter applied
 */
function handleSearch(e) {
    // Update search filter (case-insensitive)
    currentFilter.search = e.target.value.toLowerCase();
    
    // Re-render tasks with new search filter
    renderTasks();
}

/**
 * Handle sort dropdown changes
 * 
 * Updates the current sort mode and re-renders tasks with the new sorting.
 * 
 * Sort modes:
 * - 'category': Group by goal/category (default)
 * - 'due-date': Sort by due date (earliest first)
 * - 'due-today': Show only tasks due today
 * - 'due-week': Show only tasks due this week (next 7 days)
 * - 'priority': Sort by priority (Now > Next > Later)
 * 
 * Flow:
 * 1. Get selected sort mode from dropdown
 * 2. Update global currentSort variable
 * 3. Re-render tasks with new sorting applied
 */
function handleSortChange() {
    const sortSelect = document.getElementById('sortTasks');
    if (sortSelect) {
        currentSort = sortSelect.value;
        renderTasks();
    }
}

/**
 * Handle filter dropdown changes
 * 
 * Updates priority and goal filters when user selects from dropdowns.
 * Re-renders tasks to show only matching items.
 * 
 * Filters applied:
 * - Priority: Filter by 'Now', 'Next', 'Later', or all
 * - Goal: Filter by specific goal ID, or all goals
 * 
 * Flow:
 * 1. Get selected values from filter dropdowns
 * 2. Update global currentFilter object
 * 3. Re-render tasks with new filters applied
 */
function handleFilterChange() {
    // Update priority filter
    const prioritySelect = document.getElementById('filterPriority');
    if (prioritySelect) {
        currentFilter.priority = prioritySelect.value;
    }
    
    // Update goal filter
    const goalSelect = document.getElementById('filterGoal');
    if (goalSelect) {
        currentFilter.goal = goalSelect.value;
    }
    
    // Re-render tasks with new filters
    renderTasks();
}

/**
 * Toggle visibility of completed tasks
 * 
 * Switches between showing and hiding completed tasks in the task list.
 * Updates button text to reflect current state.
 * 
 * States:
 * - showCompleted = false: Hide completed tasks (default)
 * - showCompleted = true: Show completed tasks
 * 
 * Flow:
 * 1. Toggle the showCompleted boolean flag
 * 2. Update button text to reflect new state
 * 3. Re-render tasks (filtering will apply based on new state)
 */
function toggleCompleted() {
    // Toggle the flag
    showCompleted = !showCompleted;
    
    // Update button text to reflect current state
    const btn = document.getElementById('showCompleted');
    if (btn) {
        btn.textContent = showCompleted ? 'Hide Completed' : 'Show Completed';
    }
    
    // Re-render tasks (filtering logic will apply the visibility setting)
    renderTasks();
}

// Toggle task completion
async function toggleTask(taskId) {
    try {
        if (!taskId || isNaN(taskId)) {
            console.error('Invalid task ID:', taskId);
            return false;
        }
        
        const result = await eel.toggle_task(taskId)();
        
        if (!result) {
            console.error('Task not found or toggle failed for ID:', taskId);
            showErrorFeedback('Failed to toggle task. Please try again.');
            return false;
        }
        
        // Reload tasks and goals to reflect the change
        await Promise.all([loadTasks(), loadGoals()]);
        return true;
    } catch (error) {
        console.error('Error toggling task:', error);
        showErrorFeedback('Failed to toggle task. Please try again.');
        return false;
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

/* ============================================
   TASK EDITING FUNCTION
   ============================================ */

/**
 * Edit an existing task by populating the form with its data
 * 
 * This function enables editing mode for a task:
 * 1. Finds the task by ID
 * 2. Populates the task form with the task's current data
 * 3. Sets the form to "edit mode" (changes title and button text)
 * 4. Stores the task ID being edited in a global variable
 * 5. Shows the form and scrolls to it
 * 
 * When the form is submitted in edit mode, handleAddTask() will detect
 * the edit mode and call update_task() instead of add_task().
 * 
 * @param {number} taskId - ID of the task to edit
 */
function editTask(taskId) {
    // Find the task in the current tasks array
    const task = tasks.find(t => t.id === taskId);
    if (!task) {
        console.error('Task not found for editing:', taskId);
        showErrorFeedback('Task not found. Please refresh the page.');
        return;
    }
    
    // Store the task ID being edited (used by handleAddTask to detect edit mode)
    window.editingTaskId = taskId;
    
    // Populate form with task's current data
    document.getElementById('taskTitle').value = task.title;
    document.getElementById('taskDescription').value = task.description || '';
    document.getElementById('taskPriority').value = task.priority;
    document.getElementById('taskDueDate').value = task.due_date || '';
    
    // Set goal selection (handle both integer and null values)
    const goalSelect = document.getElementById('taskGoal');
    if (goalSelect) {
        goalSelect.value = task.goal_id || '';
    }
    
    // Set time spent if available
    const timeSpentInput = document.getElementById('taskTimeSpent');
    if (timeSpentInput) {
        timeSpentInput.value = task.time_spent || '';
    }
    
    // Update form title and button text to indicate edit mode
    const formContainer = document.getElementById('taskFormContainer');
    const formTitle = formContainer ? formContainer.querySelector('h2') : null;
    if (formTitle) {
        formTitle.textContent = 'Edit Task';
    }
    
    const submitButton = document.querySelector('#taskForm button[type="submit"]');
    if (submitButton) {
        submitButton.textContent = 'Update Task';
    }
    
    // Show the form (if hidden)
    if (formContainer) {
        formContainer.style.display = 'block';
    }
    
    // Update toggle button text
    const toggleTaskFormBtn = document.getElementById('toggleTaskForm');
    if (toggleTaskFormBtn) {
        toggleTaskFormBtn.innerHTML = '<span class="btn-icon">−</span> Cancel';
    }
    
    // Switch to tasks tab (in case user is on another tab)
    switchTab('tasks');
    
    // Scroll to form for better UX
    setTimeout(() => {
        const taskForm = document.querySelector('.task-form');
        if (taskForm) {
            taskForm.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }, 100);
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
    
    // Filter out tasks marked as not_completed (overdue by >24 hours)
    // These tasks are hidden from the to-do tab but still exist for analytics
    filteredTasks = filteredTasks.filter(task => !task.not_completed);
    
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
    
    // Apply sorting based on current sort mode
    let html = '';
    
    if (currentSort === 'category') {
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
    } else if (currentSort === 'due-date' || currentSort === 'due-today' || currentSort === 'due-week') {
        // Sort by due date (earliest first)
        const sortedTasks = [...filteredTasks].sort((a, b) => {
            // Incomplete tasks first
            if (a.completed !== b.completed) {
                return a.completed ? 1 : -1;
            }
            // Then by due date
            if (a.due_date && b.due_date) {
                return new Date(a.due_date) - new Date(b.due_date);
            }
            if (a.due_date) return -1;
            if (b.due_date) return 1;
            // Then by priority
            const priorityOrder = { Now: 3, Next: 2, Later: 1 };
            const priorityA = priorityOrder[a.priority] || 0;
            const priorityB = priorityOrder[b.priority] || 0;
            return priorityB - priorityA;
        });
        
        // Group by due date for better organization
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
        
        // Render by date groups
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
            html += `<div class="category-header">${escapeHtml(dateKey)}</div>`;
            html += `<div class="category-tasks-row">`;
            tasksByDate[dateKey].forEach(task => {
                html += createTaskHTML(task);
            });
            html += `</div>`;
        });
    } else if (currentSort === 'priority') {
        // Sort by priority (Now > Next > Later)
        const priorityOrder = { Now: 3, Next: 2, Later: 1 };
        const sortedTasks = [...filteredTasks].sort((a, b) => {
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
        
        // Group by priority
        const tasksByPriority = {};
        sortedTasks.forEach(task => {
            const priority = task.priority || 'Later';
            if (!tasksByPriority[priority]) {
                tasksByPriority[priority] = [];
            }
            tasksByPriority[priority].push(task);
        });
        
        // Render by priority
        const priorityOrderKeys = ['Now', 'Next', 'Later'];
        priorityOrderKeys.forEach(priority => {
            if (tasksByPriority[priority] && tasksByPriority[priority].length > 0) {
                html += `<div class="category-header">${escapeHtml(priority)} Priority</div>`;
                html += `<div class="category-tasks-row">`;
                tasksByPriority[priority].forEach(task => {
                    html += createTaskHTML(task);
                });
                html += `</div>`;
            }
        });
    }
    
    container.innerHTML = html;
    
    // Use event delegation for better reliability
    // Remove old listeners if they exist (using named functions for removal)
    if (container._taskChangeHandler) {
        container.removeEventListener('change', container._taskChangeHandler);
    }
    if (container._taskClickHandler) {
        container.removeEventListener('click', container._taskClickHandler);
    }
    
    // Create named handler functions for event delegation
    container._taskChangeHandler = async (e) => {
        if (e.target && e.target.classList.contains('task-checkbox')) {
            e.stopPropagation(); // Prevent event from bubbling
            e.preventDefault(); // Prevent default checkbox behavior
            
            const taskId = parseInt(e.target.id.replace('checkbox-', ''));
            if (taskId && !isNaN(taskId)) {
                // Store the intended state (opposite of current, since we're toggling)
                const intendedState = e.target.checked;
                
                // Disable checkbox during async operation to prevent multiple clicks
                e.target.disabled = true;
                
                try {
                    const success = await toggleTask(taskId);
                    
                    if (!success) {
                        // Revert checkbox state on failure
                        e.target.checked = !intendedState;
                    }
                    // If success, the checkbox state will be updated by renderTasks()
                } catch (error) {
                    // Revert checkbox state on error
                    e.target.checked = !intendedState;
                    console.error('Error toggling task:', error);
                } finally {
                    // Re-enable checkbox after operation completes
                    e.target.disabled = false;
                }
            }
        }
    };
    
    container._taskClickHandler = async (e) => {
        if (e.target && e.target.id) {
            const id = e.target.id;
            
            // Handle delete button
            if (id.startsWith('delete-')) {
                const taskId = parseInt(id.replace('delete-', ''));
                if (taskId && !isNaN(taskId)) {
                    await deleteTask(taskId);
                }
            }
            
            // Handle edit button
            if (id.startsWith('edit-')) {
                const taskId = parseInt(id.replace('edit-', ''));
                if (taskId && !isNaN(taskId)) {
                    editTask(taskId);
                }
            }
        }
    };
    
    // Attach event listeners
    container.addEventListener('change', container._taskChangeHandler);
    container.addEventListener('click', container._taskClickHandler);
    
    // Add ripple effects to buttons (for visual feedback)
    filteredTasks.forEach(task => {
        const checkbox = document.getElementById(`checkbox-${task.id}`);
        const deleteBtn = document.getElementById(`delete-${task.id}`);
        const editBtn = document.getElementById(`edit-${task.id}`);
        
        if (checkbox) {
            addRippleEffect(checkbox.parentElement);
        }
        if (deleteBtn) {
            addRippleEffect(deleteBtn);
        }
        if (editBtn) {
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
    // Build progress text showing both tasks and habits
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
    
    // Build time progress section if time_goal is set
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
            <div class="goal-title">${escapeHtml(goal.title)}</div>
            ${goal.description ? `<div class="goal-description">${escapeHtml(goal.description)}</div>` : ''}
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

// Edit goal
async function editGoal(goalId) {
    const goal = goals.find(g => g.id === goalId);
    if (!goal) return;
    
    // Store the goal ID being edited
    window.editingGoalId = goalId;
    
    // Populate form with goal's current data
    document.getElementById('goalTitle').value = goal.title;
    document.getElementById('goalDescription').value = goal.description || '';
    
    // Set time goal if available
    const timeGoalInput = document.getElementById('goalTimeGoal');
    if (timeGoalInput) {
        timeGoalInput.value = goal.time_goal || '';
    }
    
    // Update form title and button text
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
 * Load analytics data from backend and render it
 * 
 * This function:
 * 1. Calls the Python backend to get analytics data
 * 2. Renders the analytics using renderAnalytics()
 * 3. Handles errors gracefully
 * 
 * @async
 */
async function loadAnalytics() {
    try {
        const analytics = await eel.get_analytics()();
        renderAnalytics(analytics);
    } catch (error) {
        console.error('Error loading analytics:', error);
        const container = document.getElementById('analyticsContainer');
        if (container) {
            container.innerHTML = `
                <div class="empty-state">
                    <h3>Error loading analytics</h3>
                    <p>Please try again later.</p>
                </div>
            `;
        }
    }
}

/**
 * Render analytics data in the analytics container
 * 
 * This function creates all the analytics cards with drag/resize functionality.
 * 
 * @param {Object} analytics - Analytics data object from backend
 */
function renderAnalytics(analytics) {
    const container = document.getElementById('analyticsContainer');
    
    if (!container) {
        console.error('Analytics container not found');
        return;
    }
    
    // If no analytics data or no tasks exist, show empty state
    if (!analytics || !analytics.overall || analytics.overall.total === 0) {
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
                        <div class="stat-value">${analytics.overall.incomplete || 0}</div>
                        <div class="stat-label">Incomplete</div>
                    </div>
                    ${analytics.overall.not_completed !== undefined ? `
                    <div class="stat-item stat-danger">
                        <div class="stat-value">${analytics.overall.not_completed || 0}</div>
                        <div class="stat-label">Not Completed (Overdue)</div>
                    </div>
                    ` : ''}
                    <div class="stat-item stat-primary">
                        <div class="stat-value">${(analytics.overall.completion_percentage || 0).toFixed(1)}%</div>
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
    if (analytics.by_goal && analytics.by_goal.goals && 
        typeof analytics.by_goal.goals === 'object' && 
        Object.keys(analytics.by_goal.goals).length > 0) {
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
        const stats = analytics.by_priority && analytics.by_priority[priority];
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
    }
    
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
    if (analytics.productivity && analytics.productivity.most_productive_goal) {
        html += `
            <div class="insight-item">
                <div class="insight-icon">🏆</div>
                <div class="insight-content">
                    <div class="insight-title">Most Productive Goal</div>
                    <div class="insight-value">${escapeHtml(analytics.productivity.most_productive_goal)}</div>
                    <div class="insight-detail">${(analytics.productivity.most_productive_completion_rate || 0).toFixed(1)}% completion rate</div>
                </div>
            </div>
        `;
    }
    
    // Goal with most tasks
    if (analytics.productivity && analytics.productivity.goal_with_most_tasks) {
        html += `
            <div class="insight-item">
                <div class="insight-icon">📊</div>
                <div class="insight-content">
                    <div class="insight-title">Most Active Goal</div>
                    <div class="insight-value">${escapeHtml(analytics.productivity.goal_with_most_tasks)}</div>
                    <div class="insight-detail">${analytics.productivity.max_tasks_in_goal || 0} tasks</div>
                </div>
            </div>
        `;
    }
    
    // Goal distribution
    if (analytics.productivity && analytics.productivity.goal_distribution && 
        typeof analytics.productivity.goal_distribution === 'object' &&
        Object.keys(analytics.productivity.goal_distribution).length > 0) {
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

/**
 * Load saved card positions and sizes from localStorage
 */
function loadCardPositions() {
    try {
        const savedPositions = localStorage.getItem('analyticsCardPositions');
        const savedSizes = localStorage.getItem('analyticsCardSizes');
        
        if (savedPositions) {
            const positions = JSON.parse(savedPositions);
            Object.entries(positions).forEach(([cardId, pos]) => {
                const card = document.querySelector(`[data-card-id="${cardId}"]`);
                if (card) {
                    card.style.position = 'absolute';
                    card.style.left = pos.x + 'px';
                    card.style.top = pos.y + 'px';
                }
            });
        }
        
        if (savedSizes) {
            const sizes = JSON.parse(savedSizes);
            Object.entries(sizes).forEach(([cardId, size]) => {
                const card = document.querySelector(`[data-card-id="${cardId}"]`);
                if (card) {
                    card.style.width = size.width + 'px';
                    card.style.height = size.height + 'px';
                }
            });
        }
    } catch (error) {
        console.error('Error loading card positions:', error);
    }
}

/**
 * Initialize drag and resize functionality for analytics cards
 */
function initializeDragAndResize() {
    const cards = document.querySelectorAll('.draggable-card');
    
    cards.forEach(card => {
        const dragHandle = card.querySelector('.card-drag-handle');
        const resizeHandle = card.querySelector('.card-resize-handle');
        
        // Show handles on hover
        card.addEventListener('mouseenter', () => {
            if (dragHandle) dragHandle.style.opacity = '1';
            if (resizeHandle) resizeHandle.style.opacity = '1';
        });
        
        card.addEventListener('mouseleave', () => {
            if (dragHandle) dragHandle.style.opacity = '0';
            if (resizeHandle) resizeHandle.style.opacity = '0';
        });
        
        // Drag functionality
        if (dragHandle) {
            let isDragging = false;
            let startX, startY, initialX, initialY;
            
            dragHandle.addEventListener('mousedown', (e) => {
                isDragging = true;
                card.classList.add('dragging');
                startX = e.clientX;
                startY = e.clientY;
                
                const rect = card.getBoundingClientRect();
                initialX = rect.left;
                initialY = rect.top;
                
                e.preventDefault();
            });
            
            document.addEventListener('mousemove', (e) => {
                if (!isDragging) return;
                
                const deltaX = e.clientX - startX;
                const deltaY = e.clientY - startY;
                
                card.style.position = 'absolute';
                card.style.left = (initialX + deltaX) + 'px';
                card.style.top = (initialY + deltaY) + 'px';
                card.style.zIndex = '1000';
            });
            
            document.addEventListener('mouseup', () => {
                if (isDragging) {
                    isDragging = false;
                    card.classList.remove('dragging');
                    card.style.zIndex = '';
                    saveCardPosition(card);
                }
            });
        }
        
        // Resize functionality
        if (resizeHandle) {
            let isResizing = false;
            let startX, startY, startWidth, startHeight;
            
            resizeHandle.addEventListener('mousedown', (e) => {
                isResizing = true;
                card.classList.add('resizing');
                startX = e.clientX;
                startY = e.clientY;
                
                const rect = card.getBoundingClientRect();
                startWidth = rect.width;
                startHeight = rect.height;
                
                e.preventDefault();
                e.stopPropagation();
            });
            
            document.addEventListener('mousemove', (e) => {
                if (!isResizing) return;
                
                const deltaX = e.clientX - startX;
                const deltaY = e.clientY - startY;
                
                const newWidth = Math.max(300, startWidth + deltaX);
                const newHeight = Math.max(200, startHeight + deltaY);
                
                card.style.width = newWidth + 'px';
                card.style.height = newHeight + 'px';
            });
            
            document.addEventListener('mouseup', () => {
                if (isResizing) {
                    isResizing = false;
                    card.classList.remove('resizing');
                    saveCardSize(card);
                }
            });
        }
    });
}

/**
 * Save card position to localStorage
 */
function saveCardPosition(card) {
    try {
        const cardId = card.getAttribute('data-card-id');
        if (!cardId) return;
        
        const rect = card.getBoundingClientRect();
        const positions = JSON.parse(localStorage.getItem('analyticsCardPositions') || '{}');
        positions[cardId] = { x: rect.left, y: rect.top };
        localStorage.setItem('analyticsCardPositions', JSON.stringify(positions));
    } catch (error) {
        console.error('Error saving card position:', error);
    }
}

/**
 * Save card size to localStorage
 */
function saveCardSize(card) {
    try {
        const cardId = card.getAttribute('data-card-id');
        if (!cardId) return;
        
        const sizes = JSON.parse(localStorage.getItem('analyticsCardSizes') || '{}');
        sizes[cardId] = { 
            width: parseInt(card.style.width) || card.offsetWidth,
            height: parseInt(card.style.height) || card.offsetHeight
        };
        localStorage.setItem('analyticsCardSizes', JSON.stringify(sizes));
    } catch (error) {
        console.error('Error saving card size:', error);
    }
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
// JOURNAL FUNCTIONALITY
// ============================================

let journalTimer = null;
let journalTimerSeconds = 600; // 10 minutes in seconds
let journalTimerRunning = false;
let journalTimerPaused = false;
let journalStartTime = null;
let journalDuration = 0;

// Initialize journal functionality
function setupJournal() {
    const startBtn = document.getElementById('startTimer');
    const pauseBtn = document.getElementById('pauseTimer');
    const continueBtn = document.getElementById('continueTimer');
    const saveBtn = document.getElementById('saveEntry');
    const clearBtn = document.getElementById('clearEntry');
    const entryTextarea = document.getElementById('journalEntry');
    
    if (startBtn) {
        startBtn.addEventListener('click', startJournalTimer);
    }
    if (pauseBtn) {
        pauseBtn.addEventListener('click', pauseJournalTimer);
    }
    if (continueBtn) {
        continueBtn.addEventListener('click', continueJournalTimer);
    }
    if (saveBtn) {
        saveBtn.addEventListener('click', saveJournalEntry);
    }
    if (clearBtn) {
        clearBtn.addEventListener('click', clearJournalEntry);
    }
    if (entryTextarea) {
        // Auto-start timer when user starts typing
        entryTextarea.addEventListener('input', () => {
            if (!journalTimerRunning && !journalTimerPaused && entryTextarea.value.trim().length > 0) {
                startJournalTimer();
            }
        });
    }
}

// Start the 10-minute journal timer
function startJournalTimer() {
    if (journalTimerRunning) return;
    
    journalTimerRunning = true;
    journalTimerPaused = false;
    journalStartTime = Date.now();
    journalDuration = 0;
    
    const startBtn = document.getElementById('startTimer');
    const pauseBtn = document.getElementById('pauseTimer');
    const continueBtn = document.getElementById('continueTimer');
    const statusEl = document.getElementById('timerStatus');
    const saveBtn = document.getElementById('saveEntry');
    
    if (startBtn) startBtn.style.display = 'none';
    if (pauseBtn) pauseBtn.style.display = 'inline-block';
    if (continueBtn) continueBtn.style.display = 'none';
    if (statusEl) statusEl.textContent = 'Timer running...';
    if (saveBtn) saveBtn.disabled = false;
    
    // Update timer display every second
    journalTimer = setInterval(() => {
        journalTimerSeconds--;
        journalDuration++;
        updateTimerDisplay();
        
        if (journalTimerSeconds <= 0) {
            timerComplete();
        }
    }, 1000);
}

// Pause the timer
function pauseJournalTimer() {
    if (!journalTimerRunning) return;
    
    clearInterval(journalTimer);
    journalTimerRunning = false;
    journalTimerPaused = true;
    
    const pauseBtn = document.getElementById('pauseTimer');
    const continueBtn = document.getElementById('continueTimer');
    const statusEl = document.getElementById('timerStatus');
    
    if (pauseBtn) pauseBtn.style.display = 'none';
    if (continueBtn) continueBtn.style.display = 'inline-block';
    if (statusEl) statusEl.textContent = 'Timer paused';
}

// Continue the timer after pause
function continueJournalTimer() {
    if (!journalTimerPaused) return;
    
    journalTimerRunning = true;
    journalTimerPaused = false;
    
    const pauseBtn = document.getElementById('pauseTimer');
    const continueBtn = document.getElementById('continueTimer');
    const statusEl = document.getElementById('timerStatus');
    
    if (pauseBtn) pauseBtn.style.display = 'inline-block';
    if (continueBtn) continueBtn.style.display = 'none';
    if (statusEl) statusEl.textContent = 'Timer running...';
    
    // Resume timer
    journalTimer = setInterval(() => {
        journalTimerSeconds--;
        journalDuration++;
        updateTimerDisplay();
        
        if (journalTimerSeconds <= 0) {
            timerComplete();
        }
    }, 1000);
}

// Update timer display
function updateTimerDisplay() {
    const minutes = Math.floor(journalTimerSeconds / 60);
    const seconds = journalTimerSeconds % 60;
    const display = document.getElementById('timerDisplay');
    
    if (display) {
        display.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }
}

// Handle timer completion
function timerComplete() {
    clearInterval(journalTimer);
    journalTimerRunning = false;
    
    const pauseBtn = document.getElementById('pauseTimer');
    const continueBtn = document.getElementById('continueTimer');
    const statusEl = document.getElementById('timerStatus');
    
    if (pauseBtn) pauseBtn.style.display = 'none';
    if (continueBtn) continueBtn.style.display = 'inline-block';
    if (statusEl) statusEl.textContent = 'Timer complete! Click "Continue" to keep writing.';
    
    // Show notification
    showSuccessFeedback('10 minutes complete! You can continue writing or save your entry.');
}

// Save journal entry
async function saveJournalEntry() {
    const entryTextarea = document.getElementById('journalEntry');
    const content = entryTextarea ? entryTextarea.value.trim() : '';
    
    if (!content) {
        showErrorFeedback('Please write something before saving.');
        return;
    }
    
    try {
        const continued = journalTimerSeconds <= 0 && journalTimerPaused;
        await eel.save_journal_entry(content, journalDuration, continued)();
        
        showSuccessFeedback('Journal entry saved successfully!');
        
        // Clear entry and reset timer
        clearJournalEntry();
        
        // Reload past entries
        await loadPastEntries();
    } catch (error) {
        console.error('Error saving journal entry:', error);
        showErrorFeedback('Failed to save entry. Please try again.');
    }
}

// Clear journal entry
function clearJournalEntry() {
    const entryTextarea = document.getElementById('journalEntry');
    if (entryTextarea) {
        entryTextarea.value = '';
    }
    
    // Reset timer
    clearInterval(journalTimer);
    journalTimer = null;
    journalTimerSeconds = 600;
    journalTimerRunning = false;
    journalTimerPaused = false;
    journalStartTime = null;
    journalDuration = 0;
    
    const startBtn = document.getElementById('startTimer');
    const pauseBtn = document.getElementById('pauseTimer');
    const continueBtn = document.getElementById('continueTimer');
    const statusEl = document.getElementById('timerStatus');
    const saveBtn = document.getElementById('saveEntry');
    
    if (startBtn) startBtn.style.display = 'inline-block';
    if (pauseBtn) pauseBtn.style.display = 'none';
    if (continueBtn) continueBtn.style.display = 'none';
    if (statusEl) statusEl.textContent = 'Ready to start';
    if (saveBtn) saveBtn.disabled = true;
    
    updateTimerDisplay();
}

// Load past journal entries (last 30 days)
async function loadPastEntries() {
    const container = document.getElementById('journalEntriesContainer');
    if (!container) return;
    
    try {
        container.innerHTML = '<div class="empty-state"><div class="loading-spinner"></div><p>Loading entries...</p></div>';
        
        const entries = await eel.get_recent_entries(30)();
        
        if (entries.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <h3>No entries yet</h3>
                    <p>Start writing your first journal entry above!</p>
                </div>
            `;
            return;
        }
        
        let html = '';
        entries.forEach(entry => {
            const date = new Date(entry.date || entry.created_at);
            const dateStr = date.toLocaleDateString('en-US', { 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
            
            const duration = entry.duration_seconds || 0;
            const minutes = Math.floor(duration / 60);
            const seconds = duration % 60;
            const durationStr = duration > 0 ? `${minutes}m ${seconds}s` : '';
            
            const continuedBadge = entry.continued ? '<span class="journal-badge continued">Continued</span>' : '';
            
            html += `
                <div class="journal-entry-item">
                    <div class="journal-entry-header">
                        <span class="journal-entry-date">${escapeHtml(dateStr)}</span>
                        ${durationStr ? `<span class="journal-entry-duration">⏱ ${durationStr}</span>` : ''}
                        ${continuedBadge}
                    </div>
                    <div class="journal-entry-content">${escapeHtml(entry.content)}</div>
                </div>
            `;
        });
        
        container.innerHTML = html;
    } catch (error) {
        console.error('Error loading past entries:', error);
        container.innerHTML = `
            <div class="empty-state">
                <h3>Error loading entries</h3>
                <p>Please try again later.</p>
            </div>
        `;
    }
}

/* ============================================
   NOTIFICATION SETTINGS FUNCTIONS
   ============================================ */

/**
 * Load and display current notification settings
 */
async function loadNotificationSettings() {
    try {
        const settings = await eel.get_notification_settings()();
        
        // Populate form fields with null checks
        const enabledCheckbox = document.getElementById('notificationsEnabled');
        const emailInput = document.getElementById('notificationEmail');
        const smtpPortInput = document.getElementById('smtpPort');
        const emailUsernameInput = document.getElementById('emailUsername');
        const emailPasswordInput = document.getElementById('emailPassword');
        const checkIntervalInput = document.getElementById('checkInterval');
        
        if (enabledCheckbox) enabledCheckbox.checked = settings.enabled || false;
        if (emailInput) emailInput.value = settings.email || '';
        if (smtpPortInput) smtpPortInput.value = settings.smtp_port || 587;
        if (emailUsernameInput) emailUsernameInput.value = settings.email_username || '';
        if (emailPasswordInput) emailPasswordInput.value = settings.email_password || '';
        if (checkIntervalInput) checkIntervalInput.value = settings.check_interval_hours || 1;
        
        // Set SMTP server
        const smtpSelect = document.getElementById('smtpServer');
        const customSmtpGroup = document.getElementById('customSmtpGroup');
        const customSmtpInput = document.getElementById('customSmtpServer');
        
        if (smtpSelect && settings.smtp_server) {
            // Check if it's a preset option
            const presetOptions = ['smtp.gmail.com', 'smtp.mail.me.com', 'smtp-mail.outlook.com'];
            if (presetOptions.includes(settings.smtp_server)) {
                smtpSelect.value = settings.smtp_server;
                if (customSmtpGroup) customSmtpGroup.style.display = 'none';
            } else {
                smtpSelect.value = 'custom';
                if (customSmtpGroup) customSmtpGroup.style.display = 'block';
                if (customSmtpInput) customSmtpInput.value = settings.smtp_server;
            }
        }
    } catch (error) {
        console.error('Error loading notification settings:', error);
        // Don't show error to user if settings tab isn't open
    }
}

/**
 * Setup notification settings form event listeners
 */
function setupNotificationSettings() {
    const form = document.getElementById('notificationSettingsForm');
    const smtpSelect = document.getElementById('smtpServer');
    const customSmtpGroup = document.getElementById('customSmtpGroup');
    const testBtn = document.getElementById('testNotificationBtn');
    
    // Handle SMTP server selection
    if (smtpSelect) {
        smtpSelect.addEventListener('change', (e) => {
            if (e.target.value === 'custom') {
                customSmtpGroup.style.display = 'block';
            } else {
                customSmtpGroup.style.display = 'none';
            }
        });
    }
    
    // Handle form submission
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            await saveNotificationSettings();
        });
    }
    
    // Handle test notification button
    if (testBtn) {
        testBtn.addEventListener('click', async () => {
            await testNotification();
        });
    }
}

/**
 * Save notification settings
 */
async function saveNotificationSettings() {
    try {
        const enabledCheckbox = document.getElementById('notificationsEnabled');
        const emailInput = document.getElementById('notificationEmail');
        const smtpSelect = document.getElementById('smtpServer');
        const customSmtpInput = document.getElementById('customSmtpServer');
        const smtpPortInput = document.getElementById('smtpPort');
        const emailUsernameInput = document.getElementById('emailUsername');
        const emailPasswordInput = document.getElementById('emailPassword');
        const checkIntervalInput = document.getElementById('checkInterval');
        
        // Check if all required elements exist
        if (!enabledCheckbox || !emailInput || !smtpSelect || !smtpPortInput || 
            !emailUsernameInput || !emailPasswordInput || !checkIntervalInput) {
            showErrorFeedback('Settings form not found. Please refresh the page.');
            return;
        }
        
        const enabled = enabledCheckbox.checked;
        const email = emailInput.value.trim();
        const smtpPort = parseInt(smtpPortInput.value) || 587;
        const emailUsername = emailUsernameInput.value.trim();
        const emailPassword = emailPasswordInput.value;
        const checkInterval = parseInt(checkIntervalInput.value) || 1;
        
        // Get SMTP server
        let smtpServer = smtpSelect.value;
        if (smtpServer === 'custom') {
            if (!customSmtpInput) {
                showErrorFeedback('Custom SMTP server input not found.');
                return;
            }
            smtpServer = customSmtpInput.value.trim();
        }
        
        // Validate required fields if enabled
        if (enabled) {
            if (!email) {
                showErrorFeedback('Please enter your email address');
                return;
            }
            if (!smtpServer) {
                showErrorFeedback('Please enter SMTP server');
                return;
            }
            if (!emailUsername) {
                showErrorFeedback('Please enter email username');
                return;
            }
            if (!emailPassword) {
                showErrorFeedback('Please enter email password');
                return;
            }
        }
        
        // Save settings
        await eel.update_notification_settings(
            enabled,
            email,
            smtpServer,
            smtpPort,
            emailUsername,
            emailPassword,
            checkInterval
        )();
        
        showSuccessFeedback('Notification settings saved successfully!');
    } catch (error) {
        console.error('Error saving notification settings:', error);
        showErrorFeedback('Failed to save settings. Please try again.');
    }
}

/**
 * Send a test notification
 */
async function testNotification() {
    try {
        const emailInput = document.getElementById('notificationEmail');
        const testBtn = document.getElementById('testNotificationBtn');
        
        if (!emailInput || !testBtn) {
            showErrorFeedback('Notification form elements not found. Please refresh the page.');
            return;
        }
        
        const email = emailInput.value.trim();
        if (!email) {
            showErrorFeedback('Please enter your email address first');
            return;
        }
        
        const originalText = testBtn.textContent;
        testBtn.textContent = 'Sending...';
        testBtn.disabled = true;
        
        const result = await eel.test_notification(email)();
        
        if (result && result.success) {
            showSuccessFeedback(result.message || 'Test notification sent successfully!');
        } else {
            showErrorFeedback(result?.message || 'Failed to send test notification. Please check your settings.');
        }
        
        testBtn.textContent = originalText;
        testBtn.disabled = false;
    } catch (error) {
        console.error('Error sending test notification:', error);
        showErrorFeedback('Failed to send test notification. Please check your settings.');
        const testBtn = document.getElementById('testNotificationBtn');
        if (testBtn) {
            testBtn.disabled = false;
            testBtn.textContent = 'Send Test Notification';
        }
    }
}

// Initialize when page loads
init();

// Setup notification settings when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupNotificationSettings);
} else {
    setupNotificationSettings();
}

// Setup journal when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupJournal);
} else {
    setupJournal();
}
