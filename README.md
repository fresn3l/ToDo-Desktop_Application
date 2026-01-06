# ToDo Application

A modern desktop task management application built with Python (Eel) and web technologies. Features task management, goal tracking, analytics, journaling, and email notifications.

## Features

- **Task Management**: Create, edit, delete, and complete tasks with priorities and due dates
- **Recurring Tasks**: Set up daily, weekly, monthly, or yearly recurring tasks
- **Goal Tracking**: Link tasks to goals and track progress with time-based goals
- **Analytics Dashboard**: Comprehensive statistics and visualizations
- **Journal**: Time-tracked journal entries with weekly organization
- **Email Notifications**: Automated reminders for tasks due within 24 hours
- **Modern UI**: Glassmorphism design with smooth animations

## Installation

### Prerequisites

- Python 3.8+
- pip

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd intelligent_to-do_list
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Development Mode

Run the application:
```bash
python main.py
```

### Building a Standalone Application

To create a standalone macOS application:

1. Install PyInstaller (if not already installed):
```bash
pip install pyinstaller
```

2. Build the app:
```bash
python build_app.py
```

3. Find your app:
   - Location: `dist/ToDo.app`
   - Double-click to run

## Project Structure

```
intelligent_to-do_list/
├── main.py              # Application entry point
├── todo.py              # Task management module
├── goals.py             # Goal management module
├── analytics.py         # Analytics and statistics
├── journal.py           # Journal entry management
├── notifications.py      # Email notification system
├── data_storage.py      # Data persistence layer
├── build_app.py         # Build script for standalone app
├── requirements.txt     # Python dependencies
├── web/
│   ├── index.html       # Main HTML file
│   ├── style.css        # Styling
│   ├── app.js           # Application initialization
│   └── js/              # Modular JavaScript files
│       ├── tasks.js     # Task management logic
│       ├── goals.js     # Goal management logic
│       ├── analytics.js # Analytics rendering
│       ├── journal.js    # Journal functionality
│       ├── notifications.js # Notification settings
│       ├── tabs.js      # Tab navigation
│       ├── events.js    # Event listeners
│       ├── state.js     # State management
│       ├── ui.js        # UI utilities
│       └── utils.js     # Utility functions
└── README.md
```

## Data Storage

All data is stored locally in platform-specific Application Support directories:
- **macOS**: `~/Library/Application Support/ToDo/`
- **Windows**: `~/AppData/Local/ToDo/`
- **Linux**: `~/.local/share/ToDo/`

Data files:
- `tasks.json`: All tasks
- `goals.json`: All goals
- `Journal/`: Journal entries organized by year/month/week

## Technologies

- **Python 3**: Backend logic
- **Eel**: Desktop app framework (Python-JavaScript bridge)
- **HTML/CSS/JavaScript**: Frontend interface
- **JSON**: Local data storage
- **PyInstaller**: Application packaging

## License

This project is available for portfolio and demonstration purposes.
