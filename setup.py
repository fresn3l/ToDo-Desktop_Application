"""
Setup script for py2app (Mac-specific packaging)

Usage:
    python setup.py py2app
"""

from setuptools import setup

APP = ["main.py"]
DATA_FILES = [
    ("web", ["web/index.html", "web/style.css", "web/app.js"]),
    ("web/js", ["web/js/journal.js", "web/js/utils.js"]),
]

OPTIONS = {
    "argv_emulation": True,
    "plist": {
        "CFBundleName": "Journal",
        "CFBundleDisplayName": "Journal",
        "CFBundleGetInfoString": "Journal",
        "CFBundleIdentifier": "com.journal.app",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "NSHighResolutionCapable": True,
    },
    "packages": ["eel", "setuptools"],
    "includes": ["journal", "cluny_sync"],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
