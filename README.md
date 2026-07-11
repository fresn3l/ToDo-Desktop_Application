# Kosistenz

Journal and daily checklist desktop app (Python + Eel). Data stays local on your Mac.

## Features

- **Journal**: Time-tracked entries with optional Cluny sync
- **Daily Checklist**: Branching yes/no and multiple-choice flows from JSON
- **Custom questions**: Add your own checklist items (optional duration step)
- **Templates**: Bundled blank checklist JSON files to copy and edit
- **Local storage**: SQLite + JSON under Application Support

## Installation

### Prerequisites

- Python 3.8+
- Google Chrome (used as the app window)

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd intelligent_to-do_list
```

2. Create the virtualenv and install dependencies:
```bash
./setup_venv.sh
```

## Usage

### Development mode

```bash
./run_kosistenz.sh
# or: python main.py
```

### Dock / one-click launch (recommended)

Same pattern as Cluny: build a small `Kosistenz.app` launcher and install it to your home Applications folder.

```bash
./macos/install_app.sh
```

Then:

1. Open Finder → **Applications** (your home folder, not `/Applications`) → **Kosistenz**
2. **Drag Kosistenz to the Dock**
3. Launch from the Dock or Spotlight (`Cmd+Space`, type "Kosistenz")

The `.app` is a thin wrapper around this repo — it always runs your latest code. If you move the repo, run `./macos/install_app.sh` again.

### Standalone bundle (optional)

For a self-contained PyInstaller app (no repo path required):

```bash
pip install pyinstaller
python build_app.py
```

Output: `dist/Kosistenz.app` (also copied to `/Applications/Kosistenz.app` when permissions allow).

## Project Structure

```
intelligent_to-do_list/
├── main.py                 # Application entry point
├── journal.py              # Journal entries
├── daily_checklist.py      # Checklist flow + SQLite
├── cluny_sync.py           # Optional Cluny journal sync
├── checkin_github.py       # Optional GitHub check-in push
├── run_kosistenz.sh        # Run from repo venv
├── setup_venv.sh           # Create .venv + install deps
├── build_app.py            # PyInstaller standalone build
├── macos/
│   ├── install_app.sh      # Build + install to ~/Applications
│   ├── build_app.sh        # Build Kosistenz.app launcher
│   └── kosistenz-gui       # App executable script
├── checklists/             # Bundled checklist JSON flows
└── web/                    # Frontend (HTML/CSS/JS)
```

## Data Storage

macOS paths (legacy `ToDo` folder name preserved for existing data):

- **Journal**: `~/Library/Application Support/ToDo/Journal/`
- **Daily checklist DB**: `~/Library/Application Support/ToDo/daily_checklist.sqlite`
- **Custom checklist items**: `~/Library/Application Support/ToDo/checklist_custom_items.json`
- **Active checklist template**: `~/Library/Application Support/ToDo/checklist_selected_stem.txt`

Optional Cluny sync: set `CLUNY_SQLITE_PATH` or `CLUNY_INGEST_URL` (see `cluny_sync.py`).

## Technologies

- **Python 3** + **Eel** (Python ↔ JavaScript bridge)
- **SQLite** for checklist submissions
- **HTML/CSS/JavaScript** frontend
- **PyInstaller** (optional standalone build)

## License

This project is available for portfolio and demonstration purposes.
