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
                goal_id: int = None) -> Optional[Dict]:
    """
    Update an existing task with new values.
    
    This function allows partial updates - only the fields provided (not None)
    will be updated. This is useful for editing tasks where you might only
    want to change one field (e.g., just the title or just the priority).
    
    Args:
        task_id: ID of task to update (required)
        title: New title (optional) - Only updates if not None
        description: New description (optional) - Only updates if not None
        priority: New priority (optional) - Only updates if not None
        due_date: New due date in ISO format (optional) - Only updates if not None
        goal_id: New goal ID (optional) - Only updates if not None.
                Pass None explicitly to unlink from goal
    
    Returns:
        Optional[Dict]: Updated task dictionary if found, None if task doesn't exist
    
    Side Effects:
        - Loads tasks from storage
        - Updates matching task in memory
        - Saves updated task list to tasks.json
    
    Update Strategy:
        Uses partial update pattern - only fields that are not None are updated.
        This allows flexible updates without requiring all fields.
    
    Example:
        # Update only the title
        >>> update_task(1, title="New title")
        
        # Update multiple fields
        >>> update_task(1, title="New title", priority="Now", goal_id=2)
        
        # Unlink from goal (set goal_id to None)
        >>> update_task(1, goal_id=None)
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
            
            # Save updated tasks to persistent storage
            save_tasks(tasks)
            return task
    
    # Task not found - return None to indicate failure
    return None

@eel.expose
def toggle_task(task_id: int) -> Optional[Dict]:
    """
    Toggle task completion status (complete ↔ incomplete).
    
    This function switches a task between completed and incomplete states.
    When completing a task, it records the completion timestamp.
    When uncompleting a task, it clears the completion timestamp.
    
    Args:
        task_id: ID of task to toggle (required)
    
    Returns:
        Optional[Dict]: Updated task dictionary if found, None if task doesn't exist
    
    Side Effects:
        - Loads tasks from storage
        - Toggles task.completed boolean
        - Sets completed_at timestamp when completing
        - Clears completed_at timestamp when uncompleting
        - Saves updated task list to tasks.json
    
    Behavior:
        - If task is incomplete → marks as completed, sets completed_at timestamp
        - If task is completed → marks as incomplete, clears completed_at timestamp
    
    Example:
        # Complete a task
        >>> toggle_task(1)
        {"id": 1, "completed": True, "completed_at": "2024-12-10T15:30:00", ...}
        
        # Uncomplete the same task
        >>> toggle_task(1)
        {"id": 1, "completed": False, "completed_at": None, ...}
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
    
    This function removes a task from storage. The deletion is permanent
    and cannot be undone. The task ID is not reused (to maintain referential
    integrity with any external references).
    
    Args:
        task_id: ID of task to delete (required)
    
    Returns:
        bool: True if task was successfully deleted, False if task not found
    
    Side Effects:
        - Loads tasks from storage
        - Removes task with matching ID from the list
        - Saves updated task list to tasks.json (only if task was found)
    
    Deletion Strategy:
        Uses list comprehension to filter out the task with matching ID.
        Compares list length before and after to determine if deletion occurred.
    
    Example:
        >>> delete_task(1)
        True  # Task deleted successfully
        
        >>> delete_task(999)
        False  # Task not found
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

