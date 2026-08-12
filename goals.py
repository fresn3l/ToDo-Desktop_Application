"""
Goals Management Module

Handles goal CRUD operations, progress tracking, and linking tasks to goals.
"""

import eel
from datetime import datetime
from typing import List, Dict, Optional

# Import data storage functions
from data_storage import load_goals, save_goals, load_tasks, save_tasks
from security_utils import MAX_DESCRIPTION_LENGTH, MAX_TITLE_LENGTH, clamp_text

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
def add_goal(title: str, description: str = "", time_goal: Optional[float] = None):
    """
    Add a new goal to the system.
    
    Args:
        title: Goal title (required)
        description: Goal description (optional)
        time_goal: Time goal in hours (optional) - e.g., 200.0 for "200 hours learning python"
    
    Returns:
        Dict: The newly created goal dictionary
    
    Side Effects:
        - Saves goal to goals.json
    """
    goals = load_goals()

    title = clamp_text(title, MAX_TITLE_LENGTH).strip()
    if not title:
        raise ValueError("Goal title is required")
    description = clamp_text(description, MAX_DESCRIPTION_LENGTH)
    if time_goal is not None:
        try:
            time_goal = float(time_goal)
        except (TypeError, ValueError):
            raise ValueError("Time goal must be a number")
        if time_goal < 0:
            raise ValueError("Time goal cannot be negative")
    
    # Create new goal dictionary
    new_goal = {
        "id": len(goals) + 1,
        "title": title,
        "description": description,
        "time_goal": time_goal,  # Time goal in hours (None if not set)
        "created_at": datetime.now().isoformat()
    }
    
    # Add goal to list and save
    goals.append(new_goal)
    save_goals(goals)
    
    return new_goal

@eel.expose
def update_goal(goal_id: int, title: str = None, description: str = None, time_goal: Optional[float] = None):
    """
    Update an existing goal.
    
    Args:
        goal_id: ID of goal to update
        title: New title (optional - only updates if provided)
        description: New description (optional)
        time_goal: New time goal in hours (optional - pass None explicitly to clear)
    
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
                title = clamp_text(title, MAX_TITLE_LENGTH).strip()
                if not title:
                    raise ValueError("Goal title is required")
                goal["title"] = title
            if description is not None:
                goal["description"] = clamp_text(description, MAX_DESCRIPTION_LENGTH)
            if time_goal is not None:
                try:
                    time_goal = float(time_goal)
                except (TypeError, ValueError):
                    raise ValueError("Time goal must be a number")
                # Allow setting to None to clear time goal
                goal["time_goal"] = time_goal if time_goal > 0 else None
            
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
    
    # Unlink tasks from the deleted goal so they are not left with a stale goal_id
    tasks = load_tasks()
    for task in tasks:
        if task.get("goal_id") == goal_id:
            task["goal_id"] = None
    save_tasks(tasks)
    
    return True

# ============================================
# GOAL PROGRESS TRACKING
# ============================================

@eel.expose
def get_goal_progress(goal_id: int):
    """
    Get progress statistics for a specific goal from this app's tasks.
    Also calculates time spent if time_goal is set.
    
    Args:
        goal_id: ID of goal to get progress for
    
    Returns:
        Dict: Progress statistics with:
            - total: Total number of tasks linked to this goal
            - completed: Number of completed tasks
            - tasks_total: Total tasks linked to this goal
            - tasks_completed: Completed tasks
            - percentage: Overall completion percentage (0-100)
            - time_goal: Time goal in hours (None if not set)
            - time_spent: Total time spent in hours from completed tasks
            - time_percentage: Time progress percentage (0-100) if time_goal is set
    """
    goals = load_goals()
    tasks = load_tasks()
    
    # Find the goal to get time_goal
    goal = next((g for g in goals if g["id"] == goal_id), None)
    time_goal = goal.get("time_goal") if goal else None
    
    # Filter tasks linked to this goal
    goal_tasks = [task for task in tasks if task.get("goal_id") == goal_id]
    tasks_total = len(goal_tasks)
    tasks_completed = len([task for task in goal_tasks if task.get("completed", False)])
    
    time_spent = 0.0
    for task in goal_tasks:
        if task.get("completed", False):
            task_time = task.get("time_spent", 0.0)
            if task_time:
                time_spent += float(task_time)
    
    percentage = (tasks_completed / tasks_total * 100) if tasks_total > 0 else 0
    
    time_percentage = None
    if time_goal and time_goal > 0:
        time_percentage = min((time_spent / time_goal * 100), 100)
    
    return {
        "total": tasks_total,
        "completed": tasks_completed,
        "tasks_total": tasks_total,
        "tasks_completed": tasks_completed,
        "percentage": round(percentage, 2),
        "time_goal": time_goal,
        "time_spent": round(time_spent, 2),
        "time_percentage": round(time_percentage, 2) if time_percentage is not None else None
    }

