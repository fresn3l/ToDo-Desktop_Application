"""
Goals Management Module

This module handles all goal-related operations:
- Creating, reading, updating, deleting goals
- Tracking goal progress
- Linking/unlinking tasks to goals

All functions decorated with @eel.expose are callable from JavaScript.
"""

import eel
from datetime import datetime
from typing import List, Dict, Optional

# Import data storage functions
from data_storage import load_goals, save_goals, load_tasks, save_tasks, load_habits

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
    Delete a goal and unlink all associated tasks.
    
    Args:
        goal_id: ID of goal to delete
    
    Returns:
        bool: True if goal was deleted
    
    Side Effects:
        - Removes goal from goals.json
        - Unlinks all tasks that were linked to this goal
        - Updates tasks.json with unlinked tasks
    """
    goals = load_goals()
    
    # Remove goal from list
    goals = [goal for goal in goals if goal["id"] != goal_id]
    save_goals(goals)
    
    # Unlink tasks from deleted goal (from ToDo app)
    # This prevents orphaned goal_id references in tasks
    tasks = load_tasks()
    for task in tasks:
        if task.get("goal_id") == goal_id:
            task["goal_id"] = None
    save_tasks(tasks)
    
    # Unlink habits from deleted goal (from Habit Tracker app)
    # This prevents orphaned goal_id references in habits
    habits = load_habits()
    if habits:  # Only process if habits file exists
        from data_storage import save_habits
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
    Tracks both tasks (from ToDo app) and habits (from Habit Tracker app).
    
    Args:
        goal_id: ID of goal to get progress for
    
    Returns:
        Dict: Progress statistics with:
            - total: Total number of tasks + habits linked to this goal
            - completed: Number of completed tasks + habits with check-ins
            - tasks_total: Total tasks linked to this goal
            - tasks_completed: Completed tasks
            - habits_total: Total habits linked to this goal
            - habits_completed: Habits with at least one check-in
            - percentage: Overall completion percentage (0-100)
    
    Calculation:
        - Finds all tasks and habits linked to this goal
        - Counts total and completed items from both sources
        - Calculates overall percentage
    """
    tasks = load_tasks()
    habits = load_habits()  # Load habits from Habit Tracker app
    
    # Filter tasks linked to this goal
    goal_tasks = [task for task in tasks if task.get("goal_id") == goal_id]
    tasks_total = len(goal_tasks)
    # For tasks, "completed" means the completed field is True
    tasks_completed = len([task for task in goal_tasks if task.get("completed", False)])
    
    # Filter habits linked to this goal
    goal_habits = [habit for habit in habits if habit.get("goal_id") == goal_id]
    habits_total = len(goal_habits)
    # For habits, "completed" means having at least one check-in
    habits_completed = len([habit for habit in goal_habits 
                           if habit.get("check_ins") and len(habit.get("check_ins", [])) > 0])
    
    # Calculate overall statistics
    total = tasks_total + habits_total
    completed = tasks_completed + habits_completed
    
    # Calculate percentage (avoid division by zero)
    percentage = (completed / total * 100) if total > 0 else 0
    
    return {
        "total": total,
        "completed": completed,
        "tasks_total": tasks_total,
        "tasks_completed": tasks_completed,
        "habits_total": habits_total,
        "habits_completed": habits_completed,
        "percentage": round(percentage, 2)
    }

