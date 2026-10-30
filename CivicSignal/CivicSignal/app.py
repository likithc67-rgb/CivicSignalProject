import os
import re
import sqlite3
from datetime import datetime
from difflib import SequenceMatcher
from collections import Counter, defaultdict

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, g

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "civicsignal.db")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")

CATEGORIES = ["Road Damage", "Waterlogging", "Waste Management", "Streetlight",
              "Drainage", "Water Supply", "Public Safety", "Other"]
STATUSES = ["Submitted", "Under Review", "Assigned", "In Progress", "Resolved", "Rejected"]
DEPARTMENTS = ["Roads Department", "Water & Drainage", "Sanitation Department",
               "Electrical Department", "Public Safety", "General Administration"]

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(_error):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tracking_code TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            location TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            citizen_name TEXT,
            priority TEXT NOT NULL,
            priority_score INTEGER NOT NULL,
            priority_reason TEXT NOT NULL,
            ai_summary TEXT NOT NULL,
            duplicate_of INTEGER,
            status TEXT NOT NULL DEFAULT 'Submitted',
            department TEXT,
            assigned_to TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            resolution_note TEXT,
            FOREIGN KEY(duplicate_of) REFERENCES reports(id)
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS status_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            note TEXT,
            changed_at TEXT NOT NULL,
            FOREIGN KEY(report_id) REFERENCES reports(id) ON DELETE CASCADE
        )
    """)
    db.commit()
    db.close()

def clean_words(text):
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))

def categorize(text):
    t = (text or "").lower()
    rules = {
        "Waterlogging": ["waterlogging", "flood", "flooding", "water is standing", "rain water", "submerged"],
        "Road Damage": ["pothole", "road", "crater", "damaged road", "broken road", "asphalt"],
        "Waste Management": ["garbage", "waste", "rubbish", "dustbin", "trash", "overflowing bin"],
        "Streetlight": ["streetlight", "street light", "lamp", "dark road", "light is not working"],
        "Drainage": ["drain", "sewage", "blocked pipe", "manhole", "drainage"],
        "Water Supply": ["water supply", "no water", "drinking water", "pipeline leak", "water leakage"],
        "Public Safety": ["open manhole", "fallen electric", "live wire", "accident", "danger", "unsafe"]
    }
    for category, keywords in rules.items():
        if any(k in t for k in keywords):
            return category
    return "Other"

def summarize(text):
    text = re.sub(r"\s+", " ", (text or "")).strip()
    if len(text) <= 150:
        return text
    first = re.split(r"(?<=[.!?])\s+", text)[0]
    return first[:147].rstrip() + "..."

def find_duplicate(db, description, category, lat, lon):
    """Transparent lexical similarity heuristic; not an embedding/LLM model."""
    rows = db.execute(
        "SELECT id, description, category, latitude, longitude FROM reports ORDER BY id DESC LIMIT 200"
    ).fetchall()
    incoming = clean_words(description)
    best_id, best_score = None, 0.0
    for row in rows:
        existing = clean_words(row["description"])
        if not incoming or not existing:
            continue
        jaccard = len(incoming & existing) / max(1, len(incoming | existing))
        sequence = SequenceMatcher(None, description.lower(), row["description"].lower()).ratio()
        score = max(jaccard, sequence * 0.85)
        same_category = row["category"] == category
        nearby = False
        if lat is not None and lon is not None and row["latitude"] is not None and row["longitude"] is not None:
            nearby = abs(float(lat) - row["latitude"]) < 0.01 and abs(float(lon) - row["longitude"]) < 0.01
        adjusted = score + (0.12 if same_category else 0) + (0.12 if nearby else 0)
        if adjusted > best_score:
            best_id, best_score = row["id"], adjusted
    return (best_id, round(best_score, 2)) if best_score >= 0.48 else (None, round(best_score, 2))

def score_priority(description, category, lat, lon):
    text = description.lower()
    score, reasons = 25, []
    urgent_terms = ["live wire", "electric shock", "open manhole", "accident", "injury",
                    "fire", "collapse", "flood", "school", "hospital", "elderly", "trapped"]
    matches = [term for term in urgent_terms if term in text]
    if matches:
        score += min(35, 12 + 5 * len(matches))
        reasons.append("Potential safety/health risk: " + ", ".join(matches[:3]))
    if category in ["Public Safety", "Waterlogging"]:
        score += 18
        reasons.append(f"{category} can affect public safety or access")
    elif category in ["Drainage", "Road Damage"]:
        score += 12
        reasons.append(f"{category} can disrupt public infrastructure")
    elif category in ["Waste Management", "Water Supply", "Streetlight"]:
        score += 8
        reasons.append(f"{category} affects community services")
    if len(description) > 180:
        score += 5
        reasons.append("Description contains additional incident details")
    score = min(100, score)
    level = "Critical" if score >= 75 else "High" if score >= 58 else "Medium" if score >= 40 else "Low"
    if not reasons:
        reasons.append("No explicit emergency keywords detected; standard service issue")
    return score, level, "; ".join(reasons)

def tracking_code():
    return "CS-" + datetime.now().strftime("%y%m%d") + "-" + os.urandom(2).hex().upper()

def insert_report(db, data):
    now = datetime.now().isoformat(timespec="seconds")
    description = data["description"].strip()
    category = data.get("category") or categorize(description)
    # AI category suggestion is used when user selects "Auto detect".
    if category == "Auto detect":
        category = categorize(description)
    score, priority, reason = score_priority(description, category, data.get("latitude"), data.get("longitude"))
    duplicate_id, duplicate_score = find_duplicate(db, description, category, data.get("latitude"), data.get("longitude"))
    code = tracking_code()
    cur = db.execute("""
        INSERT INTO reports
        (tracking_code,title,description,category,location,latitude,longitude,citizen_name,
         priority,priority_score,priority_reason,ai_summary,duplicate_of,status,created_at,updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (code, data.get("title") or description[:65], description, category,
          data["location"].strip(), data.get("latitude"), data.get("longitude"),
          data.get("citizen_name") or "Anonymous", priority, score, reason,
          summarize(description), duplicate_id, "Submitted", now, now))
    report_id = cur.lastrowid
    db.execute("INSERT INTO status_history(report_id,status,note,changed_at) VALUES(?,?,?,?)",
               (report_id, "Submitted", "Complaint received by CivicSignal.", now))
    db.commit()
    return report_id, code, duplicate_id, duplicate_score

@app.route("/")
def index():
    db = get_db()
    stats = db.execute("""
        SELECT COUNT(*) total,
        SUM(CASE WHEN status='Resolved' THEN 1 ELSE 0 END) resolved,
        SUM(CASE WHEN status!='Resolved' AND status!='Rejected' THEN 1 ELSE 0 END) open_count,
        SUM(CASE WHEN priority IN ('Critical','High') AND status!='Resolved' THEN 1 ELSE 0 END) urgent
        FROM reports
    """).fetchone()
    recent = db.execute("SELECT * FROM reports ORDER BY created_at DESC LIMIT 6").fetchall()
    return render_template("index.html", stats=stats, recent=recent)

@app.route("/report", methods=["GET", "POST"])
def report():
    if request.method == "POST":
        description = request.form.get("description", "").strip()
        location = request.form.get("location", "").strip()
        if len(description) < 10 or not location:
            flash("Please enter a description (at least 10 characters) and a location.", "error")
            return redirect(url_for("report"))
        lat = request.form.get("latitude") or None
        lon = request.form.get("longitude") or None
        try:
            lat = float(lat) if lat else None
            lon = float(lon) if lon else None
        except ValueError:
            lat, lon = None, None
        data = {
            "title": request.form.get("title", "").strip(),
            "description": description,
            "category": request.form.get("category", "Auto detect"),
            "location": location,
            "latitude": lat, "longitude": lon,
            "citizen_name": request.form.get("citizen_name", "").strip()
        }
        db = get_db()
        report_id, code, duplicate_id, duplicate_score = insert_report(db, data)
        if duplicate_id:
            flash(f"Complaint submitted. Possible duplicate of report #{duplicate_id} (similarity score {duplicate_score}). Tracking ID: {code}", "success")
        else:
            flash(f"Complaint submitted successfully. Your tracking ID is {code}", "success")
        return redirect(url_for("track", code=code))
    return render_template("report.html", categories=CATEGORIES)

@app.route("/track", methods=["GET", "POST"])
def track_search():
    if request.method == "POST":
        return redirect(url_for("track", code=request.form.get("tracking_code", "").strip()))
    return render_template("track_search.html")

@app.route("/track/<code>")
def track(code):
    db = get_db()
    item = db.execute("SELECT * FROM reports WHERE tracking_code=?", (code.upper(),)).fetchone()
    if not item:
        flash("No complaint found for that tracking ID.", "error")
        return redirect(url_for("track_search"))
    history = db.execute("SELECT * FROM status_history WHERE report_id=? ORDER BY id", (item["id"],)).fetchall()
    duplicate = db.execute("SELECT tracking_code FROM reports WHERE id=?", (item["duplicate_of"],)).fetchone() if item["duplicate_of"] else None
    return render_template("track.html", item=item, history=history, duplicate=duplicate)

@app.route("/admin")
def admin():
    db = get_db()
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    priority = request.args.get("priority", "")
    sql = "SELECT * FROM reports WHERE 1=1"
    params = []
    if q:
        sql += " AND (title LIKE ? OR description LIKE ? OR location LIKE ? OR tracking_code LIKE ?)"
        params += [f"%{q}%"] * 4
    if status:
        sql += " AND status=?"; params.append(status)
    if priority:
        sql += " AND priority=?"; params.append(priority)
    sql += " ORDER BY priority_score DESC, created_at DESC"
    reports = db.execute(sql, params).fetchall()
    all_reports = db.execute("SELECT * FROM reports").fetchall()
    category_counts = Counter(r["category"] for r in all_reports)
    hotspot_counts = Counter(r["location"] for r in all_reports)
    hotspots = hotspot_counts.most_common(5)
    stats = {
        "total": len(all_reports),
        "open": sum(1 for r in all_reports if r["status"] not in ("Resolved", "Rejected")),
        "resolved": sum(1 for r in all_reports if r["status"] == "Resolved"),
        "critical": sum(1 for r in all_reports if r["priority"] == "Critical" and r["status"] != "Resolved")
    }
    map_reports = [dict(r) for r in all_reports if r["latitude"] is not None and r["longitude"] is not None]
    return render_template("admin.html", reports=reports, stats=stats,
                           category_counts=dict(category_counts), hotspots=hotspots,
                           map_reports=map_reports, statuses=STATUSES,
                           priorities=["Critical","High","Medium","Low"])

@app.route("/admin/report/<int:report_id>", methods=["GET", "POST"])
def admin_report(report_id):
    db = get_db()
    item = db.execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone()
    if not item:
        flash("Report not found.", "error")
        return redirect(url_for("admin"))
    if request.method == "POST":
        new_status = request.form.get("status", item["status"])
        department = request.form.get("department", "")
        assigned_to = request.form.get("assigned_to", "")
        note = request.form.get("note", "").strip()
        resolution_note = request.form.get("resolution_note", "").strip()
        now = datetime.now().isoformat(timespec="seconds")
        db.execute("""UPDATE reports SET status=?, department=?, assigned_to=?,
                   resolution_note=?, updated_at=? WHERE id=?""",
                   (new_status, department, assigned_to, resolution_note, now, report_id))
        if new_status != item["status"] or note:
            db.execute("INSERT INTO status_history(report_id,status,note,changed_at) VALUES(?,?,?,?)",
                       (report_id, new_status, note or f"Status changed to {new_status}.", now))
        db.commit()
        flash("Report workflow updated.", "success")
        return redirect(url_for("admin_report", report_id=report_id))
    history = db.execute("SELECT * FROM status_history WHERE report_id=? ORDER BY id DESC", (report_id,)).fetchall()
    return render_template("admin_report.html", item=item, history=history,
                           statuses=STATUSES, departments=DEPARTMENTS)

@app.route("/api/reports")
def api_reports():
    db = get_db()
    rows = db.execute("SELECT id,title,category,location,latitude,longitude,priority,status,priority_score FROM reports WHERE latitude IS NOT NULL AND longitude IS NOT NULL").fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/health")
def health():
    return jsonify({"ok": True, "app": "CivicSignal"})

if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="127.0.0.1", port=5000)
