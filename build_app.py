"""
Build a standalone Kosistenz.app with PyInstaller + a native Swift WKWebView host.

Chrome is not bundled or required. Run via ./macos/install_app.sh from a Mac.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys


def check_dependencies() -> None:
    required = ["eel", "PyInstaller"]
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


def _swiftc() -> list[str] | None:
    xcrun = shutil.which("xcrun")
    if xcrun:
        probe = subprocess.run([xcrun, "--find", "swiftc"], capture_output=True, text=True)
        if probe.returncode == 0 and probe.stdout.strip():
            return [xcrun, "--sdk", "macosx", "swiftc"]
    swiftc = shutil.which("swiftc")
    if swiftc:
        return [swiftc]
    return None


def _has_pyobjc() -> bool:
    try:
        import AppKit  # noqa: F401
        import WebKit  # noqa: F401
    except Exception:
        return False
    return True


def _install_swift_host(app_path: str) -> bool:
    """Make the Swift WKWebView binary the app executable; Python becomes the UI server."""
    macos_dir = os.path.join(app_path, "Contents", "MacOS")
    python_exe = os.path.join(macos_dir, "Kosistenz")
    bridge_exe = os.path.join(macos_dir, "kosistenz-bridge")
    swift_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "macos", "KosistenzWindow.swift")
    compiler = _swiftc()
    if compiler is None:
        print("swiftc not found.")
        return False
    if not os.path.isfile(swift_src):
        print(f"Swift source missing: {swift_src}")
        return False
    if not os.path.isfile(python_exe):
        print(f"PyInstaller executable missing: {python_exe}")
        return False

    if os.path.exists(bridge_exe):
        os.remove(bridge_exe)
    os.rename(python_exe, bridge_exe)

    cmd = compiler + [
        "-O",
        "-o", python_exe,
        "-framework", "Cocoa",
        "-framework", "WebKit",
        swift_src,
    ]
    print("Compiling native WKWebView host...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        if os.path.exists(bridge_exe) and not os.path.exists(python_exe):
            os.rename(bridge_exe, python_exe)
        print("Swift compile failed.")
        return False

    os.chmod(python_exe, os.stat(python_exe).st_mode | stat.S_IEXEC)
    os.chmod(bridge_exe, os.stat(bridge_exe).st_mode | stat.S_IEXEC)
    print(f"Native window host: {python_exe}")
    print(f"UI server:          {bridge_exe}")
    return True


def build_app() -> None:
    check_dependencies()
    if sys.platform != "darwin":
        print("This builder produces a macOS .app. Run it on a Mac.")
        sys.exit(1)

    swift_ok = _swiftc() is not None
    pyobjc_ok = _has_pyobjc()
    if not swift_ok and not pyobjc_ok:
        print("Need Xcode Command Line Tools (swiftc) to build the native window.")
        print("Run: xcode-select --install")
        print("Then install PyObjC as a fallback: pip install pyobjc-framework-Cocoa pyobjc-framework-WebKit")
        sys.exit(1)

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
        "setuptools",
        "journal",
        "cluny_sync",
        "insights",
        "timeline",
        "work",
        "workouts",
        "export_data",
        "daily_checklist",
        "reminders",
        "health_import",
        "appearance",
        "bridge",
        "paths",
        "native_mac",
        "proxy_tools",
        "packaging",
        "bottle_websocket",
        "greenlet",
        "objc",
        "objc._objc",
        "AppKit",
        "Foundation",
        "WebKit",
        "CoreFoundation",
        "PyObjCTools",
        "PyObjCTools.AppHelper",
    ]

    args = [
        "main.py",
        "--name=Kosistenz",
        "--windowed",
        "--onedir",
        "--add-data=web:web",
        "--add-data=checklists:checklists",
        "--add-data=macos/kosistenz-reminder.sh:macos",
        "--collect-all=eel",
        "--collect-all=gevent",
        "--collect-all=bottle",
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

    used_swift = _install_swift_host(app_path)
    if not used_swift and not pyobjc_ok:
        print("Could not compile the native window, and PyObjC is not installed.")
        sys.exit(1)
    if used_swift:
        print("Window host: Swift WKWebView (Python only serves the UI).")
    else:
        print("Window host: Python PyObjC WKWebView fallback.")

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
        info["CFBundleExecutable"] = "Kosistenz"
        info["CFBundlePackageType"] = "APPL"
        info["LSApplicationCategoryType"] = "public.app-category.productivity"
        info["NSHighResolutionCapable"] = True
        info["NSRequiresAquaSystemAppearance"] = False
        info["LSMinimumSystemVersion"] = "11.0"
        info["NSPrincipalClass"] = "NSApplication"
        info["NSAppTransportSecurity"] = {
            "NSAllowsLocalNetworking": True,
            "NSAllowsArbitraryLoads": False,
        }
        with open(plist_path, "wb") as handle:
            plistlib.dump(info, handle)
    except Exception as exc:
        print(f"Could not patch Info.plist: {exc}")


if __name__ == "__main__":
    build_app()
