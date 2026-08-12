"""
Setup script for py2app (Mac-specific packaging)

This creates a native Mac .app bundle using py2app.

Usage:
    python setup.py py2app

The resulting .app will be in the 'dist' folder.
"""

from setuptools import setup

APP = ['main.py']
DATA_FILES = [
    ('web', ['web/index.html', 'web/style.css', 'web/app.js']),
]

OPTIONS = {
    'argv_emulation': True,
    'plist': {
        'CFBundleName': 'ToDo',
        'CFBundleDisplayName': 'ToDo',
        'CFBundleGetInfoString': 'ToDo',
        'CFBundleIdentifier': 'com.todo.app',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
    },
    'packages': ['eel', 'setuptools'],
    'includes': ['todo', 'goals', 'analytics', 'data_storage', 'journal', 'notifications', 'security_utils'],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)

