"""
SQLite database layer for the Time Tracker app.
Stores time entries with title, start, end timestamps.
"""

import sqlite3
import os
from datetime import datetime, timedelta
from contextlib import contextmanager

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'timetrack.db')

# Full-time monthly goal. Tomer moved to a full 160h position in September 2026;
# the previous 120h scope no longer applies.
MONTHLY_TARGET_HOURS = 160

# Stefano is a finite, all-time engagement. Its hours are tracked separately
# from the monthly employment target and stop being "remaining" at this cap.
STEFANO_HOUR_CAP = 32
SEPARATE_REPORT_CATEGORIES = frozenset({'stefano'})

# Under the current agreement HUJI takes a fixed 50h a month and ELSC gets the rest.
HUJI_MONTHLY_TARGET_HOURS = 50

CATEGORY_META = {
    'consulting': {
        'label': 'Consulting',
        'short_label': 'Consulting',
        'color': '#7a3f55',
        'icon': 'comments',
        'org': 'ELSC',
    },
    'infrastructure': {
        'label': 'Infrastructure',
        'short_label': 'Infra',
        'color': '#53646c',
        'icon': 'server',
        'org': 'ELSC',
    },
    'mixed': {
        'label': 'Consulting + Infrastructure',
        'short_label': 'Combined',
        'color': '#8a6a3a',
        'icon': 'layer-group',
        'org': 'ELSC',
    },
    'huji': {
        'label': 'HUJI',
        'short_label': 'HUJI',
        'color': '#3f5f7a',
        'icon': 'graduation-cap',
        'org': 'HUJI',
    },
    'stefano': {
        'label': 'Stefano',
        'short_label': 'Stefano',
        'color': '#6b5b95',
        'icon': 'hourglass-half',
        'org': '',
    },
    'other': {
        'label': 'Other',
        'short_label': 'Other',
        'color': '#7b8794',
        'icon': 'tag',
        'org': '',
    },
}
ORDERED_CATEGORIES = ('consulting', 'infrastructure', 'mixed', 'huji', 'stefano', 'other')

# Category keys used before the September 2026 rename, mapped to their replacement.
# Both were renamed to match the labels the UI had always shown for them.
LEGACY_CATEGORIES = {
    'counseling': 'consulting',
    'development': 'infrastructure',
}
# Full names of the orgs behind the category `org` tags, used in the report header.
ORG_NAMES = {
    'ELSC': 'Edmond and Lily Safra Center for Brain Sciences',
    'HUJI': 'the Hebrew University of Jerusalem',
}

# Bar colors, kept distinct from the per-category palette.
ORG_COLORS = {
    'ELSC': '#9f4f35',
    'HUJI': '#3f5f7a',
}

# How the monthly goal is divided between them.
ORG_MONTHLY_TARGETS = {
    'ELSC': MONTHLY_TARGET_HOURS - HUJI_MONTHLY_TARGET_HOURS,
    'HUJI': HUJI_MONTHLY_TARGET_HOURS,
}

WEEKEND_DAYS = (4, 5)  # Friday and Saturday in Python's Monday-based calendar.

# Bumped whenever a one-off data migration is added; stored in PRAGMA user_version.
SCHEMA_VERSION = 2


def category_meta(category):
    """Return display metadata for a stored category value."""
    return CATEGORY_META.get(category, {
        'label': category.replace('_', ' ').title(),
        'short_label': category.replace('_', ' ').title(),
        'color': '#7b8794',
        'icon': 'tag',
        'org': '',
    })


def category_label(category):
    return category_meta(category)['label']


def category_color(category):
    return category_meta(category)['color']


def category_org(category):
    """Who the work is for: consulting, infrastructure and combined are all ELSC."""
    return category_meta(category).get('org', '')


def title_qualifier(name, category):
    """Short parenthetical for a title, never one that just repeats the name.

    The seeded titles are named after their own category ("Consulting" in
    consulting), so the category alone would read "Consulting (Consulting)".
    Fall back to the org there, which is the part that actually adds something.
    """
    label = category_label(category)
    org = category_org(category)
    if label != name:
        return f'{org} · {label}' if org else label
    return org if org != name else ''


def org_progress(by_category, dt=None):
    """Per-org progress against each org's slice of the monthly goal.

    Every org with a target gets a row even at zero hours, so both bars are always
    visible. An org carrying hours but no agreed target (or work filed under no org
    at all) is appended with target None, so those hours are never silently dropped.
    """
    logged = {}
    for cat, hours in by_category.items():
        if cat in SEPARATE_REPORT_CATEGORIES:
            continue
        org = category_org(cat) or category_label(cat)
        logged[org] = logged.get(org, 0.0) + hours

    orgs = list(ORG_MONTHLY_TARGETS)
    orgs += [org for org in logged if org not in ORG_MONTHLY_TARGETS]

    rows = []
    for org in orgs:
        hours = round(logged.get(org, 0.0), 2)
        target = ORG_MONTHLY_TARGETS.get(org)
        row = {
            'org': org,
            'name': ORG_NAMES.get(org, org),
            'logged': hours,
            'target': target,
            'color': ORG_COLORS.get(org, '#7b8794'),
        }
        if target:
            row['pace'] = calculate_month_pace(hours, dt, target_hours=target)
            row['remaining'] = round(max(target - hours, 0), 2)
            row['pct'] = round(hours / target * 100, 1)
        rows.append(row)

    # Bars share one hour scale: the largest target spans the full width and the
    # others are drawn shorter in proportion. Without this a small target fills
    # fast and reads as heavier progress than a big one at the same hour count.
    widest = max((row['target'] for row in rows if row['target']), default=0)
    for row in rows:
        if row['target']:
            row['scale_pct'] = round(row['target'] / widest * 100, 2)
    return rows


def advisor_role_lines():
    """The "AI Advisor for ..." block of the report header, one org per line."""
    names = list(ORG_NAMES.values())
    if not names:
        return []
    return [f'AI Advisor for {names[0]}'] + [f'and for {name}' for name in names[1:]]


def org_totals(by_category):
    """Group per-category hours by org, preserving ORDERED_CATEGORIES order.

    Returns [(org, total_hours, [(category, hours), ...]), ...].
    """
    by_category = {
        cat: hours for cat, hours in by_category.items()
        if cat not in SEPARATE_REPORT_CATEGORIES
    }
    ordered = list(ORDERED_CATEGORIES)
    cats = sorted(
        by_category,
        key=lambda c: ordered.index(c) if c in ordered else len(ordered),
    )
    groups = []
    index = {}
    for cat in cats:
        org = category_org(cat) or category_label(cat)
        if org not in index:
            index[org] = len(groups)
            groups.append((org, 0.0, []))
        pos = index[org]
        name, total, members = groups[pos]
        groups[pos] = (name, total + by_category[cat], members + [(cat, by_category[cat])])
    return [(name, round(total, 2), members) for name, total, members in groups]


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
                color TEXT NOT NULL DEFAULT '#9f4f35',
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
                ('Consulting', 'consulting'),
                ('Infrastructure', 'infrastructure'),
                ('Consulting + Infrastructure', 'mixed'),
                ('HUJI', 'huji'),
                ('Stefano', 'stefano'),
            ]
            conn.executemany(
                "INSERT INTO titles (name, category, color) VALUES (?, ?, ?)",
                [(name, cat, CATEGORY_META[cat]['color']) for name, cat in defaults]
            )
            conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        else:
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            if version < 1:
                _migrate_legacy_categories(conn)
            if version < 2:
                _ensure_stefano_title(conn)
            conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")


def _migrate_legacy_categories(conn):
    """Bring pre-September-2026 titles onto the renamed category keys.

    Runs once (guarded by PRAGMA user_version) so it never overwrites names or
    colors chosen after the move. This is a rename only: the combined
    "Consulting + Infrastructure" category keeps its own hours, as it always has.
    """
    for legacy, current in LEGACY_CATEGORIES.items():
        conn.execute(
            "UPDATE titles SET category=? WHERE category=?", (current, legacy)
        )

    # "Counseling" was the odd one out: the UI has always shown it as "Consulting".
    renames = [
        ('Counseling', 'Consulting'),
        ('Counseling + Infrastructure', 'Consulting + Infrastructure'),
    ]
    for old_name, new_name in renames:
        if conn.execute("SELECT 1 FROM titles WHERE name=?", (new_name,)).fetchone():
            continue
        conn.execute(
            "UPDATE titles SET name=? WHERE name=?", (new_name, old_name)
        )

    if not conn.execute("SELECT 1 FROM titles WHERE category='huji'").fetchone():
        conn.execute(
            "INSERT OR IGNORE INTO titles (name, category, color) VALUES (?, ?, ?)",
            ('HUJI', 'huji', CATEGORY_META['huji']['color'])
        )


def _ensure_stefano_title(conn):
    """Create the fixed Stefano title used for the separate capped engagement."""
    if conn.execute("SELECT 1 FROM titles WHERE category='stefano'").fetchone():
        return
    existing = conn.execute("SELECT id FROM titles WHERE name='Stefano'").fetchone()
    if existing:
        conn.execute(
            "UPDATE titles SET category=? WHERE id=?", ('stefano', existing['id'])
        )
    else:
        conn.execute(
            "INSERT INTO titles (name, category, color) VALUES (?, ?, ?)",
            ('Stefano', 'stefano', CATEGORY_META['stefano']['color'])
        )


# ── Title CRUD ──────────────────────────────────────────────

def get_titles():
    """Return all titles."""
    with get_db() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM titles ORDER BY category, name"
        ).fetchall()]


def add_title(name, category, color='#9f4f35'):
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


def _calc_split(by_category):
    """Return the 50/50 consulting/infrastructure balance for the period.

    Combined hours cover both sides at once, so they are halved into each rather
    than dropped: the balance then reflects every attributable hour. The raw
    per-category totals stay untouched for the report, which still lists Combined
    on its own line. HUJI is separate work and stays outside the balance entirely.
    """
    consulting = by_category.get('consulting', 0)
    infrastructure = by_category.get('infrastructure', 0)
    mixed = by_category.get('mixed', 0)
    huji = by_category.get('huji', 0)

    half_mixed = mixed / 2
    consulting_balance = round(consulting + half_mixed, 2)
    infrastructure_balance = round(infrastructure + half_mixed, 2)
    split_total = round(consulting_balance + infrastructure_balance, 2)
    if split_total:
        consulting_pct = round(consulting_balance / split_total * 100, 1)
        infrastructure_pct = round(infrastructure_balance / split_total * 100, 1)
    else:
        consulting_pct = 0
        infrastructure_pct = 0

    return {
        'consulting': consulting,
        'infrastructure': infrastructure,
        'mixed': mixed,
        'huji': huji,
        'consulting_balance': consulting_balance,
        'infrastructure_balance': infrastructure_balance,
        'split_total': split_total,
        'consulting_pct': consulting_pct,
        'infrastructure_pct': infrastructure_pct,
        'balance_delta': round(consulting_balance - infrastructure_balance, 2),
    }


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


def calculate_month_pace(logged_hours, dt=None, target_hours=MONTHLY_TARGET_HOURS):
    """Compare logged hours with a target prorated over Sun-Thu workdays."""
    if dt is None:
        dt = datetime.now()

    month_start, next_month = _get_month_range(dt)
    workdays = []
    day = month_start.date()
    while day < next_month.date():
        if day.weekday() not in WEEKEND_DAYS:
            workdays.append(day)
        day += timedelta(days=1)

    today = dt.date()
    elapsed_workdays = sum(day <= today for day in workdays)
    remaining_workdays = sum(day >= today for day in workdays)
    total_workdays = len(workdays)

    expected_hours = target_hours * elapsed_workdays / total_workdays
    hours_delta = logged_hours - expected_hours
    remaining_hours = max(target_hours - logged_hours, 0)
    required_daily_hours = (
        remaining_hours / remaining_workdays if remaining_workdays else remaining_hours
    )

    if hours_delta > 1:
        status = 'ahead'
    elif hours_delta < -1:
        status = 'behind'
    else:
        status = 'on_track'

    return {
        'status': status,
        'target_hours': target_hours,
        'expected_hours': round(expected_hours, 1),
        'hours_delta': round(abs(hours_delta), 1),
        'remaining_hours': round(remaining_hours, 1),
        'required_daily_hours': round(required_daily_hours, 1),
        'total_workdays': total_workdays,
        'elapsed_workdays': elapsed_workdays,
        'remaining_workdays': remaining_workdays,
        'expected_progress_pct': round(elapsed_workdays / total_workdays * 100, 1),
        'logged_progress_pct': round(min(logged_hours / target_hours * 100, 100), 1),
    }


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
        all_entries = get_entries(start_date=sd, end_date=ed)
        entries = [
            entry for entry in all_entries
            if entry['category'] not in SEPARATE_REPORT_CATEGORIES
        ]
        separate_entries = [
            entry for entry in all_entries
            if entry['category'] in SEPARATE_REPORT_CATEGORIES
        ]
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
            'split': _calc_split(by_category),
        }
        stats[period_name]['separate_hours'] = _calc_hours(separate_entries)

    stats['month']['pace'] = calculate_month_pace(stats['month']['total'], now)
    stats['month']['org_progress'] = org_progress(stats['month']['by_category'], now)
    stefano_logged = stats['total']['separate_hours']
    stats['stefano'] = {
        'cap': STEFANO_HOUR_CAP,
        'logged': stefano_logged,
        'remaining': round(max(STEFANO_HOUR_CAP - stefano_logged, 0), 2),
        'pct': round(stefano_logged / STEFANO_HOUR_CAP * 100, 1),
        'periods': {
            period: stats[period]['separate_hours']
            for period in ('today', 'week', 'month', 'total')
        },
    }
    return stats
