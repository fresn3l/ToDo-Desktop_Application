"""
Goals Management Module

This module handles all goal-related operations:
- Creating, reading, updating, deleting goals
- Tracking goal progress
- Linking/unlinking habits to goals

All functions decorated with @eel.expose are callable from JavaScript.
"""

import eel
from datetime import datetime
from typing import List, Dict, Optional

# Import data storage functions
from data_storage import load_goals, save_goals, load_habits, save_habits

# ============================================
# GOAL CRUD OPERATIONS
# ============================================

@eel.expose
def get_goals():
    """
    Get all goals from storage.
    
    Returns:
        List[Dict]: All goals in the system
    """
    return load_goals()

@eel.expose
def add_goal(title: str, description: str = ""):
    """
    Add a new goal to the system.
    
    Args:
        title: Goal title (required)
        description: Goal description (optional)
    
    Returns:
        Dict: The newly created goal dictionary
    
    Side Effects:
        - Saves goal to goals.json
    """
    goals = load_goals()
    
    # Create new goal dictionary
    new_goal = {
        "id": len(goals) + 1,
        "title": title,
        "description": description,
        "created_at": datetime.now().isoformat()
    }
    
    # Add goal to list and save
    goals.append(new_goal)
    save_goals(goals)
    
    return new_goal

@eel.expose
def update_goal(goal_id: int, title: str = None, description: str = None):
    """
    Update an existing goal.
    
    Args:
        goal_id: ID of goal to update
        title: New title (optional - only updates if provided)
        description: New description (optional)
    
    Returns:
        Dict: Updated goal dictionary, or None if goal not found
    
    Side Effects:
        - Updates goal in goals.json
    """
    goals = load_goals()
    
    # Find goal by ID
    for goal in goals:
        if goal["id"] == goal_id:
            # Update only provided fields
            if title is not None:
                goal["title"] = title
            if description is not None:
                goal["description"] = description
            
            # Save updated goals
            save_goals(goals)
            return goal
    
    # Goal not found
    return None

@eel.expose
def delete_goal(goal_id: int):
    """
    Delete a goal and unlink all associated habits.
    
    Args:
        goal_id: ID of goal to delete
    
    Returns:
        bool: True if goal was deleted
    
    Side Effects:
        - Removes goal from goals.json
        - Unlinks all habits that were linked to this goal
        - Updates habits.json with unlinked habits
    """
    goals = load_goals()
    
    # Remove goal from list
    goals = [goal for goal in goals if goal["id"] != goal_id]
    save_goals(goals)
    
    # Unlink habits from deleted goal
    # This prevents orphaned goal_id references in habits
    habits = load_habits()
    for habit in habits:
        if habit.get("goal_id") == goal_id:
            habit["goal_id"] = None
    save_habits(habits)
    
    return True

# ============================================
# GOAL PROGRESS TRACKING
# ============================================

@eel.expose
def get_goal_progress(goal_id: int):
    """
    Get progress statistics for a specific goal.
    
    Args:
        goal_id: ID of goal to get progress for
    
    Returns:
        Dict: Progress statistics with:
            - total: Total number of habits linked to this goal
            - completed: Total number of check-ins across all habits
            - percentage: Average check-ins per habit
    
    Calculation:
        - Finds all habits linked to this goal
        - Counts total habits and total check-ins
        - Calculates average check-ins per habit
    """
    habits = load_habits()
    
    # Filter habits linked to this goal
    goal_habits = [habit for habit in habits if habit.get("goal_id") == goal_id]
    
    # Calculate statistics
    total = len(goal_habits)
    completed = sum(len(habit.get("check_ins", [])) for habit in goal_habits)
    
    # Calculate average check-ins per habit (avoid division by zero)
    percentage = (completed / total) if total > 0 else 0
    
    return {
        "total": total,
        "completed": completed,
        "percentage": round(percentage, 2)
    }

