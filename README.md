# TimeTrack – Working Hours Tracker

A Progressive Web App (PWA) built with Flask and SQLite to track working hours across consulting, infrastructure, combined consulting + infrastructure, HUJI, and a separate Stefano engagement.

## Features

- **Time Log**: Homepage for adding, editing, and reviewing entries.
- **PWA Ready**: Installable on mobile devices (Android/iOS) and desktop.
- **Statistics**: View daily, weekly, and monthly totals with category breakdowns.
- **Professional UI**: Light, restrained interface for quick operational use.
- **Goal Tracking**: Monitor progress towards the 160-hour full-time monthly goal and a 50/50 consulting/infrastructure split (combined hours count half to each side).
- **Per-Org Targets**: Separate progress bars for ELSC (110h) and HUJI (50h), drawn on one shared hour scale.
- **Workday Pace**: Compare logged hours with the 160-hour goal prorated across Sunday-Thursday workdays.
- **Separate Stefano Tracking**: Track Stefano work against a one-time 32-hour cap, excluded from monthly goals and exports, with its own all-time report.

The app has two pages, Log and Stats. Titles and categories are fixed configuration
in `database.py`; they are changed there rather than through the UI.

## Tech Stack

- **Backend**: Python (Flask)
- **Database**: SQLite
- **Frontend**: HTML5, Vanilla CSS, JS
- **Icons**: Custom generated PWA icons
- **Server**: Nginx (Reverse Proxy), Systemd (Service Management)

## Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Tomer-Barak/timetrack.git
   cd timetrack
   ```

2. **Setup virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Run the app**:
   ```bash
   python3 app.py
   ```

## Repository Structure

- `app.py`: Main Flask application.
- `database.py`: SQLite interaction layer.
- `static/`: CSS, manifest, service worker, and icons.
- `templates/`: Jinja2 HTML templates (`base`, `log`, `stats`).
- `tests/`: Unit tests for pace, split, naming, and per-org progress.
- `venv/`: Virtual environment (ignored by git).
