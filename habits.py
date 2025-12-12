"""
Habit Tracking Module

This module handles all habit-related operations:
- Creating, reading, updating, deleting habits
- Daily habit check-ins
- Streak calculation
- Searching and filtering habits

All functions decorated with @eel.expose are callable from JavaScript.
"""

import eel
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional

# Import data storage functions
from data_storage import (
    load_habits, save_habits
)

# ============================================
# HABIT CRUD OPERATIONS
# ============================================

@eel.expose
def get_habits():
    """
    Get all habits from storage.
    
    Returns:
        List[Dict]: All habits in the system
    """
    return load_habits()

@eel.expose
def add_habit(title: str, description: str = "", priority: str = "Next", 
             frequency: str = "daily", goal_id: Optional[int] = None):
    """
    Add a new habit to the system.
    
    Args:
        title: Habit title (required)
        description: Habit description (optional)
        priority: Priority level - "Now", "Next", or "Later" (default: "Next")
        frequency: Frequency - "daily", "weekly", or "custom" (default: "daily")
        goal_id: ID of linked goal (optional)
    
    Returns:
        Dict: The newly created habit dictionary
    
    Side Effects:
        - Saves habit to habits.json
    """
    habits = load_habits()
    
    # Create new habit dictionary
    new_habit = {
        "id": len(habits) + 1,
        "title": title,
        "description": description,
        "priority": priority,  # Now, Next, Later
        "frequency": frequency,  # daily, weekly, custom
        "check_ins": [],  # List of dates (ISO format strings) when habit was checked in
        "created_at": datetime.now().isoformat(),
        "goal_id": goal_id
    }
    
    # Add habit to list and save
    habits.append(new_habit)
    save_habits(habits)
    
    return new_habit

@eel.expose
def update_habit(habit_id: int, title: str = None, description: str = None,
                priority: str = None, frequency: str = None,
                goal_id: Optional[int] = None):
    """
    Update an existing habit.
    
    Args:
        habit_id: ID of habit to update
        title: New title (optional)
        description: New description (optional)
        priority: New priority (optional)
        frequency: New frequency (optional)
        goal_id: New goal ID (optional, None to unlink)
    
    Returns:
        Dict: Updated habit dictionary, or None if habit not found
    """
    habits = load_habits()
    
    # Find habit by ID
    for habit in habits:
        if habit["id"] == habit_id:
            # Update only provided fields
            if title is not None:
                habit["title"] = title
            if description is not None:
                habit["description"] = description
            if priority is not None:
                habit["priority"] = priority
            if frequency is not None:
                habit["frequency"] = frequency
            if goal_id is not None:
                habit["goal_id"] = goal_id
            
            # Save updated habits
            save_habits(habits)
            return habit
    
    return None

@eel.expose
def check_in_habit(habit_id: int, check_date: str = None):
    """
    Check in a habit for a specific date (defaults to today).
    
    Args:
        habit_id: ID of habit to check in
        check_date: Date in ISO format (YYYY-MM-DD), defaults to today
    
    Returns:
        Dict: Updated habit dictionary, or None if habit not found
    """
    habits = load_habits()
    
    # Use today if no date provided
    if check_date is None:
        check_date = date.today().isoformat()
    
    # Find habit by ID
    for habit in habits:
        if habit["id"] == habit_id:
            # Ensure check_ins list exists
            if "check_ins" not in habit:
                habit["check_ins"] = []
            
            # Add check-in if not already present
            if check_date not in habit["check_ins"]:
                habit["check_ins"].append(check_date)
                habit["check_ins"].sort()  # Keep sorted
            
            # Save updated habits
            save_habits(habits)
            return habit
    
    return None

@eel.expose
def uncheck_habit(habit_id: int, check_date: str = None):
    """
    Remove a check-in for a specific date (defaults to today).
    
    Args:
        habit_id: ID of habit to uncheck
        check_date: Date in ISO format (YYYY-MM-DD), defaults to today
    
    Returns:
        Dict: Updated habit dictionary, or None if habit not found
    """
    habits = load_habits()
    
    # Use today if no date provided
    if check_date is None:
        check_date = date.today().isoformat()
    
    # Find habit by ID
    for habit in habits:
        if habit["id"] == habit_id:
            # Ensure check_ins list exists
            if "check_ins" not in habit:
                habit["check_ins"] = []
            
            # Remove check-in if present
            if check_date in habit["check_ins"]:
                habit["check_ins"].remove(check_date)
            
            # Save updated habits
            save_habits(habits)
            return habit
    
    return None

@eel.expose
def get_habit_streak(habit_id: int):
    """
    Calculate the current streak for a habit.
    
    Args:
        habit_id: ID of habit
    
    Returns:
        int: Current streak in days, or 0 if habit not found
    """
    habits = load_habits()
    
    # Find habit by ID
    for habit in habits:
        if habit["id"] == habit_id:
            check_ins = habit.get("check_ins", [])
            if not check_ins:
                return 0
            
            # Convert check-ins to date objects and sort
            check_dates = sorted([date.fromisoformat(d) for d in check_ins])
            
            # Calculate streak backwards from today
            today = date.today()
            streak = 0
            current_date = today
            
            # Check if today or yesterday was checked in
            if check_dates and check_dates[-1] >= today - timedelta(days=1):
                # Start from the most recent check-in
                idx = len(check_dates) - 1
                while idx >= 0:
                    expected_date = today - timedelta(days=streak)
                    if check_dates[idx] == expected_date or check_dates[idx] == expected_date - timedelta(days=1):
                        streak += 1
                        idx -= 1
                    elif check_dates[idx] < expected_date - timedelta(days=1):
                        break
                    else:
                        idx -= 1
            
            return streak
    
    return 0

@eel.expose
def delete_habit(habit_id: int):
    """
    Delete a habit from the system.
    
    Args:
        habit_id: ID of habit to delete
    
    Returns:
        bool: True if habit was deleted, False otherwise
    """
    habits = load_habits()
    
    # Filter out the habit with matching ID
    original_count = len(habits)
    habits = [habit for habit in habits if habit["id"] != habit_id]
    
    # Only save if a habit was actually removed
    if len(habits) < original_count:
        save_habits(habits)
        return True
    
    return False

# ============================================
# HABIT SEARCH AND FILTER
# ============================================

@eel.expose
def search_habits(query: str):
    """
    Search habits by title or description.
    
    Args:
        query: Search query string (case-insensitive)
    
    Returns:
        List[Dict]: Habits matching the search query
    """
    habits = load_habits()
    query_lower = query.lower()
    
    # Filter habits that match search query
    filtered = [
        habit for habit in habits
        if query_lower in habit["title"].lower() or
           query_lower in habit.get("description", "").lower()
    ]
    
    return filtered

@eel.expose
def filter_habits(priority: str = None, 
                 frequency: str = None, goal_id: int = None):
    """
    Filter habits by various criteria.
    
    Args:
        priority: Filter by priority level (optional)
        frequency: Filter by frequency (optional)
        goal_id: Filter by linked goal ID (optional)
    
    Returns:
        List[Dict]: Habits matching all provided filters
    """
    habits = load_habits()
    filtered = habits
    
    # Apply each filter if provided
    if priority:
        filtered = [habit for habit in filtered if habit["priority"] == priority]
    if frequency:
        filtered = [habit for habit in filtered if habit.get("frequency") == frequency]
    if goal_id is not None:
        filtered = [habit for habit in filtered if habit.get("goal_id") == goal_id]
    
    return filtered

