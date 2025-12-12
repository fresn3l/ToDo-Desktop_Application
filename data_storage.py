"""
Data Storage Module

This module handles all file I/O operations for habits and goals.
It provides a centralized way to load and save data to JSON files.

Benefits of this module:
- Single source of truth for data file paths
- Consistent error handling across all data operations
- Easy to change storage mechanism (e.g., switch to database) later
- Reusable functions for all modules
- Data stored in Application Support folder for persistence across app rebuilds
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
HABITS_FILE = str(DATA_DIR / 'habits.json')
TASKS_FILE = str(DATA_DIR / 'tasks.json')  # For ToDo app
GOALS_FILE = str(DATA_DIR / 'goals.json')  # Shared between both apps
# Categories removed - using goals instead for organization

# ============================================
# HABIT DATA OPERATIONS
# ============================================

def load_habits() -> List[Dict]:
    """
    Load habits from local JSON file.
    
    Returns:
        List[Dict]: List of habit dictionaries. Returns empty list if file doesn't exist or is invalid.
    """
    if os.path.exists(HABITS_FILE):
        try:
            with open(HABITS_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []

def save_habits(habits: List[Dict]):
    """
    Save habits to local JSON file with file locking to prevent conflicts.
    
    Args:
        habits: List of habit dictionaries to save
    """
    # Use atomic write: write to temp file first, then rename
    # This prevents corruption if the app crashes during write
    temp_file = HABITS_FILE + '.tmp'
    
    try:
        # Write to temporary file
        with open(temp_file, 'w') as f:
            if sys.platform != 'win32':
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)  # Exclusive lock
            json.dump(habits, f, indent=2)
            if sys.platform != 'win32':
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)  # Release lock
        
        # Atomic rename (atomic on Unix/macOS, should work on Windows too)
        os.replace(temp_file, HABITS_FILE)
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
    This is shared between ToDo app and Habit Tracker app.
    
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
# TASK DATA OPERATIONS (for ToDo app compatibility)
# ============================================

def load_tasks() -> List[Dict]:
    """
    Load tasks from local JSON file (for ToDo app compatibility).
    
    Returns:
        List[Dict]: List of task dictionaries. Returns empty list if file doesn't exist or is invalid.
    """
    if os.path.exists(TASKS_FILE):
        try:
            with open(TASKS_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []

def save_tasks(tasks: List[Dict]):
    """
    Save tasks to local JSON file with file locking (for ToDo app compatibility).
    
    Args:
        tasks: List of task dictionaries to save
    """
    # Use atomic write: write to temp file first, then rename
    # This prevents corruption if the app crashes during write
    temp_file = TASKS_FILE + '.tmp'
    
    try:
        # Write to temporary file
        with open(temp_file, 'w') as f:
            if sys.platform != 'win32':
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)  # Exclusive lock
            json.dump(tasks, f, indent=2)
            if sys.platform != 'win32':
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)  # Release lock
        
        # Atomic rename (atomic on Unix/macOS, should work on Windows too)
        os.replace(temp_file, TASKS_FILE)
    except Exception as e:
        # Clean up temp file on error
        if os.path.exists(temp_file):
            os.remove(temp_file)
        raise

# Categories removed - using goals instead for organization

