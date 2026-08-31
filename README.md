# Kosistenz

Journal and daily checklist for Mac. Data stays on this computer.

The app is a real `Kosistenz.app`: native traffic-light window, Dock / Spotlight, menu bar, Notification Center widget, Apple WebKit (Safari engine). **Chrome is not used.**

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
git checkout main
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

Quit with **Cmd+Q**, like any Mac app. Closing the window hides it; the menu bar extra keeps running until you quit.

Add the **Today** widget from Notification Center → Edit Widgets → Kosistenz (Lock Screen families need macOS 14+). Services: select text anywhere, then Services → **Park in All Work** or **New Journal Entry in Kosistenz**. URLs: `kosistenz://journal/new` and `kosistenz://work/park?title=Call%20dentist`.

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
- **To Do**: Dated tasks with start / finish timers
- **All Work**: Undated backlog you assign to a day later
- **Workout**: Body weight, session types, and a simple week template (expected days only)
- **Analytics**: Streaks, repeating to-do misses, template misses, body-weight sparkline
- **Menu bar**: Start or finish today’s active to do, log a session type, see whether today is empty
- **Today widget**: Notification Center (and Lock Screen on macOS 14+) — open to-dos, workout logged or not, journal streak
- **Spotlight / Services**: `kosistenz://journal/new`, `kosistenz://work/park?title=…`, plus **New Journal Entry** and **Park in All Work** in the Services menu
- **Appearance**: Themes and type (San Francisco by default on Mac)
- **Local storage**: SQLite + JSON under Application Support
- **Goals**: 1 week, 6 months, a year, 5 years. Attach a to-do (or match a
  keyword). 1-week goals get a to-do every Sunday for the coming week.
- **Calendar**: Week on a clock. Lectures you add stay hard. Class due-date
  calendars (Apple subscription or ICS URL) become to-dos with due times, not
  busy bars. **Fill week** places study around class. Nothing is written back
  to Apple Calendar.
- **iPhone (in progress)**: same Apple ID, JSON pack in iCloud Drive / Kosistenz — see `docs/iphone-sprint.md` and `ios/`

## Data Storage

macOS paths (legacy `ToDo` folder name preserved for existing data):

- **Journal**: `~/Library/Application Support/ToDo/Journal/`
- **Daily checklist DB**: `~/Library/Application Support/ToDo/daily_checklist.sqlite`
- **Work / To Do DB**: `~/Library/Application Support/ToDo/work_items.sqlite`
- **Calendar**: `~/Library/Application Support/ToDo/calendar.sqlite` plus `calendar_feeds.json`
- **Workouts DB**: `~/Library/Application Support/ToDo/workouts.sqlite`
- **Week template**: `~/Library/Application Support/ToDo/workout_plan.json`
- **Widget snapshot** (Today widget + menu bar): `~/Library/Application Support/ToDo/widget_snapshot.json`
- **Custom checklist items**: `~/Library/Application Support/ToDo/checklist_custom_items.json`
- **Active checklist template**: `~/Library/Application Support/ToDo/checklist_selected_stem.txt`
- **Appearance**: `~/Library/Application Support/ToDo/appearance.json`

Optional Cluny sync: set `CLUNY_SQLITE_PATH` or `CLUNY_INGEST_URL` (see `cluny_sync.py`).
Cluny is the local brain, not the scheduler — [docs/cluny-integration.md](docs/cluny-integration.md).

## Technologies

- **Python 3** + **Eel** (localhost bridge) and a 127.0.0.1 API for the menu bar / widget
- **Swift + WKWebView** for the Mac window (Safari engine; no Chrome)
- **WidgetKit** for the Notification Center / Lock Screen Today widget
- **SQLite** for checklist submissions and work items
- **PyInstaller** for the standalone `.app`
- **SwiftUI** iPhone companion (`ios/`) synced through iCloud Drive

## License

This project is available for portfolio and demonstration purposes.
