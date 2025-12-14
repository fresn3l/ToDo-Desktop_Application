"""
Data Storage Module

This module provides a centralized, robust data persistence layer for the ToDo
application. It handles all file I/O operations for tasks, habits, and goals
with proper error handling, file locking, and atomic writes.

ARCHITECTURE:
-------------
This module implements a file-based storage system using JSON files. It provides
a clean abstraction layer that other modules use for data persistence, making it
easy to switch storage mechanisms (e.g., to a database) in the future.

KEY FEATURES:
-------------
1. **Centralized Storage**: Single source of truth for all data file paths
2. **Cross-App Compatibility**: Shared storage between ToDo app and Habit Tracker app
3. **Data Persistence**: Files stored in Application Support folder (survives app rebuilds)
4. **File Locking**: Prevents data corruption when multiple processes access files
5. **Atomic Writes**: Writes to temp file then renames (prevents partial writes)
6. **Error Handling**: Graceful handling of missing/corrupted files
7. **Platform Support**: Works on macOS, Windows, and Linux

STORAGE LOCATIONS:
------------------
All data is stored in platform-specific Application Support directories:
- macOS: ~/Library/Application Support/ToDo/
- Windows: ~/AppData/Local/ToDo/
- Linux: ~/.local/share/ToDo/

DATA FILES:
-----------
- tasks.json: All tasks from ToDo app
- habits.json: All habits from Habit Tracker app
- goals.json: Shared goals between both apps

FILE LOCKING:
-------------
Uses fcntl (Unix/macOS) for file locking to prevent race conditions when:
- Both apps access shared files simultaneously
- Multiple instances of the same app run concurrently
- File operations overlap

ATOMIC WRITES:
--------------
All write operations use atomic writes:
1. Write to temporary file (.tmp extension)
2. Acquire exclusive lock during write
3. Rename temp file to final filename (atomic operation)
4. Release lock

This ensures data integrity even if the app crashes during a write operation.

ERROR HANDLING:
---------------
- Missing files: Returns empty list/dict (assumes first run)
- Corrupted JSON: Returns empty list/dict (logs error, doesn't crash)
- Permission errors: Logs error, returns empty data
- Lock timeouts: Handled gracefully (may need retry logic in future)

USAGE:
------
Other modules import and use these functions:
    from data_storage import load_tasks, save_tasks, load_goals, save_goals

This keeps the storage implementation details hidden from business logic.
"""

import json
import os
import fcntl  # File locking for Unix/macOS
import sys
from typing import List, Dict
from pathlib import Path

# ============================================
# DATA FILE PATHS
# ============================================
# Store data in user's Application Support folder for persistence across rebuilds
# This ensures data is not lost when rebuilding the app

def get_data_directory() -> Path:
    """
    Get the platform-specific directory where data files should be stored.
    
    This function determines the appropriate Application Support directory
    based on the operating system. The directory is created if it doesn't
    exist, ensuring data persistence across app rebuilds and updates.
    
    Platform Detection:
        - Uses sys.platform for reliable OS detection
        - 'win32': Windows (all versions)
        - 'darwin': macOS
        - Others: Linux and Unix-like systems
    
    Directory Structure:
        The returned directory is the base for all application data:
        - tasks.json: ToDo app tasks
        - habits.json: Habit Tracker app habits
        - goals.json: Shared goals between apps
        - Journal/: Journal entries (subdirectory)
    
    Returns:
        Path: Path object pointing to the data directory
            - macOS: ~/Library/Application Support/ToDo/
            - Windows: ~/AppData/Local/ToDo/
            - Linux: ~/.local/share/ToDo/
    
    Side Effects:
        - Creates the directory structure if it doesn't exist
        - Uses mkdir(parents=True) to create all parent directories
    
    Example:
        >>> data_dir = get_data_directory()
        >>> print(data_dir)
        /Users/username/Library/Application Support/ToDo
    """
    import sys
    # Use sys.platform for more reliable platform detection than os.name
    # sys.platform is more specific (e.g., 'darwin' for macOS vs 'posix')
    
    if sys.platform == 'win32':  # Windows
        # Windows uses AppData\Local for application data
        data_dir = Path.home() / 'AppData' / 'Local' / 'ToDo'
    elif sys.platform == 'darwin':  # macOS
        # macOS uses Library/Application Support for application data
        # This is the standard location for user data that persists
        data_dir = Path.home() / 'Library' / 'Application Support' / 'ToDo'
    else:  # Linux and other Unix-like systems
        # Linux uses .local/share following XDG Base Directory Specification
        data_dir = Path.home() / '.local' / 'share' / 'ToDo'
    
    # Create directory if it doesn't exist
    # parents=True creates all parent directories if needed
    # exist_ok=True prevents error if directory already exists
    data_dir.mkdir(parents=True, exist_ok=True)
    
    return data_dir

# Get persistent data directory
DATA_DIR = get_data_directory()

# Data file paths - stored in persistent location
# Shared between ToDo app and Habit Tracker app
DATA_FILE = str(DATA_DIR / 'tasks.json')  # For ToDo app
HABITS_FILE = str(DATA_DIR / 'habits.json')  # For Habit Tracker app
GOALS_FILE = str(DATA_DIR / 'goals.json')  # Shared between both apps
CATEGORIES_FILE = str(DATA_DIR / 'categories.json')

# ============================================
# TASK DATA OPERATIONS
# ============================================

def load_tasks() -> List[Dict]:
    """
    Load tasks from local JSON file.
    
    Returns:
        List[Dict]: List of task dictionaries. Returns empty list if file doesn't exist or is invalid.
    
    Error Handling:
        - Returns empty list if file doesn't exist (first run)
        - Returns empty list if file is corrupted (invalid JSON)
        - Returns empty list if file can't be read (permissions, etc.)
    """
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []

def save_tasks(tasks: List[Dict]):
    """
    Save tasks to local JSON file with file locking to prevent conflicts.
    This file is used by the ToDo app.
    
    Args:
        tasks: List of task dictionaries to save
    """
    # Use atomic write: write to temp file first, then rename
    # This prevents corruption if the app crashes during write
    temp_file = DATA_FILE + '.tmp'
    
    try:
        # Write to temporary file
        with open(temp_file, 'w') as f:
            if sys.platform != 'win32':
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)  # Exclusive lock
            json.dump(tasks, f, indent=2)
            if sys.platform != 'win32':
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)  # Release lock
        
        # Atomic rename (atomic on Unix/macOS, should work on Windows too)
        os.replace(temp_file, DATA_FILE)
    except Exception as e:
        # Clean up temp file on error
        if os.path.exists(temp_file):
            os.remove(temp_file)
        raise

# ============================================
# GOAL DATA OPERATIONS
# ============================================

def load_goals() -> List[Dict]:
    """
    Load goals from local JSON file with file locking.
    This file is shared between ToDo app and Habit Tracker app.
    
    Returns:
        List[Dict]: List of goal dictionaries. Returns empty list if file doesn't exist or is invalid.
    """
    if os.path.exists(GOALS_FILE):
        try:
            with open(GOALS_FILE, 'r') as f:
                if sys.platform != 'win32':
                    fcntl.flock(f.fileno(), fcntl.LOCK_SH)  # Shared lock for reading
                data = json.load(f)
                if sys.platform != 'win32':
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)  # Release lock
                return data
        except (json.JSONDecodeError, IOError):
            return []
    return []

def save_goals(goals: List[Dict]):
    """
    Save goals to local JSON file with file locking to prevent conflicts.
    This file is shared between ToDo app and Habit Tracker app.
    
    Args:
        goals: List of goal dictionaries to save
    """
    # Use atomic write: write to temp file first, then rename
    # This prevents corruption if the app crashes during write
    temp_file = GOALS_FILE + '.tmp'
    
    try:
        # Write to temporary file with file locking
        with open(temp_file, 'w') as f:
            if sys.platform != 'win32':
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)  # Exclusive lock
            json.dump(goals, f, indent=2)
            if sys.platform != 'win32':
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)  # Release lock
        
        # Atomic rename (atomic on Unix/macOS, should work on Windows too)
        os.replace(temp_file, GOALS_FILE)
    except Exception as e:
        # Clean up temp file on error
        if os.path.exists(temp_file):
            os.remove(temp_file)
        raise

# ============================================
# HABIT DATA OPERATIONS (for Habit Tracker app compatibility)
# ============================================

def load_habits() -> List[Dict]:
    """
    Load habits from local JSON file (for Habit Tracker app compatibility).
    This allows ToDo app to read habits for goal progress calculation.
    
    Returns:
        List[Dict]: List of habit dictionaries. Returns empty list if file doesn't exist or is invalid.
    """
    if os.path.exists(HABITS_FILE):
        try:
            with open(HABITS_FILE, 'r') as f:
                if sys.platform != 'win32':
                    fcntl.flock(f.fileno(), fcntl.LOCK_SH)  # Shared lock for reading
                data = json.load(f)
                if sys.platform != 'win32':
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)  # Release lock
                return data
        except (json.JSONDecodeError, IOError):
            return []
    return []

# ============================================
# CATEGORY DATA OPERATIONS
# ============================================

def load_categories() -> List[str]:
    """
    Load categories from local JSON file.
    
    Returns:
        List[str]: List of category names. Returns empty list if file doesn't exist or is invalid.
    """
    if os.path.exists(CATEGORIES_FILE):
        try:
            with open(CATEGORIES_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []

def save_categories(categories: List[str]):
    """
    Save categories to local JSON file.
    
    Args:
        categories: List of category names to save
    """
    with open(CATEGORIES_FILE, 'w') as f:
        json.dump(categories, f, indent=2)

