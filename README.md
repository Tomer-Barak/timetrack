# TimeTrack – Working Hours Tracker

A Progressive Web App (PWA) built with Flask and SQLite to track working hours across different categories (Counseling, Infrastructure, etc.).

## Features

- **Timer Dashboard**: Real-time clock with start/stop functionality.
- **PWA Ready**: Installable on mobile devices (Android/iOS) and desktop.
- **Statistics**: View daily, weekly, and monthly totals with category breakdowns.
- **Manual Entries**: Add or edit entries if you forgot to start the timer.
- **Dark Theme**: Sleek, modern interface using glassmorphism aesthetics.
- **Goal Tracking**: Monitor progress towards monthly targets (e.g., 80 hours/month).

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
