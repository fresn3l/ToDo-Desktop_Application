# Kosistenz

A to-do list and calendar for Mac. Data stays on this computer.

The app is a real `Kosistenz.app`: native traffic-light window, Dock / Spotlight, menu bar, and a Notification Center widget. It uses Apple WebKit. Chrome is not used.

## Install on a Mac

### What you need

- A Mac (macOS 11+)
- Python 3.8+ (`python3 --version`)
- Xcode Command Line Tools (`xcode-select --install`) so the installer can compile the native window

### Build and install

```bash
git clone https://github.com/fresn3l/ToDo-Desktop_Application.git
cd ToDo-Desktop_Application
git checkout main
chmod +x setup_venv.sh macos/install_app.sh
./macos/install_app.sh
```

That creates a virtualenv, packages a standalone app, and copies it to `/Applications/Kosistenz.app`. Finder then reveals the app. If `/Applications` is not writable, it falls back to `~/Applications`.

### Open it

1. Double-click **Kosistenz**.
2. First launch: **right-click → Open** if macOS warns about an unidentified developer.
3. Quit with **Cmd+Q**. Closing the window hides the app; the menu bar extra keeps running until you quit.

The menu bar parks a to-do and shows the next meeting. The Today widget lists open to-dos and that meeting. Services: select text anywhere, then Services → **Park in To Do**. URL: `kosistenz://work/park?title=Call%20dentist` (add `&today=1` to put it on Today).

Rebuild with `./macos/install_app.sh` after you change the source.

If launch fails, paste `~/Library/Logs/Kosistenz.log`. A good start looks like `Swift host launching`, then `UI server ready`.

### Run from the repo

```bash
./setup_venv.sh
./run_kosistenz.sh
```

That still opens the native WebKit window.

## What it is

- **Today**: Now, Next, and Later today. Now is the meeting or placed to-do you are in, or the next one and how long until it. One line captures a to-do: `Call Priya fri 25m` or `Standup 14:30`.
- **To Do**: the same line. `fri`, `25m`, `14:30`, `today`, `later`, and a trailing `park` set themselves. This week, Today, and Park decide when the line does not. Each item can have notes, a due date, an estimate, and a repeat.
- **Calendar**: day, week, month, and year. Add a meeting, or draw a work block (protected time Fill week will not pack over). Drag a to-do onto a time, or use **Fill week** to pack items that have an estimate into gaps inside the awake window. A due chip shows the calendar it came from.
- **Settings**: appearance, subscribed calendars, and the iPhone pack.

Subscribed calendars: timed events are meetings and block the clock. All-day events and short 11:59 stubs become due dates. Import from Apple Calendar skips holiday and birthday calendars. Nothing is written back.

## iPhone

Today, Calendar, and To Do over the same iCloud Drive pack. See `ios/README.md`.

## Data

macOS paths (the legacy `ToDo` folder name is kept so existing data still opens):

- **Work / To Do**: `~/Library/Application Support/ToDo/work_items.sqlite`
- **Calendar**: `~/Library/Application Support/ToDo/calendar.sqlite` plus `calendar_feeds.json`
- **Widget snapshot**: `~/Library/Application Support/ToDo/widget_snapshot.json`
- **Appearance**: `~/Library/Application Support/ToDo/appearance.json`

Older files from journal, workouts, and check-ins are left on disk. This app does not open them.

## Technologies

- **Python 3** + **Eel** (localhost bridge) and a 127.0.0.1 API for the menu bar and widget
- **Swift + WKWebView** for the Mac window
- **WidgetKit** for the Today widget
- **SQLite** for to-dos and the calendar
- **PyInstaller** for the standalone `.app`
- **SwiftUI** iPhone companion (`ios/`) synced through iCloud Drive

## License

This project is available for portfolio and demonstration purposes.
