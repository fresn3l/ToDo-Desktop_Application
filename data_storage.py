"""
Data Storage Module

This module handles all file I/O operations for tasks, habits, goals, and categories.
It provides a centralized way to load and save data to JSON files.
Data is shared between the ToDo app and Habit Tracker app.

Benefits of this module:
- Single source of truth for data file paths
- Consistent error handling across all data operations
- Easy to change storage mechanism (e.g., switch to database) later
- Reusable functions for all modules
- Data stored in Application Support folder for persistence across app rebuilds
- Shared storage between ToDo app (tasks) and Habit Tracker app (habits)
- Goals are shared between both apps
- File locking prevents data corruption when both apps access shared files
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

def get_data_directory():
    """
    Get the directory where data files should be stored.
    Uses Application Support folder for persistent storage across app rebuilds.
    
    Returns:
        Path: Directory path for data files
    """
    import sys
    # Use sys.platform for more reliable platform detection
    if sys.platform == 'win32':  # Windows
        data_dir = Path.home() / 'AppData' / 'Local' / 'ToDo'
    elif sys.platform == 'darwin':  # macOS
        data_dir = Path.home() / 'Library' / 'Application Support' / 'ToDo'
    else:  # Linux and others
        data_dir = Path.home() / '.local' / 'share' / 'ToDo'
    
    # Create directory if it doesn't exist
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

