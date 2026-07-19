# TimeTrack – Working Hours Tracker

A Progressive Web App (PWA) built with Flask and SQLite to track working hours across consulting, infrastructure, and combined consulting + infrastructure work.

## Features

- **Time Log**: Homepage for adding, editing, and reviewing manual entries.
- **Timer Dashboard**: Real-time clock with start/stop functionality.
- **PWA Ready**: Installable on mobile devices (Android/iOS) and desktop.
- **Statistics**: View daily, weekly, and monthly totals with category breakdowns.
- **Manual Entries**: Add or edit entries if you forgot to start the timer.
- **Professional UI**: Light, restrained interface for quick operational use.
- **Goal Tracking**: Monitor progress towards a 160-hour monthly scale and a 50/50 consulting/infrastructure split.
- **Workday Pace**: Compare logged hours with the 120-hour scope prorated across Sunday-Thursday workdays.

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
- `templates/`: Jinja2 HTML templates.
- `venv/`: Virtual environment (ignored by git).
