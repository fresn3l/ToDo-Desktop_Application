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
import uuid

import cluny_sync
from paths import data_directory

# ============================================
# JOURNAL STORAGE PATHS
# ============================================

def get_journal_directory():
    """Journal files live under the shared data directory / Journal."""
    base_dir = data_directory() / "Journal"
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
    filename = f'entry_{timestamp}_{uuid.uuid4().hex[:8]}.json'
    
    return entry_dir / filename

# ============================================
# JOURNAL CRUD OPERATIONS
# ============================================

JOURNAL_TAG_PRESETS = ["work", "health", "relationships"]


def _normalize_tags(tags) -> List[str]:
    if not tags:
        return []
    if isinstance(tags, str):
        raw = [t.strip().lstrip("#") for t in tags.replace(",", " ").split()]
    elif isinstance(tags, list):
        raw = [str(t).strip().lstrip("#") for t in tags]
    else:
        return []
    out = []
    seen = set()
    for t in raw:
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


@eel.expose
def get_journal_tag_presets() -> List[str]:
    return list(JOURNAL_TAG_PRESETS)


@eel.expose
def save_journal_entry(content: str, duration_seconds: int = 0, continued: bool = False, tags=None):
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
        "created_at": entry_date.isoformat(),
        "tags": _normalize_tags(tags),
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

    cluny_sync.sync_journal_entry_safe(entry)

    try:
        import work

        work.refresh_widget_snapshot()
    except Exception:
        pass

    return entry

def _load_entries_from_disk(cutoff_date: Optional[datetime] = None) -> List[Dict]:
    base_dir = get_journal_directory()
    entries = []
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
                for entry_file in week_dir.glob('entry_*.json'):
                    try:
                        with open(entry_file, 'r', encoding='utf-8') as f:
                            if sys.platform != 'win32':
                                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                            try:
                                entry = json.load(f)
                                entry_date = datetime.fromisoformat(
                                    entry.get('date', entry.get('created_at', ''))
                                )
                                if cutoff_date is None or entry_date >= cutoff_date:
                                    entries.append(entry)
                            finally:
                                if sys.platform != 'win32':
                                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                    except (json.JSONDecodeError, IOError, ValueError):
                        continue

    entries.sort(key=lambda x: x.get('date', x.get('created_at', '')), reverse=True)
    return entries


@eel.expose
def get_recent_entries(days: int = 30) -> List[Dict]:
    """Journal entries from the last N days, newest first."""
    cutoff_date = datetime.now() - timedelta(days=days)
    return _load_entries_from_disk(cutoff_date)


@eel.expose
def get_all_entries() -> List[Dict]:
    """All journal entries, newest first."""
    return _load_entries_from_disk()

