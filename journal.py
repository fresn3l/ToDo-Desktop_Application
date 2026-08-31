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
import re

import cluny_sync
from paths import data_directory

# ============================================
# JOURNAL STORAGE PATHS
# ============================================

JOURNAL_TAG_PRESETS = ["work", "health", "relationships"]
_SAFE_ENTRY_STEM = re.compile(r"^entry_[A-Za-z0-9._-]{1,120}$")
MAX_JOURNAL_IMPORT_CHARS = 200_000

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


def _entry_folder(entry_date: datetime) -> Path:
    year = entry_date.strftime("%Y")
    month = entry_date.strftime("%m")
    week_num = ((entry_date.day - 1) // 7) + 1
    folder = get_journal_directory() / year / month / f"Week_{week_num:02d}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def import_journal_entry(entry: Dict) -> Optional[Dict]:
    """Write one journal record without minting a new id (used by the iCloud pack)."""
    if not isinstance(entry, dict):
        return None
    content = str(entry.get("content") or "").strip()
    if not content or len(content) > MAX_JOURNAL_IMPORT_CHARS:
        return None
    raw = entry.get("date") or entry.get("created_at")
    try:
        when = datetime.fromisoformat(str(raw)) if raw else datetime.now()
    except (TypeError, ValueError):
        when = datetime.now()
    stem = Path(str(entry.get("id") or "").strip()).name
    if not _SAFE_ENTRY_STEM.fullmatch(stem):
        stem = f"entry_{when.strftime('%Y-%m-%d_%H-%M-%S')}_{uuid.uuid4().hex[:8]}"
    folder = _entry_folder(when).resolve()
    path = (folder / f"{stem}.json").resolve()
    root = get_journal_directory().resolve()
    if not path.is_relative_to(root) or path.parent != folder:
        return None
    if path.exists():
        return None
    record = {
        "id": stem,
        "content": content,
        "date": entry.get("date") or when.isoformat(),
        "duration_seconds": int(entry.get("duration_seconds") or 0),
        "continued": bool(entry.get("continued")),
        "created_at": entry.get("created_at") or when.isoformat(),
        "tags": _normalize_tags(entry.get("tags")),
    }
    temp_file = str(path) + ".tmp"
    with open(temp_file, "w", encoding="utf-8") as handle:
        if sys.platform != "win32":
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        json.dump(record, handle, indent=2, ensure_ascii=False)
    os.replace(temp_file, path)
    return record

# ============================================
# JOURNAL CRUD OPERATIONS
# ============================================

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

