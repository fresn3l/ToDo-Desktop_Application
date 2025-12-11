# Code Modularization

The codebase has been refactored into a modular structure for better maintainability and readability.

## Structure

### Main Entry Point
- **`web/app.js`** (38 lines) - Simple initialization file that imports and coordinates all modules

### Module Files (`web/js/`)

1. **`state.js`** - Centralized state management
   - Global state variables (tasks, goals, filters)
   - State update functions
   - Exports: `tasks`, `goals`, `showCompleted`, `currentFilter`, and setter functions

2. **`utils.js`** - Utility functions
   - `escapeHtml()` - XSS prevention
   - `formatDate()` - Date formatting
   - `isOverdue()` - Date checking
   - `PRIORITY_ORDER` - Priority constants

3. **`ui.js`** - UI utilities and animations
   - `showLoadingState()` / `hideLoadingState()`
   - `animateElements()` - Entrance animations
   - `addRippleEffect()` - Button interactions
   - `showSuccessFeedback()` / `showErrorFeedback()` - Toast notifications

4. **`tasks.js`** - Task management
   - `loadTasks()` - Load tasks from backend
   - `renderTasks()` - Render task list
   - `handleAddTask()` - Create new task
   - `toggleTask()` - Toggle completion
   - `deleteTask()` - Delete task
   - `editTask()` - Edit task
   - `handleSearch()` - Search functionality
   - `handleFilterChange()` - Filter tasks
   - `toggleCompleted()` - Show/hide completed

5. **`goals.js`** - Goal management
   - `loadGoals()` - Load goals from backend
   - `renderGoals()` - Render goal list
   - `handleAddGoal()` - Create new goal
   - `editGoal()` - Edit goal
   - `deleteGoal()` - Delete goal
   - `updateGoalSelect()` - Update goal dropdown in task form
   - `updateGoalFilter()` - Update goal filter dropdown

6. **`analytics.js`** - Analytics and visualization
   - `loadAnalytics()` - Load analytics data
   - `renderAnalytics()` - Render analytics cards
   - `setupAnalytics()` - Setup analytics event listeners
   - Drag and resize functionality for analytics cards
   - localStorage persistence for card positions/sizes

7. **`events.js`** - Event listener setup
   - `setupEventListeners()` - Setup all DOM event listeners
   - Keyboard shortcuts (Ctrl/Cmd+K for search, Escape to clear)

8. **`tabs.js`** - Tab management
   - `setupTabs()` - Setup tab buttons
   - `switchTab()` - Switch between tabs

## Benefits

1. **Separation of Concerns** - Each module has a single, clear responsibility
2. **Maintainability** - Easy to find and modify specific functionality
3. **Testability** - Each module can be tested independently
4. **Readability** - Smaller, focused files are easier to understand
5. **Reusability** - Functions can be imported and used across modules
6. **Scalability** - Easy to add new features without cluttering code

## Module Dependencies

```
app.js
├── state.js (no dependencies)
├── ui.js (no dependencies)
├── utils.js (no dependencies)
├── tasks.js
│   ├── state.js
│   ├── ui.js
│   ├── utils.js
│   └── goals.js (for updateGoalSelect/updateGoalFilter)
├── goals.js
│   ├── state.js
│   ├── ui.js
│   ├── utils.js
│   └── tasks.js (for loadTasks/renderTasks)
├── analytics.js
│   ├── utils.js
│   └── ui.js
├── events.js
│   ├── tasks.js
│   └── goals.js
└── tabs.js
    └── analytics.js
```

## Usage

The application uses ES6 modules. The main entry point (`app.js`) is loaded with `type="module"` in `index.html`:

```html
<script type="module" src="app.js"></script>
```

All modules use ES6 `import`/`export` syntax for clean dependency management.

