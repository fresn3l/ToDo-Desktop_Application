"""
Security helpers for credential storage, input validation, and file permissions.
"""

import base64
import hmac
import json
import os
import re
import secrets
import stat
from datetime import datetime
from pathlib import Path
from typing import Optional


ALLOWED_PRIORITIES = frozenset({"Now", "Next", "Later"})
ALLOWED_RECURRENCE = frozenset({"daily", "weekly", "monthly", "yearly"})

MAX_TITLE_LENGTH = 500
MAX_DESCRIPTION_LENGTH = 10_000
MAX_JOURNAL_LENGTH = 100_000
MAX_EMAIL_LENGTH = 254
MAX_SMTP_HOST_LENGTH = 253
MAX_RECURRING_INSTANCES_PER_CHECK = 60

EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,255}\.[A-Za-z]{2,}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HOSTNAME_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)"
    r"(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*$"
)
IPV4_RE = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")


def restrict_file_permissions(path) -> None:
    """Best-effort: make a file readable/writable only by the current user."""
    try:
        os.chmod(str(path), stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def restrict_directory_permissions(path) -> None:
    """Best-effort: make a directory accessible only by the current user."""
    try:
        os.chmod(str(path), stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
    except OSError:
        pass


def open_private_write(path, encoding: str = "utf-8"):
    """Open a file for writing, creating it with owner-only permissions."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    fd = os.open(str(path), flags, 0o600)
    return os.fdopen(fd, "w", encoding=encoding)


def sanitize_header_value(value) -> str:
    """Strip CR/LF to prevent email header injection."""
    if value is None:
        return ""
    return str(value).replace("\r", "").replace("\n", "").strip()


def clamp_text(value, max_len: int) -> str:
    """Return a string truncated to max_len. None becomes empty string."""
    if value is None:
        return ""
    text = str(value)
    if len(text) > max_len:
        return text[:max_len]
    return text


def validate_priority(priority, default: str = "Next") -> str:
    if priority in ALLOWED_PRIORITIES:
        return priority
    return default


def validate_recurrence(recurrence) -> Optional[str]:
    if not recurrence:
        return None
    if recurrence in ALLOWED_RECURRENCE:
        return recurrence
    raise ValueError("Invalid recurrence type")


def validate_date_string(value) -> Optional[str]:
    if not value:
        return None
    if not DATE_RE.match(str(value)):
        raise ValueError("Invalid date format; expected YYYY-MM-DD")
    datetime.strptime(value, "%Y-%m-%d")
    return value


def validate_email(email: str, required: bool = False) -> str:
    email = sanitize_header_value(email)
    if not email:
        if required:
            raise ValueError("Email address is required")
        return ""
    if len(email) > MAX_EMAIL_LENGTH or not EMAIL_RE.match(email):
        raise ValueError("Invalid email address")
    return email


def validate_smtp_host(host: str) -> str:
    host = sanitize_header_value(host).strip().lower()
    if not host:
        raise ValueError("SMTP server is required")
    if len(host) > MAX_SMTP_HOST_LENGTH:
        raise ValueError("SMTP server hostname is too long")
    if IPV4_RE.match(host):
        parts = host.split(".")
        if all(0 <= int(part) <= 255 for part in parts):
            return host
        raise ValueError("Invalid SMTP server")
    if not HOSTNAME_RE.match(host):
        raise ValueError("Invalid SMTP server hostname")
    return host


def validate_port(port) -> int:
    try:
        port_num = int(port)
    except (TypeError, ValueError):
        raise ValueError("Invalid SMTP port")
    if not 1 <= port_num <= 65535:
        raise ValueError("SMTP port out of range")
    return port_num


def validate_check_interval(hours) -> int:
    try:
        value = int(hours)
    except (TypeError, ValueError):
        raise ValueError("Invalid check interval")
    return max(1, min(value, 24))


def public_notification_settings(settings: dict) -> dict:
    """Return settings safe to send to the UI (no SMTP password)."""
    public = {key: value for key, value in settings.items() if key != "email_password"}
    public["password_set"] = bool(settings.get("email_password"))
    return public


def _secret_key_path(data_dir: Path) -> Path:
    return Path(data_dir) / ".secret_key"


def _credentials_path(data_dir: Path) -> Path:
    return Path(data_dir) / ".smtp_credentials"


def _get_or_create_secret_key(data_dir: Path) -> bytes:
    key_path = _secret_key_path(data_dir)
    if key_path.exists():
        key = key_path.read_bytes()
        if len(key) >= 32:
            return key
    key = secrets.token_bytes(32)
    fd = os.open(str(key_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, key)
    finally:
        os.close(fd)
    restrict_file_permissions(key_path)
    return key


def obfuscate_secret(plaintext: str, data_dir: Path) -> str:
    """Obfuscate a secret so casual inspection of the credentials file is not enough."""
    if not plaintext:
        return ""
    key = _get_or_create_secret_key(data_dir)
    data = plaintext.encode("utf-8")
    xored = bytes(byte ^ key[i % len(key)] for i, byte in enumerate(data))
    mac = hmac.new(key, xored, "sha256").digest()
    return base64.b64encode(mac + xored).decode("ascii")


def deobfuscate_secret(token: str, data_dir: Path) -> str:
    """Reverse obfuscate_secret. Raises ValueError if the token was tampered with."""
    if not token:
        return ""
    key = _get_or_create_secret_key(data_dir)
    try:
        raw = base64.b64decode(token.encode("ascii"), validate=True)
    except (ValueError, TypeError):
        raise ValueError("Credential integrity check failed")
    if len(raw) < 32:
        raise ValueError("Credential integrity check failed")
    mac, xored = raw[:32], raw[32:]
    expected = hmac.new(key, xored, "sha256").digest()
    if not hmac.compare_digest(mac, expected):
        raise ValueError("Credential integrity check failed")
    data = bytes(byte ^ key[i % len(key)] for i, byte in enumerate(xored))
    return data.decode("utf-8")


def save_smtp_password(password: str, data_dir: Path) -> None:
    """Store the SMTP password outside of settings JSON, owner-only."""
    creds_path = _credentials_path(data_dir)
    payload = {"email_password": obfuscate_secret(password, data_dir)}
    with open_private_write(creds_path) as handle:
        json.dump(payload, handle)
    restrict_file_permissions(creds_path)


def load_smtp_password(data_dir: Path) -> str:
    """Load the SMTP password from the private credentials file."""
    creds_path = _credentials_path(data_dir)
    if not creds_path.exists():
        return ""
    try:
        with open(creds_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        token = payload.get("email_password", "")
        if not token:
            return ""
        return deobfuscate_secret(token, data_dir)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return ""


def delete_smtp_password(data_dir: Path) -> None:
    creds_path = _credentials_path(data_dir)
    try:
        if creds_path.exists():
            os.remove(creds_path)
    except OSError:
        pass
