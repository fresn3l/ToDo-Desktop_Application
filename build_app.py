"""
Build Script for Creating Mac Application

This script uses PyInstaller to create a standalone Mac .app bundle.

Usage:
    python build_app.py

IMPORTANT: Make sure you're in your virtual environment before running!
    source venv/bin/activate  # or source .venv/bin/activate

The resulting .app will be in the 'dist' folder.

What this script does:
1. Verifies all dependencies are installed
2. Cleans previous build artifacts
3. Runs PyInstaller with optimized settings for Mac
4. Creates a standalone .app bundle that includes:
   - Python interpreter
   - All dependencies (Eel, etc.)
   - Your application code
   - Web files (HTML, CSS, JavaScript)
5. The app can run without Python installed!
"""

import PyInstaller.__main__
import os
import shutil
import sys

def check_dependencies():
    """Verify all required dependencies are installed"""
    required_modules = ['eel', 'setuptools']
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
        print("\nOr activate your virtual environment and install:")
        print("  source venv/bin/activate")
        print("  pip install -r requirements.txt")
        sys.exit(1)
    
    # Check if our modules can be imported
    try:
        import todo
        import goals
        import analytics
        import data_storage
        print("✅ All dependencies and modules verified!")
    except ImportError as e:
        print(f"\n❌ Error importing modules: {e}")
        print("Make sure all Python files are in the project directory.")
        sys.exit(1)

def build_app():
    """Build the Mac application using PyInstaller"""
    
    print("🔍 Checking dependencies...")
    check_dependencies()
    
    print("\n🧹 Cleaning previous builds...")
    # Clean previous builds
    if os.path.exists('build'):
        shutil.rmtree('build')
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    
    print("🔨 Building Mac application...")
    print("   This may take a few minutes...")
    
    # Regenerate icon from PNG to ensure it matches this branch's icon
    icon_path = 'app_icon.icns'
    icon_arg = []
    if os.path.exists('app_icon.png'):
        print("   Regenerating icon from PNG...")
        try:
            # Remove old icon if it exists
            if os.path.exists(icon_path):
                os.remove(icon_path)
            if os.path.exists('app_icon.iconset'):
                shutil.rmtree('app_icon.iconset')
            
            # Create iconset directory
            os.makedirs('app_icon.iconset', exist_ok=True)
            
            # Generate all required icon sizes
            import subprocess
            sizes = [16, 32, 128, 256, 512]
            for size in sizes:
                subprocess.run(['sips', '-z', str(size), str(size), 'app_icon.png', 
                              f'--out', f'app_icon.iconset/icon_{size}x{size}.png'], 
                             check=False, capture_output=True)
                subprocess.run(['sips', '-z', str(size*2), str(size*2), 'app_icon.png', 
                              f'--out', f'app_icon.iconset/icon_{size}x{size}@2x.png'], 
                             check=False, capture_output=True)
            
            # Convert iconset to icns
            subprocess.run(['iconutil', '-c', 'icns', 'app_icon.iconset', '-o', icon_path], 
                         check=False, capture_output=True)
            
            # Clean up iconset
            if os.path.exists('app_icon.iconset'):
                shutil.rmtree('app_icon.iconset')
            
            if os.path.exists(icon_path):
                icon_arg = [f'--icon={icon_path}']
                print(f"   ✅ Icon regenerated: {icon_path}")
            else:
                print("   ⚠️  Icon generation failed - app will use default icon")
        except Exception as e:
            print(f"   ⚠️  Error regenerating icon: {e}")
            if os.path.exists(icon_path):
                icon_arg = [f'--icon={icon_path}']
                print(f"   Using existing icon: {icon_path}")
            else:
                print("   ⚠️  No icon found - app will use default icon")
    elif os.path.exists(icon_path):
        icon_arg = [f'--icon={icon_path}']
        print(f"   Using existing icon: {icon_path}")
    else:
        print("   ⚠️  No icon found (app_icon.png or app_icon.icns) - app will use default icon")
    
    # PyInstaller arguments
    # Note: --onedir is better for Mac than --onefile (faster startup, easier debugging)
    args = [
        'main.py',                          # Main script to package
        '--name=ToDo',      # App name (will be ToDo.app)
        '--windowed',                       # No console window (GUI only)
        '--onedir',                         # Create directory with dependencies (better for Mac)
        '--add-data=web:web',               # Include web folder (format: source:destination)
        '--hidden-import=eel',              # Ensure Eel is included
        '--hidden-import=setuptools',       # Ensure setuptools is included
        '--hidden-import=todo',            # Include our custom modules
        '--hidden-import=goals',
        '--hidden-import=analytics',
        '--hidden-import=journal',
        '--hidden-import=data_storage',
        '--collect-all=eel',                # Collect all Eel data files
        '--osx-bundle-identifier=com.todo.app',  # Mac bundle identifier
        '--noconfirm',                      # Overwrite output without asking
    ] + icon_arg  # Add icon if it exists
    
    try:
        PyInstaller.__main__.run(args)
        
        # Find the built app (could be in dist/ToDo.app or dist/ToDo/ToDo.app)
        app_path = None
        if os.path.exists('dist/ToDo.app'):
            app_path = 'dist/ToDo.app'
        elif os.path.exists('dist/ToDo/ToDo.app'):
            app_path = 'dist/ToDo/ToDo.app'
        
        if not app_path:
            print("\n⚠️  Warning: Could not find built app in expected location")
            return
        
        print("\n" + "="*50)
        print("✅ Build complete!")
        print("="*50)
        print(f"📦 Your app is located at:")
        if app_path:
            print(f"   {os.path.abspath(app_path)}")
        
        # Automatically copy to Applications folder
        applications_path = '/Applications/ToDo.app'
        print(f"\n📋 Copying to Applications folder...")
        
        try:
            # Remove old app if it exists
            if os.path.exists(applications_path):
                shutil.rmtree(applications_path)
                print("   Removed old app from Applications")
            
            # Copy new app
            shutil.copytree(app_path, applications_path)
            print(f"   ✅ Successfully copied to: {applications_path}")
            
        except PermissionError:
            print("   ⚠️  Permission denied. You may need to run with sudo or copy manually.")
            print(f"   You can copy it manually: cp -R {app_path} /Applications/")
        except Exception as e:
            print(f"   ⚠️  Error copying to Applications: {e}")
            print(f"   You can copy it manually: cp -R {app_path} /Applications/")
        
        print("\n🚀 Your app is ready to use!")
        print("   - Find it in Applications folder")
        print("   - Or use Spotlight (Cmd + Space)")
        print("="*50)
        
    except Exception as e:
        print(f"\n❌ Build failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure PyInstaller is installed: pip install pyinstaller")
        print("2. Make sure you're in the project directory")
        print("3. Check that all dependencies are installed: pip install -r requirements.txt")
        sys.exit(1)

if __name__ == '__main__':
    build_app()

