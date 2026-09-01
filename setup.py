"""
Deprecated. Use ./macos/install_app.sh (PyInstaller + native WebKit window).

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
            "web/js/weekstrip.js",
            "web/js/appearance.js",
            "web/js/settings.js",
            "web/js/today.js",
            "web/js/home.js",
            "web/js/home_layout.js",
            "web/js/weather.js",
            "web/js/glance.js",
            "web/js/todo.js",
            "web/js/all_work.js",
            "web/js/goals.js",
            "web/js/heatmap.js",
            "web/js/day_brief.js",
            "web/js/counters.js",
            "web/js/reading.js",
            "web/js/word.js",
            "web/js/work.js",
            "web/js/workouts.js",
            "web/js/analytics.js",
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
    "includes": ["daily_checklist", "journal", "cluny_sync", "insights", "timeline", "export_data", "reminders", "health_import", "appearance", "bridge", "paths", "native_mac", "work", "workouts", "goals", "home_layout", "weather", "glance", "heatmap", "day_brief", "reading", "tap_counters", "word_of_the_day"],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
