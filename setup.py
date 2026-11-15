"""
Deprecated. Use ./macos/install_app.sh (PyInstaller + native WebKit window).

    python setup.py py2app
"""

from setuptools import setup

APP = ["main.py"]
DATA_FILES = [
    ("web", ["web/index.html", "web/style.css", "web/app.js", "web/tokens.css"]),
    (
        "web/js",
        [
            "web/js/utils.js",
            "web/js/tabs.js",
            "web/js/appearance.js",
            "web/js/boot-appearance.js",
            "web/js/settings.js",
            "web/js/lazy.js",
            "web/js/paste_insert.js",
            "web/js/todo.js",
            "web/js/todo_page.js",
            "web/js/work.js",
            "web/js/calendar.js",
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
    "includes": ["appearance", "bridge", "paths", "native_mac", "work", "calclock", "schedule", "icloud_sync", "phone_calendar", "phone_today", "db", "local_api"],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
