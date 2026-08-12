"""
Data Storage Module

Private data persistence for this application only.
Does not share files or directories with other apps or repositories.
"""

import json
import os
import fcntl  # File locking for Unix/macOS
import sys
from typing import List, Dict
from pathlib import Path

from security_utils import (
    open_private_write,
    restrict_directory_permissions,
    restrict_file_permissions,
)

# Unique directory name so this app does not share data with other local apps
# (for example a Habit Tracker that used Application Support/ToDo).
APP_DATA_NAME = "ToDoDesktop"

def get_data_directory() -> Path:
    """
    Get the private, platform-specific directory for this application's data.

    This directory is unique to ToDo Desktop and is not shared with other apps.
    """
    if sys.platform == 'win32':
        data_dir = Path.home() / 'AppData' / 'Local' / APP_DATA_NAME
    elif sys.platform == 'darwin':
        data_dir = Path.home() / 'Library' / 'Application Support' / APP_DATA_NAME
    else:
        data_dir = Path.home() / '.local' / 'share' / APP_DATA_NAME

    data_dir.mkdir(parents=True, exist_ok=True)
    restrict_directory_permissions(data_dir)

    return data_dir

# Get persistent data directory
DATA_DIR = get_data_directory()

DATA_FILE = str(DATA_DIR / 'tasks.json')
GOALS_FILE = str(DATA_DIR / 'goals.json')

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
    
    Args:
        tasks: List of task dictionaries to save
    """
    # Use atomic write: write to temp file first, then rename
    # This prevents corruption if the app crashes during write
    temp_file = DATA_FILE + '.tmp'
    
    try:
        # Write to temporary file with owner-only permissions
        with open_private_write(temp_file) as f:
            if sys.platform != 'win32':
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)  # Exclusive lock
            json.dump(tasks, f, indent=2)
            if sys.platform != 'win32':
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)  # Release lock
        
        # Atomic rename (atomic on Unix/macOS, should work on Windows too)
        os.replace(temp_file, DATA_FILE)
        restrict_file_permissions(DATA_FILE)
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
    
    Args:
        goals: List of goal dictionaries to save
    """
    # Use atomic write: write to temp file first, then rename
    # This prevents corruption if the app crashes during write
    temp_file = GOALS_FILE + '.tmp'
    
    try:
        # Write to temporary file with file locking and owner-only permissions
        with open_private_write(temp_file) as f:
            if sys.platform != 'win32':
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)  # Exclusive lock
            json.dump(goals, f, indent=2)
            if sys.platform != 'win32':
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)  # Release lock
        
        # Atomic rename (atomic on Unix/macOS, should work on Windows too)
        os.replace(temp_file, GOALS_FILE)
        restrict_file_permissions(GOALS_FILE)
    except Exception as e:
        # Clean up temp file on error
        if os.path.exists(temp_file):
            os.remove(temp_file)
        raise


