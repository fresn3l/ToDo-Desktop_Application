"""
Notifications Module

Handles email notifications for tasks due within 24 hours.
Supports custom SMTP configuration and notification scheduling.
"""

import eel
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
import os
from pathlib import Path

# Import data storage functions
from data_storage import load_tasks, get_data_directory
from security_utils import (
    clamp_text,
    delete_smtp_password,
    load_smtp_password,
    open_private_write,
    public_notification_settings,
    restrict_file_permissions,
    sanitize_header_value,
    save_smtp_password,
    validate_check_interval,
    validate_email,
    validate_port,
    validate_smtp_host,
)

# ============================================
# NOTIFICATION SETTINGS STORAGE
# ============================================

def get_settings_file() -> str:
    """Get the path to the notification settings file."""
    data_dir = get_data_directory()
    return str(Path(data_dir) / 'notification_settings.json')

def load_notification_settings() -> Dict:
    """
    Load notification settings from storage.
    
    Returns:
        Dict: Settings dictionary with:
            - enabled: bool - Whether notifications are enabled
            - email: str - Email address to send notifications to
            - smtp_server: str - SMTP server (e.g., 'smtp.gmail.com')
            - smtp_port: int - SMTP port (usually 587 for TLS)
            - email_username: str - Email username for authentication
            - check_interval_hours: int - How often to check (default: 1)
            SMTP password is stored separately and is not included here.
    """
    settings_file = get_settings_file()
    default_settings = {
        "enabled": False,
        "email": "",
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "email_username": "",
        "email_password": "",
        "check_interval_hours": 1
    }
    
    had_plaintext_in_file = False
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r') as f:
                loaded = json.load(f)
            had_plaintext_in_file = "email_password" in loaded
            settings = {**default_settings, **loaded}
        except (json.JSONDecodeError, IOError):
            settings = default_settings
    else:
        settings = default_settings

    data_dir = get_data_directory()
    stored_password = load_smtp_password(data_dir)

    # Migrate legacy plaintext passwords out of settings JSON
    legacy_password = settings.pop("email_password", "") or ""
    if stored_password:
        settings["email_password"] = stored_password
    elif legacy_password:
        save_smtp_password(legacy_password, data_dir)
        settings["email_password"] = legacy_password
    else:
        settings["email_password"] = ""

    if had_plaintext_in_file:
        _write_settings_file(settings)

    return settings

def _write_settings_file(settings: Dict):
    """Persist non-secret notification settings with owner-only permissions."""
    settings_file = get_settings_file()
    safe_settings = {k: v for k, v in settings.items() if k != "email_password"}
    with open_private_write(settings_file) as f:
        json.dump(safe_settings, f, indent=2)
    restrict_file_permissions(settings_file)


def save_notification_settings(settings: Dict):
    """
    Save notification settings to storage.
    
    Args:
        settings: Settings dictionary to save
    """
    data_dir = get_data_directory()
    if "email_password" in settings:
        password = settings.get("email_password") or ""
        if password:
            save_smtp_password(password, data_dir)
        else:
            delete_smtp_password(data_dir)

    _write_settings_file(settings)

# ============================================
# NOTIFICATION FUNCTIONS
# ============================================

@eel.expose
def get_notification_settings() -> Dict:
    """
    Get current notification settings for the UI.
    The SMTP password is never returned to the frontend.
    """
    return public_notification_settings(load_notification_settings())

@eel.expose
def update_notification_settings(enabled: bool = None, email: str = None,
                                  smtp_server: str = None, smtp_port: int = None,
                                  email_username: str = None, email_password: str = None,
                                  check_interval_hours: int = None) -> Dict:
    """
    Update notification settings.
    
    Args:
        enabled: Enable/disable notifications
        email: Email address to send notifications to
        smtp_server: SMTP server address
        smtp_port: SMTP port number
        email_username: Email username for authentication
        email_password: Email password
        check_interval_hours: How often to check for due tasks (in hours)
    
    Returns:
        Dict: Updated settings
    """
    settings = load_notification_settings()
    
    if enabled is not None:
        settings["enabled"] = bool(enabled)
    if email is not None:
        settings["email"] = validate_email(email, required=bool(settings.get("enabled")))
    if smtp_server is not None:
        settings["smtp_server"] = validate_smtp_host(smtp_server) if smtp_server else settings["smtp_server"]
    if smtp_port is not None:
        settings["smtp_port"] = validate_port(smtp_port)
    if email_username is not None:
        settings["email_username"] = clamp_text(sanitize_header_value(email_username), 254)
    if email_password:
        # Only update the stored password when the user actually submitted a new one
        settings["email_password"] = email_password
    if check_interval_hours is not None:
        settings["check_interval_hours"] = validate_check_interval(check_interval_hours)
    
    save_notification_settings(settings)
    return public_notification_settings(settings)

def send_email_notification(task: Dict, recipient_email: str, settings: Dict) -> bool:
    """
    Send an email notification for a task due within 24 hours.
    
    Args:
        task: Task dictionary
        recipient_email: Email address to send to
        settings: Notification settings with SMTP credentials
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        # Create email message
        msg = MIMEMultipart()
        sender = sanitize_header_value(settings.get("email_username", ""))
        recipient = sanitize_header_value(recipient_email)
        title = sanitize_header_value(task.get("title", "Untitled Task"))
        msg['From'] = sender
        msg['To'] = recipient
        msg['Subject'] = f"Task Due Soon: {title}"
        
        # Format due date
        due_date_str = "No due date"
        if task.get('due_date'):
            try:
                due_date = datetime.strptime(task['due_date'], "%Y-%m-%d")
                due_date_str = due_date.strftime("%B %d, %Y")
            except ValueError:
                due_date_str = sanitize_header_value(task['due_date'])
        
        # Calculate hours until due
        hours_until_due = "N/A"
        if task.get('due_date'):
            try:
                due_date = datetime.strptime(task['due_date'], "%Y-%m-%d")
                due_date = due_date.replace(hour=23, minute=59, second=59)
                now = datetime.now()
                time_diff = due_date - now
                if time_diff.total_seconds() > 0:
                    hours = int(time_diff.total_seconds() / 3600)
                    hours_until_due = f"{hours} hours"
                else:
                    hours_until_due = "Overdue"
            except ValueError:
                pass
        
        # Create email body
        body = f"""
Task Reminder

Your task "{title}" is due soon!

Details:
• Title: {title}
• Priority: {sanitize_header_value(task.get('priority', 'Not set'))}
• Due Date: {due_date_str}
• Time Until Due: {hours_until_due}
• Description: {clamp_text(task.get('description', 'No description'), 2000)}

Don't forget to complete this task!
"""
        
        msg.attach(MIMEText(body, 'plain'))
        
        host = validate_smtp_host(settings["smtp_server"])
        port = validate_port(settings["smtp_port"])
        username = settings["email_username"]
        password = settings["email_password"]
        context = ssl.create_default_context()

        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=20, context=context) as server:
                server.login(username, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=20) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(username, password)
                server.send_message(msg)
        
        return True
    except Exception as e:
        print(f"Error sending email notification: {e}")
        return False

def get_tasks_due_soon(hours_threshold: int = 24) -> List[Dict]:
    """
    Get tasks that are due within the specified hours.
    
    Args:
        hours_threshold: Number of hours to look ahead (default: 24)
    
    Returns:
        List[Dict]: List of tasks due within the threshold
    """
    tasks = load_tasks()
    now = datetime.now()
    due_soon = []
    
    for task in tasks:
        # Skip completed or not_completed tasks
        if task.get("completed", False) or task.get("not_completed", False):
            continue
        
        # Skip tasks without due dates
        if not task.get("due_date"):
            continue
        
        try:
            # Parse due date
            due_date = datetime.strptime(task["due_date"], "%Y-%m-%d")
            due_date = due_date.replace(hour=23, minute=59, second=59)
            
            # Calculate time difference
            time_diff = due_date - now
            
            # Check if due within threshold
            if 0 <= time_diff.total_seconds() <= (hours_threshold * 3600):
                due_soon.append(task)
        except (ValueError, KeyError):
            continue
    
    return due_soon

def get_sent_notifications_file() -> str:
    """Get the path to the sent notifications tracking file."""
    data_dir = get_data_directory()
    return str(Path(data_dir) / 'sent_notifications.json')

def load_sent_notifications() -> Dict:
    """
    Load the record of sent notifications.
    
    Returns:
        Dict: Dictionary mapping task_id to last notification timestamp
    """
    notifications_file = get_sent_notifications_file()
    if os.path.exists(notifications_file):
        try:
            with open(notifications_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}

def save_sent_notification(task_id: int):
    """
    Record that a notification was sent for a task.
    
    Args:
        task_id: ID of the task that was notified
    """
    notifications_file = get_sent_notifications_file()
    sent_notifications = load_sent_notifications()
    sent_notifications[str(task_id)] = datetime.now().isoformat()
    
    with open_private_write(notifications_file) as f:
        json.dump(sent_notifications, f, indent=2)
    restrict_file_permissions(notifications_file)

def should_send_notification(task: Dict, hours_threshold: int = 24) -> bool:
    """
    Check if a notification should be sent for a task.
    
    Args:
        task: Task dictionary
        hours_threshold: Hours threshold for due date
    
    Returns:
        bool: True if notification should be sent
    """
    # Check if task is due within threshold
    if not task.get("due_date"):
        return False
    
    try:
        due_date = datetime.strptime(task["due_date"], "%Y-%m-%d")
        due_date = due_date.replace(hour=23, minute=59, second=59)
        now = datetime.now()
        time_diff = due_date - now
        
        # Must be due within threshold and not overdue
        if not (0 <= time_diff.total_seconds() <= (hours_threshold * 3600)):
            return False
    except (ValueError, KeyError):
        return False
    
    # Check if notification was already sent recently (within last 12 hours)
    sent_notifications = load_sent_notifications()
    task_id_str = str(task.get("id"))
    
    if task_id_str in sent_notifications:
        try:
            last_sent = datetime.fromisoformat(sent_notifications[task_id_str])
            hours_since_sent = (datetime.now() - last_sent).total_seconds() / 3600
            # Don't send again if sent within last 12 hours
            if hours_since_sent < 12:
                return False
        except (ValueError, KeyError):
            pass
    
    return True

@eel.expose
def check_and_send_notifications() -> Dict:
    """
    Check for tasks due within 24 hours and send email notifications.
    
    This function:
    1. Loads notification settings
    2. Checks if notifications are enabled
    3. Finds tasks due within 24 hours
    4. Sends email notifications for tasks that need reminders
    5. Tracks sent notifications
    
    Returns:
        Dict: Result with:
            - checked: bool - Whether check was performed
            - enabled: bool - Whether notifications are enabled
            - tasks_found: int - Number of tasks due soon
            - notifications_sent: int - Number of notifications sent
            - errors: List[str] - List of error messages
    """
    settings = load_notification_settings()
    
    result = {
        "checked": True,
        "enabled": settings.get("enabled", False),
        "tasks_found": 0,
        "notifications_sent": 0,
        "errors": []
    }
    
    # Check if notifications are enabled
    if not settings.get("enabled", False):
        return result
    
    # Check if email is configured
    if not settings.get("email") or not settings.get("email_username") or not settings.get("email_password"):
        result["errors"].append("Email not configured")
        return result
    
    try:
        # Get tasks due within 24 hours
        due_soon_tasks = get_tasks_due_soon(hours_threshold=24)
        result["tasks_found"] = len(due_soon_tasks)
        
        # Send notifications for tasks that need them
        for task in due_soon_tasks:
            if should_send_notification(task, hours_threshold=24):
                success = send_email_notification(
                    task,
                    settings["email"],
                    settings
                )
                
                if success:
                    save_sent_notification(task.get("id"))
                    result["notifications_sent"] += 1
                else:
                    result["errors"].append(f"Failed to send notification for task: {task.get('title', 'Unknown')}")
    
    except Exception as e:
        result["errors"].append(f"Error checking notifications: {str(e)}")
    
    return result

@eel.expose
def test_notification(email: str = None) -> Dict:
    """
    Send a test notification email.
    
    Args:
        email: Optional email address (uses settings if not provided)
    
    Returns:
        Dict: Result with success status and message
    """
    settings = load_notification_settings()
    
    if not email:
        email = settings.get("email")

    try:
        email = validate_email(email or "", required=True)
    except ValueError:
        return {"success": False, "message": "No valid email address provided"}
    
    if not settings.get("email_username") or not settings.get("email_password"):
        return {"success": False, "message": "Email credentials not configured"}
    
    # Create a test task
    test_task = {
        "id": 0,
        "title": "Test Notification",
        "description": "This is a test notification from your ToDo app.",
        "priority": "Now",
        "due_date": (datetime.now() + timedelta(hours=12)).strftime("%Y-%m-%d"),
        "completed": False
    }
    
    success = send_email_notification(test_task, email, settings)
    
    if success:
        return {"success": True, "message": "Test notification sent successfully!"}
    else:
        return {"success": False, "message": "Failed to send test notification. Check your email settings."}

