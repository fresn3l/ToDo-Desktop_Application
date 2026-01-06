"""
Task Management Module

Handles all task-related CRUD operations including recurring tasks, overdue detection,
and automatic instance generation. Provides backend API for task management via Eel framework.
"""

import eel
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# Import data storage functions
# These handle the low-level file I/O operations with proper error handling
# and file locking to prevent data corruption
from data_storage import (
    load_tasks, save_tasks
)

# ============================================
# TASK CRUD OPERATIONS
# ============================================

def _check_and_mark_overdue_tasks(tasks: List[Dict]) -> List[Dict]:
    """
    Mark tasks as not_completed if overdue by more than 24 hours.
    For recurring tasks, creates next instance even if current one wasn't completed.
    
    Args:
        tasks: List of task dictionaries
    
    Returns:
        Updated tasks list
    """
    now = datetime.now()
    updated = False
    
    for task in tasks:
        # Skip if task is already completed or already marked as not_completed
        if task.get("completed", False) or task.get("not_completed", False):
            continue
        
        # Skip if task has no due_date
        if not task.get("due_date"):
            continue
        
        # For recurring tasks, check if it's overdue (past due date by >24 hours)
        # Recurring tasks that aren't completed by end of day should be marked as not_completed
        is_recurring = bool(task.get("recurrence"))
        
        try:
            # Parse due_date (format: "YYYY-MM-DD")
            # Convert to datetime at end of day (23:59:59) to ensure full day has passed
            due_date_str = task["due_date"]
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
            # Set to end of day to ensure 24 hours have passed
            due_date = due_date.replace(hour=23, minute=59, second=59)
            
            # Calculate time difference
            time_diff = now - due_date
            
            # If overdue by more than 24 hours, mark as not_completed
            # For recurring tasks, this happens at end of day if not completed
            if time_diff > timedelta(hours=24):
                task["not_completed"] = True
                task["not_completed_at"] = now.isoformat()
                updated = True
                
                # For recurring tasks, create the next instance even if this one wasn't completed
                if is_recurring:
                    # Find the template
                    template = task
                    if not task.get("is_recurring_template", False):
                        parent_id = task.get("parent_task_id")
                        if parent_id:
                            for t in tasks:
                                if t["id"] == parent_id and t.get("is_recurring_template", False):
                                    template = t
                                    break
                    
                    # Create next instance
                    if template.get("is_recurring_template", False):
                        template["due_date"] = task.get("due_date", template.get("due_date", ""))
                        _create_next_recurring_instance(template, tasks)
        except (ValueError, KeyError) as e:
            # Skip tasks with invalid due_date format
            continue
    
    # Save if any tasks were updated
    if updated:
        save_tasks(tasks)
    
    return tasks

@eel.expose
def get_tasks() -> List[Dict]:
    """
    Get all tasks from storage.
    
    Automatically creates missing recurring task instances and marks overdue tasks
    as not_completed for analytics purposes.
    
    Returns:
        List of all task dictionaries
    """
    tasks = load_tasks()
    # Check and create missing recurring instances
    tasks = _check_and_create_recurring_instances(tasks)
    # Check and mark overdue tasks
    tasks = _check_and_mark_overdue_tasks(tasks)
    return tasks

@eel.expose
def add_task(title: str, description: str = "", priority: str = "Next", 
             due_date: str = "", goal_id: Optional[int] = None, time_spent: Optional[float] = None,
             recurrence: Optional[str] = None, recurrence_end_date: Optional[str] = None) -> Dict:
    """
    Add a new task to the system.
    
    Args:
        title: Task title (required)
        description: Task description (optional)
        priority: Priority level - "Now", "Next", or "Later" (default: "Next")
        due_date: Due date in ISO format "YYYY-MM-DD" (optional)
        goal_id: ID of linked goal (optional)
        time_spent: Time spent in hours for time-based goal tracking (optional)
        recurrence: Recurrence type - "daily", "weekly", "monthly", "yearly" (optional)
        recurrence_end_date: End date for recurrence in "YYYY-MM-DD" format (optional)
    
    Returns:
        The newly created task dictionary
    """
    # Load existing tasks from storage
    tasks = load_tasks()
    
    # Create new task dictionary with all properties
    # This is the canonical task structure used throughout the application
    new_task = {
        "id": len(tasks) + 1,  # Simple auto-increment ID
        "title": title,
        "description": description,
        "priority": priority,  # Now, Next, Later
        "due_date": due_date,
        "completed": False,  # New tasks start as incomplete
        "created_at": datetime.now().isoformat(),  # ISO format timestamp
        "completed_at": None  # Will be set when task is completed
    }
    
    # Add goal_id if provided (optional field)
    # Tasks without a goal are categorized as "Misc" in the UI
    if goal_id is not None:
        new_task["goal_id"] = goal_id
    
    # Add time_spent if provided (optional field)
    # Used for tracking time spent on tasks linked to time-based goals
    if time_spent is not None and time_spent > 0:
        new_task["time_spent"] = float(time_spent)
    
    # Add recurrence fields if provided
    # recurrence: 'daily', 'weekly', 'monthly', 'yearly', or None
    if recurrence:
        new_task["recurrence"] = recurrence
        new_task["is_recurring_template"] = True
        new_task["parent_task_id"] = None  # Template tasks have no parent
        if recurrence_end_date:
            new_task["recurrence_end_date"] = recurrence_end_date
    
    # Add task to list and save to persistent storage
    tasks.append(new_task)
    save_tasks(tasks)  # Persists to JSON file with file locking
    
    # If this is a recurring task, create the first instance
    if recurrence and due_date:
        _create_next_recurring_instance(new_task, tasks)
    
    return new_task

@eel.expose
def update_task(task_id: int, title: str = None, description: str = None,
                priority: str = None, due_date: str = None,
                goal_id: int = None, time_spent: Optional[float] = None,
                recurrence: Optional[str] = None, recurrence_end_date: Optional[str] = None) -> Optional[Dict]:
    """
    Update an existing task with new values. Supports partial updates.
    
    Args:
        task_id: ID of task to update
        title: New title (optional)
        description: New description (optional)
        priority: New priority (optional)
        due_date: New due date in ISO format "YYYY-MM-DD" (optional)
        goal_id: New goal ID (optional, pass None to unlink)
        time_spent: New time spent in hours (optional)
        recurrence: Recurrence type (optional)
        recurrence_end_date: Recurrence end date (optional)
    
    Returns:
        Updated task dictionary if found, None otherwise
    """
    tasks = load_tasks()
    
    # Find task by ID (linear search - fine for small task lists)
    for task in tasks:
        if task["id"] == task_id:
            # Update only provided fields (None means "don't change")
            # This allows partial updates - only change what's provided
            if title is not None:
                task["title"] = title
            if description is not None:
                task["description"] = description
            if priority is not None:
                task["priority"] = priority
            if due_date is not None:
                task["due_date"] = due_date
            if goal_id is not None:
                # Note: goal_id can be explicitly set to None to unlink from goal
                task["goal_id"] = goal_id
            if time_spent is not None:
                # Update time_spent (can be set to 0 or None to clear)
                if time_spent > 0:
                    task["time_spent"] = float(time_spent)
                else:
                    task.pop("time_spent", None)  # Remove if 0 or negative
            
            # Update recurrence fields if provided
            if recurrence is not None:
                if recurrence:
                    task["recurrence"] = recurrence
                    task["is_recurring_template"] = True
                    task["parent_task_id"] = None
                    if recurrence_end_date:
                        task["recurrence_end_date"] = recurrence_end_date
                else:
                    # Remove recurrence if set to empty/None
                    task.pop("recurrence", None)
                    task.pop("is_recurring_template", None)
                    task.pop("parent_task_id", None)
                    task.pop("recurrence_end_date", None)
            elif recurrence_end_date is not None:
                # Update end date only
                if recurrence_end_date:
                    task["recurrence_end_date"] = recurrence_end_date
                else:
                    task.pop("recurrence_end_date", None)
            
            # Save updated tasks to persistent storage
            save_tasks(tasks)
            return task
    
    # Task not found - return None to indicate failure
    return None

@eel.expose
def toggle_task(task_id: int) -> Optional[Dict]:
    """
    Toggle task completion status. For recurring tasks, creates next instance when completed.
    
    Args:
        task_id: ID of task to toggle
    
    Returns:
        Updated task dictionary if found, None otherwise
    """
    tasks = load_tasks()
    
    # Find task by ID
    for task in tasks:
        if task["id"] == task_id:
            # Toggle completion status using boolean NOT operator
            task["completed"] = not task["completed"]
            
            # Update completion timestamp based on new state
            if task["completed"]:
                # Task is now completed - record when it was completed
                task["completed_at"] = datetime.now().isoformat()
                
                # If this is a recurring task, create the next instance
                if task.get("recurrence"):
                    # Find the template (could be this task if it's a template, or find parent)
                    template = task
                    if not task.get("is_recurring_template", False):
                        parent_id = task.get("parent_task_id")
                        if parent_id:
                            for t in tasks:
                                if t["id"] == parent_id and t.get("is_recurring_template", False):
                                    template = t
                                    break
                    
                    # Create next instance
                    if template.get("is_recurring_template", False):
                        # Update template's due_date to this task's due_date for next calculation
                        template["due_date"] = task.get("due_date", template.get("due_date", ""))
                        _create_next_recurring_instance(template, tasks)
            else:
                # Task is now incomplete - clear completion timestamp
                task["completed_at"] = None
            
            # Save updated tasks to persistent storage
            save_tasks(tasks)
            return task
    
    # Task not found - return None to indicate failure
    return None

@eel.expose
def delete_task(task_id: int) -> bool:
    """
    Delete a task from the system permanently.
    
    Args:
        task_id: ID of task to delete
    
    Returns:
        True if task was deleted, False if not found
    """
    tasks = load_tasks()
    
    # Store original count to check if deletion occurred
    original_count = len(tasks)
    
    # Filter out the task with matching ID using list comprehension
    # This creates a new list without the task to delete
    tasks = [task for task in tasks if task["id"] != task_id]
    
    # Only save if a task was actually removed (list length decreased)
    if len(tasks) < original_count:
        save_tasks(tasks)  # Persist changes to storage
        return True  # Deletion successful
    
    # Task not found - no changes made
    return False

# ============================================
# TASK SEARCH AND FILTER
# ============================================

@eel.expose
def search_tasks(query: str):
    """Search tasks by title or description (case-insensitive)."""
    tasks = load_tasks()
    query_lower = query.lower()
    
    # Filter tasks that match search query
    filtered = [
        task for task in tasks
        if query_lower in task["title"].lower() or
           query_lower in task.get("description", "").lower()
    ]
    
    return filtered

@eel.expose
def filter_tasks(priority: str = None, 
                completed: bool = None, due_date: str = None, goal_id: int = None):
    """Filter tasks by priority, completion status, due date, or goal ID."""
    tasks = load_tasks()
    filtered = tasks
    
    # Apply each filter if provided
    if priority:
        filtered = [task for task in filtered if task["priority"] == priority]
    if completed is not None:
        filtered = [task for task in filtered if task["completed"] == completed]
    if due_date:
        filtered = [task for task in filtered if task.get("due_date") == due_date]
    if goal_id is not None:
        filtered = [task for task in filtered if task.get("goal_id") == goal_id]
    
    return filtered

# ============================================
# RECURRING TASKS
# ============================================

def _create_next_recurring_instance(template_task: Dict, tasks: List[Dict]) -> Optional[Dict]:
    """
    Create the next instance of a recurring task.
    
    Args:
        template_task: The recurring task template
        tasks: List of all tasks (modified in place)
    
    Returns:
        Newly created task instance, or None if recurrence has ended
    """
    recurrence = template_task.get("recurrence")
    if not recurrence:
        return None
    
    # Check if recurrence has ended
    recurrence_end_date = template_task.get("recurrence_end_date")
    if recurrence_end_date:
        try:
            end_date = datetime.strptime(recurrence_end_date, "%Y-%m-%d")
            if datetime.now().date() > end_date.date():
                return None  # Recurrence has ended
        except ValueError:
            pass  # Invalid date format, continue anyway
    
    # Get the last instance's due_date or use template's due_date
    last_due_date = template_task.get("due_date")
    if not last_due_date:
        return None  # Can't create instance without a due date
    
    try:
        last_date = datetime.strptime(last_due_date, "%Y-%m-%d")
    except ValueError:
        return None  # Invalid date format
    
    # Calculate next due date based on recurrence type
    if recurrence == "daily":
        next_date = last_date + timedelta(days=1)
    elif recurrence == "weekly":
        next_date = last_date + timedelta(weeks=1)
    elif recurrence == "monthly":
        # Add one month (approximate - uses 30 days)
        next_date = last_date + timedelta(days=30)
    elif recurrence == "yearly":
        next_date = last_date + timedelta(days=365)
    else:
        return None  # Unknown recurrence type
    
    # Check if next date exceeds recurrence_end_date
    if recurrence_end_date:
        try:
            end_date = datetime.strptime(recurrence_end_date, "%Y-%m-%d")
            if next_date.date() > end_date.date():
                return None  # Would exceed end date
        except ValueError:
            pass
    
    # Create new task instance
    new_instance = {
        "id": len(tasks) + 1,
        "title": template_task["title"],
        "description": template_task.get("description", ""),
        "priority": template_task.get("priority", "Next"),
        "due_date": next_date.strftime("%Y-%m-%d"),
        "completed": False,
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "recurrence": recurrence,
        "is_recurring_template": False,
        "parent_task_id": template_task["id"] if template_task.get("is_recurring_template") else template_task.get("parent_task_id")
    }
    
    # Copy optional fields
    if "goal_id" in template_task:
        new_instance["goal_id"] = template_task["goal_id"]
    if "time_spent" in template_task:
        new_instance["time_spent"] = template_task["time_spent"]
    if recurrence_end_date:
        new_instance["recurrence_end_date"] = recurrence_end_date
    
    tasks.append(new_instance)
    save_tasks(tasks)
    
    return new_instance

def _check_and_create_recurring_instances(tasks: List[Dict]) -> List[Dict]:
    """
    Check for recurring tasks and create missing instances up to today.
    
    Args:
        tasks: List of all tasks
    
    Returns:
        Updated tasks list
    """
    today = datetime.now().date()
    updated = False
    
    # Find all recurring templates
    templates = [t for t in tasks if t.get("is_recurring_template", False)]
    
    for template in templates:
        recurrence = template.get("recurrence")
        if not recurrence:
            continue
        
        # Find the most recent instance for this template
        instances = [
            t for t in tasks 
            if t.get("parent_task_id") == template["id"] or 
               (t.get("is_recurring_template", False) and t["id"] == template["id"])
        ]
        
        # Get the latest due_date from instances
        latest_due_date = None
        if instances:
            due_dates = [t.get("due_date") for t in instances if t.get("due_date")]
            if due_dates:
                try:
                    latest_due_date = max([datetime.strptime(d, "%Y-%m-%d") for d in due_dates])
                except ValueError:
                    pass
        
        # If no instances, use template's due_date
        if not latest_due_date and template.get("due_date"):
            try:
                latest_due_date = datetime.strptime(template["due_date"], "%Y-%m-%d")
            except ValueError:
                continue
        
        if not latest_due_date:
            continue
        
        # Create instances up to today (or a few days ahead for daily tasks)
        while latest_due_date.date() < today:
            next_instance = _create_next_recurring_instance(template, tasks)
            if not next_instance:
                break  # Recurrence ended or error
            
            # Update latest_due_date for next iteration
            try:
                latest_due_date = datetime.strptime(next_instance["due_date"], "%Y-%m-%d")
            except ValueError:
                break
            updated = True
    
    return tasks

@eel.expose
def create_next_recurring_instance(template_task_id: int) -> Optional[Dict]:
    """
    Manually create the next instance of a recurring task.
    
    Args:
        template_task_id: ID of the recurring task template
    
    Returns:
        Newly created task instance, or None if error
    """
    tasks = load_tasks()
    
    # Find the template (could be the template itself or an instance)
    template = None
    for task in tasks:
        if task["id"] == template_task_id:
            template = task
            break
    
    if not template:
        return None
    
    # If this is an instance, find the template
    if not template.get("is_recurring_template", False):
        parent_id = template.get("parent_task_id")
        if parent_id:
            for task in tasks:
                if task["id"] == parent_id and task.get("is_recurring_template", False):
                    template = task
                    break
    
    if not template.get("is_recurring_template", False):
        return None
    
    # Create next instance
    return _create_next_recurring_instance(template, tasks)

