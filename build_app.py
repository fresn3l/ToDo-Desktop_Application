"""
Build a standalone Kosistenz.app with PyInstaller.

The window is native (WKWebView on macOS). Chrome is not bundled or required.
Run via ./macos/install_app.sh from a Mac.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys


def check_dependencies() -> None:
    required = ["eel", "webview", "PyInstaller"]
    missing = []
    for module in required:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    if missing:
        print(f"Missing dependencies: {', '.join(missing)}")
        print("Run: ./setup_venv.sh")
        sys.exit(1)
    print("Dependencies OK.")


def maybe_build_icon() -> list[str]:
    icon_path = "app_icon.icns"
    if os.path.exists("app_icon.png"):
        print("Regenerating icon from PNG...")
        try:
            if os.path.exists("app_icon.iconset"):
                shutil.rmtree("app_icon.iconset")
            os.makedirs("app_icon.iconset", exist_ok=True)
            sizes = [16, 32, 128, 256, 512]
            for size in sizes:
                subprocess.run(
                    [
                        "sips", "-z", str(size), str(size), "app_icon.png",
                        "--out", f"app_icon.iconset/icon_{size}x{size}.png",
                    ],
                    check=False,
                    capture_output=True,
                )
                subprocess.run(
                    [
                        "sips", "-z", str(size * 2), str(size * 2), "app_icon.png",
                        "--out", f"app_icon.iconset/icon_{size}x{size}@2x.png",
                    ],
                    check=False,
                    capture_output=True,
                )
            subprocess.run(
                ["iconutil", "-c", "icns", "app_icon.iconset", "-o", icon_path],
                check=False,
                capture_output=True,
            )
            shutil.rmtree("app_icon.iconset", ignore_errors=True)
        except Exception as exc:
            print(f"Icon generation skipped: {exc}")
    if os.path.exists(icon_path):
        print(f"Using icon: {icon_path}")
        return [f"--icon={icon_path}"]
    print("No app_icon.icns — macOS will use a default icon.")
    return []


def build_app() -> None:
    check_dependencies()
    import PyInstaller.__main__

    print("Cleaning previous builds...")
    for folder in ("build", "dist"):
        if os.path.exists(folder):
            shutil.rmtree(folder)

    hidden = [
        "eel",
        "bottle",
        "gevent",
        "geventwebsocket",
        "webview",
        "setuptools",
        "checkin_github",
        "daily_checklist",
        "journal",
        "cluny_sync",
        "insights",
        "timeline",
        "export_data",
        "recovery",
        "reminders",
        "health_import",
        "appearance",
        "bridge",
        "paths",
        "proxy_tools",
        "packaging",
        "bottle_websocket",
        "geventwebsocket",
        "greenlet",
    ]
    if sys.platform == "darwin":
        hidden += [
            "webview.platforms.cocoa",
            "objc",
            "objc._objc",
            "AppKit",
            "Foundation",
            "WebKit",
            "CoreFoundation",
            "Quartz",
            "CoreGraphics",
        ]
    elif sys.platform == "win32":
        hidden.append("webview.platforms.edgechromium")
    else:
        hidden.append("webview.platforms.gtk")

    args = [
        "main.py",
        "--name=Kosistenz",
        "--windowed",
        "--onedir",
        "--add-data=web:web",
        "--add-data=checklists:checklists",
        "--add-data=macos/kosistenz-reminder.sh:macos",
        "--collect-all=eel",
        "--collect-all=webview",
        "--collect-all=gevent",
        "--collect-all=bottle",
        "--copy-metadata=pywebview",
        "--osx-bundle-identifier=com.kosistenz.app",
        "--noconfirm",
        *maybe_build_icon(),
    ]
    for name in hidden:
        args.append(f"--hidden-import={name}")

    print("Building standalone app (this takes a few minutes)...")
    PyInstaller.__main__.run(args)

    app_path = None
    for candidate in ("dist/Kosistenz.app", "dist/Kosistenz/Kosistenz.app"):
        if os.path.exists(candidate):
            app_path = candidate
            break
    if not app_path:
        print("Build finished but Kosistenz.app was not found under dist/.")
        sys.exit(1)

    print(f"Built: {os.path.abspath(app_path)}")
    _patch_info_plist(app_path)


def _patch_info_plist(app_path: str) -> None:
    plist_path = os.path.join(app_path, "Contents", "Info.plist")
    if not os.path.exists(plist_path):
        return
    try:
        import plistlib

        with open(plist_path, "rb") as handle:
            info = plistlib.load(handle)
        info["CFBundleName"] = "Kosistenz"
        info["CFBundleDisplayName"] = "Kosistenz"
        info["LSApplicationCategoryType"] = "public.app-category.productivity"
        info["NSHighResolutionCapable"] = True
        info["NSRequiresAquaSystemAppearance"] = False
        info["LSMinimumSystemVersion"] = "11.0"
        with open(plist_path, "wb") as handle:
            plistlib.dump(info, handle)
    except Exception as exc:
        print(f"Could not patch Info.plist: {exc}")


if __name__ == "__main__":
    build_app()
