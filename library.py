"""Library tab — browse and organize Cluny documents."""

from __future__ import annotations

import base64
import subprocess
import sys
from typing import Any, Dict, Optional

import eel

import cluny_client


@eel.expose
def library_list(
    collection: str = "",
    source: str = "",
) -> Dict[str, Any]:
    return cluny_client.library_list(
        collection=collection or None,
        source=source or None,
    )


@eel.expose
def library_filters() -> Dict[str, Any]:
    return cluny_client.library_collections()


@eel.expose
def library_get(doc_id: str) -> Dict[str, Any]:
    return cluny_client.library_get(str(doc_id or "").strip())


@eel.expose
def library_update(doc_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Invalid update payload")
    return cluny_client.library_update(str(doc_id or "").strip(), payload)


@eel.expose
def library_delete_doc(doc_id: str) -> Dict[str, Any]:
    return cluny_client.library_delete(str(doc_id or "").strip())


@eel.expose
def library_search(
    q: str,
    collection: str = "",
    source: str = "",
    limit: int = 50,
) -> Dict[str, Any]:
    return cluny_client.library_search(
        str(q or ""),
        collection=collection or None,
        source=source or None,
        limit=limit,
    )


@eel.expose
def library_create_collection(name: str) -> Dict[str, Any]:
    return cluny_client.library_create_collection(str(name or "").strip())


@eel.expose
def library_delete_collection(name: str, force: bool = False) -> Dict[str, Any]:
    return cluny_client.library_delete_collection(str(name or "").strip(), force=force)


@eel.expose
def library_upload_b64(
    filename: str,
    content_b64: str,
    title: str = "",
    collection: str = "",
    copy_into_library: bool = False,
) -> Dict[str, Any]:
    raw = base64.b64decode(content_b64 or "")
    return cluny_client.ingest_file_bytes(
        filename,
        raw,
        title=title or None,
        collection=collection or None,
        copy_into_library=copy_into_library,
    )


@eel.expose
def library_stats() -> Dict[str, Any]:
    try:
        return cluny_client.stats()
    except ValueError as exc:
        return {"error": str(exc)}


@eel.expose
def library_open_data_dir() -> bool:
    """Reveal Cluny data directory in Finder (macOS)."""
    try:
        data = cluny_client.stats()
    except ValueError:
        return False
    path = str(data.get("data_dir") or "").strip()
    if not path:
        return False
    if sys.platform == "darwin":
        subprocess.run(["open", path], check=False)
        return True
    return False


@eel.expose
def library_reveal_path(path: str) -> bool:
    """Reveal a file or folder in Finder (macOS)."""
    target = str(path or "").strip()
    if not target or sys.platform != "darwin":
        return False
    subprocess.run(["open", "-R", target], check=False)
    return True
