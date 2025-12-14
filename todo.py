"""
Todo/Task Management Module

This module handles all task-related CRUD (Create, Read, Update, Delete) operations
for the ToDo application. It provides the backend API for task management that
is called from the JavaScript frontend via the Eel framework.

Module Responsibilities:
- Creating new tasks with validation
- Reading/retrieving tasks from storage
- Updating existing tasks (title, description, priority, due date, goal)
- Deleting tasks
- Toggling task completion status
- Searching and filtering tasks

Data Structure:
Each task is a dictionary with the following keys:
- id: Integer - Unique identifier for the task
- title: String - Task title (required)
- description: String - Task description (optional)
- priority: String - Priority level: "Now", "Next", or "Later"
- due_date: String - Due date in ISO format (optional)
- goal_id: Integer - ID of linked goal (optional, None for "Misc")
- completed: Boolean - Whether task is completed
- created_at: String - Creation timestamp in ISO format
- completed_at: String - Completion timestamp in ISO format (None if not completed)

Storage:
Tasks are persisted to JSON files via the data_storage module.
The storage location is platform-specific:
- macOS: ~/Library/Application Support/ToDo/tasks.json
- Windows: ~/AppData/Local/ToDo/tasks.json
- Linux: ~/.local/share/ToDo/tasks.json

All functions decorated with @eel.expose are callable from JavaScript.
"""

import eel
from datetime import datetime
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

@eel.expose
def get_tasks() -> List[Dict]:
    """
    Get all tasks from storage.
    
    This is a simple read operation that retrieves all tasks from the JSON file.
    Used by the frontend to display the task list and for filtering/searching.
    
    Returns:
        List[Dict]: List of all task dictionaries. Returns empty list if no tasks exist
                    or if there's an error reading the file.
    
    Example return value:
        [
            {
                "id": 1,
                "title": "Complete project",
                "description": "Finish the ToDo app",
                "priority": "Now",
                "due_date": "2024-12-31",
                "goal_id": 1,
                "completed": False,
                "created_at": "2024-12-01T10:00:00",
                "completed_at": None
            },
            ...
        ]
    
    Error Handling:
        - If file doesn't exist, returns empty list
        - If file is corrupted, data_storage.load_tasks() handles it gracefully
    """
    return load_tasks()

@eel.expose
def add_task(title: str, description: str = "", priority: str = "Next", 
             due_date: str = "", goal_id: Optional[int] = None) -> Dict:
    """
    Add a new task to the system.
    
    This function creates a new task with the provided information and saves it
    to persistent storage. The task is assigned a unique ID based on the current
    number of tasks (simple auto-increment).
    
    Args:
        title: Task title (required) - The main task description
        description: Task description (optional) - Additional details about the task
        priority: Priority level (default: "Next")
            - "Now": High priority, do immediately
            - "Next": Medium priority, do soon (default)
            - "Later": Low priority, do when possible
        due_date: Due date in ISO format (optional) - Format: "YYYY-MM-DD"
        goal_id: ID of linked goal (optional) - Links task to a specific goal.
                If None, task is categorized as "Misc"
    
    Returns:
        Dict: The newly created task dictionary with all fields populated
    
    Side Effects:
        - Loads existing tasks from storage
        - Appends new task to the list
        - Saves updated task list to tasks.json
        - Creates timestamp for created_at field
    
    ID Generation:
        Uses simple auto-increment: new_id = len(tasks) + 1
        Note: This can create duplicate IDs if tasks are deleted, but is sufficient
        for this application. For production, consider using UUIDs.
    
    Example:
        >>> add_task("Buy groceries", "Milk, eggs, bread", "Now", "2024-12-15", 1)
        {
            "id": 5,
            "title": "Buy groceries",
            "description": "Milk, eggs, bread",
            "priority": "Now",
            "due_date": "2024-12-15",
            "goal_id": 1,
            "completed": False,
            "created_at": "2024-12-10T14:30:00.123456",
            "completed_at": None
        }
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
    
    # Add task to list and save to persistent storage
    tasks.append(new_task)
    save_tasks(tasks)  # Persists to JSON file with file locking
    
    return new_task

@eel.expose
def update_task(task_id: int, title: str = None, description: str = None,
                priority: str = None, due_date: str = None,
                goal_id: int = None):
    """
    Update an existing task.
    
    Args:
        task_id: ID of task to update
        title: New title (optional - only updates if provided)
        description: New description (optional)
        priority: New priority (optional)
        due_date: New due date (optional)
        goal_id: New goal ID (optional)
    
    Returns:
        Dict: Updated task dictionary, or None if task not found
    
    Side Effects:
        - Updates task in tasks.json
    """
    tasks = load_tasks()
    
    # Find task by ID
    for task in tasks:
        if task["id"] == task_id:
            # Update only provided fields (None means "don't change")
            if title is not None:
                task["title"] = title
            if description is not None:
                task["description"] = description
            if priority is not None:
                task["priority"] = priority
            if due_date is not None:
                task["due_date"] = due_date
            if goal_id is not None:
                task["goal_id"] = goal_id
            
            # Save updated tasks
            save_tasks(tasks)
            return task
    
    # Task not found
    return None

@eel.expose
def toggle_task(task_id: int):
    """
    Toggle task completion status.
    
    Args:
        task_id: ID of task to toggle
    
    Returns:
        Dict: Updated task dictionary, or None if task not found
    
    Side Effects:
        - Updates task.completed in tasks.json
        - Sets/clears completed_at timestamp
    """
    tasks = load_tasks()
    
    # Find task by ID
    for task in tasks:
        if task["id"] == task_id:
            # Toggle completion status
            task["completed"] = not task["completed"]
            
            # Update completion timestamp
            if task["completed"]:
                task["completed_at"] = datetime.now().isoformat()
            else:
                task["completed_at"] = None
            
            # Save updated tasks
            save_tasks(tasks)
            return task
    
    # Task not found
    return None

@eel.expose
def delete_task(task_id: int):
    """
    Delete a task from the system.
    
    Args:
        task_id: ID of task to delete
    
    Returns:
        bool: True if task was deleted, False otherwise
    
    Side Effects:
        - Removes task from tasks.json
    """
    tasks = load_tasks()
    
    # Filter out the task with matching ID
    original_count = len(tasks)
    tasks = [task for task in tasks if task["id"] != task_id]
    
    # Only save if a task was actually removed
    if len(tasks) < original_count:
        save_tasks(tasks)
        return True
    
    return False

# ============================================
# TASK SEARCH AND FILTER
# ============================================

@eel.expose
def search_tasks(query: str):
    """
    Search tasks by title or description.
    
    Args:
        query: Search query string (case-insensitive)
    
    Returns:
        List[Dict]: Tasks matching the search query
    
    Search Logic:
        - Searches in task title
        - Searches in task description
        - Case-insensitive matching
    """
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
    """
    Filter tasks by various criteria.
    
    Args:
        priority: Filter by priority level (optional)
        completed: Filter by completion status (optional)
        due_date: Filter by due date (optional)
        goal_id: Filter by linked goal ID (optional)
    
    Returns:
        List[Dict]: Tasks matching all provided filters
    
    Filter Logic:
        - All filters are ANDed together (must match all)
        - None values mean "don't filter by this criteria"
    """
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

