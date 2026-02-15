"""
TimeTrack – Working Hours PWA
Flask application serving a single-page-style time tracker.
"""

from flask import (
    Flask, render_template, request, redirect,
    url_for, jsonify, flash, send_from_directory
)
from datetime import datetime
import logging
import database as db

app = Flask(__name__)
app.secret_key = 'timetrack-secret-2026'
app.config['TEMPLATES_AUTO_RELOAD'] = True

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── PWA boilerplate ─────────────────────────────────────────

@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json',
                               mimetype='application/manifest+json')


@app.route('/sw.js')
def service_worker():
    return send_from_directory('static', 'sw.js',
                               mimetype='application/javascript')


@app.after_request
def add_no_cache_headers(response):
    if response.mimetype == 'text/html':
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response


# ── Pages ───────────────────────────────────────────────────

@app.route('/')
def index():
    """Main dashboard – timer + recent log + stats overview."""
    titles = db.get_titles()
    active = db.get_active_entry()
    recent = db.get_recent_entries(20)
    stats = db.get_stats()

    # Calculate elapsed seconds for the running timer (avoids timezone issues in JS)
    elapsed_seconds = 0
    if active and active.get('start_time'):
        from datetime import datetime as _dt
        start = _dt.strptime(active['start_time'], '%Y-%m-%d %H:%M:%S')
        elapsed_seconds = int((_dt.now() - start).total_seconds())

    return render_template('index.html',
                           titles=titles,
                           active=active,
                           recent=recent,
                           stats=stats,
                           elapsed_seconds=elapsed_seconds)


@app.route('/stats')
def stats_page():
    """Detailed statistics page."""
    stats = db.get_stats()
    titles = db.get_titles()
    return render_template('stats.html', stats=stats, titles=titles)


@app.route('/log')
def log_page():
    """Full time entry log with edit/delete."""
    entries = db.get_recent_entries(200)
    titles = db.get_titles()
    return render_template('log.html', entries=entries, titles=titles)


@app.route('/titles')
def titles_page():
    """Manage titles."""
    titles = db.get_titles()
    return render_template('titles.html', titles=titles)


# ── Timer API ───────────────────────────────────────────────

@app.route('/api/start', methods=['POST'])
def api_start():
    data = request.get_json()
    title_id = data.get('title_id')
    if not title_id:
        return jsonify({'error': 'title_id required'}), 400
    db.start_entry(int(title_id))
    active = db.get_active_entry()
    return jsonify({'ok': True, 'active': active})


@app.route('/api/stop', methods=['POST'])
def api_stop():
    db.stop_entry()
    return jsonify({'ok': True})


@app.route('/api/status')
def api_status():
    active = db.get_active_entry()
    return jsonify({'active': active})


# ── Entry CRUD API ──────────────────────────────────────────

@app.route('/api/entry', methods=['POST'])
def api_add_entry():
    """Add a manual entry."""
    data = request.get_json()
    title_id = data.get('title_id')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    if not all([title_id, start_time, end_time]):
        return jsonify({'error': 'title_id, start_time, end_time required'}), 400
    db.add_manual_entry(int(title_id), start_time, end_time)
    return jsonify({'ok': True})


@app.route('/api/entry/<int:entry_id>', methods=['PUT'])
def api_update_entry(entry_id):
    """Update an existing entry."""
    data = request.get_json()
    title_id = data.get('title_id')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    if not all([title_id, start_time, end_time]):
        return jsonify({'error': 'title_id, start_time, end_time required'}), 400
    db.update_entry(entry_id, int(title_id), start_time, end_time)
    return jsonify({'ok': True})


@app.route('/api/entry/<int:entry_id>', methods=['DELETE'])
def api_delete_entry(entry_id):
    db.delete_entry(entry_id)
    return jsonify({'ok': True})


# ── Title CRUD ──────────────────────────────────────────────

@app.route('/api/title', methods=['POST'])
def api_add_title():
    data = request.get_json()
    name = data.get('name', '').strip()
    category = data.get('category', 'other')
    color = data.get('color', '#6366f1')
    if not name:
        return jsonify({'error': 'name required'}), 400
    try:
        db.add_title(name, category, color)
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    return jsonify({'ok': True})


@app.route('/api/title/<int:title_id>', methods=['PUT'])
def api_update_title(title_id):
    data = request.get_json()
    name = data.get('name', '').strip()
    category = data.get('category', 'other')
    color = data.get('color', '#6366f1')
    if not name:
        return jsonify({'error': 'name required'}), 400
    db.update_title(title_id, name, category, color)
    return jsonify({'ok': True})


@app.route('/api/title/<int:title_id>', methods=['DELETE'])
def api_delete_title(title_id):
    db.delete_title(title_id)
    return jsonify({'ok': True})


# ── Stats API ───────────────────────────────────────────────

@app.route('/api/stats')
def api_stats():
    return jsonify(db.get_stats())


@app.route('/api/clear-all', methods=['POST'])
def api_clear_all():
    """Delete ALL time entries. Titles are kept."""
    db.clear_all_entries()
    return jsonify({'ok': True})


# ── Boot ────────────────────────────────────────────────────

if __name__ == '__main__':
    db.init_db()
    app.run(debug=False, host='0.0.0.0', port=5013)
