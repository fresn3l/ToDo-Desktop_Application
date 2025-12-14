"""
Journal Module

This module handles journal entry creation, storage, and retrieval.
Journal entries are stored in a hierarchical folder structure:
- Main folder: ~/Library/Application Support/ToDo/Journal/
- Yearly subfolders: YYYY/
- Monthly subfolders: YYYY/MM/
- Weekly subfolders: YYYY/MM/Week_XX/
- Individual entries: YYYY/MM/Week_XX/entry_YYYY-MM-DD_HH-MM-SS.json

All functions decorated with @eel.expose are callable from JavaScript.
"""

import eel
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import fcntl
import sys

# ============================================
# JOURNAL STORAGE PATHS
# ============================================

def get_journal_directory():
    """
    Get the base directory for journal entries.
    Uses Application Support folder for persistence.
    
    Returns:
        Path: Base journal directory path
    """
    if sys.platform == 'win32':  # Windows
        base_dir = Path.home() / 'AppData' / 'Local' / 'ToDo' / 'Journal'
    elif sys.platform == 'darwin':  # macOS
        base_dir = Path.home() / 'Library' / 'Application Support' / 'ToDo' / 'Journal'
    else:  # Linux and others
        base_dir = Path.home() / '.local' / 'share' / 'ToDo' / 'Journal'
    
    # Create directory if it doesn't exist
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir

def get_entry_path(entry_date: datetime = None) -> Path:
    """
    Get the file path for a journal entry based on date.
    Creates the folder structure if it doesn't exist.
    
    Args:
        entry_date: Datetime object for the entry (defaults to now)
    
    Returns:
        Path: Full path to the entry file
    """
    if entry_date is None:
        entry_date = datetime.now()
    
    base_dir = get_journal_directory()
    
    # Create folder structure: YYYY/MM/Week_XX/
    year = entry_date.strftime('%Y')
    month = entry_date.strftime('%m')
    
    # Calculate week number (1-4 or 5 depending on month)
    day = entry_date.day
    week_num = ((day - 1) // 7) + 1
    week_folder = f'Week_{week_num:02d}'
    
    # Create full path
    entry_dir = base_dir / year / month / week_folder
    entry_dir.mkdir(parents=True, exist_ok=True)
    
    # Create filename with timestamp
    timestamp = entry_date.strftime('%Y-%m-%d_%H-%M-%S')
    filename = f'entry_{timestamp}.json'
    
    return entry_dir / filename

# ============================================
# JOURNAL CRUD OPERATIONS
# ============================================

@eel.expose
def save_journal_entry(content: str, duration_seconds: int = 0, continued: bool = False):
    """
    Save a new journal entry.
    
    Args:
        content: The journal entry text content
        duration_seconds: Time spent writing (in seconds)
        continued: Whether the entry was continued after timer
    
    Returns:
        Dict: The saved entry dictionary with metadata
    """
    entry_date = datetime.now()
    entry_path = get_entry_path(entry_date)
    
    # Create entry dictionary
    entry = {
        "id": entry_path.stem,  # Use filename without extension as ID
        "content": content,
        "date": entry_date.isoformat(),
        "duration_seconds": duration_seconds,
        "continued": continued,
        "created_at": entry_date.isoformat()
    }
    
    # Save to file with atomic write and file locking
    temp_file = str(entry_path) + '.tmp'
    with open(temp_file, 'w', encoding='utf-8') as f:
        # Acquire exclusive lock for writing
        if sys.platform != 'win32':
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            json.dump(entry, f, indent=2, ensure_ascii=False)
        finally:
            if sys.platform != 'win32':
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    
    # Atomically replace old file with new one
    os.replace(temp_file, entry_path)
    
    return entry

@eel.expose
def get_recent_entries(days: int = 30) -> List[Dict]:
    """
    Get journal entries from the last N days.
    
    Args:
        days: Number of days to look back (default: 30)
    
    Returns:
        List[Dict]: List of journal entries, sorted by date (newest first)
    """
    base_dir = get_journal_directory()
    entries = []
    cutoff_date = datetime.now() - timedelta(days=days)
    
    # Walk through all journal folders
    if not base_dir.exists():
        return []
    
    for year_dir in base_dir.iterdir():
        if not year_dir.is_dir():
            continue
        
        for month_dir in year_dir.iterdir():
            if not month_dir.is_dir():
                continue
            
            for week_dir in month_dir.iterdir():
                if not week_dir.is_dir():
                    continue
                
                # Look for entry JSON files
                for entry_file in week_dir.glob('entry_*.json'):
                    try:
                        # Read entry with file locking
                        with open(entry_file, 'r', encoding='utf-8') as f:
                            if sys.platform != 'win32':
                                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                            try:
                                entry = json.load(f)
                                # Parse entry date
                                entry_date = datetime.fromisoformat(entry.get('date', entry.get('created_at', '')))
                                
                                # Only include entries within the date range
                                if entry_date >= cutoff_date:
                                    entries.append(entry)
                            finally:
                                if sys.platform != 'win32':
                                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                    except (json.JSONDecodeError, IOError, ValueError) as e:
                        # Skip corrupted or invalid entries
                        continue
    
    # Sort by date (newest first)
    entries.sort(key=lambda x: x.get('date', x.get('created_at', '')), reverse=True)
    
    return entries

@eel.expose
def get_all_entries() -> List[Dict]:
    """
    Get all journal entries (no date limit).
    
    Returns:
        List[Dict]: List of all journal entries, sorted by date (newest first)
    """
    base_dir = get_journal_directory()
    entries = []
    
    if not base_dir.exists():
        return []
    
    # Walk through all journal folders
    for year_dir in base_dir.iterdir():
        if not year_dir.is_dir():
            continue
        
        for month_dir in year_dir.iterdir():
            if not month_dir.is_dir():
                continue
            
            for week_dir in month_dir.iterdir():
                if not week_dir.is_dir():
                    continue
                
                # Look for entry JSON files
                for entry_file in week_dir.glob('entry_*.json'):
                    try:
                        # Read entry with file locking
                        with open(entry_file, 'r', encoding='utf-8') as f:
                            if sys.platform != 'win32':
                                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                            try:
                                entry = json.load(f)
                                entries.append(entry)
                            finally:
                                if sys.platform != 'win32':
                                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                    except (json.JSONDecodeError, IOError, ValueError):
                        # Skip corrupted or invalid entries
                        continue
    
    # Sort by date (newest first)
    entries.sort(key=lambda x: x.get('date', x.get('created_at', '')), reverse=True)
    
    return entries

