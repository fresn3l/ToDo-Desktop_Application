"""
Optional: record daily checklist completion in the GitHub repo (checkins/YYYY-MM-DD.json)
so GitHub Actions can see whether you submitted today before sending a Twilio SMS.

Environment (set before launching Kosistenz):
  KOSISTENZ_GITHUB_TOKEN   — classic PAT or fine-grained PAT with Contents: Read and write
  KOSISTENZ_GITHUB_REPO    — "owner/repo"
  KOSISTENZ_GITHUB_BRANCH  — branch to commit on (default: DailyChecklist)

If unset, submissions stay local-only (SQLite) as usual.
"""

from __future__ import annotations

import base64
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any, Dict


def is_enabled() -> bool:
    return bool(os.environ.get("KOSISTENZ_GITHUB_TOKEN") and os.environ.get("KOSISTENZ_GITHUB_REPO"))


def _parse_repo(spec: str) -> tuple[str, str]:
    parts = spec.strip().split("/", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError("KOSISTENZ_GITHUB_REPO must be owner/repo")
    return parts[0], parts[1]


def try_push_checkin(local_date: str, payload: Dict[str, Any]) -> None:
    """Upsert checkins/<local_date>.json on GitHub. Logs and returns on failure."""
    if not is_enabled():
        return
    token = os.environ["KOSISTENZ_GITHUB_TOKEN"].strip()
    owner, repo = _parse_repo(os.environ["KOSISTENZ_GITHUB_REPO"])
    branch = os.environ.get("KOSISTENZ_GITHUB_BRANCH", "DailyChecklist").strip()
    path = f"checkins/{local_date}.json"
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    body_bytes = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
    b64 = base64.b64encode(body_bytes).decode("ascii")

    req_headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Kosistenz-checkin",
    }

    sha = None
    get_req = urllib.request.Request(url, headers=req_headers, method="GET")
    try:
        with urllib.request.urlopen(get_req, timeout=45) as resp:
            existing = json.loads(resp.read().decode())
            sha = existing.get("sha")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise

    put_body: Dict[str, Any] = {
        "message": f"Kosistenz check-in {local_date}",
        "content": b64,
        "branch": branch,
    }
    if sha:
        put_body["sha"] = sha

    put_data = json.dumps(put_body).encode("utf-8")
    put_req = urllib.request.Request(
        url,
        data=put_data,
        headers={**req_headers, "Content-Type": "application/json"},
        method="PUT",
    )
    with urllib.request.urlopen(put_req, timeout=45) as resp:
        resp.read()


def safe_try_push_checkin(local_date: str, payload: Dict[str, Any]) -> None:
    try:
        try_push_checkin(local_date, payload)
    except Exception as e:
        print(f"[Kosistenz] GitHub check-in failed (saved locally): {e}", file=sys.stderr)
