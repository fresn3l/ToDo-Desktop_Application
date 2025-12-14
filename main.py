"""
Main Application Entry Point

This is the main file that initializes the Eel application and starts the desktop app.
It imports all modules containing @eel.expose functions, which makes them available
to JavaScript.

Module Structure:
    - data_storage.py: File I/O operations (not exposed to JavaScript)
    - todo.py: Task management functions (exposed to JavaScript)
    - goals.py: Goal management functions (exposed to JavaScript)
    - categories.py: Category management functions (exposed to JavaScript)
    - analytics.py: Analytics and statistics functions (exposed to JavaScript)
    - main.py: Application initialization and startup (this file)

Why This Structure?
    - Separation of Concerns: Each module handles one aspect of the application
    - Maintainability: Easy to find and modify specific functionality
    - Testability: Each module can be tested independently
    - Scalability: Easy to add new features without cluttering main.py
    - Reusability: Functions can be imported and used in other projects
"""

import eel

# ============================================
# IMPORT ALL MODULES WITH @eel.expose FUNCTIONS
# ============================================
# These imports are necessary to register all @eel.expose decorators
# Eel scans imported modules for @eel.expose decorators when eel.init() is called

# Import task management module
# This makes all task-related functions available to JavaScript
import todo

# Import goal management module
# This makes all goal-related functions available to JavaScript
import goals

# Categories module removed - using goals instead

# Import analytics module
# This makes all analytics functions available to JavaScript
import analytics

# Import journal module
# This makes all journal-related functions available to JavaScript
import journal

# Note: We don't import data_storage.py directly because:
# - It doesn't have @eel.expose functions
# - It's only used internally by other modules
# - This keeps the API clean (only expose what JavaScript needs)

# ============================================
# EEL INITIALIZATION
# ============================================
# Initialize Eel with the web folder
# This tells Eel where to find HTML/CSS/JavaScript files
# Must be called AFTER importing modules with @eel.expose decorators

eel.init('web')

# ============================================
# APPLICATION STARTUP
# ============================================
# This block only runs when the file is executed directly (not when imported)

if __name__ == '__main__':
    # Start the Eel application
    # This opens a desktop window and loads the HTML interface
    
    # Browser options:
    # - 'chrome' (default): Most common, works on all platforms
    # - 'edge': Pre-installed on Windows 10+, must install on macOS/Linux
    # - 'chrome-app': App mode (no browser UI) - CURRENT SETTING
    # - None: Use system default browser
    # 
    # Recommendation: Use 'chrome' for best cross-platform compatibility
    # Use 'edge' if targeting Windows users specifically
    # Use 'chrome-app' for a more native desktop app feel
    
    eel.start(
        'index.html',      # HTML file to load
        size=(900, 700),   # Window size (width, height)
        port=0,            # Auto-select available port
        mode='chrome-app'  # Browser mode
    )
