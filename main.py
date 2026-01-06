"""
ToDo Application - Main Entry Point

Desktop task management application built with Python (Eel) and modern web technologies.
Provides task management, goal tracking, analytics, journaling, and notification features.
"""

import eel
import threading
import time

import todo
import goals
import analytics
import journal
import notifications

eel.init('web')


def notification_scheduler():
    """Background thread that periodically checks for tasks due soon and sends notifications."""
    while True:
        try:
            notifications.check_and_send_notifications()
        except Exception as e:
            print(f"Error in notification scheduler: {e}")
        
        time.sleep(3600)


if __name__ == '__main__':
    scheduler_thread = threading.Thread(target=notification_scheduler, daemon=True)
    scheduler_thread.start()
    
    try:
        notifications.check_and_send_notifications()
    except Exception as e:
        print(f"Error checking notifications on startup: {e}")
    
    eel.start('index.html', size=(900, 700), port=0, mode='chrome-app')
