"""
Journal Module

Handles journal entry creation, storage, and retrieval.
Entries are stored in a hierarchical folder structure by year/month/week.
"""

import eel
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import fcntl
import sys

from data_storage import get_data_directory
from security_utils import (
    MAX_JOURNAL_LENGTH,
    clamp_text,
    open_private_write,
    restrict_directory_permissions,
    restrict_file_permissions,
)

# ============================================
# JOURNAL STORAGE PATHS
# ============================================

def get_journal_directory():
    """
    Get the base directory for journal entries.
    Uses this app's private data directory (not shared with other apps).
    """
    base_dir = get_data_directory() / 'Journal'
    base_dir.mkdir(parents=True, exist_ok=True)
    restrict_directory_permissions(base_dir)
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
    restrict_directory_permissions(entry_dir)
    
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
    content = clamp_text(content, MAX_JOURNAL_LENGTH)
    try:
        duration_seconds = max(0, int(duration_seconds or 0))
    except (TypeError, ValueError):
        duration_seconds = 0
    continued = bool(continued)

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
    with open_private_write(temp_file) as f:
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
    restrict_file_permissions(entry_path)
    
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
    try:
        days = max(1, min(int(days), 365))
    except (TypeError, ValueError):
        days = 30

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

