"""
Setup script for py2app (Mac-specific packaging)

Usage:
    python setup.py py2app
"""

from setuptools import setup

APP = ["main.py"]
DATA_FILES = [
    ("web", ["web/index.html", "web/style.css", "web/app.js"]),
    (
        "web/js",
        [
            "web/js/journal.js",
            "web/js/utils.js",
            "web/js/tabs.js",
            "web/js/daily_checklist.js",
            "web/js/review.js",
            "web/js/timeline.js",
        ],
    ),
    (
        "checklists",
        [
            "checklists/default.json",
            "checklists/blank-template-1.json",
            "checklists/blank-template-2.json",
            "checklists/blank-template-3.json",
            "checklists/blank-template-4.json",
            "checklists/morning.json",
            "checklists/evening.json",
        ],
    ),
]

OPTIONS = {
    "argv_emulation": True,
    "plist": {
        "CFBundleName": "Kosistenz",
        "CFBundleDisplayName": "Kosistenz",
        "CFBundleGetInfoString": "Kosistenz",
        "CFBundleIdentifier": "com.kosistenz.app",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "NSHighResolutionCapable": True,
    },
    "packages": ["eel", "setuptools"],
    "includes": ["checkin_github", "daily_checklist", "journal", "cluny_sync", "insights", "timeline", "export_data", "recovery", "reminders"],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
