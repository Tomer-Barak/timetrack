"""
TimeTrack – Working Hours PWA
Flask application serving a single-page-style time tracker.
"""

from flask import (
    Flask, render_template, request, redirect,
    url_for, jsonify, send_from_directory, Response
)
from datetime import datetime
import logging
import database as db

app = Flask(__name__)
app.secret_key = 'timetrack-secret-2026'
app.config['TEMPLATES_AUTO_RELOAD'] = True

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.context_processor
def inject_template_config():
    return {
        'category_meta': db.CATEGORY_META,
        'ordered_categories': db.ORDERED_CATEGORIES,
        'category_label': db.category_label,
        'category_color': db.category_color,
        'category_org': db.category_org,
        'separate_report_categories': db.SEPARATE_REPORT_CATEGORIES,
        'title_qualifier': db.title_qualifier,
        'monthly_target_hours': db.MONTHLY_TARGET_HOURS,
    }


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
    """Main log and manual-entry page."""
    entries = db.get_recent_entries(200)
    titles = db.get_titles()
    stats = db.get_stats()
    return render_template('log.html', entries=entries, titles=titles, stats=stats)


@app.route('/stats')
def stats_page():
    """Detailed statistics page."""
    stats = db.get_stats()
    titles = db.get_titles()
    current_month = datetime.now().strftime('%Y-%m')
    return render_template('stats.html', stats=stats, titles=titles, current_month=current_month)


@app.route('/log')
def log_page():
    """Legacy log URL; the log is now the homepage."""
    return redirect(url_for('index'))


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


# ── Stats API ───────────────────────────────────────────────

@app.route('/api/stats')
def api_stats():
    return jsonify(db.get_stats())


@app.route('/api/clear-all', methods=['POST'])
def api_clear_all():
    """Delete ALL time entries. Titles are kept."""
    db.clear_all_entries()
    return jsonify({'ok': True})


@app.route('/api/report/export')
def api_export_report():
    month_str = request.args.get('month')
    if not month_str:
        month_str = datetime.now().strftime('%Y-%m')
        
    try:
        year, month = map(int, month_str.split('-'))
        start_date = f"{year:04d}-{month:02d}-01 00:00:00"
        
        if month == 12:
            next_year, next_month = year + 1, 1
        else:
            next_year, next_month = year, month + 1
            
        end_date = f"{next_year:04d}-{next_month:02d}-01 00:00:00"
    except ValueError:
        return "Invalid month format. Use YYYY-MM", 400

    entries = [
        entry for entry in db.get_entries(start_date=start_date, end_date=end_date)
        if entry['category'] not in db.SEPARATE_REPORT_CATEGORIES
    ]
    
    import io
    output = io.StringIO()
    
    total_seconds = 0.0
    title_seconds = {}
    category_seconds = {}
    
    month_obj = datetime.strptime(month_str, '%Y-%m')
    month_display = month_obj.strftime('%B %Y')
    
    output.write("Tomer Barak - AI R&D\n")
    output.write("ID: 200660397\n")
    for line in db.advisor_role_lines():
        output.write(line + "\n")
    output.write("=" * 40 + "\n\n")
    
    output.write(f"TimeTrack Report: {month_display}\n")
    output.write("-" * 40 + "\n\n")
    
    for e in entries:
        start = datetime.strptime(e['start_time'], '%Y-%m-%d %H:%M:%S')
        end = datetime.strptime(e['end_time'], '%Y-%m-%d %H:%M:%S')
        seconds = (end - start).total_seconds()
        
        t_name = e['title_name']
        title_seconds[t_name] = title_seconds.get(t_name, 0.0) + seconds
        category = e['category']
        category_seconds[category] = category_seconds.get(category, 0.0) + seconds
        total_seconds += seconds
        
    output.write("--- SUMMARY ---\n")
    output.write(f"Total Hours: {round(total_seconds / 3600, 2)}h\n\n")
    
    if category_seconds:
        output.write("By Category:\n")
        category_hours = {
            cat: round(seconds / 3600, 2) for cat, seconds in category_seconds.items()
        }
        for org, org_hours, members in db.org_totals(category_hours):
            output.write(f"  {org}: {org_hours}h\n")
            # A single category named after its own org adds nothing to spell out.
            if len(members) == 1 and db.category_label(members[0][0]) == org:
                continue
            for cat, hours in members:
                output.write(f"    - {db.category_label(cat)}: {hours}h\n")
        output.write("\n")

    if title_seconds:
        output.write("By Title:\n")
        # Sort descending by hours
        for t, seconds in sorted(title_seconds.items(), key=lambda x: x[1], reverse=True):
            output.write(f"  - {t}: {round(seconds / 3600, 2)}h\n")
    
    output.write("\n--- DETAILS ---\n")
    if not entries:
        output.write("No entries found for this month.\n")
    else:
        for e in reversed(entries):  # Sort oldest first for presentation
            start = datetime.strptime(e['start_time'], '%Y-%m-%d %H:%M:%S')
            end = datetime.strptime(e['end_time'], '%Y-%m-%d %H:%M:%S')
            hours = round((end - start).total_seconds() / 3600, 2)
            
            start_str = start.strftime('%d-%m-%Y %H:%M')
            end_str = end.strftime('%d-%m-%Y %H:%M')
            output.write(f"[{start_str} to {end_str}] {e['title_name']} : {hours}h\n")
        
    return Response(
        output.getvalue(),
        mimetype="text/plain",
        headers={"Content-disposition": f"attachment; filename=timetrack_report_{month_str}.txt"}
    )


@app.route('/api/report/stefano/export')
def api_export_stefano_report():
    """Export the finite Stefano engagement independently of monthly work."""
    import io

    entries = [
        entry for entry in db.get_entries()
        if entry['category'] == 'stefano'
    ]
    total_seconds = 0.0
    title_seconds = {}
    for entry in entries:
        start = datetime.strptime(entry['start_time'], '%Y-%m-%d %H:%M:%S')
        end = datetime.strptime(entry['end_time'], '%Y-%m-%d %H:%M:%S')
        seconds = (end - start).total_seconds()
        total_seconds += seconds
        title = entry['title_name']
        title_seconds[title] = title_seconds.get(title, 0.0) + seconds

    logged = round(total_seconds / 3600, 2)
    remaining = round(max(db.STEFANO_HOUR_CAP - logged, 0), 2)
    output = io.StringIO()
    output.write("Tomer Barak - Stefano Time Report\n")
    output.write("=" * 40 + "\n\n")
    output.write("--- SUMMARY ---\n")
    output.write(f"Total Hours: {logged}h\n")
    output.write(f"Engagement Cap: {db.STEFANO_HOUR_CAP}h\n")
    output.write(f"Hours Remaining: {remaining}h\n")

    if title_seconds:
        output.write("\nBy Title:\n")
        for title, seconds in sorted(
            title_seconds.items(), key=lambda item: item[1], reverse=True
        ):
            output.write(f"  - {title}: {round(seconds / 3600, 2)}h\n")

    output.write("\n--- DETAILS ---\n")
    if not entries:
        output.write("No Stefano entries found.\n")
    else:
        for entry in reversed(entries):
            start = datetime.strptime(entry['start_time'], '%Y-%m-%d %H:%M:%S')
            end = datetime.strptime(entry['end_time'], '%Y-%m-%d %H:%M:%S')
            hours = round((end - start).total_seconds() / 3600, 2)
            output.write(
                f"[{start.strftime('%d-%m-%Y %H:%M')} to "
                f"{end.strftime('%d-%m-%Y %H:%M')}] "
                f"{entry['title_name']} : {hours}h\n"
            )

    return Response(
        output.getvalue(),
        mimetype="text/plain",
        headers={
            "Content-disposition": "attachment; filename=stefano_time_report.txt"
        },
    )




# ── Boot ────────────────────────────────────────────────────

if __name__ == '__main__':
    db.init_db()
    app.run(debug=False, host='0.0.0.0', port=5013)
