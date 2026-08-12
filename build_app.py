"""
Build Script for Creating Mac Application

Uses PyInstaller to create a standalone macOS .app bundle.
The resulting app will be in the 'dist' folder.
"""

import PyInstaller.__main__
import os
import shutil
import sys


def check_dependencies():
    """Verify all required dependencies are installed"""
    required_modules = ["eel", "setuptools"]
    missing = []

    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)

    if missing:
        print(f"\n❌ Missing dependencies: {', '.join(missing)}")
        print("\nPlease install dependencies first:")
        print("  pip install -r requirements.txt")
        sys.exit(1)

    try:
        import checkin_github
        import daily_checklist
        import journal
        import cluny_sync

        print("✅ All dependencies and modules verified!")
    except ImportError as e:
        print(f"\n❌ Error importing modules: {e}")
        sys.exit(1)


def build_app():
    """Build the Mac application using PyInstaller"""

    print("🔍 Checking dependencies...")
    check_dependencies()

    print("\n🧹 Cleaning previous builds...")
    if os.path.exists("build"):
        shutil.rmtree("build")
    if os.path.exists("dist"):
        shutil.rmtree("dist")

    print("🔨 Building Mac application...")
    print("   This may take a few minutes...")

    icon_path = "app_icon.icns"
    icon_arg = []
    if os.path.exists("app_icon.png"):
        print("   Regenerating icon from PNG...")
        try:
            if os.path.exists(icon_path):
                os.remove(icon_path)
            if os.path.exists("app_icon.iconset"):
                shutil.rmtree("app_icon.iconset")

            os.makedirs("app_icon.iconset", exist_ok=True)

            import subprocess

            sizes = [16, 32, 128, 256, 512]
            for size in sizes:
                subprocess.run(
                    [
                        "sips",
                        "-z",
                        str(size),
                        str(size),
                        "app_icon.png",
                        "--out",
                        f"app_icon.iconset/icon_{size}x{size}.png",
                    ],
                    check=False,
                    capture_output=True,
                )
                subprocess.run(
                    [
                        "sips",
                        "-z",
                        str(size * 2),
                        str(size * 2),
                        "app_icon.png",
                        "--out",
                        f"app_icon.iconset/icon_{size}x{size}@2x.png",
                    ],
                    check=False,
                    capture_output=True,
                )

            subprocess.run(
                ["iconutil", "-c", "icns", "app_icon.iconset", "-o", icon_path],
                check=False,
                capture_output=True,
            )

            if os.path.exists("app_icon.iconset"):
                shutil.rmtree("app_icon.iconset")

            if os.path.exists(icon_path):
                icon_arg = [f"--icon={icon_path}"]
                print(f"   ✅ Icon regenerated: {icon_path}")
            else:
                print("   ⚠️  Icon generation failed - app will use default icon")
        except Exception as e:
            print(f"   ⚠️  Error regenerating icon: {e}")
            if os.path.exists(icon_path):
                icon_arg = [f"--icon={icon_path}"]
    elif os.path.exists(icon_path):
        icon_arg = [f"--icon={icon_path}"]
        print(f"   Using existing icon: {icon_path}")
    else:
        print("   ⚠️  No icon found - app will use default icon")

    args = [
        "main.py",
        "--name=Kosistenz",
        "--windowed",
        "--onedir",
        "--add-data=web:web",
        "--add-data=checklists:checklists",
        "--hidden-import=eel",
        "--hidden-import=setuptools",
        "--hidden-import=checkin_github",
        "--hidden-import=daily_checklist",
        "--hidden-import=journal",
        "--hidden-import=cluny_sync",
        "--hidden-import=insights",
        "--hidden-import=timeline",
        "--hidden-import=export_data",
        "--hidden-import=recovery",
        "--hidden-import=reminders",
        "--hidden-import=health_import",
        "--hidden-import=appearance",
        "--collect-all=eel",
        "--osx-bundle-identifier=com.kosistenz.app",
        "--noconfirm",
    ] + icon_arg

    try:
        PyInstaller.__main__.run(args)

        app_path = None
        if os.path.exists("dist/Kosistenz.app"):
            app_path = "dist/Kosistenz.app"
        elif os.path.exists("dist/Kosistenz/Kosistenz.app"):
            app_path = "dist/Kosistenz/Kosistenz.app"

        if not app_path:
            print("\n⚠️  Warning: Could not find built app in expected location")
            return

        print("\n" + "=" * 50)
        print("✅ Build complete!")
        print("=" * 50)
        print("📦 Your app is located at:")
        print(f"   {os.path.abspath(app_path)}")

        applications_path = "/Applications/Kosistenz.app"
        print(f"\n📋 Copying to Applications folder...")

        try:
            if os.path.exists(applications_path):
                shutil.rmtree(applications_path)
                print("   Removed old app from Applications")

            shutil.copytree(app_path, applications_path)
            print(f"   ✅ Successfully copied to: {applications_path}")

        except PermissionError:
            print("   ⚠️  Permission denied. Copy manually if needed.")
            print(f"   cp -R {app_path} /Applications/")
        except Exception as e:
            print(f"   ⚠️  Error copying to Applications: {e}")

        print("\n🚀 Build finished.")
        print("=" * 50)

    except Exception as e:
        print(f"\n❌ Build failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    build_app()
