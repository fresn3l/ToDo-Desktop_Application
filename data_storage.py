"""
Data Storage Module

This module handles all file I/O operations for tasks, goals, and categories.
It provides a centralized way to load and save data to JSON files.

Benefits of this module:
- Single source of truth for data file paths
- Consistent error handling across all data operations
- Easy to change storage mechanism (e.g., switch to database) later
- Reusable functions for all modules
"""

import json
import os
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
DATA_FILE = str(DATA_DIR / 'tasks.json')
GOALS_FILE = str(DATA_DIR / 'goals.json')
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
    Save tasks to local JSON file.
    
    Args:
        tasks: List of task dictionaries to save
    
    Side Effects:
        - Overwrites existing tasks.json file
        - Creates file if it doesn't exist
    """
    with open(DATA_FILE, 'w') as f:
        json.dump(tasks, f, indent=2)

# ============================================
# GOAL DATA OPERATIONS
# ============================================

def load_goals() -> List[Dict]:
    """
    Load goals from local JSON file.
    
    Returns:
        List[Dict]: List of goal dictionaries. Returns empty list if file doesn't exist or is invalid.
    """
    if os.path.exists(GOALS_FILE):
        try:
            with open(GOALS_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []

def save_goals(goals: List[Dict]):
    """
    Save goals to local JSON file.
    
    Args:
        goals: List of goal dictionaries to save
    """
    with open(GOALS_FILE, 'w') as f:
        json.dump(goals, f, indent=2)

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

