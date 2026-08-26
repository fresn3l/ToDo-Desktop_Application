# Kosistenz

Journal and daily checklist for Mac. Data stays on this computer.

The app is a real `Kosistenz.app`: native traffic-light window, Dock / Spotlight, Apple WebKit (Safari engine). **Chrome is not used.**

## Install on a Mac

### What you need

- A Mac (macOS 11+)
- Python 3.8+ (`python3 --version`)
- Xcode Command Line Tools (`xcode-select --install`) so the installer can compile the native window

You do **not** need Google Chrome.

### Build and install

```bash
git clone https://github.com/fresn3l/ToDo-Desktop_Application.git
cd ToDo-Desktop_Application
git checkout cursor/native-macos-app-7484
chmod +x setup_venv.sh macos/install_app.sh
./macos/install_app.sh
```

That creates a virtualenv, packages a standalone app, and copies it to:

`/Applications/Kosistenz.app`

Finder then reveals the app so you can double-click it. If `/Applications` is not writable, it falls back to `~/Applications`.

### Open it

1. Finder should jump to **Kosistenz** after install. Double-click it.
2. Or Finder sidebar → **Applications** → **Kosistenz**
3. First launch: **right-click → Open** if macOS warns about an unidentified developer
4. Optional: drag Kosistenz to the Dock, or use Spotlight (`Cmd+Space`)

Quit with **Cmd+Q**, like any Mac app.

If you change the source and want a fresh bundle, run `./macos/install_app.sh` again. You must rebuild after `git pull` — opening the old app will still use the previous window code.

If launch fails, paste `~/Library/Logs/Kosistenz.log`. A good start looks like `Swift host launching`, then `UI server ready`.

### Run from the repo (optional)

For day-to-day coding without rebuilding the `.app`:

```bash
./setup_venv.sh
./run_kosistenz.sh
```

That still opens the **native WebKit window**, not Chrome.

## Features

- **Journal**: Timed entries
- **Daily checklist**: Branching morning / evening / full flows
- **Review + Timeline**: Week strip, streaks, markdown export
- **Appearance**: Themes and type (San Francisco by default on Mac)
- **Local storage**: SQLite + JSON under Application Support

## Data Storage

macOS paths (legacy `ToDo` folder name preserved for existing data):

- **Journal**: `~/Library/Application Support/ToDo/Journal/`
- **Daily checklist DB**: `~/Library/Application Support/ToDo/daily_checklist.sqlite`
- **Custom checklist items**: `~/Library/Application Support/ToDo/checklist_custom_items.json`
- **Active checklist template**: `~/Library/Application Support/ToDo/checklist_selected_stem.txt`
- **Appearance**: `~/Library/Application Support/ToDo/appearance.json`

Optional Cluny sync: set `CLUNY_SQLITE_PATH` or `CLUNY_INGEST_URL` (see `cluny_sync.py`).

## Technologies

- **Python 3** + **Eel** (localhost bridge only)
- **Swift + WKWebView** for the Mac window (Safari engine; no Chrome)
- **SQLite** for checklist submissions
- **PyInstaller** for the standalone `.app`

## License

This project is available for portfolio and demonstration purposes.
