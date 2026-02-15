"""
SQLite database layer for the Time Tracker app.
Stores time entries with title, start, end timestamps.
"""

import sqlite3
import os
from datetime import datetime, timedelta
from contextlib import contextmanager

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'timetrack.db')


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create tables if they don't exist."""
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS titles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL DEFAULT 'other',
                color TEXT NOT NULL DEFAULT '#6366f1',
                created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS time_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title_id INTEGER NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (title_id) REFERENCES titles(id) ON DELETE CASCADE
            )
        ''')
        # Seed default titles if empty
        cursor = conn.execute("SELECT COUNT(*) FROM titles")
        if cursor.fetchone()[0] == 0:
            defaults = [
                ('Counseling', 'counseling', '#8b5cf6'),
                ('Infrastructure', 'development', '#06b6d4'),
            ]
            conn.executemany(
                "INSERT INTO titles (name, category, color) VALUES (?, ?, ?)",
                defaults
            )


# ── Title CRUD ──────────────────────────────────────────────

def get_titles():
    """Return all titles."""
    with get_db() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM titles ORDER BY category, name"
        ).fetchall()]


def add_title(name, category, color='#6366f1'):
    """Add a new title."""
    with get_db() as conn:
        conn.execute(
            "INSERT INTO titles (name, category, color) VALUES (?, ?, ?)",
            (name, category, color)
        )


def update_title(title_id, name, category, color):
    """Update a title."""
    with get_db() as conn:
        conn.execute(
            "UPDATE titles SET name=?, category=?, color=? WHERE id=?",
            (name, category, color, title_id)
        )


def delete_title(title_id):
    """Delete a title and its entries."""
    with get_db() as conn:
        conn.execute("DELETE FROM titles WHERE id=?", (title_id,))


# ── Time Entry CRUD ────────────────────────────────────────

def get_active_entry():
    """Return the currently running entry, if any."""
    with get_db() as conn:
        row = conn.execute('''
            SELECT te.*, t.name as title_name, t.category, t.color
            FROM time_entries te
            JOIN titles t ON te.title_id = t.id
            WHERE te.end_time IS NULL
            ORDER BY te.start_time DESC LIMIT 1
        ''').fetchone()
        return dict(row) if row else None


def start_entry(title_id):
    """Start a new time entry. Stops any running entry first."""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with get_db() as conn:
        # Stop any running entries
        conn.execute(
            "UPDATE time_entries SET end_time=? WHERE end_time IS NULL",
            (now,)
        )
        conn.execute(
            "INSERT INTO time_entries (title_id, start_time) VALUES (?, ?)",
            (title_id, now)
        )


def stop_entry():
    """Stop the currently running entry."""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with get_db() as conn:
        conn.execute(
            "UPDATE time_entries SET end_time=? WHERE end_time IS NULL",
            (now,)
        )


def update_entry(entry_id, title_id, start_time, end_time):
    """Update an existing time entry."""
    with get_db() as conn:
        conn.execute(
            "UPDATE time_entries SET title_id=?, start_time=?, end_time=? WHERE id=?",
            (title_id, start_time, end_time, entry_id)
        )


def delete_entry(entry_id):
    """Delete a time entry."""
    with get_db() as conn:
        conn.execute("DELETE FROM time_entries WHERE id=?", (entry_id,))


def clear_all_entries():
    """Delete ALL time entries (reset stats). Titles are kept."""
    with get_db() as conn:
        conn.execute("DELETE FROM time_entries")


def add_manual_entry(title_id, start_time, end_time):
    """Add a manual time entry."""
    with get_db() as conn:
        conn.execute(
            "INSERT INTO time_entries (title_id, start_time, end_time) VALUES (?, ?, ?)",
            (title_id, start_time, end_time)
        )


def get_entries(start_date=None, end_date=None, title_id=None):
    """
    Get time entries with optional date and title filtering.
    Only returns completed entries (with end_time).
    """
    query = '''
        SELECT te.*, t.name as title_name, t.category, t.color
        FROM time_entries te
        JOIN titles t ON te.title_id = t.id
        WHERE te.end_time IS NOT NULL
    '''
    params = []
    if start_date:
        query += " AND te.start_time >= ?"
        params.append(start_date)
    if end_date:
        query += " AND te.start_time < ?"
        params.append(end_date)
    if title_id:
        query += " AND te.title_id = ?"
        params.append(title_id)
    query += " ORDER BY te.start_time DESC"
    with get_db() as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]


def get_recent_entries(limit=50):
    """Get the most recent entries for the log view."""
    with get_db() as conn:
        return [dict(r) for r in conn.execute('''
            SELECT te.*, t.name as title_name, t.category, t.color
            FROM time_entries te
            JOIN titles t ON te.title_id = t.id
            WHERE te.end_time IS NOT NULL
            ORDER BY te.start_time DESC
            LIMIT ?
        ''', (limit,)).fetchall()]


# ── Statistics helpers ──────────────────────────────────────

def _calc_hours(entries):
    """Sum hours for a list of entries."""
    total = 0.0
    for e in entries:
        if e['end_time']:
            start = datetime.strptime(e['start_time'], '%Y-%m-%d %H:%M:%S')
            end = datetime.strptime(e['end_time'], '%Y-%m-%d %H:%M:%S')
            total += (end - start).total_seconds() / 3600
    return round(total, 2)


def _get_israeli_week_range(dt=None):
    """Return (sunday, next_sunday) for the Israeli week containing dt."""
    if dt is None:
        dt = datetime.now()
    # Python weekday: Monday=0 ... Sunday=6
    # Israeli week starts on Sunday
    days_since_sunday = (dt.weekday() + 1) % 7
    sunday = dt - timedelta(days=days_since_sunday)
    sunday = sunday.replace(hour=0, minute=0, second=0, microsecond=0)
    next_sunday = sunday + timedelta(days=7)
    return sunday, next_sunday


def _get_month_range(dt=None):
    """Return (first_of_month, first_of_next_month)."""
    if dt is None:
        dt = datetime.now()
    first = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if first.month == 12:
        next_first = first.replace(year=first.year + 1, month=1)
    else:
        next_first = first.replace(month=first.month + 1)
    return first, next_first


def get_stats():
    """
    Return aggregated stats: today, this week, this month, total – 
    broken down by category and overall.
    """
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')
    today_end = (now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
    week_start, week_end = _get_israeli_week_range(now)
    month_start, month_end = _get_month_range(now)

    periods = {
        'today': (today_start, today_end),
        'week': (week_start.strftime('%Y-%m-%d %H:%M:%S'), week_end.strftime('%Y-%m-%d %H:%M:%S')),
        'month': (month_start.strftime('%Y-%m-%d %H:%M:%S'), month_end.strftime('%Y-%m-%d %H:%M:%S')),
        'total': (None, None),
    }

    stats = {}
    for period_name, (sd, ed) in periods.items():
        entries = get_entries(start_date=sd, end_date=ed)
        # Overall
        total_hours = _calc_hours(entries)
        # By category
        cats = {}
        for e in entries:
            cat = e['category']
            if cat not in cats:
                cats[cat] = []
            cats[cat].append(e)
        by_category = {cat: _calc_hours(ents) for cat, ents in cats.items()}
        # By title
        titles_map = {}
        for e in entries:
            tname = e['title_name']
            if tname not in titles_map:
                titles_map[tname] = {'entries': [], 'category': e['category'], 'color': e['color']}
            titles_map[tname]['entries'].append(e)
        by_title = {
            tname: {
                'hours': _calc_hours(info['entries']),
                'category': info['category'],
                'color': info['color'],
            }
            for tname, info in titles_map.items()
        }
        stats[period_name] = {
            'total': total_hours,
            'by_category': by_category,
            'by_title': by_title,
        }

    return stats
