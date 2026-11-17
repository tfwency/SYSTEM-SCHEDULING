"""
TEACHER SCHEDULING SYSTEM - San Jose Litex Senior High School

Local run:      pip install flask
                python flask_app.py       ->  open http://127.0.0.1:5000
PythonAnywhere: save this file as  mysite/flask_app.py , then press Reload.

Default accounts (change the passwords after the first sign-in):
  Administrator   admin / (no ID needed)       password  admin123
  Grade 11        msantos / T-1001             password  teacher123
  Grade 12        jreyes / T-1002              password  teacher123
  MID             adelacruz / T-1003           password  teacher123

Two documents, modeled on the school's printed sheets:
  CLASS PROGRAM     one per section (room, adviser, Monday to Friday timetable,
                    legend, signatories). Teachers see the grade levels they handle.
  TEACHER'S PROGRAM one per teacher (loads, official time, timetable, daily teaching,
                    intervention and ancillary minutes). Only that teacher and the
                    administrator can open it.
  PROBLEM REPORTS   Anyone can report a problem (message + optional photo) from the sign-in
                    page or from Profile & Settings. The administrator is notified with a badge
                    in the menu, a banner, a pop-up and an inbox page (Reports).
  NOTIFICATIONS     A bell icon shows the unread count. Teachers are told when the administrator
                    updates their program or assigns them to a class period or section; the
                    administrator sees problem reports there. Both can delete what is finished.

ADMIN MAIN NAVIGATION (follows the order of the work)
  01 Dashboard             progress of every step, alerts, progress by section
  02 School Setup          school year, term, document details, logo, timetable, shifts, rules
  03 Curriculum Management the fixed Strengthened Curriculum: 5 core subjects, Academic (5 clusters)
                           and TechPro (10 clusters); choose what is offered and set minutes/rooms
  04 Section Management    grade level, section, track, cluster, shift, room, adviser
  05 Teacher Management    accounts, profiles, specialization (curriculum choices), official time
  06 Teacher Loading       who teaches each subject of a section; qualifications
  07 Room Management       classrooms and laboratories / workshops
  08 Schedule Generator    automatic draft, manual adjustment, class programs
  09 Validation Center     conflicts, loading checks, time allocation
  10 Reports and Printing  print class and teacher programs, Excel/PDF downloads
  11 User Management       accounts, roles and permissions, requests and problem reports, audit trail
"""
import base64
import json
import os
import re
import secrets
import sqlite3
import time
from functools import wraps

from flask import (Flask, abort, flash, g, make_response, redirect,
                   render_template, request, session, url_for)
from jinja2 import DictLoader
from markupsafe import Markup
from werkzeug.security import check_password_hash, generate_password_hash

APP_NAME = "TEACHER SCHEDULING SYSTEM"
BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "scheduling.db")


def load_secret():
    """Use SECRET_KEY if set, otherwise create and keep a random key file."""
    env = os.environ.get("SECRET_KEY")
    if env:
        return env
    path = os.path.join(BASE, "secret.key")
    try:
        with open(path) as fh:
            return fh.read().strip()
    except OSError:
        key = secrets.token_hex(32)
        try:
            with open(path, "w") as fh:
                fh.write(key)
        except OSError:
            pass
        return key


app = Flask(__name__)
app.secret_key = load_secret()
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                  PERMANENT_SESSION_LIFETIME=8 * 3600,
                  MAX_CONTENT_LENGTH=20 * 1024 * 1024)
MAX_LOGO = 2 * 1024 * 1024
# San Jose-Litex Senior High School seal, used until the administrator uploads another logo.
DEFAULT_LOGO = base64.b64decode(
    "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"
    "+Nz+f1Yd1AAAAABJRU5ErkJggg==")


DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
CATS = {"G11": "Grade 11 Teacher", "G12": "Grade 12 Teacher",
        "MID": "MID Teacher (Grades 11 and 12)"}
CAT_SHORT = {"G11": "Grade 11", "G12": "Grade 12", "MID": "MID Teacher"}  # how a grade level is shown
GRADES = {"G11": [11], "G12": [12], "MID": [11, 12]}
USER_TYPES = [
    ("G11", "Grade 11 Teacher", "Views Grade 11 class programs"),
    ("G12", "Grade 12 Teacher", "Views Grade 12 class programs"),
    ("MID", "MID Teacher", "Handles Grades 11 and 12 and views both class programs"),
    ("ADMIN", "Administrator", "Manages and edits schedules and class programs"),
]
KINDS = {"class": "Class period", "recess": "Recess", "homeroom": "Homeroom",
         "intervention": "Intervention / Remediation"}
KIND_LABEL = {"recess": "RECESS", "homeroom": "Homeroom",
              "intervention": "Intervention/Remediation"}
DEFAULT_CFG = {
    "school_name": "San Jose-Litex Senior High School",
    "school_address": "San Jose, Montalban, Rizal",
    "term": "Second Term, SY 2026-2027",
    "principal_name": "Arleen D. Canapi", "principal_title": "Principal II",
    "psds_name": "Priscilla V. Jose", "psds_title": "PSDS - Cluster 1",
    "sdo_name": "Doris DJ. Estalilla, CESO V",
    "sdo_title": "Schools Division Superintendent",
}
TERM_NAMES = ["First Term", "Second Term", "Third Term"]
SETTING_FIELDS = [
    ("school_name", "School name"), ("school_address", "School address"),
    ("term", "Term and school year"),
    ("principal_name", "Principal name"), ("principal_title", "Principal title"),
    ("psds_name", "District supervisor name"), ("psds_title", "District supervisor title"),
    ("sdo_name", "Division superintendent name"), ("sdo_title", "Division superintendent title"),
]
BUILDINGS = ["1", "2", "3"]
FLOORS = ["2", "3", "4"]
TRACKS = ["Academic", "TechPro"]

# ---------------------------------------------------------------- Strengthened Curriculum (fixed)
# These are the only subjects, tracks and clusters the system offers. Every drop-down, section,
# teacher specialization and the schedule generator use exactly these names.
CORE_SUBJECTS = [  # code, name
    ("EC/MK", "Effective Communication / Mabisang Komunikasyon"),
    ("LCS", "Life and Career Skills"),
    ("GM", "General Mathematics"),
    ("GS", "General Science"),
    ("PKLP", "Pag-aaral ng Kasaysayan at Lipunang Pilipino (Philippine History and Society)"),
]
ACADEMIC_CLUSTERS = [  # code, name, specializations, room type
    ("ASSH", "Arts, Social Sciences, and Humanities", [], "Regular"),
    ("BE", "Business and Entrepreneurship", [], "Regular"),
    ("STEM", "Science, Technology, Engineering, and Mathematics (STEM)", [], "Regular"),
    ("SHW", "Sports, Health, and Wellness", [], "Regular"),
    ("FE", "Field Experience", [], "Regular"),
]
TECHPRO_CLUSTERS = [
    ("AWHC", "Aesthetic, Wellness, and Human Care", ["Beauty Care", "Hairdressing", "Caregiving"], "TechPro Workshop"),
    ("AFBFI", "Agri-Fishery Business and Food Innovation", ["Crop Production", "Aquaculture", "Food Processing"], "TechPro Workshop"),
    ("ACE", "Artisanry and Creative Enterprise", ["Handicrafts/Weaving"], "TechPro Workshop"),
    ("ASET", "Automotive and Small Engine Technologies", ["Automotive Electrical and Engine Repair"], "TechPro Workshop"),
    ("CBT", "Construction and Building Technology", ["Carpentry", "Construction Operations"], "TechPro Workshop"),
    ("CADT", "Creative Arts and Design Technology", ["Animation", "Visual/Media Arts"], "Computer Laboratory"),
    ("HT", "Hospitality and Tourism", ["Tourism Promotion", "Tour Guiding", "Culinary"], "Cookery Laboratory"),
    ("ICT", "ICT Support and Computer Programming Technologies", ["Computer Systems Servicing", "Programming", "Broadband Installation"], "Computer Laboratory"),
    ("IND", "Industrial Technologies", ["Electronics Assembly", "Refrigeration and Air-Conditioning"], "TechPro Workshop"),
    ("MAR", "Maritime", [], "TechPro Workshop"),
]
TRACK_CLUSTERS = {"Academic": [c[1] for c in ACADEMIC_CLUSTERS], "TechPro": [c[1] for c in TECHPRO_CLUSTERS]}
CLUSTER_SPECS = {c[1]: c[2] for c in ACADEMIC_CLUSTERS + TECHPRO_CLUSTERS}
SPEC_TO_CLUSTER = {sp: c[1] for c in TECHPRO_CLUSTERS for sp in c[2]}
CORE_NAMES = [n for _c, n in CORE_SUBJECTS]
SPEC_GROUPS = [  # what a teacher can be specialized in (the exact system choices)
    ("Core subjects", CORE_NAMES),
    ("Academic clusters", TRACK_CLUSTERS["Academic"]),
    ("TechPro clusters", TRACK_CLUSTERS["TechPro"]),
    ("TechPro specializations", sorted(SPEC_TO_CLUSTER)),
]
CURRICULUM_NAMES = {n for _g, items in SPEC_GROUPS for n in items}
SPEC_SEP = "; "
# Older example data used free-text specializations; these are the ones the app itself created.
LEGACY_SPEC = {
    "Mathematics": CORE_NAMES[2], "English": CORE_NAMES[0], "Filipino": CORE_NAMES[0],
    "Science": CORE_NAMES[3], "Social Studies": CORE_NAMES[4], "Physical Education": "Sports, Health, and Wellness",
    "Research": CORE_NAMES[1], "Mathematics / Science": CORE_NAMES[2] + SPEC_SEP + CORE_NAMES[3],
    "TechPro - Food and Beverage": "Hospitality and Tourism", "TechPro - Bartending": "Hospitality and Tourism",
    "TechPro - Home Economics": "Hospitality and Tourism",
}
ADMIN_NAV = [  # number, title, subtitle, endpoint, endpoints that keep it highlighted, icon
    ("01", "Dashboard", "Overall progress and alerts", "dashboard", ("dashboard",), "grid"),
    ("02", "School Setup", "School year, terms, timetable and shifts", "settings", ("settings",), "gear"),
    ("03", "Curriculum Management", "Tracks, clusters, subjects and offerings", "curriculum", ("curriculum",), "book"),
    ("04", "Section Management", "Grade levels, sections and clusters", "sections", ("sections", "section_edit"), "people"),
    ("05", "Teacher Management", "Teacher profiles, specialization and availability", "teachers",
     ("teachers", "teacher_edit", "teacher_view"), "badge"),
    ("06", "Teacher Loading", "Subject assignments and load computations", "auto_loading",
     ("auto_loading", "auto_quals"), "clipboard"),
    ("07", "Room Management", "Classrooms and specialized laboratories", "auto_rooms", ("auto_rooms", "auto_room"), "building"),
    ("08", "Schedule Generator", "Automatic generation and manual editing", "auto_generate",
     ("quick_input", "auto_generate", "program", "entry_edit"), "calendar"),
    ("09", "Validation Center", "Conflicts and scheduling recommendations", "auto_conflicts",
     ("auto_conflicts", "auto_time"), "shieldcheck"),
    ("10", "Reports and Printing", "Schedules and teaching-load reports", "auto_reports",
     ("auto_reports", "print_classes", "print_teachers"), "table"),
    ("11", "User Management", "Roles, permissions and audit trail", "users",
     ("users", "user_roles", "user_audit", "reports", "signup_requests"), "shield"),
]
NAV_ICONS = {
    "grid": '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    "gear": '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>',
    "book": '<path d="M2 4h6a4 4 0 0 1 4 4v13a3 3 0 0 0-3-3H2z"/><path d="M22 4h-6a4 4 0 0 0-4 4v13a3 3 0 0 1 3-3h7z"/>',
    "people": '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.9"/><path d="M16 3.1a4 4 0 0 1 0 7.8"/>',
    "badge": '<rect x="4" y="3" width="16" height="18" rx="2"/><circle cx="12" cy="10" r="3"/><path d="M7 18c.8-2.2 2.7-3.5 5-3.5s4.2 1.3 5 3.5"/>',
    "clipboard": '<path d="M9 4H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2h-2"/><rect x="9" y="2" width="6" height="4" rx="1"/><path d="M9 11h.01M13 11h3M9 15h.01M13 15h3"/>',
    "building": '<path d="M3 21V9l6-4v16"/><path d="M9 21V3h12v18"/><path d="M13 8h4M13 12h4M13 16h4M3 21h18"/>',
    "calendar": '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/><circle cx="12" cy="16" r="2.5"/>',
    "shieldcheck": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4"/>',
    "table": '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/>',
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
}
SUBNAV = {  # pages that belong to one menu item are reached with tabs, not with extra menu items
    "loading": [("Subject Assignments", "auto_loading"), ("Qualifications", "auto_quals")],
    "schedule": [("Quick Input", "quick_input"), ("Generate", "auto_generate"), ("Class Programs (edit by hand)", "program")],
    "validation": [("Conflicts and Loading", "auto_conflicts"), ("Time Allocation", "auto_time")],
    "reports": [("Downloads and Summaries", "auto_reports"), ("Print Class Programs", "print_classes"),
                ("Print Teacher's Programs", "print_teachers")],
    "users": [("Accounts", "users"), ("Requests and Problem Reports", "reports"),
              ("Roles and Permissions", "user_roles"), ("Audit Trail", "user_audit")],
}
MAX_FAILS, LOCK_SECONDS = 5, 300
FAILS = {}  # (ip, username) -> (count, time of first failure)


def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return session["csrf"]


def nav_icon(key):
    return Markup('<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" '
                  'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
                  + NAV_ICONS.get(key, "") + "</svg>")


def main_nav():
    """The administrator's 11-item main navigation (number, icon, title, subtitle, arrow)."""
    ep, out = request.endpoint, []
    for num, title, sub, endpoint, group, icon in ADMIN_NAV:
        on = ep in group
        out.append(
            f'<a class="mn{" on" if on else ""}" href="{url_for(endpoint)}"{" aria-current=page" if on else ""}>'
            f'<span class="mn-num">{num}</span><span class="mn-ic">{nav_icon(icon)}</span>'
            f'<span class="mn-tx"><b>{title}</b><small>{sub}</small></span>'
            '<svg class="mn-go" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" '
            'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg></a>')
    return Markup("".join(out))


def nav_back():
    """Where Back goes when the browser has no earlier page of this site."""
    ep = request.endpoint
    if g.get("user") and g.user["role"] == "admin":
        for _n, _t, _s, endpoint, group, _i in ADMIN_NAV:
            if ep in group:
                return url_for("dashboard") if ep == endpoint else url_for(endpoint)
        return url_for("dashboard")
    return url_for("home")


def subnav(group):
    """Tabs shown inside a menu item that has more than one page."""
    items = "".join(
        f'<a class="step{" on" if request.endpoint == ep else ""}" href="{url_for(ep)}">{label}</a>'
        for label, ep in SUBNAV[group])
    return Markup(f'<div class="steps noprint" role="navigation" aria-label="Pages in this section">{items}</div>')


app.jinja_env.globals.update(
    main_nav=main_nav, subnav=subnav, nav_back=nav_back, track_clusters=TRACK_CLUSTERS, spec_groups=SPEC_GROUPS,
    curriculum_names=CURRICULUM_NAMES, core_subjects=CORE_SUBJECTS, spec_sep=SPEC_SEP,
    days=DAYS, cats=CATS, kinds=KINDS, app_name=APP_NAME,
    buildings=BUILDINGS, floors=FLOORS, tracks=TRACKS, catname=CAT_SHORT,
    csrf_field=lambda: Markup(f'<input type="hidden" name="csrf" value="{csrf_token()}">'))


# --------------------------------------------------------------- database
def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db


def query(sql, args=(), one=False):
    rows = db().execute(sql, args).fetchall()
    return (rows[0] if rows else None) if one else rows


def run(sql, args=()):
    conn = db()
    conn.execute(sql, args)
    conn.commit()


@app.teardown_appcontext
def close_db(_):
    conn = g.pop("db", None)
    if conn:
        conn.close()


def add_col(conn, table, col, decl):
    have = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    if col not in have:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")


def init_db():
    conn = sqlite3.connect(DB)
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY, teacher_id TEXT UNIQUE, username TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL, role TEXT NOT NULL, category TEXT, password_hash TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS sections(
        id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, grade INTEGER NOT NULL, track TEXT);
    CREATE TABLE IF NOT EXISTS classes(
        id INTEGER PRIMARY KEY, section_id INTEGER NOT NULL, day TEXT NOT NULL,
        start TEXT NOT NULL, end TEXT NOT NULL, subject TEXT NOT NULL, teacher_id INTEGER);
    CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY, v TEXT);
    CREATE TABLE IF NOT EXISTS signup_requests(
        id INTEGER PRIMARY KEY, full_name TEXT NOT NULL, username TEXT NOT NULL,
        teacher_id TEXT NOT NULL, category TEXT NOT NULL, password_hash TEXT NOT NULL, created TEXT);
    CREATE TABLE IF NOT EXISTS files(
        k TEXT PRIMARY KEY, mime TEXT, data BLOB, updated INTEGER);
    CREATE TABLE IF NOT EXISTS reports(
        id INTEGER PRIMARY KEY, user_id INTEGER, name TEXT, contact TEXT, message TEXT NOT NULL,
        photo BLOB, photo_mime TEXT, created TEXT, is_read INTEGER DEFAULT 0,
        resolved INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS report_photos(
        id INTEGER PRIMARY KEY, report_id INTEGER NOT NULL, data BLOB, mime TEXT);
    CREATE TABLE IF NOT EXISTS notifications(
        id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, kind TEXT, message TEXT NOT NULL,
        link TEXT, created TEXT, is_read INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS reset_requests(
        id INTEGER PRIMARY KEY, username TEXT NOT NULL, full_name TEXT NOT NULL,
        note TEXT, created TEXT);
    """)
    # Upgrades for databases made by earlier versions.
    add_col(conn, "reset_requests", "teacher_id", "TEXT")
    add_col(conn, "users", "email", "TEXT")
    add_col(conn, "signup_requests", "email", "TEXT")
    conn.execute("""CREATE TABLE IF NOT EXISTS otp_codes(
        id INTEGER PRIMARY KEY, purpose TEXT, email TEXT, ref TEXT, code_hash TEXT,
        expires REAL, attempts INTEGER DEFAULT 0, created REAL, payload TEXT)""")
    for col, decl in [("item", "TEXT"), ("subject_area", "TEXT"), ("ancillary", "TEXT"),
                      ("official_time", "TEXT"), ("intervention_min", "INTEGER DEFAULT 0"),
                      ("ancillary_min", "INTEGER DEFAULT 0"), ("specialization", "TEXT"),
                      ("teaching_load", "TEXT")]:
        add_col(conn, "users", col, decl)
    add_col(conn, "sections", "room", "TEXT")
    add_col(conn, "sections", "adviser_id", "INTEGER")
    add_col(conn, "sections", "building", "TEXT")
    add_col(conn, "sections", "floor", "TEXT")
    add_col(conn, "classes", "kind", "TEXT DEFAULT 'class'")
    add_col(conn, "classes", "code", "TEXT")
    conn.execute("UPDATE users SET category='MID' WHERE category='MEET'")
    # Give sections a building and floor from their room number (only where none is set yet).
    for nm, rm in SAMPLE_ROOMS.items():
        if conn.execute("SELECT 1 FROM sections WHERE name=? AND COALESCE(building,'')=''", (nm,)).fetchone():
            conn.execute("UPDATE sections SET room=?, building='1', floor=? WHERE name=?",
                         ("Room " + rm, rm[0], nm))
    for sid, rm in conn.execute("SELECT id, room FROM sections WHERE COALESCE(building,'')=''").fetchall():
        bld, flr = room_place(rm)
        if bld:
            conn.execute("UPDATE sections SET building=?, floor=? WHERE id=?", (bld, flr, sid))
    # Only two tracks exist now: TechPro and Academic (older data said "TVL").
    conn.execute("UPDATE sections SET track='TechPro' WHERE track LIKE 'TVL%'")
    conn.execute("UPDATE users SET specialization=replace(specialization,'TVL - ','TechPro - ') "
                 "WHERE specialization LIKE 'TVL - %'")
    conn.execute("UPDATE users SET subject_area=replace(subject_area,'TVL - ','TechPro - ') "
                 "WHERE subject_area LIKE '%TVL - %'")
    conn.commit()

    if not conn.execute("SELECT 1 FROM users").fetchone():
        ins = ("INSERT INTO users(teacher_id,username,full_name,role,category,password_hash,"
               "item,subject_area,ancillary,official_time,intervention_min,ancillary_min) "
               "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)")
        pw = generate_password_hash("teacher123")
        conn.execute(ins, ("ADMIN-001", "admin", "System Administrator", "admin", None,
                           generate_password_hash("admin123"), None, None, None, None, 0, 0))
        conn.execute(ins, ("T-1001", "msantos", "Maria Santos", "teacher", "G11", pw, "Teacher I",
                           "EC / MK / LCS / PKLP / Food and Beverage Operation",
                           "ADVISER (11-CHEF)", "6:00 AM - 3:00 PM", 60, 60))
        conn.execute(ins, ("T-1002", "jreyes", "Jose Reyes", "teacher", "G12", pw, "Teacher II",
                           "PR 2 / Bartending", "ADVISER (12-RECEPTIONIST)",
                           "12:00 NN - 7:00 PM", 60, 60))
        conn.execute(ins, ("T-1003", "adelacruz", "Ana Dela Cruz", "teacher", "MID", pw,
                           "Teacher III", "General Mathematics / General Science", "",
                           "6:00 AM - 3:00 PM", 60, 0))
        for uid, spec in ((2, "TechPro - Food and Beverage"), (3, "TechPro - Bartending"), (4, "Mathematics / Science")):
            conn.execute("UPDATE users SET specialization=? WHERE id=?", (spec, uid))
        conn.execute("INSERT INTO sections(name,grade,track,room,building,floor,adviser_id) "
                     "VALUES('11-Chef',11,'TechPro','Room 309','1','3',2)")
        conn.execute("INSERT INTO sections(name,grade,track,room,building,floor,adviser_id) "
                     "VALUES('12-Receptionist',12,'TechPro','Room 309','1','3',3)")
        cls = ("INSERT INTO classes(section_id,day,start,end,subject,code,kind,teacher_id) "
               "VALUES(?,?,?,?,?,?,?,?)")
        GS, GM = ("General Science", "GS"), ("General Mathematics", "GM")
        EC, MK = ("Effective Communication", "EC"), ("Mabisang Komunikasyon", "MK")
        LCS, PK = ("Life and Career Skills", "LCS"), ("Pag-aaral ng Kasaysayan at Lipunang Pilipino", "PKLP")
        FB = ("Food & Beverage Operation", "")
        MS, AD = 2, 4  # Maria Santos, Ana Dela Cruz
        chef = {
            "Monday": [("06:00", "07:00", GS, AD), ("07:00", "08:00", EC, MS), ("08:00", "09:00", PK, MS),
                       ("09:30", "10:30", LCS, MS), ("10:30", "11:30", GM, AD), ("11:30", "12:30", MK, MS)],
            "Tuesday": [("06:00", "07:00", GS, AD), ("07:00", "09:00", FB, MS), ("09:30", "10:30", EC, MS),
                        ("10:30", "11:30", GM, AD), ("11:30", "12:30", MK, MS)],
            "Wednesday": [("06:00", "07:00", LCS, MS), ("07:00", "09:00", FB, MS), ("09:30", "10:30", GS, AD),
                          ("10:30", "11:30", PK, MS), ("11:30", "12:30", GM, AD)],
            "Thursday": [("06:00", "07:00", LCS, MS), ("07:00", "09:00", FB, MS), ("09:30", "10:30", PK, MS),
                         ("10:30", "11:30", GM, AD), ("11:30", "12:30", GS, AD)],
            "Friday": [("06:00", "07:00", LCS, MS), ("07:00", "09:00", FB, MS), ("09:30", "10:30", PK, MS)],
        }
        for d, items in chef.items():
            for st, en, (subj, code), tid in items:
                conn.execute(cls, (1, d, st, en, subj, code or None, "class", tid))
            conn.execute(cls, (1, d, "09:00", "09:30", "RECESS", None, "recess", None))
        conn.execute(cls, (1, "Friday", "10:30", "11:30", "Homeroom", None, "homeroom", None))
        conn.execute(cls, (1, "Friday", "11:30", "12:30", "Intervention/Remediation", None,
                           "intervention", None))
        for d in DAYS:
            conn.execute(cls, (2, d, "13:00", "15:00", "Practical Research 2", "PR2", "class", 3))
            conn.execute(cls, (2, d, "15:00", "15:30", "RECESS", None, "recess", None))
            conn.execute(cls, (2, d, "15:30", "17:30", "Bartending", "BAR", "class", 3))
        conn.commit()

    if not conn.execute("SELECT 1 FROM users WHERE lower(username)='admin2'").fetchone():
        conn.execute("""INSERT INTO users(teacher_id,username,full_name,role,category,password_hash,
                         intervention_min,ancillary_min) VALUES(?,?,?,?,?,?,?,?)""",
                     ("ADMIN-002", "admin2", "System Administrator", "admin", None,
                      generate_password_hash("admin123"), 0, 0))
        conn.commit()
    conn.close()


def get_cfg():
    cfg = dict(DEFAULT_CFG)
    try:
        for r in query("SELECT k,v FROM settings"):
            cfg[r["k"]] = r["v"]
    except sqlite3.Error:
        pass
    return cfg


@app.context_processor
def inject():
    cfg = get_cfg()
    u = g.get("user")
    pending = (query("SELECT COUNT(*) AS n FROM signup_requests", one=True)["n"]
               if u and u["role"] == "admin" else 0)
    logo = query("SELECT updated FROM files WHERE k='logo'", one=True)
    new_reports = admin_alerts() if u and u["role"] == "admin" else 0
    bell = 0
    if u:
        bell = (new_reports if u["role"] == "admin" else
                query("SELECT COUNT(*) AS n FROM notifications WHERE user_id=? AND is_read=0",
                      (u["id"],), one=True)["n"])
    return {"cfg": cfg, "new_reports": new_reports, "bell": bell,
            "tlabels": teacher_labels() if u else {}, "pending": pending,
            "has_logo": True, "custom_logo": bool(logo),
            "logo_url": url_for("logo", v=logo["updated"] if logo else 0),
            "year": time.strftime("%Y"),
            "approval": approval() if u and u["role"] == "admin" else None}


# ------------------------------------------------------------------- helpers
@app.before_request
def load_user():
    uid = session.get("uid")
    g.user = query("SELECT * FROM users WHERE id=?", (uid,), one=True) if uid else None
    if request.method == "POST":
        sent = request.form.get("csrf", "")
        if not sent or not secrets.compare_digest(sent, session.get("csrf", "")):
            abort(400)


@app.errorhandler(400)
@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(413)
def show_error(e):
    notes = {400: ("Request not accepted", "Your session may have expired. Go back, reload the page and try again."),
             403: ("Access not allowed", "Your account does not have permission to open this page."),
             404: ("Page not found", "The page you asked for does not exist."),
             413: ("File too large", "The file you sent is too large. Use smaller screenshots (3 MB each, 5 at most).")}
    title, text = notes[e.code]
    return render_template("error.html", title=title, text=text), e.code


def tomin(v):
    h, m = v.split(":")[:2]
    return int(h) * 60 + int(m)


@app.template_filter("tm")
def tm(v):
    h, m = divmod(int(v), 60)
    return f"{(h % 12) or 12}:{m:02d} {'AM' if h < 12 else 'PM'}"


@app.template_filter("t12")
def t12(v):
    return tm(tomin(v))


@app.template_filter("tmin")
def tmin(v):
    return tomin(v)


@app.template_filter("stamp12")
def stamp12(v):
    """Format a stored 'YYYY-MM-DD HH:MM' timestamp as normal Philippine time,
    e.g. 'Nov 8, 2026, 2:30 PM' instead of military time."""
    try:
        d = time.strptime((v or "").strip(), "%Y-%m-%d %H:%M")
    except ValueError:
        return v or ""
    h = (d.tm_hour % 12) or 12
    return (time.strftime("%b ", d) + str(d.tm_mday) + time.strftime(", %Y, ", d)
            + f"{h}:{d.tm_min:02d} " + ("AM" if d.tm_hour < 12 else "PM"))


def official_minutes(text):
    """Length of the official time, e.g. '6:00 AM - 3:00 PM' -> 540. None when unreadable."""
    found = re.findall(r"(\d{1,2})(?::(\d{2}))?\s*(AM|PM|NN)\b", text or "", re.I)
    if len(found) < 2:
        return None

    def conv(h, m, ap):
        h, m, ap = int(h), int(m or 0), ap.upper()
        h = h % 12 if ap == "AM" else (h % 12 + 12 if ap == "PM" else 12)
        return h * 60 + m
    span = conv(*found[1]) - conv(*found[0])
    return span if span > 0 else None


@app.template_filter("hrs")
def hrs(total):
    h, m = divmod(int(total), 60)
    parts = []
    if h:
        parts.append(f"{h} hr" + ("s" if h != 1 else ""))
    if m:
        parts.append(f"{m} min")
    return " ".join(parts) or "0 hrs"


def login_required(role=None):
    def deco(f):
        @wraps(f)
        def wrapper(*a, **k):
            if not g.user:
                return redirect(url_for("login"))
            if role and g.user["role"] != role:
                abort(403)
            return f(*a, **k)
        return wrapper
    return deco


def grades_for(user):
    return GRADES.get(user["category"], [])


def to_int(v, lo=0, hi=600):
    try:
        n = int(v)
    except (TypeError, ValueError):
        return None
    return n if lo <= n <= hi else None


def admin_alerts():
    """What the administrator's bell counts: unread problem reports plus account
    requests and password-reset requests that are still waiting for action."""
    return sum(query(sql, one=True)["n"] for sql in (
        "SELECT COUNT(*) AS n FROM reports WHERE is_read=0",
        "SELECT COUNT(*) AS n FROM signup_requests",
        "SELECT COUNT(*) AS n FROM reset_requests"))


def teacher_labels():
    """TEACHER-01, TEACHER-02 ... in the order the teacher accounts were created."""
    rows = query("SELECT id FROM users WHERE role='teacher' ORDER BY id")
    return {r["id"]: f"TEACHER-{i:02d}" for i, r in enumerate(rows, 1)}


def ancillary_text(t):
    adv = query("SELECT name FROM sections WHERE adviser_id=? ORDER BY name", (t["id"],))
    return (t["ancillary"] or "").strip() or (
        "ADVISER (" + ", ".join(a["name"].upper() for a in adv) + ")" if adv else "None")


def category_clash(tid, cat):
    """True when the teacher still has periods or an advisory outside the new grade level."""
    gs = GRADES[cat]
    marks = ",".join("?" * len(gs))
    return bool(query(f"""SELECT 1 FROM classes c JOIN sections s ON s.id=c.section_id
                          WHERE c.teacher_id=? AND s.grade NOT IN ({marks})""", (tid, *gs), one=True)
                or query(f"SELECT 1 FROM sections WHERE adviser_id=? AND grade NOT IN ({marks})",
                         (tid, *gs), one=True))


def sync_category(tid):
    """Keep a teacher's grade level matching what they are assigned: class periods and
    advisory in both Grade 11 and Grade 12 -> MID Teacher; only one grade level left ->
    back to G11 or G12. A teacher with no assignments at all keeps whatever the
    administrator set."""
    if not tid:
        return
    t = query("SELECT * FROM users WHERE id=? AND role='teacher'", (tid,), one=True)
    if not t:
        return
    gs = {r["grade"] for r in query(
        """SELECT s.grade FROM classes c JOIN sections s ON s.id=c.section_id
           WHERE c.teacher_id=? UNION SELECT grade FROM sections WHERE adviser_id=?""",
        (tid, tid))}
    new = "MID" if gs >= {11, 12} else ("G11" if gs == {11} else ("G12" if gs == {12} else None))
    if not new or new == t["category"]:
        return
    run("UPDATE users SET category=? WHERE id=?", (new, tid))
    if new == "MID":
        msg = ("Your role was automatically changed to MID Teacher (Grades 11 and 12) "
               "because you were assigned in both grade levels.")
    else:
        msg = (f"Your role was automatically changed back to {CATS[new]} "
               "because you are now assigned in one grade level only.")
    notify(tid, "role", msg, url_for("profile"))


def maybe_promote_to_mid(tid, sec_grade):
    """When a G11-only or G12-only teacher is assigned a class in the other grade
    level, they now teach both levels, so their role becomes MID teacher
    (handles grades 11 and 12) and every entry in their program counts under
    that role. The teacher is notified of the change."""
    sync_category(tid)


def timeline(entries):
    """Turn entries into a Monday-Friday timetable.

    Rows run between every start/end time found in the entries. An entry that
    lasts across several rows becomes one tall cell (rowspan), like the printed
    program. Returns (rows, cells, rowmins).
    """
    pts = sorted({tomin(e["start"]) for e in entries} | {tomin(e["end"]) for e in entries})
    rows = list(zip(pts, pts[1:]))
    idx = {p: i for i, p in enumerate(pts)}
    cells = {d: [None] * len(rows) for d in DAYS}
    rowmins = [0] * len(rows)
    for e in sorted(entries, key=lambda r: (tomin(r["start"]), tomin(r["end"]))):
        i, j = idx[tomin(e["start"])], idx[tomin(e["end"])]
        if e["kind"] == "class":
            rowmins[i] += tomin(e["end"]) - tomin(e["start"])
        col = cells[e["day"]]
        if col[i] is None:
            span = j - i
            for k in range(i + 1, j):
                if col[k] is not None:
                    span = k - i
                    break
            col[i] = {"e": e, "span": span, "more": []}
            for k in range(i + 1, i + span):
                col[k] = "skip"
        else:  # overlapping data from an older version: keep it visible
            owner = col[i]
            if owner == "skip":
                k = i
                while col[k] == "skip":
                    k -= 1
                owner = col[k]
            owner["more"].append(e)
    return rows, cells, rowmins


def parse_minutes(text):
    """Minutes from '45', '1:00 PM - 2:30 PM' or '13:00-14:30'. None when it cannot be read."""
    text = (text or "").strip()
    if text.isdigit():
        return int(text)
    span = official_minutes(text)
    if span:
        return span
    f = re.match(r"^(\d{1,2}):(\d{2})\s*(?:-|to)\s*(\d{1,2}):(\d{2})$", text)
    if f:
        d = (int(f[3]) * 60 + int(f[4])) - (int(f[1]) * 60 + int(f[2]))
        return d if d > 0 else None
    return None


def minute_overrides(tid):
    r = query("SELECT v FROM settings WHERE k=?", (f"tmins_{tid}",), one=True)
    try:
        data = json.loads(r["v"]) if r else {}
    except ValueError:
        data = {}
    return data if isinstance(data, dict) else {}


def teacher_summary(t):
    auto = {d: 0 for d in DAYS}
    for r in query("SELECT day,start,end FROM classes WHERE teacher_id=? AND kind='class'", (t["id"],)):
        auto[r["day"]] += tomin(r["end"]) - tomin(r["start"])
    inter0, anc0 = t["intervention_min"] or 0, t["ancillary_min"] or 0
    ov = minute_overrides(t["id"])

    def pick(key, d, default):
        v = (ov.get(key) or {}).get(d)
        return v if isinstance(v, int) and 0 <= v <= 1440 else default
    per = {d: pick("teach", d, auto[d]) for d in DAYS}
    inter = {d: pick("inter", d, inter0) for d in DAYS}
    anc = {d: pick("anc", d, anc0) for d in DAYS}
    total = {d: per[d] + inter[d] + anc[d] for d in DAYS}
    loads = query("""SELECT COUNT(*) AS n FROM (SELECT DISTINCT section_id, subject FROM classes
                     WHERE teacher_id=? AND kind='class')""", (t["id"],), one=True)["n"]
    official = official_minutes(t["official_time"])
    total_w = sum(total.values())
    # Weekly workload follows the official time when it is set (minutes per day x 5 days).
    work_w = official * len(DAYS) if official else total_w
    return dict(teach=per, teach_w=sum(per.values()), inter=inter, inter_w=sum(inter.values()),
                anc=anc, anc_w=sum(anc.values()), total=total, total_w=total_w, work_w=work_w,
                loads=loads, official=official,
                auto=dict(teach=auto, inter=inter0, anc=anc0))


# -------------------------------------------------------------------- auth
@app.route("/", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("home"))
    sel = request.form.get("utype", "")
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        num = request.form.get("teacher_num", "").strip()
        tid = f"T-{num}" if num else ""
        key = (request.remote_addr, username.lower())
        count, first = FAILS.get(key, (0, 0))
        if count and time.time() - first > LOCK_SECONDS:
            FAILS.pop(key, None)
            count = 0
        if count >= MAX_FAILS:
            flash("Too many failed sign-in attempts. Wait 5 minutes and try again.", "error")
            return render_template("login.html", types=USER_TYPES, sel=sel)
        u = query("SELECT * FROM users WHERE lower(username)=lower(?)", (username,), one=True)
        ok = False
        if u and check_password_hash(u["password_hash"], request.form.get("password", "")):
            if sel == "ADMIN":
                ok = u["role"] == "admin"
            elif sel in CATS:
                ok = (u["role"] == "teacher" and u["category"] == sel
                      and (u["teacher_id"] or "").lower() == tid.lower())
        if ok:
            FAILS.pop(key, None)
            session.clear()
            session.permanent = True
            session["uid"] = u["id"]
            audit_event(u, "Signed in")
            return redirect(url_for("home"))
        FAILS[key] = (count + 1, first if count else time.time())
        audit_event(None, "Failed sign-in", f"username: {username[:40]}")
        flash("Sign-in failed. Check the user type, username, Teacher ID and password.", "error")
    return render_template("login.html", types=USER_TYPES, sel=sel)


MAX_PENDING = 100
SIGNUP_LOG = {}  # ip -> times of recent sign-up requests
RESET_LOG = {}  # ip -> times of recent forgot-password requests
MAX_RESETS = 200



# ---------------------------------------------------------------- Gmail verification (OTP)
GMAIL_RE = re.compile(r"[a-z0-9][a-z0-9._+-]{0,63}@gmail\.com")
OTP_MINUTES, OTP_TRIES, OTP_WAIT = 10, 5, 60
OTP_LOG = {}  # ip -> times of recent code requests


@app.context_processor
def _mail_helpers():
    return {"mask_email": lambda a: mask_email(a)}


def valid_gmail(addr):
    return bool(GMAIL_RE.fullmatch((addr or "").strip().lower()))


def mask_email(addr):
    name, _, host = (addr or "").partition("@")
    return (name[:2] + "*" * max(1, len(name) - 2) + "@" + host) if name else ""


def mail_ready():
    return bool(os.environ.get("BREVO_API_KEY") or
                (os.environ.get("GMAIL_USER") and os.environ.get("GMAIL_APP_PASSWORD")))


def send_mail(to, subject, text):
    """Send one plain-text email. Returns (True, '') or (False, reason).
    BREVO_API_KEY (+ MAIL_FROM)  -> Brevo over HTTPS, which also works on hosts that block SMTP.
    GMAIL_USER + GMAIL_APP_PASSWORD -> Gmail SMTP (needs a host that allows port 587)."""
    sender_name = get_cfg().get("school_name") or "Teacher Scheduling System"
    try:
        if os.environ.get("BREVO_API_KEY"):
            import urllib.request
            frm = os.environ.get("MAIL_FROM") or os.environ.get("GMAIL_USER") or ""
            body = json.dumps({"sender": {"name": sender_name, "email": frm},
                               "to": [{"email": to}], "subject": subject,
                               "textContent": text}).encode()
            req = urllib.request.Request(
                "https://api.brevo.com/v3/smtp/email", data=body, method="POST",
                headers={"api-key": os.environ["BREVO_API_KEY"], "content-type": "application/json",
                         "accept": "application/json"})
            urllib.request.urlopen(req, timeout=15).read()
            return True, ""
        if os.environ.get("GMAIL_USER") and os.environ.get("GMAIL_APP_PASSWORD"):
            import smtplib
            from email.message import EmailMessage
            msg = EmailMessage()
            msg["From"] = f"{sender_name} <{os.environ['GMAIL_USER']}>"
            msg["To"], msg["Subject"] = to, subject
            msg.set_content(text)
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as smtp:
                smtp.starttls()
                smtp.login(os.environ["GMAIL_USER"], os.environ["GMAIL_APP_PASSWORD"].replace(" ", ""))
                smtp.send_message(msg)
            return True, ""
        if os.environ.get("OTP_DEBUG"):  # testing only: show the email in the server log
            print(f"[OTP_DEBUG] to {to}: {subject}\n{text}")
            return True, ""
        return False, "Email sending is not set up yet. Please tell the administrator."
    except Exception as exc:  # network, login or provider problems
        print("Email could not be sent:", exc)
        return False, "The code could not be sent right now. Please try again in a moment."


def _otp_hash(code, email, purpose):
    import hashlib, hmac
    return hmac.new(app.secret_key.encode() if isinstance(app.secret_key, str) else app.secret_key,
                    f"{purpose}|{email}|{code}".encode(), hashlib.sha256).hexdigest()


def send_otp(purpose, email, ref="", payload=None):
    """Create and email a 6-digit code. Returns (True, '') or (False, reason)."""
    if not mail_ready() and not os.environ.get("OTP_DEBUG"):
        return False, "Email sending is not set up yet. Please tell the administrator."
    now = time.time()
    ip_recent = [t for t in OTP_LOG.get(request.remote_addr, []) if now - t < 600]
    if len(ip_recent) >= 8:
        return False, "Too many codes requested from this device. Please wait 10 minutes."
    last = query("SELECT created FROM otp_codes WHERE purpose=? AND email=? ORDER BY id DESC",
                 (purpose, email), one=True)
    if last and now - last["created"] < OTP_WAIT:
        return False, f"Please wait {int(OTP_WAIT - (now - last['created'])) + 1} seconds before asking for a new code."
    code = f"{secrets.randbelow(1000000):06d}"
    ok, err = send_mail(email, "Your verification code",
                        f"Your verification code is {code}\n\nIt expires in {OTP_MINUTES} minutes. "
                        "If you did not ask for this code, you can ignore this email and nothing will change.")
    if not ok:
        return False, err
    run("DELETE FROM otp_codes WHERE purpose=? AND email=?", (purpose, email))
    run("INSERT INTO otp_codes(purpose,email,ref,code_hash,expires,created,payload) VALUES(?,?,?,?,?,?,?)",
        (purpose, email, str(ref), _otp_hash(code, email, purpose), now + OTP_MINUTES * 60, now,
         json.dumps(payload) if payload is not None else None))
    OTP_LOG[request.remote_addr] = ip_recent + [now]
    return True, ""


def check_otp(purpose, email, code):
    """Returns (payload_or_True, '') when right, or (None, reason). A wrong code uses one try."""
    import hmac
    row = query("SELECT * FROM otp_codes WHERE purpose=? AND email=? ORDER BY id DESC", (purpose, email), one=True)
    code = (code or "").strip().replace(" ", "")
    if not row:
        return None, "No code was sent yet. Ask for a new one."
    if time.time() > row["expires"]:
        run("DELETE FROM otp_codes WHERE id=?", (row["id"],))
        return None, "That code has expired. Ask for a new one."
    if row["attempts"] >= OTP_TRIES:
        run("DELETE FROM otp_codes WHERE id=?", (row["id"],))
        return None, "Too many wrong tries. Ask for a new code."
    if not hmac.compare_digest(row["code_hash"], _otp_hash(code, email, purpose)):
        run("UPDATE otp_codes SET attempts=attempts+1 WHERE id=?", (row["id"],))
        return None, "That code is not correct. Check the email and try again."
    run("DELETE FROM otp_codes WHERE id=?", (row["id"],))
    return (json.loads(row["payload"]) if row["payload"] else True), ""


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """A teacher who forgot their password sends a request that the administrator handles."""
    if request.method == "POST":
        f = request.form
        user = clean(f.get("username"), 40)
        num = (f.get("teacher_num") or "").strip()
        tcode = f"T-{num}" if num else ""
        now = time.time()
        recent = [t for t in RESET_LOG.get(request.remote_addr, []) if now - t < 600]
        err = None
        u = None
        if len(recent) >= 5:
            err = "Too many requests from this device. Please wait 10 minutes and try again."
        elif not user:
            err = "Enter your username."
        elif not num.isdigit():
            err = "Enter your Teacher ID number (digits only)."
        else:
            u = query("""SELECT * FROM users WHERE lower(username)=lower(?) AND role='teacher'
                         AND lower(teacher_id)=lower(?)""", (user, tcode), one=True)
            if not u:
                err = "We could not find a teacher account with that username and Teacher ID."
        if err:
            flash(err, "error")
            return render_template("forgot_password.html", v=f)
        RESET_LOG[request.remote_addr] = recent + [now]
        if query("SELECT COUNT(*) AS n FROM reset_requests", one=True)["n"] >= MAX_RESETS:
            flash("The request list is full. Please contact the administrator directly.", "error")
            return render_template("forgot_password.html", v=f)
        run("INSERT INTO reset_requests(username,full_name,teacher_id,note,created) VALUES(?,?,?,?,?)",
            (u["username"], u["full_name"], u["teacher_id"], "Forgot password.", ph_stamp()))
        flash("Your request was sent to the administrator. Ask them to reset your password; "
              "you will get a temporary password to change in Settings.", "ok")
        return redirect(url_for("login"))
    return render_template("forgot_password.html", v={})


@app.route("/forgot-password/verify", methods=["GET", "POST"])
def forgot_verify():
    return redirect(url_for("forgot_password"))


def next_teacher_id():
    """The next Teacher ID in sequence, one past the highest number currently in use,
    so a newly approved teacher's ID continues the existing chronological order."""
    best = 1000
    for row in query("SELECT teacher_id FROM users WHERE role='teacher' AND teacher_id IS NOT NULL"):
        m = re.fullmatch(r"T-(\d+)", (row["teacher_id"] or "").strip())
        if m:
            best = max(best, int(m.group(1)))
    n = best + 1
    while query("SELECT 1 FROM users WHERE lower(teacher_id)=lower(?)", (f"T-{n}",), one=True):
        n += 1
    return f"T-{n}"


def id_taken(username, tid, skip_req=0):
    """True when the username or Teacher ID is used by an account or another waiting request."""
    return bool(
        query("SELECT 1 FROM users WHERE lower(username)=lower(?) OR lower(teacher_id)=lower(?)",
              (username, tid), one=True)
        or query("""SELECT 1 FROM signup_requests WHERE id!=?
                    AND (lower(username)=lower(?) OR lower(teacher_id)=lower(?))""",
                 (skip_req, username, tid), one=True))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    """Teachers without an account send a request; the administrator checks and approves it."""
    if g.user:
        return redirect(url_for("home"))
    f = request.form
    if request.method == "POST":
        name, user = clean(f.get("full_name")), clean(f.get("username"), 40)
        cat, pw = f.get("category", ""), f.get("password", "")
        num = f.get("teacher_num", "").strip()
        tid = f"T-{int(num)}" if num.isdigit() and len(num) <= 9 and int(num) > 0 else ""
        now = time.time()
        recent = [t for t in SIGNUP_LOG.get(request.remote_addr, []) if now - t < 600]
        err = None
        if len(recent) >= 5:
            err = "Too many requests from this device. Please wait 10 minutes and try again."
        elif not (name and user) or cat not in CATS:
            err = "Complete all fields and choose the grade level you handle."
        elif not tid:
            err = "Enter your Teacher ID number (digits only), for example 1001."
        elif not re.fullmatch(r"[A-Za-z0-9_.-]{3,40}", user):
            err = "The username needs 3 to 40 letters, numbers, dots, dashes or underscores (no spaces)."
        elif len(pw) < 6:
            err = "The password needs at least 6 characters."
        elif pw != f.get("confirm"):
            err = "The password and its confirmation do not match."
        elif id_taken(user, tid):
            err = "That username or Teacher ID is already in use or waiting for approval. Check your Teacher ID with the administrator."
        elif query("SELECT COUNT(*) AS n FROM signup_requests", one=True)["n"] >= MAX_PENDING:
            err = "The request list is full. Please contact the administrator."
        if err:
            flash(err, "error")
            return render_template("signup.html", v=f)
        SIGNUP_LOG[request.remote_addr] = recent + [now]
        run("""INSERT INTO signup_requests(full_name,username,teacher_id,category,password_hash,email,created)
               VALUES(?,?,?,?,?,?,?)""", (name, user, tid, cat, generate_password_hash(pw), "", ph_stamp()))
        flash("Your request was sent. You can sign in once the administrator approves your account.", "ok")
        return redirect(url_for("login"))
    return render_template("signup.html", v={})


def email_taken(email, skip_uid=0):
    return False


@app.route("/signup/verify", methods=["GET", "POST"])
def signup_verify():
    return redirect(url_for("signup"))


TEMP_PASSWORD = "teacher123"  # what a reset gives the teacher; they change it in Settings


def random_password(n=8):
    import secrets, string
    alpha = string.ascii_uppercase + string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alpha) for _ in range(n))


@app.route("/admin/requests", methods=["GET", "POST"])
@login_required("admin")
def signup_requests():
    if request.method == "POST":
        f = request.form
        if f.get("action") == "reset_done":
            rr = query("SELECT * FROM reset_requests WHERE id=?", (f.get("rrid", type=int),), one=True)
            if not rr:
                flash("That password reset request was already handled.", "error")
            else:
                u = query("SELECT * FROM users WHERE lower(username)=lower(?) AND role='teacher'",
                          (rr["username"],), one=True)
                if not u:
                    flash("That teacher account no longer exists.", "error")
                else:
                    temp = TEMP_PASSWORD
                    run("UPDATE users SET password_hash=? WHERE id=?",
                        (generate_password_hash(temp), u["id"]))
                    run("DELETE FROM reset_requests WHERE id=?", (rr["id"],))
                    notify(u["id"], "reset",
                           f"Your password was reset by the administrator. Temporary password: {temp} "
                           "- please sign in and change it in Settings.", url_for("account_settings"))
                    flash(f"{u['full_name']}'s password was reset to the temporary password "
                          f"{temp} and they were notified in-app.", "ok")
            return redirect(url_for("reports"))
        if f.get("action") == "reset_cancel":
            run("DELETE FROM reset_requests WHERE id=?", (f.get("rrid", type=int),))
            flash("Password reset request dismissed.", "ok")
            return redirect(url_for("reports"))
        r = query("SELECT * FROM signup_requests WHERE id=?", (f.get("rid", type=int),), one=True)
        if not r:
            flash("That request was already handled.", "error")
        elif f.get("action") == "reject":
            run("DELETE FROM signup_requests WHERE id=?", (r["id"],))
            flash(f"Request from {r['full_name']} was rejected and removed.", "ok")
        else:
            name, cat = clean(f.get("full_name")), f.get("category", "")
            num = f.get("teacher_num", "").strip()
            tid = f"T-{num}" if num else ""
            if not (name and num) or cat not in CATS:
                flash("Enter the name and Teacher ID number and choose a grade level.", "error")
            elif not num.isdigit():
                flash("The Teacher ID number must be a whole number.", "error")
            elif id_taken(r["username"], tid, skip_req=r["id"]):
                flash("That Teacher ID or username is already in use.", "error")
            else:
                try:
                    run("""INSERT INTO users(teacher_id,username,full_name,role,category,password_hash,
                                             intervention_min,ancillary_min) VALUES(?,?,?,?,?,?,0,0)""",
                        (tid, r["username"], name, "teacher", cat, r["password_hash"]))
                    run("DELETE FROM signup_requests WHERE id=?", (r["id"],))
                    flash(f"{name} was approved and added to the teachers list. They sign in with "
                          f"username {r['username']} and Teacher ID {tid}. Set their specialization, "
                          "ancillary and official time in Teacher Management.", "ok")
                except sqlite3.IntegrityError:
                    flash("That Teacher ID or username is already in use.", "error")
        return redirect(url_for("reports"))
    return redirect(url_for("reports"))


@app.route("/logout")
def logout():
    if g.get("user"):
        audit_event(g.user, "Signed out")
    session.clear()
    return redirect(url_for("login"))


@app.route("/home")
@login_required()
def home():
    return redirect(url_for("dashboard" if g.user["role"] == "admin" else "profile"))


@app.route("/account")
@login_required()
def account():
    """Profile: the account's own visible details. Read-only; see Settings to change anything."""
    teacher = g.user["role"] == "teacher"
    return render_template("account.html",
                           summ=teacher_summary(g.user) if teacher else None,
                           ancillary=ancillary_text(g.user) if teacher else "")


@app.route("/account/settings", methods=["GET", "POST"])
@login_required()
def account_settings():
    """Settings: edit name/username and change password."""
    if request.method == "POST":
        f = request.form
        if f.get("action") == "profile":
            name = clean(f.get("full_name"))
            user = clean(f.get("username"), 40)
            if not (name and user):
                flash("Enter your name and username.", "error")
            elif not re.fullmatch(r"[A-Za-z0-9_.-]{3,40}", user):
                flash("The username needs 3 to 40 letters, numbers, dots, dashes or underscores "
                      "(no spaces).", "error")
            elif query("SELECT 1 FROM users WHERE lower(username)=lower(?) AND id!=?",
                       (user, g.user["id"]), one=True):
                flash("That username is already in use.", "error")
            else:
                run("UPDATE users SET full_name=?, username=? WHERE id=?", (name, user, g.user["id"]))
                flash("Profile updated.", "ok")
            return redirect(url_for("account_settings"))
        if not check_password_hash(g.user["password_hash"], f.get("current", "")):
            flash("The current password is incorrect.", "error")
        elif len(f.get("new", "")) < 6:
            flash("The new password needs at least 6 characters.", "error")
        elif f.get("new") != f.get("confirm"):
            flash("The new password and its confirmation do not match.", "error")
        else:
            run("UPDATE users SET password_hash=? WHERE id=?",
                (generate_password_hash(f["new"]), g.user["id"]))
            flash("Password changed.", "ok")
        return redirect(url_for("account_settings"))
    return render_template("account_settings.html")


def ph_time():
    """The current time as a struct_time in Philippines time (GMT+8), regardless of the
    server's own timezone, since this school is in the Philippines."""
    return time.gmtime(time.time() + 8 * 3600)


def ph_stamp():
    """The current Philippines-time timestamp, formatted the way it is stored in the database."""
    return time.strftime("%Y-%m-%d %H:%M", ph_time())


def today_text():
    d = ph_time()
    return time.strftime("%B ", d) + str(d.tm_mday) + time.strftime(", %Y", d)


def notify(uid, kind, message, link=None):
    """Tell a teacher something changed. Admin accounts never receive these."""
    if not uid:
        return
    u = query("SELECT role FROM users WHERE id=?", (uid,), one=True)
    if not u or u["role"] != "teacher":
        return
    actor = g.user["full_name"] if g.get("user") and g.user["role"] == "admin" else None
    if actor:
        message = f"{message} (By: {actor})"
    run("INSERT INTO notifications(user_id,kind,message,link,created,is_read) VALUES(?,?,?,?,?,0)",
        (uid, kind, message, link, ph_stamp()))
    g.setdefault("_notified", set()).add(uid)
    run("""DELETE FROM notifications WHERE user_id=? AND id NOT IN
           (SELECT id FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT 100)""", (uid, uid))


def notify_program(uid):
    """Generic 'your program changed' notice. Repeated edits refresh one unread notice
    instead of stacking up, and a more specific notice made in the same request wins."""
    if uid in g.get("_notified", set()):
        return
    row = query("SELECT id FROM notifications WHERE user_id=? AND kind='program' AND is_read=0",
                (uid,), one=True)
    if row:
        run("UPDATE notifications SET created=? WHERE id=?", (ph_stamp(), row["id"]))
        g.setdefault("_notified", set()).add(uid)
    else:
        notify(uid, "program", "The administrator updated your Teacher's Program.", url_for("profile"))


def sec_label(sec):
    return sec["name"]


def short_section(name):
    """'11-Chef' -> 'Chef' (the grade prefix is added again when saving)."""
    return re.sub(r"^\s*1[12]\s*[-\u2013]\s*", "", name or "").strip()


def full_section(grade, name):
    base = short_section(name)
    return f"{grade}-{base}" if base else ""


app.jinja_env.filters["shortsec"] = lambda v: short_section(v)


def dur_options(cur, hi=600):
    """Choices for a per-day duration: every 5 min up to 3 hrs, then every 15 min."""
    vals = set(range(0, 181, 5)) | set(range(180, hi + 1, 15))
    try:
        vals.add(int(cur or 0))
    except (TypeError, ValueError):
        vals.add(0)
    return sorted(v for v in vals if v <= max(hi, int(cur or 0)))


def dur_text(v):
    h, m = divmod(int(v), 60)
    parts = []
    if h:
        parts.append(f"{h} hr" + ("s" if h != 1 else ""))
    if m:
        parts.append(f"{m} min")
    return " ".join(parts) or "0 min"


def official_range(text):
    """'6:00 AM - 3:00 PM' -> ('06:00', '15:00') for the time pickers."""
    found = re.findall(r"(\d{1,2})(?::(\d{2}))?\s*(AM|PM|NN)\b", text or "", re.I)
    if len(found) < 2:
        return ("", "")

    def conv(h, m, ap):
        h, m, ap = int(h), int(m or 0), ap.upper()
        h = h % 12 if ap == "AM" else (h % 12 + 12 if ap == "PM" else 12)
        return f"{h % 24:02d}:{m:02d}"
    return (conv(*found[0]), conv(*found[1]))


app.jinja_env.globals["dur_options"] = dur_options
app.jinja_env.filters["durtxt"] = dur_text
app.jinja_env.filters["otimes"] = official_range


def touch(kind, ident):
    """Remember the date the admin last changed a class program or a teacher's program."""
    if ident:
        run("INSERT OR REPLACE INTO settings(k,v) VALUES(?,?)", (f"upd_{kind}_{ident}", today_text()))
        if kind == "teacher":
            notify_program(ident)


def touch_teacher_of_entry(tid):
    touch("teacher", tid)


def touch_recess_teachers(sid):
    """A recess change also shows on the Teacher's Program of everyone teaching that section."""
    for r in query("SELECT DISTINCT teacher_id FROM classes WHERE section_id=? AND teacher_id IS NOT NULL", (sid,)):
        touch("teacher", r["teacher_id"])


def stamp(kind, ident):
    """The date the admin last changed the program, or None when it was never updated."""
    r = query("SELECT v FROM settings WHERE k=?", (f"upd_{kind}_{ident}",), one=True)
    return {"label": "DATE UPDATED", "date": r["v"]} if r else None


# ---------------------------------------------------------- teacher's program
def teacher_data(t):
    """Everything one Teacher's Program page needs."""
    rows = [dict(r) for r in query(
        """SELECT c.*, s.name AS section_name FROM classes c
           JOIN sections s ON s.id=c.section_id WHERE c.teacher_id=? AND c.kind='class'""", (t["id"],))]
    secids = sorted({r["section_id"] for r in rows})
    if secids:  # show the recess of the sections this teacher handles
        seen = set()
        for r in query(f"""SELECT c.*, s.name AS section_name FROM classes c
                           JOIN sections s ON s.id=c.section_id
                           WHERE c.kind='recess' AND c.section_id IN ({','.join('?' * len(secids))})""",
                       secids):
            key = (r["day"], r["start"], r["end"])
            if key not in seen:
                seen.add(key)
                rows.append(dict(r))
    trows, cells, rowmins = timeline(rows)
    return dict(t=t, rows=trows, cells=cells, rowmins=rowmins,
                summ=teacher_summary(t), ancillary=ancillary_text(t),
                stamp=stamp("teacher", t["id"]))


def show_teacher(t):
    pick = (query("SELECT id, full_name, teacher_id FROM users WHERE role='teacher' "
                  "ORDER BY full_name") if g.user["role"] == "admin" else [])
    return render_template("profile.html", t=t, d=teacher_data(t), pick=pick)


@app.route("/profile")
@login_required("teacher")
def profile():
    return show_teacher(g.user)


@app.route("/teacher/<int:tid>")
@login_required("admin")
def teacher_view(tid):
    t = query("SELECT * FROM users WHERE id=? AND role='teacher'", (tid,), one=True)
    if not t:
        abort(404)
    return show_teacher(t)


# -------------------------------------------------------------- class program
def class_data(cur, labels=None):
    """Everything one Class Program page needs."""
    labels = labels or teacher_labels()
    rows = [dict(r) for r in query(
        """SELECT c.*, u.full_name AS teacher_name FROM classes c
           LEFT JOIN users u ON u.id=c.teacher_id WHERE c.section_id=?""", (cur["id"],))]
    adviser = None
    if cur["adviser_id"]:
        a = query("SELECT full_name FROM users WHERE id=?", (cur["adviser_id"],), one=True)
        adviser = a["full_name"] if a else None
    legend = sorted({(r["code"], r["subject"]) for r in rows if r["kind"] == "class" and r["code"]})
    me = g.get("user")
    only_me = bool(me and me["role"] == "teacher")  # teachers see only their own periods named
    for r in rows:
        r["teacher_label"] = labels.get(r["teacher_id"]) if r.get("teacher_id") else None
        r["other"] = bool(only_me and r.get("teacher_id") and r["teacher_id"] != me["id"])
        if r["other"]:
            r["teacher_label"] = r["teacher_name"] = None
    tlegend = sorted({(r["teacher_label"], r["teacher_name"]) for r in rows
                      if r["kind"] == "class" and r["teacher_label"]})
    trows, cells, _ = timeline(rows)
    return dict(cur=cur, rows=trows, cells=cells, adviser=adviser, legend=legend, tlegend=tlegend,
                stamp=stamp("section", cur["id"]))


@app.route("/program")
@login_required()
def program():
    u = g.user
    if u["role"] == "admin":
        secs = [dict(r, is_adv=0) for r in sched_secs()]
    else:
        # Teachers only see the class programs they are actually assigned to:
        # sections where they teach a period, or sections they advise.
        # Sections they advise are labelled (My Advisory) but keep their normal order.
        secs = query("""SELECT DISTINCT s.*, (s.adviser_id=?) AS is_adv FROM sections s
                        WHERE s.adviser_id=? OR EXISTS(
                            SELECT 1 FROM classes c WHERE c.section_id=s.id AND c.teacher_id=?)
                        ORDER BY s.grade, s.name""", (u["id"], u["id"], u["id"]))
    total = len(secs)
    grades = sorted({x["grade"] for x in secs})
    grade = request.args.get("grade", type=int)
    if grade not in grades:
        grade = None
    if grade:
        secs = [x for x in secs if x["grade"] == grade]
    tracks = [t for t in TRACKS if any(x["track"] == t for x in secs)]
    track = request.args.get("track", "")
    if track not in tracks:
        track = ""
    if track:
        secs = [x for x in secs if x["track"] == track]
    gtotal = len(secs)
    q = request.args.get("q", "").strip()[:60]
    if q:  # section name, track or room number: every word must appear
        words = q.lower().split()

        def hit(x):
            hay = f"{x['name']} {x['track'] or ''} {x['room'] or ''}".lower()
            flat = re.sub(r"\s+", "", hay)
            return all(w in hay or w in flat for w in words)
        secs = [x for x in secs if hit(x)]
    sid = request.args.get("section", type=int)
    cur = next((x for x in secs if x["id"] == sid), secs[0] if secs else None)
    d = class_data(cur) if cur else None
    editing = u["role"] == "admin" and request.args.get("edit") == "1"
    docs = []
    if secs and not editing and (u["role"] == "admin" or q):
        labels = teacher_labels()
        docs = [class_data(x, labels) for x in secs]
    teachers = (query("SELECT * FROM users WHERE role='teacher' ORDER BY full_name")
                if editing else [])
    return render_template("program.html", secs=secs, cur=cur, d=d, teachers=teachers,
                           q=q, total=total, gtotal=gtotal, editing=editing, docs=docs,
                           grade=grade, grades=grades, ptracks=tracks, ptrack=track)


def picked_ids():
    return {int(x) for x in request.args.getlist("id") if x.isdigit()}


@app.route("/admin/print/classes")
@login_required("admin")
def print_classes():
    secs = sched_secs()
    ids = picked_ids()
    if not ids:
        items = [(x["id"], x["name"], x["room"] or "", "") for x in secs]
        return render_template("printpick.html", items=items, title="Choose class programs to print",
                               back_url=url_for("program"))
    labels = teacher_labels()
    docs = [class_data(x, labels) for x in secs if x["id"] in ids]
    return render_template("printall.html", kind="class", docs=docs,
                           title="Print selected class programs", back_url=url_for("print_classes"))


@app.route("/admin/print/teachers")
@login_required("admin")
def print_teachers():
    rows = query("SELECT * FROM users WHERE role='teacher' ORDER BY id")
    ids = picked_ids()
    if not ids:
        labels = teacher_labels()
        items = [(t["id"], f"{labels.get(t['id'], 'Teacher')} - {t['full_name']}",
                  t["teacher_id"] or "", f"{t['full_name']} {t['teacher_id'] or ''}".lower())
                 for t in rows]
        return render_template("printpick.html", items=items, title="Choose teachers' programs to print",
                               back_url=url_for("teachers"), searchable=True)
    docs = [teacher_data(t) for t in rows if t["id"] in ids]
    return render_template("printall.html", kind="teacher", docs=docs,
                           title="Print selected teachers' programs", back_url=url_for("print_teachers"))


# --------------------------------------------------------------- admin tools
def overlaps(a1, a2, b1, b2):
    return a1 < b2 and b1 < a2


def valid_time(v):
    try:
        h, m = v.split(":")[:2]
        return 0 <= int(h) < 24 and 0 <= int(m) < 60
    except (ValueError, AttributeError):
        return False


def normalize(kind, subj, tid):
    """Recess, homeroom and intervention periods have no teacher and a standard label."""
    if kind != "class":
        return subj or KIND_LABEL[kind], None
    return subj, tid


def check_entry(sec, day, st, en, subj, tid, kind, exclude=0):
    """Return an error message, or None when the entry can be saved."""
    if (not sec or day not in DAYS or kind not in KINDS or not subj
            or not (valid_time(st) and valid_time(en))):
        return "Complete all fields before saving."
    if tomin(en) <= tomin(st):
        return "End time must be later than start time."
    t = None
    if tid:
        t = query("SELECT * FROM users WHERE id=? AND role='teacher'", (tid,), one=True)
        if not t:
            return "Selected teacher was not found."
        # Note: a teacher assigned outside their current grade level is no longer
        # blocked here; entry_add/entry_edit auto-promotes them to MID instead.
    for r in query("""SELECT c.*, s.name AS sname FROM classes c
                      JOIN sections s ON s.id=c.section_id
                      WHERE c.day=? AND c.id!=? AND (c.section_id=? OR c.teacher_id=?)""",
                   (day, exclude, sec["id"], tid)):
        if overlaps(tomin(st), tomin(en), tomin(r["start"]), tomin(r["end"])):
            who = ("This section already has" if r["section_id"] == sec["id"]
                   else f"{t['full_name']} already teaches")
            return (f"Time conflict on {day}: {who} {r['subject']} ({r['sname']}), "
                    f"{t12(r['start'])} to {t12(r['end'])}.")
    return None


def time_note(mins, ndays, kind, tid):
    """Plain-language time summary shown right after a period is saved."""
    note = f"Time: {hrs(mins)} per day"
    if ndays > 1:
        note += f" x {ndays} days = {hrs(mins * ndays)} per week"
    note += "."
    if kind == "class" and tid:
        t = query("SELECT * FROM users WHERE id=?", (tid,), one=True)
        if t:
            sm = teacher_summary(t)
            note += (f" {teacher_labels().get(tid, 'Teacher')} ({t['full_name']}) now has "
                     f"{hrs(sm['teach_w'])} of teaching per week and {hrs(sm['work_w'])} "
                     "of weekly workload.")
    return note


@app.post("/admin/entry")
@login_required("admin")
def entry_add():
    f = request.form
    sid = f.get("section_id", type=int)
    sec = query("SELECT * FROM sections WHERE id=?", (sid,), one=True)
    kind = f.get("kind", "class")
    days = [d for d in DAYS if d in f.getlist("day")]
    st, en = f.get("start", ""), f.get("end", "")
    code = f.get("code", "").strip() or None
    if kind not in KINDS:
        flash("Choose a valid period type.", "error")
        return redirect(url_for("program", section=sid, edit=1))
    subj, tid = normalize(kind, f.get("subject", "").strip(), f.get("teacher_id", type=int))
    if not days:
        flash("Select at least one day.", "error")
        return redirect(url_for("program", section=sid, edit=1))
    for d in days:
        err = check_entry(sec, d, st, en, subj, tid, kind)
        if err:
            flash(err + " Nothing was saved.", "error")
            return redirect(url_for("program", section=sid, edit=1))
    for d in days:
        run("INSERT INTO classes(section_id,day,start,end,subject,code,kind,teacher_id) "
            "VALUES(?,?,?,?,?,?,?,?)", (sid, d, st, en, subj, code, kind, tid))
    if tid:
        maybe_promote_to_mid(tid, sec["grade"])
        notify(tid, "assigned", f"You were assigned to {sec_label(sec)}: {subj}, "
               f"{', '.join(d[:3] for d in days)}, {t12(st)} to {t12(en)}.", url_for("program", section=sid))
    touch("section", sid)
    touch_teacher_of_entry(tid)
    if kind == "recess":
        touch_recess_teachers(sid)
    flash(f"Saved for {len(days)} day" + ("s. " if len(days) != 1 else ". ")
          + time_note(tomin(en) - tomin(st), len(days), kind, tid), "ok")
    return redirect(url_for("program", section=sid, edit=1))


@app.route("/admin/entry/<int:eid>/edit", methods=["GET", "POST"])
@login_required("admin")
def entry_edit(eid):
    e = query("SELECT * FROM classes WHERE id=?", (eid,), one=True)
    if not e:
        abort(404)
    sec = query("SELECT * FROM sections WHERE id=?", (e["section_id"],), one=True)
    if request.method == "POST":
        f = request.form
        kind = f.get("kind", "class")
        day, st, en = f.get("day"), f.get("start", ""), f.get("end", "")
        code = f.get("code", "").strip() or None
        if kind not in KINDS:
            flash("Choose a valid period type.", "error")
            return redirect(url_for("entry_edit", eid=eid))
        subj, tid = normalize(kind, f.get("subject", "").strip(), f.get("teacher_id", type=int))
        err = check_entry(sec, day, st, en, subj, tid, kind, exclude=eid)
        if err:
            flash(err, "error")
            return redirect(url_for("entry_edit", eid=eid))
        unchanged = (day == e["day"] and st == e["start"] and en == e["end"] and subj == e["subject"]
                     and code == e["code"] and kind == e["kind"] and tid == e["teacher_id"])
        if unchanged:
            flash("No changes were made.", "ok")
            return redirect(url_for("program", section=sec["id"], edit=1))
        run("UPDATE classes SET day=?,start=?,end=?,subject=?,code=?,kind=?,teacher_id=? WHERE id=?",
            (day, st, en, subj, code, kind, tid, eid))
        sync_category(tid)
        sync_category(e["teacher_id"])
        if tid and tid != e["teacher_id"]:
            notify(tid, "assigned", f"You were assigned to {sec_label(sec)}: {subj}, {day}, "
                   f"{t12(st)} to {t12(en)}.", url_for("program", section=sec["id"]))
        if e["teacher_id"] and e["teacher_id"] != tid:
            notify(e["teacher_id"], "removed",
                   f"You were removed from {sec_label(sec)}: {e['subject']}, {e['day']}.", url_for("profile"))
        touch("section", sec["id"])
        touch_teacher_of_entry(tid)
        touch_teacher_of_entry(e["teacher_id"])
        if kind == "recess" or e["kind"] == "recess":
            touch_recess_teachers(sec["id"])
        flash("Class period updated. " + time_note(tomin(en) - tomin(st), 1, kind, tid), "ok")
        return redirect(url_for("program", section=sec["id"], edit=1))
    teachers = query("SELECT * FROM users WHERE role='teacher' ORDER BY full_name")
    return render_template("entry_edit.html", e=e, sec=sec, teachers=teachers)


@app.post("/admin/entry/<int:eid>/delete")
@login_required("admin")
def entry_delete(eid):
    row = query("SELECT section_id, teacher_id, kind, subject, day FROM classes WHERE id=?", (eid,), one=True)
    run("DELETE FROM classes WHERE id=?", (eid,))
    if row:
        sync_category(row["teacher_id"])
        if row["teacher_id"]:
            sec = query("SELECT * FROM sections WHERE id=?", (row["section_id"],), one=True)
            notify(row["teacher_id"], "removed", f"A class period was removed from your program: "
                   f"{row['subject']} ({sec_label(sec) if sec else 'section'}), {row['day']}.", url_for("profile"))
        touch("section", row["section_id"])
        touch_teacher_of_entry(row["teacher_id"])
        if row["kind"] == "recess":
            touch_recess_teachers(row["section_id"])
    flash("Class period removed.", "ok")
    return redirect(url_for("program", section=row["section_id"] if row else None, edit=1))


@app.route("/admin/teachers", methods=["GET", "POST"])
@login_required("admin")
def teachers():
    """05 Teacher Management: accounts, profiles, specialization and availability in one table."""
    if request.method == "POST":
        f = request.form
        try:
            num = f.get("teacher_num", "").strip()
            if not num.isdigit():
                raise ValueError
            fields = [f"T-{num}", f["username"].strip(), f["full_name"].strip()]
            if f["category"] not in CATS or len(f["password"]) < 6 or not all(fields):
                raise ValueError
            run("""INSERT INTO users(teacher_id,username,full_name,role,category,password_hash,
                                     intervention_min,ancillary_min)
                   VALUES(?,?,?,?,?,?,0,0)""",
                (*fields, "teacher", f["category"], generate_password_hash(f["password"])))
            flash("Teacher account created. Press Edit on the new row to set specialization and official time.", "ok")
        except sqlite3.IntegrityError:
            flash("That username or Teacher ID is already in use.", "error")
        except (ValueError, KeyError):
            flash("Complete all fields. The password needs at least 6 characters.", "error")
        return redirect(url_for("teachers"))
    rows = query("SELECT * FROM users WHERE role='teacher' ORDER BY id")  # TEACHER-01, 02, 03 ...
    summ = {r["id"]: teacher_summary(r) for r in rows}
    return render_template("teachers.html", rows=rows, summ=summ, suggested_id=next_teacher_id())


@app.route("/admin/teachers/<int:tid>/edit", methods=["GET", "POST"])
@login_required("admin")
def teacher_edit(tid):
    t = query("SELECT * FROM users WHERE id=? AND role='teacher'", (tid,), one=True)
    if not t:
        abort(404)
    if request.method == "POST":
        f = request.form
        name = f.get("full_name", "").strip()
        num = f.get("teacher_num", "").strip()
        code = f"T-{num}" if num else ""
        user, cat = f.get("username", "").strip(), f.get("category", "")
        inter, anc = to_int(f.get("intervention_min")), to_int(f.get("ancillary_min"))
        back = redirect(url_for("teacher_edit", tid=tid))
        if not (name and num and user) or cat not in CATS:
            flash("Complete the name, Teacher ID number, username and teacher type.", "error")
            return back
        if not num.isdigit():
            flash("The Teacher ID number must be a whole number.", "error")
            return back
        if inter is None or anc is None:
            flash("Minutes must be a whole number from 0 to 600.", "error")
            return back
        if category_clash(tid, cat):
            flash("This teacher still has class periods or an advisory in a grade level the new type "
                  "does not cover. Remove or reassign those first.", "error")
            return back
        item = f.get("item", "").strip()
        subj_area = f.get("subject_area", "").strip()
        spec = f.get("specialization", "").strip()
        load = f.get("teaching_load", "").strip()
        anc_txt = f.get("ancillary", "").strip()
        off = f.get("official_time", "").strip()
        unchanged = (name == t["full_name"] and code == t["teacher_id"] and user == t["username"]
                     and cat == t["category"] and item == (t["item"] or "")
                     and subj_area == (t["subject_area"] or "") and spec == (t["specialization"] or "")
                     and load == (t["teaching_load"] or "") and anc_txt == (t["ancillary"] or "")
                     and off == (t["official_time"] or "") and inter == (t["intervention_min"] or 0)
                     and anc == (t["ancillary_min"] or 0))
        if unchanged:
            flash("No changes were made.", "ok")
            return redirect(url_for("teachers"))
        try:
            run("""UPDATE users SET full_name=?, teacher_id=?, username=?, category=?, item=?,
                   subject_area=?, specialization=?, teaching_load=?, ancillary=?, official_time=?,
                   intervention_min=?, ancillary_min=? WHERE id=?""",
                (name, code, user, cat, item, subj_area, spec, load, anc_txt, off, inter, anc, tid))
            touch("teacher", tid)
            if spec != (t["specialization"] or ""):
                match_quals(tid)
            flash("Teacher details updated.", "ok")
            return redirect(url_for("teachers"))
        except sqlite3.IntegrityError:
            flash("That username or Teacher ID is already in use.", "error")
            return back
    return render_template("teacher_edit.html", t=t)


@app.post("/admin/teachers/<int:tid>/minutes")
@login_required("admin")
def teacher_minutes(tid):
    """Admin edits the daily minutes shown on a Teacher's Program. Totals are computed."""
    t = query("SELECT * FROM users WHERE id=? AND role='teacher'", (tid,), one=True)
    if not t:
        abort(404)
    back = redirect(url_for("teacher_view", tid=tid))
    f = request.form
    if f.get("action") == "reset":
        run("DELETE FROM settings WHERE k=?", (f"tmins_{tid}",))
        touch("teacher", tid)
        flash("The minutes are automatic again.", "ok")
        return back
    sm = teacher_summary(dict(t, official_time=t["official_time"]))
    auto = dict(teach=sm["auto"]["teach"], inter={d: sm["auto"]["inter"] for d in DAYS},
                anc={d: sm["auto"]["anc"] for d in DAYS})
    labels = dict(teach="Daily actual teaching minutes", inter="Intervention / Remediation",
                  anc="Ancillary / Adviser's minutes")
    data, bad = {}, []
    for key in ("teach", "inter", "anc"):
        data[key] = {}
        for d in DAYS:
            raw = f.get(f"{key}_{d}", "").strip()
            if not raw:
                continue
            v = parse_minutes(raw)
            if v is None or v > 1440:
                bad.append(f"{labels[key]} on {d}")
            elif v != auto[key][d]:
                data[key][d] = v
    if bad:
        flash("Could not read: " + "; ".join(bad) + ". Type minutes like 45, or a time like "
              "1:00 PM - 2:30 PM. Nothing was saved.", "error")
        return back
    run("INSERT OR REPLACE INTO settings(k,v) VALUES(?,?)", (f"tmins_{tid}", json.dumps(data)))
    touch("teacher", tid)
    flash("Minutes saved. The total daily working minutes were computed.", "ok")
    return back


@app.post("/admin/teachers/<int:tid>/delete")
@login_required("admin")
def teacher_delete(tid):
    run("UPDATE classes SET teacher_id=NULL WHERE teacher_id=?", (tid,))
    run("UPDATE sections SET adviser_id=NULL WHERE adviser_id=?", (tid,))
    run("DELETE FROM settings WHERE k IN (?,?)", (f"tmins_{tid}", f"upd_teacher_{tid}"))
    run("DELETE FROM users WHERE id=? AND role='teacher'", (tid,))
    flash("Teacher account deleted. Their class periods and advisory are now unassigned. "
          "Other teachers keep their Teacher IDs.", "ok")
    return redirect(url_for("teachers"))


def clean(v, n=200):
    return (v or "").strip()[:n]


def minutes_field(f, key, current):
    v = f.get(key)
    return to_int((current or 0) if v is None else (v.strip() or 0))


# Room numbers from the school floor plans: 2xx = floor 2, 3xx = floor 3, 4xx = floor 4.
# The example sections share rooms the way the plans show (Grade 11 and Grade 12 in one room).
SAMPLE_ROOMS = {"11-Chef": "309", "12-Receptionist": "309",
                "11-Baker": "301", "12-Pastry": "301",
                "11-Barista": "308", "12-Bartender": "308",
                "11-Cookery": "310", "12-Steward": "310",
                "11-Housekeeping": "311", "12-Concierge": "311",
                "11-Tourism": "405", "12-Events": "405"}


def room_place(room):
    """('1', '3') for 'Room 308': building 1, floor from the first digit of the room number."""
    m = re.search(r"\b([234])\d{2}\b", room or "")
    return ("1", m.group(1)) if m else ("", "")


ACADEMIC_SAMPLE = {"11-Tourism", "12-Events", "12-Concierge"}  # the other example sections are TechPro
SAMPLE_CLUSTER = {n: ("Business and Entrepreneurship" if n in ACADEMIC_SAMPLE else "Hospitality and Tourism")
                  for n in list(SAMPLE_ROOMS) + ["11-Chef", "12-Receptionist"]}


def sample_data():
    """Add 10 example sections and 20 example teachers (safe to press twice)."""
    pw = generate_password_hash("teacher123")
    pool = ["Hospitality and Tourism", "Business and Entrepreneurship", "Sports, Health, and Wellness",
            "Hospitality and Tourism", "Arts, Social Sciences, and Humanities"]
    specs = [SPEC_SEP.join([CORE_NAMES[n % 5], CORE_NAMES[(n + 2) % 5], pool[n % len(pool)]]) for n in range(20)]
    names = [("Roberto Villanueva", "G11"), ("Carmela Aquino", "G11"), ("Dennis Magsaysay", "G11"),
             ("Liza Fernandez", "G11"), ("Mark Anthony Ramos", "G11"),
             ("Teresita Bautista", "G12"), ("Rogelio Navarro", "G12"), ("Jennifer Castillo", "G12"),
             ("Eduardo Mendoza", "G12"), ("Gloria Pascual", "G12"),
             ("Ramon Garcia", "MID"), ("Elena Torres", "MID"), ("Victor Domingo", "MID"),
             ("Maribel Soriano", "MID"), ("Albert Cruz", "MID"), ("Rowena Lim", "MID"),
             ("Patrick Santiago", "MID"), ("Nenita Aguilar", "MID"), ("Joel Manalo", "MID"),
             ("Cynthia Estrada", "MID")]
    secs = [(n, int(n[:2]), "Room " + SAMPLE_ROOMS[n]) for n in (
        "11-Baker", "11-Barista", "11-Cookery", "11-Housekeeping", "11-Tourism",
        "12-Bartender", "12-Pastry", "12-Events", "12-Concierge", "12-Steward")]
    slots = {11: [("06:00", "07:00"), ("07:00", "08:00"), ("08:00", "08:30"),
                  ("08:30", "09:30"), ("09:30", "10:30")],
             12: [("13:00", "14:00"), ("14:00", "15:00"), ("15:00", "15:30"),
                  ("15:30", "16:30"), ("16:30", "17:30")]}
    core_pairs = [(n, c) for c, n in CORE_SUBJECTS]
    cluster_code = {c[1]: c[0] for c in ACADEMIC_CLUSTERS + TECHPRO_CLUSTERS}
    tids, new_t, new_s = [], [], 0
    for n, (name, cat) in enumerate(names):
        row = query("SELECT id FROM users WHERE role='teacher' AND lower(full_name)=lower(?)",
                    (name,), one=True)
        if row:
            tids.append(row["id"])
            continue
        parts = name.split()
        user = (parts[0][0] + parts[-1]).lower()
        base, k = user, 1
        while query("SELECT 1 FROM users WHERE lower(username)=?", (user,), one=True):
            k += 1
            user = f"{base}{k}"
        morning = n < 5 or 10 <= n < 15
        run("""INSERT INTO users(teacher_id,username,full_name,role,category,password_hash,item,
                                 specialization,official_time,intervention_min,ancillary_min)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (next_teacher_id(), user, name, "teacher", cat, pw, ["Teacher I", "Teacher II", "Teacher III"][n % 3],
             specs[n % len(specs)], "6:00 AM - 3:00 PM" if morning else "12:00 PM - 7:00 PM",
             60, 60 if n < 10 else 0))
        new = query("SELECT id FROM users WHERE username=?", (user,), one=True)["id"]
        tids.append(new)
        new_t.append(new)
    for i, (name, grade, room) in enumerate(secs):
        if query("SELECT 1 FROM sections WHERE name=?", (name,), one=True):
            continue
        conn = db()
        bld, flr = room_place(room)
        cur = conn.execute("INSERT INTO sections(name,grade,track,room,building,floor,adviser_id,cluster) "
                           "VALUES(?,?,?,?,?,?,?,?)",
                           (name, grade, "Academic" if name in ACADEMIC_SAMPLE else "TechPro", room, bld, flr,
                            tids[i], SAMPLE_CLUSTER[name]))
        conn.commit()
        sid = cur.lastrowid
        sl = slots[grade]
        for day in DAYS:
            for idx, (st, en) in enumerate(sl):
                if idx == 2:
                    run("INSERT INTO classes(section_id,day,start,end,subject,code,kind,teacher_id) "
                        "VALUES(?,?,?,?,?,?,?,?)", (sid, day, st, en, "RECESS", None, "recess", None))
                    continue
                k = idx if idx < 2 else idx - 1
                teacher = tids[i] if k % 2 == 0 else tids[10 + i]
                six = core_pairs + [(SAMPLE_CLUSTER[name], cluster_code[SAMPLE_CLUSTER[name]])]
                sname, code = six[(i + k) % 6]
                run("INSERT INTO classes(section_id,day,start,end,subject,code,kind,teacher_id) "
                    "VALUES(?,?,?,?,?,?,?,?)", (sid, day, st, en, sname, code, "class", teacher))
        touch("section", sid)
        new_s += 1
    for tid in new_t:
        rows = query("SELECT DISTINCT subject FROM classes WHERE teacher_id=? AND kind='class' "
                     "ORDER BY subject", (tid,))
        run("UPDATE users SET subject_area=? WHERE id=?", (" / ".join(r["subject"] for r in rows), tid))
    return len(new_t), new_s


@app.route("/admin/assignments", methods=["GET", "POST"])
@login_required("admin")
def assignments():
    """Saves the editable rows of the Teacher Management table (the page itself is /admin/teachers)."""
    if request.method == "POST":
        f = request.form
        labels, updates, errors = teacher_labels(), [], []
        for t in query("SELECT * FROM users WHERE role='teacher' ORDER BY id"):
            i = t["id"]
            if f"name_{i}" not in f:
                continue
            name, cat = clean(f.get(f"name_{i}")), f.get(f"cat_{i}", "")
            inter = minutes_field(f, f"inter_{i}", t["intervention_min"])
            ancm = minutes_field(f, f"ancm_{i}", t["ancillary_min"])
            if not name or cat not in CATS:
                errors.append(f"{labels[i]}: enter a name and choose a grade level.")
            elif inter is None or ancm is None:
                errors.append(f"{labels[i]}: minutes must be a whole number from 0 to 600.")
            elif cat != t["category"] and category_clash(i, cat):
                errors.append(f"{labels[i]} still has periods or an advisory in a grade level that "
                              "the new type does not cover. Remove or reassign those first.")
            else:
                def pick(key, cur, n=200):
                    return clean(f.get(key), n) if key in f else (cur or "")
                updates.append((name, cat, pick(f"subj_{i}", t["subject_area"], 400), pick(f"spec_{i}", t["specialization"], 800),
                                pick(f"load_{i}", t["teaching_load"], 60), pick(f"anc_{i}", t["ancillary"]),
                                pick(f"time_{i}", t["official_time"], 60), inter, ancm, i))
        if errors:
            for e in errors:
                flash(e + " Nothing was saved.", "error")
        else:
            conn = db()
            old = {r["id"]: tuple(r[k] for k in ("full_name", "category", "subject_area", "specialization",
                                                  "teaching_load", "ancillary", "official_time",
                                                  "intervention_min", "ancillary_min"))
                   for r in query("SELECT * FROM users WHERE role='teacher'")}
            conn.executemany("""UPDATE users SET full_name=?, category=?, subject_area=?,
                                specialization=?, teaching_load=?, ancillary=?, official_time=?, intervention_min=?, ancillary_min=?
                                WHERE id=?""", updates)
            conn.commit()
            for u in updates:
                o = old.get(u[-1])
                if o is not None and tuple((x or "") if isinstance(x, str) or x is None else x for x in o) != \
                        tuple((x or "") if isinstance(x, str) or x is None else x for x in u[:-1]):
                    touch("teacher", u[-1])
                if o is not None and (o[3] or "") != u[3]:
                    match_quals(u[-1])  # a new specialization qualifies the teacher for those subjects
            flash("Teacher details saved.", "ok")
    return redirect(url_for("teachers"))


def adviser_error(aid, grade):
    if not aid:
        return None
    a = query("SELECT * FROM users WHERE id=? AND role='teacher'", (aid,), one=True)
    if not a:
        return "Selected adviser was not found."
    return None  # a teacher advising the other grade level becomes MID automatically


def section_fields(f, current=None):
    """Track, cluster and shift from a section form. The cluster must belong to the chosen track."""
    track, cluster = f.get("track", "").strip(), f.get("cluster", "").strip()
    track = track if track in TRACKS else ""
    if cluster:
        owner = next((t for t, lst in TRACK_CLUSTERS.items() if cluster in lst), None)
        if not owner:
            return None, "Choose a cluster from the list."
        if track and owner != track:
            return None, f"{cluster} belongs to the {owner} track, not {track}."
        track = owner
        row = query("SELECT offered FROM subjects WHERE name=?", (cluster,), one=True)
        if row and row["offered"] == 0 and cluster != (current["cluster"] if current else ""):
            return None, f"{cluster} is turned off. Turn it on in Curriculum Management first."
    shift = f.get("shift", "").strip().upper()
    if shift not in get_tt():
        shift = "AM" if f.get("grade") in ("11", 11) else "PM"
        shift = shift if shift in get_tt() else None
    return dict(track=track, cluster=cluster or None, shift=shift), None


@app.route("/admin/sections", methods=["GET", "POST"])
@login_required("admin")
def sections():
    """04 Section Management: grade level, section, track, cluster, shift, room and adviser."""
    if request.method == "POST":
        f = request.form
        grade, aid = f.get("grade", type=int), f.get("adviser_id", type=int)
        name = full_section(grade, f.get("name", ""))
        extra, err = section_fields(f)
        if grade not in (11, 12) or not name:
            flash("Enter a section name and choose 11 or 12.", "error")
        elif err:
            flash(err, "error")
        elif adviser_error(aid, grade):
            flash(adviser_error(aid, grade), "error")
        else:
            bldg = f.get("building", "").strip()
            floor = f.get("floor", "").strip()
            try:
                conn = db()
                cur = conn.execute("INSERT INTO sections(name,grade,track,cluster,shift,room,adviser_id,building,floor) "
                                   "VALUES(?,?,?,?,?,?,?,?,?)",
                                   (name, grade, extra["track"], extra["cluster"], extra["shift"],
                                    f.get("room", "").strip(), aid, bldg or None, floor or None))
                conn.commit()
                sync_section_subjects(cur.lastrowid)
                sync_category(aid)
                if aid:
                    notify(aid, "adviser", f"You were assigned as adviser of {name}.", url_for("program"))
                flash("Section added with its core subjects" + (" and cluster." if extra["cluster"] else "."), "ok")
            except sqlite3.IntegrityError:
                flash("A section with that name already exists.", "error")
        return redirect(url_for("sections"))
    rows = query("""SELECT s.*, u.full_name AS adviser,
                    (SELECT COUNT(*) FROM section_subjects WHERE section_id=s.id) AS nsub,
                    (SELECT COUNT(*) FROM loads l WHERE l.section_id=s.id AND l.teacher_id IS NOT NULL
                       AND EXISTS(SELECT 1 FROM section_subjects x WHERE x.section_id=l.section_id
                                  AND x.subject_id=l.subject_id)) AS nload
                    FROM sections s LEFT JOIN users u ON u.id=s.adviser_id ORDER BY s.grade, s.name""")
    teachers_ = query("SELECT * FROM users WHERE role='teacher' ORDER BY full_name")
    return render_template("sections.html", rows=rows, teachers=teachers_, **section_form_data())


def section_form_data():
    offered = {r["name"] for r in query("SELECT name FROM subjects WHERE kind='cluster' AND COALESCE(offered,1)=1")}
    return dict(offered_clusters={t: [c for c in lst if c in offered] for t, lst in TRACK_CLUSTERS.items()},
                shifts=sorted(get_tt()), room_names=[r["name"] for r in query(
                    "SELECT name FROM rooms WHERE rtype='Regular' ORDER BY name")])


@app.route("/admin/sections/<int:sid>/edit", methods=["GET", "POST"])
@login_required("admin")
def section_edit(sid):
    s = query("SELECT * FROM sections WHERE id=?", (sid,), one=True)
    if not s:
        abort(404)
    if request.method == "POST":
        f = request.form
        grade, aid = f.get("grade", type=int), f.get("adviser_id", type=int)
        name = full_section(grade, f.get("name", ""))
        back = redirect(url_for("section_edit", sid=sid))
        if grade not in (11, 12) or not name:
            flash("Enter a section name and choose 11 or 12.", "error")
            return back
        extra, err = section_fields(f, s)
        if err:
            flash(err, "error")
            return back
        if adviser_error(aid, grade):
            flash(adviser_error(aid, grade), "error")
            return back
        bldg = f.get("building", "").strip()
        floor = f.get("floor", "").strip()
        try:
            run("""UPDATE sections SET name=?, grade=?, track=?, cluster=?, shift=?, room=?, adviser_id=?,
                   building=?, floor=? WHERE id=?""",
                (name, grade, extra["track"], extra["cluster"], extra["shift"], f.get("room", "").strip(), aid,
                 bldg or None, floor or None, sid))
            sync_section_subjects(sid)
            for x in {aid, s["adviser_id"]} | {r["teacher_id"] for r in query(
                    "SELECT DISTINCT teacher_id FROM classes WHERE section_id=?", (sid,))}:
                sync_category(x)
            if aid and aid != s["adviser_id"]:
                notify(aid, "adviser", f"You were assigned as adviser of {name}.",
                       url_for("program", section=sid))
            if s["adviser_id"] and s["adviser_id"] != aid:
                notify(s["adviser_id"], "removed",
                       f"You are no longer the adviser of {sec_label(s)}.", url_for("profile"))
            touch("section", sid)
            flash("Section updated.", "ok")
            return redirect(url_for("sections"))
        except sqlite3.IntegrityError:
            flash("A section with that name already exists.", "error")
            return back
    teachers_ = query("SELECT * FROM users WHERE role='teacher' ORDER BY full_name")
    return render_template("section_edit.html", s=s, teachers=teachers_, **section_form_data())


@app.post("/admin/sections/<int:sid>/delete")
@login_required("admin")
def section_delete(sid):
    who = {r["teacher_id"] for r in query("SELECT DISTINCT teacher_id FROM classes WHERE section_id=?", (sid,))}
    sec = query("SELECT adviser_id FROM sections WHERE id=?", (sid,), one=True)
    if sec:
        who.add(sec["adviser_id"])
    run("DELETE FROM classes WHERE section_id=?", (sid,))
    run("DELETE FROM sections WHERE id=?", (sid,))
    for x in who:
        sync_category(x)
    flash("Section and its class program were deleted.", "ok")
    return redirect(url_for("sections"))


def sniff_image(data):
    """Return the image type from the first bytes of the file (never trust the file name)."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


@app.route("/logo")
def logo():
    r = query("SELECT mime,data FROM files WHERE k='logo'", one=True)
    data, mime = (bytes(r["data"]), r["mime"]) if r else (DEFAULT_LOGO, "image/png")
    resp = make_response(data)
    resp.headers["Content-Type"] = mime
    resp.headers["Cache-Control"] = "public, max-age=86400"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    return resp


@app.post("/admin/logo")
@login_required("admin")
def logo_upload():
    f = request.files.get("logo")
    if not f or not f.filename:
        flash("Choose an image file first.", "error")
    else:
        data = f.read(MAX_LOGO + 1)
        mime = sniff_image(data)
        if len(data) > MAX_LOGO:
            flash("That image is too large. Use a file under 2 MB.", "error")
        elif not mime:
            flash("Use a PNG, JPG, GIF or WEBP image.", "error")
        else:
            run("INSERT OR REPLACE INTO files(k,mime,data,updated) VALUES('logo',?,?,?)",
                (mime, data, int(time.time())))
            flash("School logo saved.", "ok")
    return redirect(url_for("settings"))


@app.post("/admin/logo/remove")
@login_required("admin")
def logo_remove():
    run("DELETE FROM files WHERE k='logo'")
    flash("The default school logo is now in use.", "ok")
    return redirect(url_for("settings"))


def save_timetable_rules(f):
    text = f.get("tt_text", "")
    tt = parse_tt(text)
    md, tn, mw = to_int(f.get("max_day"), 60, 720), to_int(f.get("turnover"), 0, 120), to_int(f.get("max_week"), 60, 3000)
    if not tt:
        return False, "The timetable has no readable periods. Add at least one period to a shift."
    if tt_overlap(tt):
        return False, tt_overlap(tt)
    if md is None or tn is None or mw is None:
        return False, "Daily limit must be 60-720 minutes, weekly limit 60-3000 and turnover 0-120 minutes."
    sset("tt_text", text)
    sset("max_teach_day", md)
    sset("max_teach_week", mw)
    sset("turnover", tn)
    return True, ("Timetable, shifts and scheduling rules saved. Run Validation Center to see whether "
                  "existing class programs still fit.")


@app.route("/admin/settings", methods=["GET", "POST"])
@login_required("admin")
def settings():
    """02 School Setup: school year and term, document details, logo, timetable, shifts and rules."""
    if request.method == "POST":
        f = request.form
        act = f.get("action")
        if act == "timetable":
            ok, msg = save_timetable_rules(f)
            flash(msg, "ok" if ok else "error")
            return redirect(url_for("settings") + "#timetable")
        if act == "g12_toggle":
            if f.get("value") == "on":
                sset("g12_programs", "1")
                flash("Grade 12 class programs are on. Generate them from Quick Input.", "ok")
            else:
                sset("g12_programs", "")
                run("DELETE FROM classes WHERE section_id IN (SELECT id FROM sections WHERE grade=12)")
                flash("Grade 12 class programs were removed. Grade 12 sections, teachers and loading stay in the system.", "ok")
            return redirect(url_for("settings") + "#grade12")
        if act == "import_tt":
            up = request.files.get("tt_file")
            if not up or not up.filename.lower().endswith(".xlsx"):
                flash("Choose an Excel file (.xlsx).", "error")
                return redirect(url_for("settings") + "#timetable")
            try:
                text, errs = read_tt_excel(up)
            except ImportError:
                flash("Excel import needs a package. Run:  pip install openpyxl", "error")
                return redirect(url_for("settings") + "#timetable")
            except Exception:
                flash("That file could not be read. Download the template, fill it in and try again.", "error")
                return redirect(url_for("settings") + "#timetable")
            tt = parse_tt(text)
            if errs:
                flash(" ".join(errs[:3]) + (f" (+{len(errs) - 3} more)" if len(errs) > 3 else "") + " Nothing was imported.", "error")
            elif not tt:
                flash("No time slots were found in the file. Use the columns Shift, Start, End, Type.", "error")
            elif tt_overlap(tt):
                flash(tt_overlap(tt) + " Nothing was imported.", "error")
            else:
                sset("tt_text", text)
                flash(f"Imported {sum(len(v) for v in tt.values())} time slots in {len(tt)} shift(s): {', '.join(sorted(tt))}.", "ok")
            return redirect(url_for("settings") + "#timetable")
        if act == "reset_tt":
            sset("tt_text", DEFAULT_TT)
            flash("The timetable was reset to the standard AM and PM shifts.", "ok")
            return redirect(url_for("settings") + "#timetable")
        sy, tn_ = f.get("school_year", "").strip(), f.get("term_name", "").strip()
        ym = re.match(r"^(\d{4})-(\d{4})$", sy)
        if not f.get("school_name", "").strip():
            flash("The school name is required.", "error")
        elif not ym or int(ym[2]) != int(ym[1]) + 1 or tn_ not in TERM_NAMES:
            flash("Enter the school year like 2026-2027 (consecutive years) and choose the term.", "error")
        else:
            vals = {k: f.get(k, "").strip() for k, _ in SETTING_FIELDS}
            vals["term"] = f"{tn_}, SY {sy}"
            for k, v in vals.items():
                run("INSERT OR REPLACE INTO settings(k,v) VALUES(?,?)", (k, v))
            flash(f"School year saved: {vals['term']}.", "ok")
        return redirect(url_for("settings"))
    tt = get_tt()
    shifts = []
    for name in sorted(tt, key=lambda k: tt[k][0][0]):
        per = tt[name]
        cls = sum(e - s for s, e, k in per if k == "class")
        shifts.append(dict(name=name, start=hhmm(per[0][0]), end=hhmm(per[-1][1]), day=cls, week=cls * len(DAYS),
                           n=sum(1 for p in per if p[2] == "class")))
    tm_ = re.match(r"^(.*?),\s*SY\s*(\d{4}-\d{4})$", get_cfg()["term"] or "")
    return render_template("settings.html", g12_on=g12_programs(), fields=[x for x in SETTING_FIELDS if x[0] != "term"], terms=TERM_NAMES,
                           term_name=tm_[1] if tm_ else "", school_year=tm_[2] if tm_ else "", tt_text=gset("tt_text", "") or DEFAULT_TT,
                           max_day=gset("max_teach_day", "360"), max_week=gset("max_teach_week", "1800"),
                           turnover=gset("turnover", "0"), shifts=shifts)


# ------------------------------------------------------------ problem reports
REPORT_LOG = {}  # ip -> times of recent reports
MAX_REPORTS = 500
MAX_PHOTO = 3 * 1024 * 1024
MAX_PHOTOS = 5


@app.route("/help")
def help_center():
    """A plain guide on how to use the system. Open to everyone, signed in or not."""
    return render_template("help.html")


@app.route("/report", methods=["GET", "POST"])
def report():
    """Anyone (signed in or not) can send the administrator a message and an optional photo."""
    u = g.user
    f = request.form
    if request.method == "POST":
        msg = (f.get("message") or "").strip()[:2000]
        code = "" if u else clean(f.get("teacher_id"), 40)
        who = u
        if not u and code:
            who = query("SELECT * FROM users WHERE role='teacher' AND lower(teacher_id)=lower(?)",
                        (code,), one=True)
        name = who["full_name"] if who else ""
        contact = (who["teacher_id"] or who["username"]) if who else ""
        now = time.time()
        recent = [t for t in REPORT_LOG.get(request.remote_addr, []) if now - t < 600]
        err = None
        if len(recent) >= 5:
            err = "Too many reports from this device. Please wait 10 minutes and try again."
        elif not u and not code:
            err = "Please enter your Teacher ID."
        elif not who:
            err = "We could not find that Teacher ID. Check it and try again."
        elif len(msg) < 5:
            err = "Describe the problem in a few words (at least 5 characters)."
        elif query("SELECT COUNT(*) AS n FROM reports", one=True)["n"] >= MAX_REPORTS:
            err = "The report inbox is full. Please contact the administrator directly."
        shots = []
        picked = [p for p in request.files.getlist("photos") if p and p.filename]
        if not err and len(picked) > MAX_PHOTOS:
            err = "You can upload up to 5 screenshots only."
        if not err:
            for p in picked:
                data = p.read(MAX_PHOTO + 1)
                mime = sniff_image(data)
                if len(data) > MAX_PHOTO:
                    err = "A screenshot is too large. Use images under 3 MB each."
                elif not mime:
                    err = "Use PNG, JPG, GIF or WEBP screenshots."
                if err:
                    break
                shots.append((data, mime))
        if err:
            flash(err, "error")
            return render_template("report.html", v=f)
        conn = db()
        cur = conn.execute("""INSERT INTO reports(user_id,name,contact,message,created,is_read,resolved)
               VALUES(?,?,?,?,?,0,0)""",
            (who["id"] if who else None, name, contact, msg, ph_stamp()))
        for data, mime in shots:
            conn.execute("INSERT INTO report_photos(report_id,data,mime) VALUES(?,?,?)",
                         (cur.lastrowid, data, mime))
        conn.commit()
        REPORT_LOG[request.remote_addr] = recent + [now]
        flash("Your report was sent to the administrator. Thank you for letting us know.", "ok")
        return redirect(url_for("help_center") if u else url_for("login"))
    return render_template("report.html", v={})


@app.route("/admin/reports", methods=["GET", "POST"])
@login_required("admin")
def reports():
    if request.method == "POST":
        f = request.form
        rid, act = f.get("rid", type=int), f.get("action")
        if act == "resolve" and rid:
            run("UPDATE reports SET resolved=1-resolved, is_read=1 WHERE id=?", (rid,))
        elif act == "delete" and rid:
            run("DELETE FROM report_photos WHERE report_id=?", (rid,))
            run("DELETE FROM reports WHERE id=?", (rid,))
            flash("Report deleted.", "ok")
        elif act == "clear":
            run("DELETE FROM report_photos WHERE report_id IN (SELECT id FROM reports WHERE resolved=1)")
            run("DELETE FROM reports WHERE resolved=1")
            flash("Resolved reports were cleared.", "ok")
        return redirect(url_for("reports"))
    rows = query("""SELECT id,user_id,name,contact,message,created,is_read,resolved,
                           (photo IS NOT NULL) AS has_photo FROM reports
                    ORDER BY resolved, id DESC""")
    fresh = {r["id"] for r in rows if not r["is_read"]}
    run("UPDATE reports SET is_read=1 WHERE is_read=0")  # opening the inbox clears the badge
    shots = {}
    for r in query("SELECT id, report_id FROM report_photos ORDER BY id"):
        shots.setdefault(r["report_id"], []).append(r["id"])
    return render_template("reports.html", rows=rows, fresh=fresh, shots=shots,
                           any_resolved=any(r["resolved"] for r in rows),
                           signup_rows=query("SELECT * FROM signup_requests ORDER BY id"),
                           reset_rows=query("SELECT * FROM reset_requests ORDER BY id"),
                           suggested_id=next_teacher_id())


@app.route("/notifications", methods=["GET", "POST"])
@login_required("teacher")
def notifications():
    uid = g.user["id"]
    if request.method == "POST":
        f = request.form
        if f.get("action") == "delete" and f.get("rid", type=int):
            run("DELETE FROM notifications WHERE id=? AND user_id=?", (f.get("rid", type=int), uid))
        elif f.get("action") == "clear":
            run("DELETE FROM notifications WHERE user_id=?", (uid,))
            flash("All notifications were deleted.", "ok")
        return redirect(url_for("notifications"))
    rows = query("SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC", (uid,))
    fresh = {r["id"] for r in rows if not r["is_read"]}
    run("UPDATE notifications SET is_read=1 WHERE user_id=? AND is_read=0", (uid,))
    return render_template("notifications.html", rows=rows, fresh=fresh)


@app.route("/notifications/count")
@login_required()
def notif_count():
    u = g.user
    if u["role"] == "admin":
        n = admin_alerts()
    else:
        n = query("SELECT COUNT(*) AS n FROM notifications WHERE user_id=? AND is_read=0",
                  (u["id"],), one=True)["n"]
    resp = make_response(json.dumps({"n": n}))
    resp.headers["Content-Type"] = "application/json"
    resp.headers["Cache-Control"] = "no-store"
    return resp


@app.route("/admin/reports/shot/<int:pid>")
@login_required("admin")
def report_shot(pid):
    r = query("SELECT data, mime FROM report_photos WHERE id=?", (pid,), one=True)
    if not r or not r["data"]:
        abort(404)
    resp = make_response(bytes(r["data"]))
    resp.headers["Content-Type"] = r["mime"] or "image/jpeg"
    resp.headers["Cache-Control"] = "private, max-age=3600"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    return resp


@app.route("/admin/reports/<int:rid>/photo")
@login_required("admin")
def report_photo(rid):
    r = query("SELECT photo, photo_mime FROM reports WHERE id=?", (rid,), one=True)
    if not r or not r["photo"]:
        abort(404)
    resp = make_response(bytes(r["photo"]))
    resp.headers["Content-Type"] = r["photo_mime"] or "image/jpeg"
    resp.headers["Cache-Control"] = "private, max-age=3600"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    return resp


# ---------------------------------------------------------------- templates
CSS = """
:root{--navy:#1b1f7a;--blue:#2d32c8;--tint:#eceefc;--paper:#f5f6fc;--line:#d3d7ee;--ink:#1c2133;
--muted:#5d6482;--gold:#a67c1f;--ok:#2e6b4a;--bad:#9b2c2c;--recess:#ffe94d;--recess-ink:#1c2733}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.55 "Inter","Segoe UI",Arial,sans-serif}
h1,h2,h3{font-family:"Poppins","Segoe UI",Arial,sans-serif;color:var(--navy);line-height:1.25;margin:0 0 .6rem}
h1{font-size:1.9rem}h2{font-size:1.3rem;margin-top:1.8rem}
a{color:var(--blue)}
:focus-visible{outline:3px solid var(--gold);outline-offset:2px}
.top{background:var(--navy);color:#fff;border-bottom:4px solid var(--gold)}
.top .in{max-width:1180px;margin:auto;padding:.8rem 1.2rem;display:flex;flex-wrap:wrap;gap:1rem;align-items:center;justify-content:space-between}
.brand-name{font-family:"Poppins","Segoe UI",Arial,sans-serif;font-size:1.15rem;font-weight:700}
.brand-name small{display:block;font:400 .8rem "Inter","Segoe UI",Arial,sans-serif;color:#cfd9e6}
.top nav{display:flex;flex-wrap:wrap;gap:.3rem;align-items:center}
.top nav a{color:#fff;text-decoration:none;padding:.4rem .8rem;border-radius:3px}
.top nav a:hover,.top nav a.on{background:rgba(255,255,255,.16)}
.who{font-size:.9rem;color:#cfd9e6;margin-left:.6rem}
main{max-width:1180px;margin:auto;padding:1.6rem 1.2rem 3rem}
footer{text-align:center;color:var(--muted);font-size:.85rem;padding:1.5rem}
.card{background:#fff;border:1px solid var(--line);border-radius:4px;padding:1.2rem 1.4rem;margin:1rem 0}
.head{display:flex;flex-wrap:wrap;gap:.8rem;align-items:center;justify-content:space-between;margin-bottom:.8rem}
.head h1,.head h2{margin:0}
.msg{padding:.7rem 1rem;border-radius:3px;margin:0 0 1rem;border-left:4px solid}
.msg.ok{background:#e7f2ec;border-color:var(--ok);color:#1d4a33}
.msg.error{background:#f8e8e8;border-color:var(--bad);color:#6e1f1f}
label{display:block;font-weight:600;margin:.7rem 0 .2rem;font-size:.95rem}
input,select,textarea{width:100%;padding:.55rem .65rem;border:1px solid #aab4c0;border-radius:3px;font:inherit;background:#fff}
button,.btn{background:var(--blue);color:#fff;border:0;border-radius:3px;padding:.6rem 1.1rem;font:inherit;font-weight:600;cursor:pointer;text-decoration:none;display:inline-block}
button:hover,.btn:hover{background:var(--navy)}
.btn.plain,button.plain{background:#fff;color:var(--blue);border:1px solid var(--blue)}
.btn.plain:hover,button.plain:hover{background:var(--tint)}
.small{padding:.3rem .7rem;font-size:.85rem}
button.danger{background:#fff;color:var(--bad);border:1px solid var(--bad);padding:.3rem .7rem;font-size:.85rem}
button.danger:hover{background:var(--bad);color:#fff}
.hint{color:var(--muted);font-size:.85rem;margin:.2rem 0 0}
.formgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:0 1rem;align-items:end}
.formgrid .wide{grid-column:1/-1}
.chk{display:inline-flex;gap:.4rem;align-items:center;font-weight:400;margin:.2rem .9rem .2rem 0}
.chk input{width:auto}
.scroll{overflow-x:auto;background:#fff;border:1px solid var(--line);border-radius:4px}
table{border-collapse:collapse;width:100%}
.doc{background:#fff;border:1px solid var(--line);border-radius:4px;padding:1.6rem 1.8rem;margin:1rem 0}
.letterhead{text-align:center;border-bottom:2px solid var(--navy);padding-bottom:.7rem;margin-bottom:.9rem}
.letterhead .school{font-family:"Poppins","Segoe UI",Arial,sans-serif;font-weight:700;font-size:1.3rem;color:var(--navy)}
.letterhead .addr{color:var(--muted);font-size:.95rem}
.doc-date{text-align:left;font-weight:700;font-size:.95rem;margin:.2rem 0 .5rem;color:var(--navy)}
.letterhead>a{display:flex;flex:none}.logolink{display:inline-block}
.picklist{display:grid;grid-template-columns:repeat(auto-fill,minmax(15rem,1fr));gap:.5rem .9rem;margin-top:.6rem}
.minedit{border-collapse:collapse;width:100%;min-width:640px}.minedit th,.minedit td{border:1px solid var(--line,#d5dbe8);padding:.4rem .5rem;text-align:left}
.minedit input{width:100%;min-width:5.5rem}.minedit tr.tot td,.minedit tr.tot th{background:var(--tint,#eef2fb);font-weight:700}
details.card>summary{cursor:pointer;font-weight:700;color:var(--navy)}
body .slot .acts .btn,body .slot .acts button{padding:.3rem .7rem;font-size:.85rem;min-height:34px}
.editbanner{background:var(--tint,#eef2fb);border-left:4px solid var(--blue);padding:.6rem .9rem;border-radius:4px;margin:.4rem 0 .8rem}
.doc-title{text-align:center;font-size:1.55rem;margin:.4rem 0 0}
.doc-sub{text-align:center;font-weight:600;color:var(--muted);margin:.1rem 0 .6rem}
.room{text-align:center;font-family:"Poppins","Segoe UI",Arial,sans-serif;font-weight:700;font-size:1.2rem;color:var(--navy);margin:.6rem 0}
.roombtn{all:unset;cursor:pointer;font:inherit;font-weight:500;color:var(--navy);text-decoration:underline dotted;text-underline-offset:3px;border-radius:6px;padding:.1rem .3rem}
.roombtn:hover,.roombtn[aria-expanded=true]{background:var(--tint)}
.roombtn:focus-visible{outline:3px solid var(--gold);outline-offset:2px}
.roompop{display:none;margin:.3rem auto 0;max-width:220px;font-size:.8rem;font-weight:600;color:var(--navy);background:#fff;border:1px solid var(--line);border-radius:8px;padding:.3rem .7rem}
.roompop.show{display:block}
@media print{body .roombtn{display:inline!important;text-decoration:underline!important;text-underline-offset:4px;color:#000!important;font-weight:500!important;cursor:default}
body .roompop,body .roompop.show{display:none!important}}
html.pm .roombtn{display:inline!important;text-decoration:underline!important;text-underline-offset:4px;color:#000!important;font-weight:500!important}
html.pm .roompop,html.pm .roompop.show{display:none!important}
@media print{.doc{zoom:var(--zl,1)}}
@media print and (orientation:portrait){.doc{zoom:var(--zp,1)}}
.sign.cls,.doc .sign.cls{display:grid!important;grid-template-columns:1fr 1fr!important;gap:.4rem 3rem!important;text-align:center}
.sign.cls>div:nth-child(1),.sign.cls>div:nth-child(4){grid-column:1/-1;width:min(62%,340px);justify-self:center}
.sign.cls .role{text-align:center}
.sign.cls .role,.doc .sign.cls .role{text-align:center!important;color:var(--ink)}
.sign.cls .name,.doc .sign.cls .name{border-top:0!important;padding-top:0!important;text-decoration:underline;text-decoration-thickness:1px;text-underline-offset:3px}
html.pm .sign.cls,.doc .sign.cls{grid-template-columns:1fr 1fr!important}
@media print{.doc .sign.cls{display:grid!important;grid-template-columns:1fr 1fr!important}}
mark.lgc{background:none;color:inherit;font-weight:700;padding:0}
.room,.room .roombtn{font-weight:500}
.room .roombtn{text-decoration:underline;text-decoration-thickness:1px;text-underline-offset:4px}
@media print{.room,.room .roombtn,html.pm .room{font-weight:500!important}body .roombtn,.room .roombtn{text-decoration-thickness:1px!important}}
html.pm .room,html.pm .room .roombtn{font-weight:500!important;text-decoration-thickness:1px!important}
a.seclink{color:inherit;text-decoration:underline dotted;text-underline-offset:2px}
a.seclink:hover{color:var(--blue)}
@media print{a.seclink{text-decoration:none!important;color:inherit!important}}
.meta{display:flex;justify-content:space-between;flex-wrap:wrap;gap:.3rem 2.5rem;margin:.8rem 0 1rem}
.meta div{margin:.1rem 0}.meta b{color:var(--navy)}
.legend{font-size:.9rem;margin:.7rem 0 0}
.grid{min-width:860px}
.grid th,.grid td{border:1px solid var(--line);padding:.35rem .45rem;vertical-align:top;text-align:left}
.grid thead th{background:#cfe0f0;color:var(--navy);font-weight:700;text-align:center}
.grid tbody th{background:var(--tint);color:var(--navy);white-space:nowrap;width:140px;font-weight:600}
.grid td.num{text-align:center;font-weight:600;width:100px;white-space:nowrap}
.slot{background:var(--tint);border-left:4px solid var(--blue);padding:.3rem .5rem;margin:0 0 .25rem;border-radius:2px;height:calc(100% - .25rem)}
.slot.rec{background:var(--recess);border-left-color:var(--gold);text-align:center;color:var(--recess-ink)}
.slot strong{display:block;color:var(--navy)}
.slot.rec strong{color:inherit}
.slot span{color:var(--muted);font-size:.88rem;display:block}
.sum th{font-weight:700}
.sum.a th,.sum.a td{background:#ece6f2}
.sum.b th,.sum.b td{background:#e3efd8;font-weight:700}
.sum td{text-align:center;font-weight:600}
.acts{display:flex;gap:.4rem;margin-top:.4rem;flex-wrap:wrap}
.acts form{margin:0}
.empty{color:var(--muted);text-align:center;padding:1.4rem!important}
.sign{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:1rem 2rem;margin-top:2rem;text-align:center}
.sign .role{font-size:.9rem;color:var(--muted);text-align:left}
.sign .name{font-weight:700;color:var(--navy);margin-top:1.8rem;border-top:1px solid var(--ink);padding-top:.2rem}
.sign .title{font-size:.9rem}
.list th,.list td{padding:.6rem .7rem;border-bottom:1px solid var(--line);text-align:left;vertical-align:middle}
.list th{background:var(--tint);color:var(--navy)}
.list form.inline{display:flex;gap:.4rem}.list form.inline input{min-width:130px}
.row-acts{display:flex;gap:.4rem;align-items:center}.row-acts form{margin:0}
.pick{display:flex;flex-wrap:wrap;gap:.8rem;align-items:end;margin-bottom:1rem}
.pick select{min-width:240px;width:auto}
.shotbtn{all:unset;cursor:zoom-in;display:inline-block}
.advpick{position:relative}
.advlist{list-style:none;margin:.25rem 0 0;padding:.25rem;position:absolute;left:0;right:0;z-index:30;max-height:15rem;overflow:auto;background:#fff;border:1px solid var(--line);border-radius:8px;box-shadow:0 8px 24px rgba(27,31,122,.2)}
.advlist[hidden],.advlist li[hidden]{display:none}
.advlist li{display:flex;flex-direction:column;padding:.5rem .7rem;border-radius:6px;cursor:pointer;line-height:1.25}
.advlist li:hover{background:var(--tint)}
.advlist li small{color:var(--muted)}
.advlist li.advnone{color:var(--muted);cursor:default}
.shotbox[hidden]{display:none}
.shotbox{position:fixed;inset:0;z-index:55;background:rgba(10,12,40,.9);display:flex;align-items:center;justify-content:center;padding:3.2rem 1rem 1rem}
.shotbox img{max-width:100%;max-height:100%;border-radius:6px;box-shadow:0 10px 40px rgba(0,0,0,.5)}
body .shotbox .shotback{position:fixed!important;top:.9rem;top:max(.9rem,env(safe-area-inset-top));left:.9rem;left:max(.9rem,env(safe-area-inset-left));z-index:60;width:auto;height:auto;min-height:44px;padding:.5rem 1rem .5rem .8rem;display:inline-flex;align-items:center;gap:.4rem;background:#fff;color:var(--navy);font-weight:700;border-radius:999px;box-shadow:0 4px 14px rgba(0,0,0,.35);overflow:visible}
body .shotbox .shotback:hover{background:#e3e7fb}
.shotbox .shotback svg{width:20px;height:20px;flex:none}
.tidfield{display:flex;align-items:stretch}
.tidfield .tidfix{display:inline-flex;align-items:center;padding:0 .6rem;border:1.5px solid var(--line);border-right:0;border-radius:8px 0 0 8px;background:var(--tint);color:var(--navy);font-weight:700}
.tidfield input{border-radius:0 8px 8px 0!important;flex:1;min-width:0}
.narrow{max-width:520px}
.cardrow{display:flex;flex-wrap:wrap;align-items:stretch;gap:1rem}
.cardrow>.card{flex:1 1 320px;margin:1rem 0;display:flex;flex-direction:column}
.cardrow>.card form{display:flex;flex-direction:column;flex:1}
fieldset{border:0;padding:0;margin:1rem 0}legend{font-weight:600;color:var(--navy);margin-bottom:.4rem;padding:0}
@media(max-width:800px){.doc{padding:1rem}}
@page{margin:10mm}
@media print{.top,.pick,footer,.card,button,.acts,.noprint,.btn{display:none!important}
body{background:#fff;font-size:12px}main{padding:0;max-width:none}
.doc{border:0;padding:0;margin:0}.scroll{border:0;overflow:visible}.grid{min-width:0}
.sign{margin-top:1.2rem}
.slot,.sum th,.sum td,.grid thead th,.grid tbody th{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
textarea{resize:vertical}
.assign td{vertical-align:top}.assign textarea{min-width:180px}.assign input,.assign select{min-width:130px}
.assign .tn{font-weight:700;color:var(--navy);letter-spacing:.03em}
.assign tr.rowview .vc{display:none!important}
/* Aligned columns: fixed widths, words wrap at spaces, everything starts at the top. */
table.list.assign{table-layout:fixed;width:100%;min-width:1040px}
table.list.assign th,table.list.assign td{vertical-align:top;text-align:left;padding:.65rem .55rem;font-size:.86rem;line-height:1.4}
table.list.assign th{font-size:.78rem;white-space:normal;word-break:normal;overflow-wrap:normal}
table.list.assign th:nth-child(1){width:104px}table.list.assign th:nth-child(2){width:80px}
table.list.assign th:nth-child(3){width:136px}table.list.assign th:nth-child(4){width:120px}
table.list.assign th:nth-child(5){width:78px}table.list.assign th:nth-child(6){width:116px}
table.list.assign th:nth-child(7){width:92px}table.list.assign th:nth-child(8){width:92px}
table.list.assign th:nth-child(9){width:80px}table.list.assign th:nth-child(10){width:80px}
table.list.assign th:nth-child(11){width:76px}
table.list.assign .tn{white-space:nowrap}
table.list.assign .vtext{display:block;white-space:pre-wrap;overflow-wrap:break-word;word-break:normal}
table.list.assign .hint{font-size:.74rem;line-height:1.35;margin:.3rem 0 0;overflow-wrap:break-word;word-break:normal}
table.list.assign td input:not([type=hidden]),table.list.assign td select,table.list.assign td textarea{width:100%;min-width:0;box-sizing:border-box;font-size:.82rem;padding:.35rem .4rem}
table.list.assign .otime{display:flex;flex-direction:column;gap:.2rem;align-items:stretch}
table.list.assign .otime input{font-size:.76rem;padding:.3rem .25rem}
table.list.assign .otime span{font-size:.74rem;text-align:center}
table.list.assign td.editcell{padding-left:.4rem;padding-right:.5rem}
table.list.assign .rowedit[hidden],table.list.assign .rowsave[hidden]{display:none!important}
table.list.assign .row-acts{display:flex;flex-direction:column;gap:.35rem;align-items:stretch}
table.list.assign .rowsave{display:flex;flex-direction:column;gap:.35rem}
table.list.assign .row-acts button{width:100%;min-width:0;padding:.4rem .3rem;font-size:.8rem}
table.list.assign .otime input{height:2rem;min-height:0;flex:none}
table.list.assign td textarea{min-height:5.6rem;resize:vertical}
@media(max-width:800px){table.list.assign{table-layout:auto;min-width:0}}
.assign tr.rowedit-on .vtext{display:none}
.assign .vtext{display:block;white-space:normal;overflow-wrap:anywhere;line-height:1.4;font-size:.93rem;color:var(--ink);padding:.15rem 0}
.assign .vtext.muted{color:var(--muted)}
.assign td:first-child .vtext{font-weight:600}
.assign tr.rowedit-on{background:#f4f6ff;outline:2px solid #c5cbe3}
.assign .editcell{white-space:nowrap}.assign .rowsave{display:inline-flex;gap:.4rem}.assign .rowsave[hidden]{display:none}
.assign tr.arow td{vertical-align:top}
@media(min-width:801px){.assign th.editth,.assign td.editcell{position:sticky;right:0;z-index:2;box-shadow:-8px 0 10px -8px rgba(27,31,122,.35)}
.assign td.editcell{background:#fff}.assign tr.rowedit-on td.editcell{background:#f4f6ff}.assign th.editth{background:#e6eaf8}}
.assign tr.rowedit-on{background:#f4f6ff;outline:2px solid #c5cbe3}
.assign .editcell{white-space:nowrap}.assign .rowsave{display:inline-flex;gap:.4rem}.assign .rowsave[hidden]{display:none}
.grid td.recess,.grid tbody th.recess{background:var(--recess);color:var(--recess-ink);-webkit-print-color-adjust:exact;print-color-adjust:exact}
.top .in{max-width:1240px;display:grid;grid-template-columns:1fr auto;grid-template-areas:"brand acct" "tabs tabs";gap:.25rem 1rem;align-items:center;padding:.7rem 1.2rem .45rem}
.brand-name{grid-area:brand}
.top nav{display:contents}
.tabs{grid-area:tabs;display:flex;flex-wrap:wrap;gap:.2rem;border-top:1px solid rgba(255,255,255,.2);padding-top:.45rem}
.acct{grid-area:acct;display:flex;align-items:center;gap:.4rem;justify-content:flex-end}
.top nav a{padding:.5rem .85rem;border-radius:6px;font-size:.97rem;font-weight:600;transition:background .15s}
.who{margin:0}
main{max-width:1240px}
input:not([type=checkbox]):not([type=radio]):not([type=hidden]),select{height:2.9rem}
.menubtn{display:none;background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.4)}
.mobile-days{display:none}
.daytabs{display:flex;gap:.3rem;margin-bottom:.8rem}
.daytab{flex:1;background:#fff;color:var(--blue);border:1px solid var(--blue);padding:.6rem 0}
.daytab.on{background:var(--blue);color:#fff}
.dayp{display:none}.dayp.on{display:block}
.dayp h3{margin:.2rem 0 .4rem}
.mrow{margin:.55rem 0}
.mtime{font-weight:600;color:var(--navy);font-size:.92rem;padding:.3rem .6rem;background:var(--tint);border:1px solid var(--line);border-bottom:0;border-radius:4px 4px 0 0}
.mtime.recess{background:var(--recess);color:var(--recess-ink)}
.mrow .slot{height:auto;margin:0;border-radius:0 0 4px 4px;border:1px solid var(--line);border-left-width:4px}
.mrow .slot.rec{border-left-color:var(--gold)}
.mnone{color:var(--muted);text-align:center;padding:1.2rem}
.msum{margin-top:1rem;border:1px solid var(--line);border-radius:4px;overflow:hidden}
.msum div{display:flex;justify-content:space-between;padding:.45rem .7rem;background:#ece6f2}
.msum div.tot{background:#e3efd8;font-weight:700}
.msum div+div{border-top:1px solid var(--line)}
@media(max-width:800px){
body{font-size:16px}
h1{font-size:1.5rem}
main{padding:1rem .8rem 2.2rem}
button,.btn{min-height:44px}
.small,button.danger{min-height:40px}
.card{padding:1rem}
.head{flex-direction:column;align-items:stretch}
.head .btn,.head button{text-align:center;width:100%}
.pick select{min-width:0;width:100%}.pick>div{width:100%}
.formgrid{grid-template-columns:1fr}
.doc{padding:.9rem}
.doc-title{font-size:1.25rem}
.meta{flex-direction:column;gap:0}
.gridwrap{display:none}
.mobile-days{display:block}
.sign{grid-template-columns:1fr}
.scroll:has(.list.stack){overflow:visible;border:0;background:transparent}
.list.stack,.list.stack tbody,.list.stack tr,.list.stack td{display:block;width:100%}
.list.stack thead{display:none}
.list.stack tr{border:1px solid var(--line);border-radius:4px;margin:.7rem 0;padding:.5rem .7rem;background:#fff}
.list.stack td{border:0;padding:.35rem 0}
.list.stack td[data-label]::before{content:attr(data-label);display:block;font-size:.76rem;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}
.list.stack td.empty{text-align:center}
.list form.inline{flex-direction:column}
.assign input,.assign select,.assign textarea{min-width:0}
.row-acts{flex-wrap:wrap}
}
.top{background:linear-gradient(90deg,#1b1f7a,#2d32c8);border-bottom:0}
.grid thead th{background:#dfe2fa}
.card,.doc,.scroll,.msg{border-radius:10px}
input,select,textarea,button,.btn{border-radius:6px}
.viewtoggle{font-size:.9rem}
html{-webkit-text-size-adjust:100%}
a,button,.btn,select,.chk,.daytab{touch-action:manipulation;-webkit-tap-highlight-color:rgba(45,50,200,.15)}
button,.btn{transition:background .15s,box-shadow .15s,transform .06s}
button:hover,.btn:hover{box-shadow:0 3px 8px rgba(27,31,122,.22)}
button:active,.btn:active{transform:translateY(1px);box-shadow:none}
button:disabled{opacity:.65;cursor:wait;box-shadow:none}
input:focus,select:focus,textarea:focus{border-color:var(--blue);box-shadow:0 0 0 3px rgba(45,50,200,.16);outline:0}
.list tbody tr{transition:background .12s}.list tbody tr:hover{background:#f7f8fe}
.chk{padding:.4rem .6rem;border:1px solid var(--line);border-radius:6px;background:#fff;cursor:pointer}
.chk:has(input:checked){background:var(--tint);border-color:var(--blue)}
.chk input{width:1.2rem;height:1.2rem;accent-color:var(--blue)}
.daytab{min-height:44px;font-weight:600}
.pwwrap{position:relative;display:block}
.pwwrap input,.login .pwwrap input{padding-right:3rem}
.eye{position:absolute;right:.2rem;top:50%;transform:translateY(-50%);width:2.6rem;height:2.6rem;min-height:0!important;padding:0;background:transparent;color:var(--muted);border:0;display:flex;align-items:center;justify-content:center;border-radius:6px}
.eye:hover{background:var(--tint);color:var(--blue);box-shadow:none}
.eye:active{transform:translateY(-50%)}
.eye svg{width:22px;height:22px}
@media(max-width:1100px){
.top .in{display:flex;flex-wrap:wrap;justify-content:space-between;padding:.6rem .9rem}
.menubtn{display:inline-block;min-height:44px}
.top nav{display:none;width:100%;flex-direction:column;gap:.2rem;padding-top:.5rem;border-top:1px solid rgba(255,255,255,.25)}
.top.open nav{display:flex}
.tabs{flex-direction:column;border-top:0;padding-top:0}
.acct{flex-direction:column;align-items:stretch;justify-content:flex-start;border-top:1px solid rgba(255,255,255,.2);padding-top:.3rem}
.top nav a{padding:.8rem .7rem;font-size:1.02rem}
.who{padding:.3rem .7rem}
}
/* ---- sign-in / sign-up screens ---- */
.login{min-height:100vh;min-height:100dvh;display:grid;grid-template-columns:6fr 5fr;background:#fff}
.login .side{position:relative;overflow:hidden;background:linear-gradient(160deg,#2c31c9,#1a1d85);color:#fff;padding:3.5rem 3.5rem 2rem;display:flex;flex-direction:column;justify-content:space-between}
.login .arcs{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}
.login .side-in{position:relative;margin:auto 0;max-width:30rem}
.login .logo{width:64px;height:64px;margin-bottom:2.2rem;display:block}
.login .side h1{letter-spacing:.02em;font:700 clamp(1.8rem,3.4vw,2.6rem)/1.15 "Inter","Segoe UI",Arial,sans-serif;color:#fff;margin:0 0 1.4rem}
.login .side p{color:#d9dcff;max-width:28rem;margin:0}
.login .copy{position:relative;color:#b9bdf3;font-size:.85rem}
.login .panel{display:flex;padding:2rem 3rem;position:relative}
.helpfab{position:absolute;top:1.1rem;right:1.1rem;display:inline-flex;align-items:center;justify-content:center;width:42px;height:42px;border-radius:50%;background:var(--tint);color:var(--navy);text-decoration:none;box-shadow:0 2px 6px rgba(27,31,122,.15)}
.helpfab:hover{background:#dde2fb}
.helpfab-q{position:absolute;top:-3px;right:-3px;width:16px;height:16px;border-radius:50%;background:var(--gold);color:#fff;font-size:.68rem;font-weight:800;line-height:16px;text-align:center}
@media(max-width:800px){.helpfab{top:.7rem;right:.7rem;width:38px;height:38px}}
.authform{display:flex;flex-direction:column;width:100%;max-width:420px;margin:0 auto;min-height:calc(100vh - 4rem)}
.auth-brand{font-weight:700;font-size:1.15rem;color:#111}
.auth-body{margin:auto 0;padding:1.5rem 0}
.auth-body h2{font:700 1.6rem "Inter","Segoe UI",Arial,sans-serif;color:#111;margin:0 0 .4rem}
.auth-note{color:var(--muted);font-size:.85rem;margin:0 0 1rem}
.login label{font-size:.8rem;color:var(--muted);margin:1.1rem 0 0}
.login input,.login select{border:0;border-bottom:1.5px solid #cfd3e3;border-radius:0;padding:.6rem 0;background:transparent;font-size:1rem}
.login input:focus,.login select:focus{outline:0;border-bottom-color:var(--blue);box-shadow:0 2px 0 var(--blue)}
button.dark{background:#111;color:#fff;width:100%;padding:.85rem;margin-top:1.6rem;border-radius:6px}
button.dark:hover{background:#000}
.auth-foot{text-align:center;color:var(--muted);font-size:.85rem;margin:1.2rem 0 0}
.auth-foot a{font-weight:600}
@media(max-width:1100px){.login .side{padding:2.5rem 2rem}.login .panel{padding:2rem 1.8rem}}
@media(max-width:800px){
.login{grid-template-columns:1fr}
.login .side{padding:1.5rem 1.3rem 1.3rem;min-height:0}
.login .side-in{margin:0}
.login .logo{width:40px;height:40px;margin-bottom:.9rem}
.login .side h1{font-size:1.9rem;margin-bottom:.6rem}
.login .side p{font-size:.95rem}
.login .copy{display:none}
.login .panel{padding:1.2rem 1.3rem 2rem}
.authform{min-height:0}
.auth-brand{display:none}
.auth-body{padding:.4rem 0}
}
@media print{.mobile-days{display:none!important}.gridwrap{display:block!important}}

/* ======== Soft 3D (neumorphic) theme ======== */
:root{--bg:#e8edf5;--sh-d:rgba(150,165,190,.55);--sh-l:rgba(255,255,255,.95);--face:#f3f6fb}
body{background:linear-gradient(160deg,#eff3f9,#dde4ef) fixed}
.top{background:var(--face);color:var(--navy);border-bottom:0;border-radius:0 0 26px 26px;box-shadow:0 10px 24px var(--sh-d),0 -2px 0 #fff inset}
.brand-name{color:var(--navy)}.brand-name small{color:var(--muted)}
.tabs{border-top:1px solid rgba(27,31,122,.1)}
.top nav a{color:var(--navy);border-radius:14px;box-shadow:4px 4px 9px var(--sh-d),-4px -4px 9px var(--sh-l);background:var(--face);margin:.15rem .1rem}
.top nav a:hover{background:#fff}
.top nav a.on{background:linear-gradient(180deg,#4a52ee,#2d32c8);color:#fff;box-shadow:inset 3px 3px 7px rgba(0,0,30,.35),inset -2px -2px 5px rgba(255,255,255,.2)}
.who{color:var(--muted)}
.card,.doc,.scroll,.msg{border:0;background:var(--face);border-radius:22px;box-shadow:9px 9px 20px var(--sh-d),-9px -9px 20px var(--sh-l)}
.doc{background:#fbfcfe}
.scroll{background:#fbfcfe}
.msg{border-left:6px solid}
input:not([type=checkbox]):not([type=radio]):not([type=hidden]),select,textarea{border:0;border-radius:14px;background:#eef2f8;box-shadow:inset 4px 4px 9px var(--sh-d),inset -4px -4px 9px var(--sh-l)}
input:focus,select:focus,textarea:focus{box-shadow:inset 4px 4px 9px var(--sh-d),inset -4px -4px 9px var(--sh-l),0 0 0 3px rgba(45,50,200,.28)}
/* 3D buttons */
button,.btn{background:linear-gradient(180deg,#5a61f4 0%,#2d32c8 55%,#2227a8 100%);color:#fff;border:0;border-radius:16px;padding:.7rem 1.4rem;text-shadow:0 1px 1px rgba(0,0,40,.4);
box-shadow:0 6px 0 #161a6b,0 12px 18px rgba(27,31,122,.35),inset 0 2px 0 rgba(255,255,255,.4);position:relative;margin-bottom:6px;transition:transform .08s,box-shadow .08s,filter .15s}
button:hover,.btn:hover{background:linear-gradient(180deg,#6970ff 0%,#3a40da 55%,#2a2fb8 100%);filter:brightness(1.04);transform:translateY(-1px);
box-shadow:0 7px 0 #161a6b,0 14px 20px rgba(27,31,122,.38),inset 0 2px 0 rgba(255,255,255,.45)}
button:active,.btn:active{transform:translateY(5px);box-shadow:0 1px 0 #161a6b,0 3px 6px rgba(27,31,122,.3),inset 0 2px 0 rgba(255,255,255,.25)}
.btn.plain,button.plain{background:linear-gradient(180deg,#ffffff,#e6ebf5);color:var(--blue);text-shadow:none;border:0;
box-shadow:0 6px 0 #b4bfd6,0 12px 18px var(--sh-d),inset 0 2px 0 #fff}
.btn.plain:hover,button.plain:hover{background:linear-gradient(180deg,#ffffff,#eef2fb);box-shadow:0 7px 0 #b4bfd6,0 14px 20px var(--sh-d),inset 0 2px 0 #fff}
.btn.plain:active,button.plain:active{box-shadow:0 1px 0 #b4bfd6,0 3px 6px var(--sh-d),inset 0 2px 0 #fff}
button.danger{background:linear-gradient(180deg,#fff,#f5e4e4);color:var(--bad);border:0;text-shadow:none;box-shadow:0 4px 0 #d3aeae,0 8px 12px var(--sh-d),inset 0 2px 0 #fff}
button.danger:hover{background:linear-gradient(180deg,#d65a5a,#9b2c2c);color:#fff;box-shadow:0 5px 0 #6a1b1b,0 9px 14px rgba(155,44,44,.35),inset 0 2px 0 rgba(255,255,255,.35)}
button.danger:active{box-shadow:0 1px 0 #6a1b1b}
.small,.btn.small,button.small{padding:.4rem .9rem;border-radius:12px;margin-bottom:4px;box-shadow:0 4px 0 #161a6b,0 8px 12px rgba(27,31,122,.3),inset 0 2px 0 rgba(255,255,255,.4)}
.btn.plain.small,button.plain.small{box-shadow:0 4px 0 #b4bfd6,0 8px 12px var(--sh-d),inset 0 2px 0 #fff}
button.dark{background:linear-gradient(180deg,#444a63,#1a1d2b 60%,#0d0f18);box-shadow:0 6px 0 #000,0 12px 18px rgba(0,0,0,.35),inset 0 2px 0 rgba(255,255,255,.25);border-radius:999px;padding:.95rem;margin-bottom:8px}
button.dark:hover{background:linear-gradient(180deg,#575e7a,#262a3b 60%,#12141f)}
button.dark:active{box-shadow:0 1px 0 #000,0 3px 6px rgba(0,0,0,.3)}
.daytab{background:linear-gradient(180deg,#fff,#e6ebf5);color:var(--blue);border:0;box-shadow:0 4px 0 #b4bfd6,0 8px 12px var(--sh-d),inset 0 2px 0 #fff;margin-bottom:6px}
.daytab.on{background:linear-gradient(180deg,#5a61f4,#2227a8);color:#fff;box-shadow:inset 3px 3px 7px rgba(0,0,30,.4)}
.menubtn{background:linear-gradient(180deg,#fff,#e6ebf5);color:var(--navy);border:0;text-shadow:none;box-shadow:0 4px 0 #b4bfd6,0 8px 12px var(--sh-d),inset 0 2px 0 #fff}
button.eye{background:transparent;box-shadow:none;margin:0;text-shadow:none;border-radius:50%;color:var(--muted);filter:none}
button.eye:hover{background:var(--tint);box-shadow:none;transform:translateY(-50%)}
button.eye:active{transform:translateY(-50%);box-shadow:none}
button:disabled{box-shadow:0 2px 0 #161a6b;transform:translateY(3px)}
.chk{border:0;border-radius:14px;background:var(--face);box-shadow:4px 4px 9px var(--sh-d),-4px -4px 9px var(--sh-l)}
.chk:has(input:checked){background:#e1e5fb;box-shadow:inset 3px 3px 7px var(--sh-d),inset -3px -3px 7px var(--sh-l)}
.list th{background:#e6eaf8}.list tbody tr:hover{background:#f3f5fd}
/* sign-in screens */
.login .panel{background:var(--face)}
.login input:not([type=checkbox]):not([type=radio]):not([type=hidden]),.login select{border:0;border-bottom:1.5px solid #cfd3e3;border-radius:0;background:transparent;box-shadow:none;height:auto}
.login input:focus,.login select:focus{box-shadow:0 2px 0 var(--blue)}
/* ======== Program tables: aligned columns ======== */
.grid{table-layout:fixed;width:100%;min-width:900px;border-collapse:collapse}
.grid col.c-time{width:15%}.grid col.c-min{width:9%}
.grid th,.grid td{vertical-align:middle;text-align:center;padding:.4rem .35rem;word-wrap:break-word;overflow-wrap:anywhere}
.grid td{height:1px;border-color:#d9deef}
.grid thead th{padding:.7rem .4rem;background:#dfe2fa}
.grid tbody th{width:auto;white-space:normal;font-size:.9rem;line-height:1.25;text-align:center}
.grid td.num{width:auto;text-align:center}
.slot{height:100%;margin:0;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;min-height:2.7rem;border-left:0;border-radius:10px;padding:.35rem .4rem;background:#e9ecfc;box-shadow:3px 3px 7px var(--sh-d),-3px -3px 7px var(--sh-l)}
.slot.rec{box-shadow:inset 2px 2px 5px rgba(0,0,0,.12)}
.slot strong,.slot span{width:100%;text-align:center}
.slot .acts{justify-content:center}
.sum th{text-align:left;padding-left:.6rem}
.sum td{text-align:center}
.legend{line-height:1.5}
@page{margin:6mm}
@media print{
body{background:#fff!important;font-size:10px;line-height:1.25}
main{padding:0!important;max-width:none!important}
.mobile-days{display:none!important}
.gridwrap{display:block!important;overflow:visible!important;border:0!important;background:none!important}
.doc{padding:0!important;margin:0!important;border:0!important;border-radius:0!important;background:#fff!important;break-inside:avoid;page-break-inside:avoid;page-break-after:avoid}
.letterhead{padding-bottom:3px;margin-bottom:4px}
.letterhead .school{font-size:15px}
.letterhead .addr{font-size:10px}
.doc-title{font-size:15px;margin:2px 0 0}
.doc-sub{font-size:10px;margin:0 0 3px}
.room{font-size:12px;margin:3px 0}
.meta{margin:4px 0;font-size:10px;gap:0 2rem}
.meta div{margin:0}
.grid{min-width:0!important;width:100%;font-size:9px}
.grid th,.grid td{padding:2px 3px!important}
.grid thead th{padding:3px!important}
.slot{min-height:0!important;padding:1px 3px!important;font-size:9px}
.slot span{font-size:8.5px}
.legend{font-size:9px;margin:3px 0 0}
.sign{margin-top:6px!important;gap:2px 1rem;grid-template-columns:repeat(auto-fit,minmax(140px,1fr))}
.sign .name{margin-top:12px;font-size:10px}
.sign .role,.sign .title{font-size:9px}
.doc *{box-shadow:none!important;text-shadow:none!important}
}
html.pm body{background:#fff!important;font-size:10px;line-height:1.25}
html.pm main{padding:0!important;max-width:none!important}
html.pm .mobile-days{display:none!important}
html.pm .gridwrap{display:block!important;overflow:visible!important;border:0!important;background:none!important}
html.pm .doc{padding:0!important;margin:0!important;border:0!important;border-radius:0!important;background:#fff!important;break-inside:avoid;page-break-inside:avoid;page-break-after:avoid}
html.pm .letterhead{padding-bottom:3px;margin-bottom:4px}
html.pm .letterhead .school{font-size:15px}
html.pm .letterhead .addr{font-size:10px}
html.pm .doc-title{font-size:15px;margin:2px 0 0}
html.pm .doc-sub{font-size:10px;margin:0 0 3px}
html.pm .room{font-size:12px;margin:3px 0}
html.pm .meta{margin:4px 0;font-size:10px;gap:0 2rem}
html.pm .meta div{margin:0}
html.pm .grid{min-width:0!important;width:100%;font-size:9px}
html.pm .grid th,html.pm .grid td{padding:2px 3px!important}
html.pm .grid thead th{padding:3px!important}
html.pm .slot{min-height:0!important;padding:1px 3px!important;font-size:9px}
html.pm .slot span{font-size:8.5px}
html.pm .legend{font-size:9px;margin:3px 0 0}
html.pm .sign{margin-top:6px!important;gap:2px 1rem;grid-template-columns:repeat(auto-fit,minmax(140px,1fr))}
html.pm .sign .name{margin-top:12px;font-size:10px}
html.pm .sign .role,html.pm .sign .title{font-size:9px}
html.pm .doc *{box-shadow:none!important;text-shadow:none!important}
/* ======== Header and menu alignment ======== */
.top .in{max-width:1240px;margin:0 auto;display:grid;grid-template-columns:minmax(0,1fr) auto;grid-template-areas:"brand acct" "tabs tabs";align-items:center;gap:.55rem 1rem;padding:.75rem 1.2rem .65rem}
.brand{grid-area:brand;display:flex;align-items:center;gap:.8rem;min-width:0;text-decoration:none;color:var(--navy)}
.brand-logo{width:50px;height:50px;flex:none;object-fit:contain;border-radius:50%;background:#fff;padding:0;box-shadow:3px 3px 8px var(--sh-d),-3px -3px 8px var(--sh-l)}
.brand .brand-name{line-height:1.2}
.top .tabs{grid-area:tabs;display:flex;flex-wrap:wrap;align-items:center;justify-content:flex-start;gap:.5rem;border-top:1px solid rgba(27,31,122,.1);padding-top:.65rem}
.top .acct{grid-area:acct;display:flex;align-items:center;justify-content:flex-end;gap:.6rem;justify-self:end}
.top .tabs a,.top .acct a{display:inline-flex;align-items:center;justify-content:center;min-height:42px;margin:0;padding:0 1.05rem;white-space:nowrap;font-size:.95rem;font-weight:600;line-height:1.1;text-decoration:none;border-radius:14px}
.top .acct .who{max-width:240px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:600}
@media(max-width:1100px){
.top .in{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;padding:.65rem .9rem}
.top nav{display:none;width:100%;flex-direction:column;gap:.5rem;align-items:stretch;padding-top:.5rem;border-top:1px solid rgba(27,31,122,.1)}
.top.open nav{display:flex}
.top .brand{flex:1 1 0}
.top .brand-name{font-size:1rem}
.top .brand-name small{font-size:.7rem}
.menubtn{flex:none}
.menubtn:hover,.menubtn:active{background:linear-gradient(180deg,#fff,#e6ebf5);color:var(--navy)}
.top .tabs{flex-direction:column;flex-wrap:nowrap;align-items:stretch;gap:.5rem;border-top:0;padding-top:0}
.top .acct{flex-direction:column;align-items:stretch;justify-self:stretch;gap:.5rem;border-top:1px solid rgba(27,31,122,.1);padding-top:.5rem}
.top .tabs a,.top .acct a{justify-content:flex-start;width:100%;min-height:46px;padding:0 1rem;font-size:1rem}
.top .acct .who{max-width:none;padding:.2rem 1rem}
}
/* ======== Menu as a small box ======== */
@media(max-width:1100px){
body .top{position:relative}
body .top .in{position:static}
body .top nav{position:absolute!important;top:calc(100% + 6px);right:.7rem;left:auto!important;width:min(270px,calc(100vw - 1.4rem))!important;z-index:90;background:#fff;border:1px solid #c9cff0!important;border-radius:14px;box-shadow:0 14px 34px rgba(27,31,122,.3);padding:.55rem!important;max-height:calc(100vh - 110px);overflow-y:auto;gap:.3rem!important}
body .top nav::before{content:"";position:absolute;top:-7px;right:20px;width:12px;height:12px;background:#fff;border-left:1px solid #c9cff0;border-top:1px solid #c9cff0;transform:rotate(45deg)}
body .top .tabs{gap:.3rem!important}
body .top .tabs a,body .top .acct a{min-height:42px!important;font-size:.95rem!important;padding:0 .8rem!important}
body .top .acct{padding-top:.4rem!important;gap:.3rem!important}
body .top .acct .who{padding:.15rem .8rem!important;font-size:.85rem}
body .top .acct .bell.desk{display:none}
}
/* ======== Back button (icon) ======== */
.backbtn{display:inline-flex;align-items:center;justify-content:center;width:46px;height:46px;flex:none;border-radius:50%;color:var(--blue);background:linear-gradient(180deg,#fff,#e6ebf5);box-shadow:0 5px 0 #b4bfd6,0 10px 14px var(--sh-d),inset 0 2px 0 #fff;text-decoration:none;margin-bottom:5px;transition:transform .08s,box-shadow .08s}
.backbtn:hover{background:#fff;transform:translateY(-1px)}
.backbtn:active{transform:translateY(4px);box-shadow:0 1px 0 #b4bfd6,0 3px 6px var(--sh-d),inset 0 2px 0 #fff}
.backbtn svg{width:24px;height:24px}
.titlerow{display:flex;align-items:center;gap:.9rem;margin-bottom:.5rem}
.titlerow h1{margin:0}
/* ======== School logo ======== */
.letterhead{display:flex;align-items:center;justify-content:center;gap:1.1rem;text-align:center}
.letterhead .lh-text{flex:1;min-width:0}
.lh-logo{width:92px;height:92px;flex:none;object-fit:contain;display:block}
.lh-spacer{visibility:hidden}
.login .logoimg{width:120px;height:120px;object-fit:contain;background:#fff;border-radius:50%;padding:4px;box-shadow:0 8px 20px rgba(0,0,40,.3)}
@media(max-width:800px){.lh-logo{width:52px;height:52px}.letterhead{gap:.6rem}.login .logoimg{width:64px;height:64px;margin-bottom:.9rem}}
.logoedit{display:flex;gap:1.4rem;align-items:center;flex-wrap:wrap}
.logoprev{width:120px;height:120px;object-fit:contain;border-radius:50%;background:#fff;padding:4px;box-shadow:inset 3px 3px 7px var(--sh-d),inset -3px -3px 7px var(--sh-l)}
.logoprev.none{display:flex;align-items:center;justify-content:center;text-align:center;color:var(--muted);font-size:.85rem}
input[type=file]{height:auto!important;padding:.6rem .7rem}
/* ======== Search sections ======== */
.pick .searchbox{flex:1 1 320px;max-width:520px}
.sfield{position:relative}
.sfield>svg{position:absolute;left:.9rem;top:50%;transform:translateY(-50%);width:20px;height:20px;color:var(--muted);pointer-events:none}
.sfield input{padding-left:2.7rem;padding-right:2.8rem;-webkit-appearance:none;appearance:none}
.sfield input::-webkit-search-cancel-button{display:none}
.sclear{position:absolute;right:.5rem;top:50%;transform:translateY(-50%);width:2rem;height:2rem;display:flex;align-items:center;justify-content:center;border-radius:50%;color:var(--muted);text-decoration:none;font-size:1.5rem;line-height:1}
.sclear:hover{background:var(--tint);color:var(--blue)}
/* ======== Clickable teacher number ======== */
.slot button.tlink{all:unset;display:inline-flex;align-items:center;min-height:30px;padding:0 .4rem;cursor:pointer;color:var(--blue);font-weight:700;font-size:.88rem;text-decoration:underline dotted;text-underline-offset:3px;border-radius:6px;-webkit-tap-highlight-color:transparent}
.slot button.tlink:hover,.slot button.tlink[aria-expanded=true]{background:rgba(45,50,200,.12)}
.slot button.tlink:focus-visible{outline:3px solid var(--gold);outline-offset:2px}
.slot .tname{display:none;font-weight:700;color:var(--navy);font-size:.88rem}
.slot .tname.show{display:block}
/* ======== Computed time ======== */
.hm{display:block;font-weight:400;font-size:.78rem;color:var(--muted);margin-top:.1rem}
@media print{
.lh-logo{width:66px!important;height:66px!important}
.slot button.tlink{display:inline-flex!important;color:inherit!important;text-decoration:none!important;min-height:0!important;padding:0!important}
.slot .tname{font-size:9px}
.hm{font-size:8px}
.backbtn{display:none!important}
}
html.pm .lh-logo{width:66px;height:66px}
@media print{
.slot button.tlink{font-size:9px!important;min-height:0!important;padding:0!important;display:inline!important}
.slot .tname{font-size:9px!important}
main{animation:none!important;opacity:1!important;transform:none!important}
}
html.pm .slot button.tlink{font-size:9px!important;min-height:0!important;padding:0!important;display:inline!important}
html.pm .slot .tname{font-size:9px!important}
html.pm main{animation:none!important;opacity:1!important;transform:none!important}
/* ======== Flat formal theme ======== */
body{background:#f3f5fb}
main{animation:fadein .35s ease}
@keyframes fadein{from{opacity:0}to{opacity:1}}
.top{background:#fff;border-radius:0;box-shadow:none;border-bottom:3px solid var(--blue)}
.brand-logo{box-shadow:none}
body .card,body .doc,body .scroll,body .msg{box-shadow:none;border:1px solid var(--line);border-radius:8px;background:#fff}
body .msg{border-left-width:5px}
main input:not([type=checkbox]):not([type=radio]):not([type=hidden]),main select,main textarea{background:#fff;border:1px solid #b9c0d9;border-radius:6px;box-shadow:none}
main input:not([type=checkbox]):not([type=radio]):not([type=hidden]):focus,main select:focus,main textarea:focus{border-color:var(--blue);box-shadow:0 0 0 3px rgba(45,50,200,.18)}
/* schedule tables: flat, no 3D */
body .scroll.gridwrap{border:1px solid #c5cbe3;border-radius:8px;box-shadow:none;background:#fff}
body .grid thead th{background:var(--navy);color:#fff;border-color:var(--navy)}
body .grid td,body .grid th{border:1px solid #d9deef}
body .grid thead th{border-color:var(--navy)}
body .grid tbody th{background:#eef0fb;color:var(--navy)}
body .grid td.recess,body .grid tbody th.recess{background:var(--recess);color:var(--recess-ink)}
body .slot{box-shadow:none;background:#e9ecfc;border-left:4px solid var(--blue);border-radius:4px}
body .slot.rec{box-shadow:none;border-left:0;background:transparent}
body .mrow .slot{box-shadow:none}
body .msum{box-shadow:none}
/* buttons: solid fills, no outlines, no 3D */
body button,body .btn{background:var(--blue);color:#fff;border:0;border-radius:6px;padding:.65rem 1.25rem;margin-bottom:0;text-shadow:none;box-shadow:none;filter:none;transform:none;font-weight:600;transition:background .15s,color .15s}
body button:hover,body .btn:hover{background:var(--navy);box-shadow:none;filter:none;transform:none}
body button:active,body .btn:active{background:#12165a;box-shadow:none;transform:none}
body button:disabled{opacity:.6;cursor:wait;box-shadow:none;transform:none}
body .btn.plain,body button.plain{background:#e3e7fb;color:var(--navy);border:0;box-shadow:none}
body .btn.plain:hover,body button.plain:hover{background:#cfd6f6;color:var(--navy);box-shadow:none}
body .btn.plain:active,body button.plain:active{background:#bfc8f2;box-shadow:none;transform:none}
body button.danger{background:#fbe4e4;color:var(--bad);border:0;box-shadow:none;text-shadow:none}
body button.danger:hover{background:var(--bad);color:#fff;box-shadow:none}
body button.danger:active{background:#7a2020;box-shadow:none}
body .small,body .btn.small,body button.small{padding:.4rem .9rem;border-radius:6px;margin-bottom:0;box-shadow:none}
body .btn.plain.small,body button.plain.small{box-shadow:none}
body button.dark{background:#1c2133;border:0;border-radius:6px;box-shadow:none;padding:.85rem;margin-bottom:0}
body button.dark:hover{background:#000}
body .daytab{background:#e3e7fb;color:var(--navy);border:0;border-radius:6px;box-shadow:none;margin-bottom:0}
body .daytab.on{background:var(--blue);color:#fff;box-shadow:none}
body .menubtn,body .menubtn:hover,body .menubtn:active{background:#e3e7fb;color:var(--navy);border:0;border-radius:6px;box-shadow:none;margin-bottom:0}
body button.eye,body button.eye:hover,body button.eye:active{background:transparent;border:0;box-shadow:none;margin:0;padding:0;color:var(--muted);border-radius:6px}
body button.eye:hover{background:var(--tint);color:var(--blue)}
body .backbtn{background:#e3e7fb;color:var(--navy);border:0;border-radius:6px;box-shadow:none;margin-bottom:0;transform:none}
body .backbtn:hover{background:#cfd6f6;transform:none}
body .backbtn:active{background:#bfc8f2;box-shadow:none;transform:none}
body .top .tabs a,body .top .acct a{background:#eef0fb;color:var(--navy);border:0;border-radius:6px;box-shadow:none}
body .top .tabs a:hover,body .top .acct a:hover{background:#d9def8}
body .top .tabs a.on{background:var(--blue);color:#fff;box-shadow:none}
body .chk{box-shadow:none;border:0;border-radius:6px;background:#eef0fb}
body .chk:has(input:checked){box-shadow:none;background:#d5dbf8}
/* ======== Opening intro ======== */
#intro{position:fixed;inset:0;z-index:9999;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:.9rem;background:linear-gradient(160deg,#2c31c9,#1a1d85);color:#fff;text-align:center;padding:2rem;cursor:pointer;transition:opacity .6s ease,visibility .6s}
#intro.hide{opacity:0;visibility:hidden}
html.introseen #intro{display:none}
#intro .i-logo{width:150px;height:150px;object-fit:contain;background:transparent;border-radius:0;padding:0;filter:drop-shadow(0 0 2px rgba(255,255,255,.7)) drop-shadow(0 0 8px rgba(255,255,255,.35));animation:ifade .6s ease both}
#intro h1{color:#fff;font-size:clamp(1.6rem,4.2vw,2.6rem);margin:.4rem 0 0;animation:irise .8s .25s both}
#intro .i-sch{color:#e6e8ff;font-weight:600;font-size:1.1rem;animation:irise .8s .4s both}
@keyframes ifade{from{opacity:0}to{opacity:1}}
#intro .i-sub{color:#b9bdf3;font-size:.95rem;animation:irise .8s .55s both}
#intro .i-bar{width:min(260px,70vw);height:4px;background:rgba(255,255,255,.25);border-radius:4px;overflow:hidden;margin-top:1rem}
#intro .i-bar i{display:block;height:100%;width:0;background:var(--recess);animation:iload 2.3s .2s ease-out forwards}
body #intro button.i-skip{background:rgba(255,255,255,.16);color:#fff;margin-top:1rem;padding:.5rem 1.2rem;font-size:.9rem}
body #intro button.i-skip:hover{background:rgba(255,255,255,.28)}
@keyframes ipop{from{transform:scale(.6);opacity:0}to{transform:scale(1);opacity:1}}
@keyframes irise{from{transform:translateY(14px);opacity:0}to{transform:none;opacity:1}}
@keyframes iload{to{width:100%}}
@media(prefers-reduced-motion:reduce){ #intro *{animation:none!important}#intro .i-bar i{width:100%}main{animation:none}}
@media print{ #intro{display:none!important}}
@media print{
.doc{padding:0!important;margin:0!important;border:0!important;border-radius:0!important;box-shadow:none!important;background:#fff!important;width:auto!important}
.doc + .doc{break-before:page!important;page-break-before:always!important}
.meta{display:flex!important;flex-direction:row!important;flex-wrap:nowrap!important;justify-content:space-between!important;gap:0 2rem!important;font-size:10px!important;line-height:1.3!important;margin:4px 0!important}
.meta > div{flex:1 1 50%!important;min-width:0!important;margin:0!important}
.doc-title{font-size:15px!important;margin:2px 0 0!important}
.gridwrap{display:block!important;overflow:visible!important;border:0!important;background:none!important}
.mobile-days{display:none!important}
.grid{min-width:0!important;width:100%!important;table-layout:fixed!important;font-size:9px!important}
.grid th, .grid td, .grid thead th, .grid tbody th{font-size:9px!important;line-height:1.2!important;padding:2px 3px!important;white-space:normal!important;width:auto!important}
.grid td.num{white-space:nowrap!important}
.slot{min-height:0!important;padding:1px 3px!important;font-size:9px!important;border-radius:0!important}
.slot strong{font-size:9px!important}
.sign{display:grid!important;grid-template-columns:repeat(auto-fit,minmax(140px,1fr))!important;margin-top:6px!important;gap:2px 1rem!important}
.sign .name{margin-top:12px!important;font-size:10px!important}
.sign .role, .sign .title, .legend{font-size:9px!important}
.room{font-size:12px!important;margin:3px 0!important}
}
html.pm .doc{padding:0!important;margin:0!important;border:0!important;border-radius:0!important;box-shadow:none!important;background:#fff!important;width:auto!important}
html.pm .doc + .doc{break-before:page!important;page-break-before:always!important}
html.pm .meta{display:flex!important;flex-direction:row!important;flex-wrap:nowrap!important;justify-content:space-between!important;gap:0 2rem!important;font-size:10px!important;line-height:1.3!important;margin:4px 0!important}
html.pm .meta > div{flex:1 1 50%!important;min-width:0!important;margin:0!important}
html.pm .doc-title{font-size:15px!important;margin:2px 0 0!important}
html.pm .gridwrap{display:block!important;overflow:visible!important;border:0!important;background:none!important}
html.pm .mobile-days{display:none!important}
html.pm .grid{min-width:0!important;width:100%!important;table-layout:fixed!important;font-size:9px!important}
html.pm .grid th,html.pm .grid td,html.pm .grid thead th,html.pm .grid tbody th{font-size:9px!important;line-height:1.2!important;padding:2px 3px!important;white-space:normal!important;width:auto!important}
html.pm .grid td.num{white-space:nowrap!important}
html.pm .slot{min-height:0!important;padding:1px 3px!important;font-size:9px!important;border-radius:0!important}
html.pm .slot strong{font-size:9px!important}
html.pm .sign{display:grid!important;grid-template-columns:repeat(auto-fit,minmax(140px,1fr))!important;margin-top:6px!important;gap:2px 1rem!important}
html.pm .sign .name{margin-top:12px!important;font-size:10px!important}
html.pm .sign .role,html.pm .sign .title,html.pm .legend{font-size:9px!important}
html.pm .room{font-size:12px!important;margin:3px 0!important}
/* ---- boxed sign-in / sign-up card ---- */
.login .auth-body{background:#fff;border:1.5px solid #cfd6ea;border-radius:16px;padding:2rem 2rem 1.6rem;margin:auto 0;box-shadow:0 12px 32px rgba(27,31,122,.12),0 2px 6px rgba(27,31,122,.06)}
.login .auth-body h2{padding-bottom:.7rem;margin-bottom:.8rem;border-bottom:2px solid var(--blue)}
.login .auth-body input:not([type=checkbox]):not([type=radio]):not([type=hidden]),.login .auth-body select{border:1.5px solid #cfd6ea;border-radius:8px;padding:.65rem .8rem;background:#f8faff;margin-top:.3rem}
.login .auth-body input:focus,.login .auth-body select:focus{outline:0;border-color:var(--blue);background:#fff;box-shadow:0 0 0 3px rgba(44,49,201,.15)}
.login .auth-body .tidfield{margin-top:.3rem}
.login .auth-body .tidfield .tidfix{border:1.5px solid #cfd6ea;border-right:0;border-radius:8px 0 0 8px;background:#eef2fb;color:var(--navy)}
.login .auth-body .tidfield input{margin-top:0!important;border-left:0!important}
.login .auth-body .pwwrap input{padding-right:3rem}
.login .auth-body label{margin-top:1rem}
.login .auth-body button.dark{border-radius:8px;box-shadow:0 6px 14px rgba(17,17,17,.25)}
@media(max-width:800px){.login .auth-body{padding:1.4rem 1.2rem 1.2rem;border-radius:14px}}
.brandrow{display:flex;align-items:center;gap:.9rem;margin-bottom:2.2rem}
.login .brandrow .logo,.login .brandrow .logoimg{margin-bottom:0;flex:none}
.brandschool small{display:block;font-weight:500;font-size:.8rem;letter-spacing:.04em;color:#c9ccf7;margin-top:.15rem}
.brandschool{font-size:.95rem;font-weight:600;letter-spacing:.03em;line-height:1.3;color:#e6e8ff;max-width:13rem}
@media(max-width:800px){.brandrow{margin-bottom:.9rem;gap:.7rem}.brandschool{font-size:.85rem}}
@media(min-width:801px){
.login .brandrow{gap:1.2rem;align-items:center;margin-bottom:2rem}
.login .brandrow .logoimg,.login .brandrow .logo{width:108px;height:108px}
.login .brandrow .brandschool{font-family:"Poppins","Segoe UI",Arial,sans-serif;font-size:1.3rem;font-weight:600;line-height:1.25;letter-spacing:0;max-width:20rem;color:#fff;align-self:center;text-wrap:balance}
.login .brandrow .brandschool small{font-family:"Inter","Segoe UI",Arial,sans-serif;font-size:.9rem;font-weight:500;letter-spacing:.05em;margin-top:.45rem}
}

/* ======== Typography refresh ======== */
body{font-family:"Inter","Segoe UI",Arial,sans-serif;font-size:16px;line-height:1.6;letter-spacing:.005em;-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
h1,h2,h3,.brand-name,.letterhead .school,.doc-title,.room,.login .side h1,.login .auth-body h2,#intro h1{font-family:"Poppins","Segoe UI",Arial,sans-serif;letter-spacing:-.01em}
h1{font-size:2rem;font-weight:700;line-height:1.2}
h2{font-size:1.4rem;font-weight:600;line-height:1.3}
h3{font-size:1.15rem;font-weight:600;line-height:1.3}
main h1::after{content:"";display:block;width:52px;height:4px;margin-top:.5rem;border-radius:4px;background:linear-gradient(90deg,var(--blue),var(--gold))}
label{font-weight:600;font-size:.92rem;color:#2b3350;letter-spacing:.01em}
input,select,textarea{font-size:1rem;font-family:inherit}
button,.btn{font-family:"Inter","Segoe UI",Arial,sans-serif;font-weight:600;letter-spacing:.01em}
.hint{font-size:.88rem;line-height:1.45}
.msg{font-size:.97rem}
.list th{font-family:"Poppins","Segoe UI",Arial,sans-serif;font-weight:600;font-size:.88rem;letter-spacing:.02em}
.list td{font-size:.97rem}
.grid thead th{font-family:"Poppins","Segoe UI",Arial,sans-serif;font-weight:600;font-size:.92rem;letter-spacing:.02em}
.slot strong{font-weight:600}
.legend{font-size:.92rem}
.login .auth-body h2{font-size:1.55rem;font-weight:700}
@media(max-width:800px){h1{font-size:1.55rem}h2{font-size:1.25rem}}

/* ======== Menu button: three lines ======== */
.menubtn{display:none;width:48px;height:48px;padding:0;align-items:center;justify-content:center}
.bars{position:relative;display:block;width:24px;height:18px}
.bars i{position:absolute;left:0;right:0;height:3px;border-radius:3px;background:currentColor;transition:transform .25s,opacity .2s,top .25s}
.bars i:nth-child(1){top:0}.bars i:nth-child(2){top:7.5px}.bars i:nth-child(3){top:15px}
.top.open .bars i:nth-child(1){top:7.5px;transform:rotate(45deg)}
.top.open .bars i:nth-child(2){opacity:0}
.top.open .bars i:nth-child(3){top:7.5px;transform:rotate(-45deg)}
@media(max-width:1100px){body .menubtn{display:inline-flex}}

/* ======== Tap feedback: pressed, ripple and loading states ======== */
html{-webkit-tap-highlight-color:rgba(45,50,200,.25)}
body button:not(.eye):not(.tlink):not(.sclear),body .btn,body .backbtn,body .top .tabs a,body .top .acct a,body .daytab,body .tresults a{position:relative;overflow:hidden;-webkit-user-select:none;user-select:none;-webkit-touch-callout:none}
.ripple{position:absolute;border-radius:50%;background:rgba(255,255,255,.55);transform:scale(0);animation:ripple .6s ease-out forwards;pointer-events:none}
body .btn.plain .ripple,body button.plain .ripple,body .top .tabs a .ripple,body .top .acct a .ripple,body .daytab .ripple,body .menubtn .ripple,body .backbtn .ripple,body .tresults .ripple,body button.danger .ripple{background:rgba(45,50,200,.3)}
@keyframes ripple{from{transform:scale(0);opacity:.9}to{transform:scale(1);opacity:0}}
body button.tap,body .btn.tap,body .backbtn.tap,body .daytab.tap,body .menubtn.tap{transform:scale(.94)!important;filter:brightness(.8)!important;box-shadow:inset 0 3px 10px rgba(0,0,0,.35)!important;transition:transform .08s,filter .08s}
body button.dark.tap{background:#2d32c8!important;filter:none!important}
body button.plain.tap,body .btn.plain.tap,body .daytab.tap:not(.on),body .menubtn.tap{background:#aab6f5!important;filter:none!important;color:var(--navy)!important}
body button.danger.tap{background:var(--bad)!important;color:#fff!important;filter:none!important}
body .top .tabs a.tap,body .top .acct a.tap{background:var(--blue)!important;color:#fff!important;transform:scale(.97)}
body .tresults a.tap{background:#cfd6f6!important;transform:scale(.98)}
.chk:active{background:#c9d1f7!important}
body button.busy{cursor:wait}
body button.busy:disabled{opacity:.92}
body button.busy::after{content:"";display:inline-block;width:1em;height:1em;margin-left:.6rem;border:2px solid rgba(255,255,255,.45);border-top-color:#fff;border-radius:50%;animation:spin .7s linear infinite;vertical-align:-.15em}
body button.plain.busy::after,body button.danger.busy::after{border-color:rgba(45,50,200,.25);border-top-color:var(--blue)}
body button.dark.busy{background:#2d32c8}
@keyframes spin{to{transform:rotate(360deg)}}
@media print{.ripple{display:none!important}}

/* ======== Report a problem, notifications ======== */
.reportlnk{display:flex!important;align-items:center;justify-content:center;gap:.5rem;margin-top:.9rem;width:100%}
.photoprev{display:block;max-width:100%;max-height:220px;margin-top:.6rem;border-radius:8px;border:1px solid var(--line)}
.photoprev[hidden],.badge[hidden],.sclear[hidden],.toast[hidden]{display:none!important}
.badge{display:inline-block;min-width:1.35rem;padding:0 .4rem;margin-left:.45rem;border-radius:999px;background:#d92d2d;color:#fff;font-size:.75rem;font-weight:700;line-height:1.35rem;text-align:center}
a.msg{display:block;text-decoration:none}
.msg.notice{background:#fff6dc;border-color:var(--gold);color:#5a4210}
.pill{display:inline-block;padding:.15rem .6rem;border-radius:999px;font-size:.75rem;font-weight:700;margin-left:.3rem}
.pill.new{background:#fde68a;color:#5a4210}.pill.ok{background:#d1fae5;color:#14532d}
.report.fresh{border-left:5px solid var(--gold)}.report.done{opacity:.8}
.rhead{display:flex;justify-content:space-between;gap:1rem;flex-wrap:wrap}
.rmsg{white-space:pre-wrap;margin:.7rem 0;overflow-wrap:anywhere}
.rphoto{max-width:100%;max-height:340px;border-radius:8px;border:1px solid var(--line);display:block}
.toast{position:fixed;left:50%;bottom:1.2rem;transform:translateX(-50%);max-width:92vw;background:#1c2133;color:#fff;padding:.8rem 1.2rem;border-radius:10px;box-shadow:0 10px 30px rgba(0,0,0,.3);z-index:9000;display:flex;gap:1rem;align-items:center}
.toast a{color:#ffd966;font-weight:700}
body .toast button.toastx{background:transparent;padding:0 .4rem;font-size:1.4rem;line-height:1;min-height:0;color:#fff}

/* ======== Teacher search ======== */
.tsearch{margin:0 0 1rem;max-width:560px}
[data-find][hidden],#tqnone[hidden]{display:none!important}
.tresults{list-style:none;margin:.6rem 0 0;padding:0;display:grid;gap:.4rem}
.tresults a{display:flex;justify-content:space-between;gap:1rem;padding:.65rem .9rem;border:1px solid var(--line);border-radius:8px;background:#fff;text-decoration:none;color:var(--navy);font-weight:600}
.tresults a:hover{background:var(--tint)}
.tresults small{color:var(--muted);font-weight:500}

/* ======== Notification bell ======== */
body .bell,body .top .acct a.bell{position:relative;display:inline-flex;align-items:center;justify-content:center;width:44px;height:44px;min-height:44px;padding:0;border-radius:50%;background:#e3e7fb;color:var(--navy);overflow:visible;text-decoration:none}
body .top .acct a.bell{justify-content:center;width:44px}
.bell .badge{position:absolute;top:-4px;right:-4px;margin:0}
body .bell.on{background:var(--blue);color:#fff}
body .bell:active{background:var(--blue);color:#fff;transform:scale(.9)}
.bell.mob{display:none!important}
@media(max-width:1100px){.bell.mob{display:inline-flex!important;margin-left:auto;margin-right:.6rem}.acct .bell.desk{display:none!important}}
.note.fresh{border-left:5px solid var(--gold)}

/* ======== Type filter (Excel-style V button) ======== */
.typeth{position:relative}
.thwrap{display:inline-flex;align-items:center;gap:.4rem}
body button.vbtn{min-height:0;width:26px;height:26px;padding:0;border-radius:6px;background:#e3e7fb;color:var(--navy);display:inline-flex;align-items:center;justify-content:center;box-shadow:none}
.typeth.open .vbtn,.typeth.active .vbtn{background:var(--blue);color:#fff}
.list th.typeth.open,.list th.typeth.active{background:#dfe4fb;color:var(--blue)}
td.typecell.hl{background:#eef1ff;font-weight:600;color:var(--blue)}
.vmenu{position:fixed;z-index:200;min-width:240px;background:#fff;border:1px solid var(--line);border-radius:10px;box-shadow:0 12px 30px rgba(20,25,80,.28);padding:.35rem;display:grid;gap:.15rem;text-align:left;font-family:"Inter","Segoe UI",Arial,sans-serif}
.vmenu[hidden]{display:none}
body .vmenu button.vopt{background:transparent;color:var(--navy);box-shadow:none;border:0;text-align:left;justify-content:flex-start;padding:.6rem .75rem;font-weight:500;border-radius:6px;width:100%;min-height:0;display:block}
body .vmenu button.vopt:hover{background:#eef0fb}
body .vmenu button.vopt.on{background:var(--blue);color:#fff;font-weight:600}
.typesel{display:none;margin:0 0 1rem;max-width:560px}
@media(max-width:800px){.typesel{display:block}}

/* ======== Save / Cancel button rows ======== */
body .btnrow{display:flex;flex-wrap:wrap;gap:.7rem;align-items:stretch;margin:1.2rem 0 0}
body .btnrow>*{margin:0}
body .btnrow button,body .btnrow .btn{display:inline-flex;align-items:center;justify-content:center;min-height:46px;padding:0 1.4rem;line-height:1.2;text-align:center;vertical-align:top}
@media(max-width:800px){body .btnrow>*{flex:1 1 0;min-width:0}}

/* ======== Screenshots ======== */
.thumbs{display:grid;grid-template-columns:repeat(auto-fill,minmax(110px,1fr));gap:.6rem;margin-top:.6rem}
.thumbs:empty{display:none}
.thumb{position:relative;border:1px solid var(--line);border-radius:8px;overflow:hidden;background:#fff}
.thumb img{display:block;width:100%;height:110px;object-fit:cover}
body .thumb button.thumbx{position:absolute;top:4px;right:4px;width:28px;height:28px;min-height:0;padding:0;border-radius:50%;background:rgba(28,33,51,.85);color:#fff;font-size:1.2rem;line-height:1;display:flex;align-items:center;justify-content:center}
body .brand-logo{background:transparent;border-radius:0;padding:0;box-shadow:none;filter:drop-shadow(0 0 2px rgba(255,255,255,.8)) drop-shadow(0 1px 4px rgba(27,31,122,.25))}
.login .logoimg{background:transparent;border-radius:0;padding:0;box-shadow:none;filter:drop-shadow(0 0 2px rgba(255,255,255,.7)) drop-shadow(0 0 8px rgba(255,255,255,.35))}
.otime{display:flex;align-items:center;gap:.4rem;flex-wrap:wrap}
.otime input[type=time]{flex:1 1 7.5rem;min-width:7.5rem}
.minedit select{width:100%;min-width:7rem}
.assign select{min-width:130px}
.progitem{margin:0 0 2.6rem;padding-bottom:1.4rem;border-bottom:2px dashed #c5cbe3;min-height:70vh;scroll-margin-top:1rem}
.progitem:last-child{border-bottom:0}
.progitem .doc{margin:.4rem 0 .6rem}
.progitem .grid tbody tr{height:3.4rem}
body button.fabtop{position:fixed;right:1.1rem;bottom:1.1rem;z-index:150;width:54px;height:54px;min-height:0;padding:0;border-radius:50%;display:flex;align-items:center;justify-content:center;box-shadow:0 6px 18px rgba(27,31,122,.4)}
body button.fabtop svg{width:26px;height:26px}
.fabtop[hidden]{display:none!important}
body button.fabtop{position:fixed!important;right:1.1rem;right:max(1.1rem,env(safe-area-inset-right));bottom:1.1rem;bottom:max(1.1rem,env(safe-area-inset-bottom));overflow:visible}
@media(max-width:800px){body button.fabtop{width:48px;height:48px;right:.8rem;bottom:.9rem}}
button.linklike{all:unset;cursor:pointer;color:var(--blue);text-decoration:underline;font-weight:600;font-size:.9rem}
a.btn.signout{background:#fff;color:var(--bad);border:1px solid var(--bad)}
a.btn.signout:hover{background:var(--bad);color:#fff}
.advtag{display:inline-block;margin:0 0 .5rem;padding:.25rem .7rem;border-radius:999px;background:#fff4d6;color:#7a5200;font-weight:700;font-size:.85rem}
.helpfab.inline{position:relative;top:auto;right:auto;margin-left:auto;flex:none}
@media print{.progitem{margin:0!important;padding:0!important;border:0!important;min-height:0!important}.progitem+.progitem{break-before:page!important;page-break-before:always!important}}
html.pm .progitem{margin:0!important;padding:0!important;border:0!important;min-height:0!important}
html.pm .progitem+.progitem{break-before:page!important;page-break-before:always!important}
.rgallery{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:.6rem;margin-top:.6rem}
.rgallery img{width:100%;height:150px;object-fit:cover;border-radius:8px;border:1px solid var(--line);display:block}
"""

ADDON_CSS = """
.steps{display:flex;flex-wrap:wrap;gap:.4rem;margin:0 0 1rem}
.step{padding:.4rem .9rem;border:1px solid var(--line);border-radius:999px;background:#fff;color:var(--navy);text-decoration:none;font-weight:600;font-size:.9rem}
.step.on,.step:hover{background:var(--blue);color:#fff;border-color:var(--blue)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:.7rem;margin:.6rem 0}
.kpi{background:var(--tint);border:1px solid var(--line);border-radius:8px;padding:.7rem .9rem}
.kpi b{display:block;font:700 1.6rem "Poppins","Segoe UI",sans-serif;color:var(--navy)}.kpi span{color:var(--muted);font-size:.85rem}
.kpi.bad b{color:var(--bad)}.kpi.ok b{color:var(--ok)}
.mx{border-collapse:collapse;width:auto;min-width:100%}.mx td,.mx th{border:1px solid var(--line);text-align:center;padding:.35rem .45rem;font-size:.85rem}
.mx th{background:var(--tint);color:var(--navy)}.mx td.l,.mx th.l{text-align:left}
.ck{width:auto!important;transform:scale(1.2)}
.tt{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.9rem;min-height:12rem}
.why{color:var(--bad)}.okt{color:var(--ok)}
.bar{height:8px;background:var(--tint);border-radius:99px;overflow:hidden;min-width:70px}.bar i{display:block;height:100%;background:var(--blue)}
details.card>summary{cursor:pointer;font-weight:600;color:var(--navy)}
ul.issues{margin:.3rem 0 0;padding-left:1.2rem}ul.issues li{margin:.2rem 0}

/* ======== Admin main navigation (the 11 menu items) ======== */
.shell{display:block}
.mainnav,.side{display:flex;flex-direction:column;gap:.45rem}
.mn{display:grid;grid-template-columns:2rem 2.4rem minmax(0,1fr) 1.2rem;align-items:center;gap:.5rem;padding:.7rem .8rem;border-radius:14px;text-decoration:none;color:var(--ink);background:#fff;border:1px solid var(--line);min-height:62px}
.mn:hover{background:var(--tint)}
.mn.on{background:var(--blue);border-color:var(--blue);color:#fff}
.mn-num{font:600 .82rem "Poppins","Segoe UI",sans-serif;color:var(--muted);text-align:center}
.mn-ic{display:flex;align-items:center;justify-content:center;color:var(--navy)}
.mn-tx b{display:block;font:600 1rem/1.2 "Poppins","Segoe UI",sans-serif;white-space:normal}
.mn-tx small{display:block;font-size:.8rem;line-height:1.3;color:var(--muted);margin-top:.1rem;white-space:normal}
.mn-go{color:var(--muted)}
.mn.on .mn-num,.mn.on .mn-ic,.mn.on .mn-tx small,.mn.on .mn-go{color:#fff}
.side-h{font:700 .78rem "Poppins","Segoe UI",sans-serif;letter-spacing:.09em;text-transform:uppercase;color:var(--muted);padding:.2rem .4rem .3rem}
.side-f{display:flex;flex-wrap:wrap;gap:.3rem .9rem;padding:.8rem .4rem 0;font-size:.9rem}
.side{display:none}
@media(min-width:1101px){
 .shell{display:grid;grid-template-columns:318px minmax(0,1fr);align-items:start;max-width:1640px;margin:0 auto}
 .side{display:flex;position:sticky;top:0;max-height:100vh;overflow-y:auto;padding:1rem .8rem 2rem 1rem}
 body .top .mainnav,body .top .admtabs{display:none!important}
 body .top .in{grid-template-areas:"brand acct"}
 .shellmain main{max-width:1180px;margin-left:0}
 .shellmain footer{text-align:left;padding-left:1.2rem}
}
@media(max-width:1100px){
 body .top nav{width:min(420px,calc(100vw - 1rem))!important;right:.5rem!important;max-height:calc(100vh - 90px)}
 body .top .mainnav{gap:.4rem}
 body .top .mn{min-height:60px;background:#fff}
 body .top .mn.on{background:var(--blue)}
 body .top .admtabs{margin-top:.2rem}
}
@media print{.shell{display:block!important}.side{display:none!important}}
/* ======== Dashboard ======== */
.dash-top{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(0,1fr);gap:1rem;align-items:stretch}
@media(max-width:800px){.dash-top{grid-template-columns:1fr}}
.ring{display:flex;align-items:center;gap:1.1rem}
.ring .pct{width:92px;height:92px;border-radius:50%;display:grid;place-items:center;flex:none;background:conic-gradient(var(--blue) calc(var(--p)*1%),var(--tint) 0)}
.ring .pct span{width:70px;height:70px;border-radius:50%;background:#fff;display:grid;place-items:center;font:700 1.25rem "Poppins","Segoe UI",sans-serif;color:var(--navy)}
.stepcards{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:.7rem;margin:.6rem 0 1rem}
.stepcard{display:block;text-decoration:none;color:var(--ink);background:#fff;border:1px solid var(--line);border-radius:12px;padding:.8rem .9rem;border-left:5px solid #c9cde4}
.stepcard.done{border-left-color:var(--ok)}.stepcard.todo{border-left-color:var(--gold)}
.stepcard b{font-family:"Poppins","Segoe UI",sans-serif;color:var(--navy)}
.stepcard small{display:block;color:var(--muted);margin-top:.2rem}
.stepcard .st{float:right;font-size:.75rem;font-weight:700;border-radius:99px;padding:.1rem .55rem}
.stepcard.done .st{background:#d1fae5;color:#14532d}.stepcard.todo .st{background:#fde68a;color:#5a4210}
.alerts{list-style:none;margin:.3rem 0 0;padding:0}
.alerts li{display:flex;gap:.7rem;align-items:flex-start;justify-content:space-between;padding:.55rem .2rem;border-top:1px solid var(--line)}
.alerts li:first-child{border-top:0}
.alerts .dot{flex:none;width:.7rem;height:.7rem;border-radius:50%;margin-top:.45rem;background:var(--gold)}
.alerts .bad .dot{background:var(--bad)}
.alerts .t{flex:1;min-width:0;overflow-wrap:anywhere}
/* ======== Curriculum / pickers ======== */
.cur-note{background:var(--tint);border:1px solid var(--line);border-radius:10px;padding:.7rem .9rem;margin:.5rem 0 1rem}
.cur-name{font-weight:600}.cur-spec{display:block;font-size:.82rem;color:var(--muted)}
table.list td input[type=number]{max-width:7.5rem}
.specpick{min-width:220px}
.specpick .sp-text{display:none;white-space:normal;overflow-wrap:anywhere;font-size:.93rem}
.specpick details.sp-box{border:1px solid var(--line);border-radius:10px;background:#fff;padding:.3rem .6rem}
.specpick summary{cursor:pointer;font-weight:600;color:var(--navy);font-size:.92rem}
.specpick .sp-list{max-height:260px;overflow:auto;margin-top:.4rem}
.specpick fieldset{border:0;border-top:1px solid var(--line);margin:.4rem 0 0;padding:.3rem 0 0}
.specpick legend{font-size:.78rem;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:var(--muted);padding:0}
.specpick label{display:flex;gap:.5rem;align-items:flex-start;font-weight:400;font-size:.9rem;margin:.15rem 0}
.specpick input[type=checkbox]{width:auto!important;margin-top:.25rem;transform:scale(1.15)}
.assign tr.rowview .specpick .sp-text{display:block}
.assign tr.rowview .specpick details.sp-box{display:none}
.chipline{display:flex;flex-wrap:wrap;gap:.3rem;margin-top:.3rem}
.chip{background:var(--tint);border:1px solid var(--line);border-radius:99px;padding:.05rem .6rem;font-size:.8rem}
table.list.assign.tm{table-layout:fixed;width:100%;min-width:880px}
table.list.assign.tm th:nth-child(1){width:21%}table.list.assign.tm th:nth-child(2){width:11%}
table.list.assign.tm th:nth-child(3){width:30%}table.list.assign.tm th:nth-child(4){width:15%}
table.list.assign.tm th:nth-child(5){width:13%}table.list.assign.tm th:nth-child(6){width:10%}
.assign .specpick{min-width:0}.assign .specpick .sp-text{white-space:normal;overflow-wrap:anywhere;line-height:1.4}
.assign .specpick .sp-list{max-height:220px}
table.list.assign.tm td{vertical-align:top}
@media(max-width:800px){table.list.assign.tm{min-width:0}}
.stepcard .roles{border-top:1px dashed var(--line);margin-top:.5rem;padding-top:.4rem;font-size:.8rem}

.dock{display:none}
@media(max-width:1100px){
 .dock{display:grid;grid-template-columns:repeat(3,1fr);position:fixed;left:0;right:0;bottom:0;z-index:60;background:#fff;border-top:1px solid var(--line);padding:.3rem .5rem calc(.3rem + env(safe-area-inset-bottom,0px));box-shadow:0 -4px 14px rgba(20,30,80,.12)}
 .dock a,.dock button{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:.1rem;min-height:52px;border:0;background:transparent;color:var(--navy);font:600 .78rem "Poppins","Segoe UI",sans-serif;text-decoration:none;border-radius:12px;box-shadow:none;text-shadow:none;transform:none}
 .dock a:active,.dock button:active{background:var(--tint);transform:none;box-shadow:none}
 body{padding-bottom:calc(72px + env(safe-area-inset-bottom,0px))}
}
@media print{.dock{display:none!important}}
details.tip{margin:.2rem 0 .8rem;font-size:.92rem}
details.tip summary{cursor:pointer;color:var(--muted);font-weight:600;list-style:none}
details.tip summary::before{content:"\\24D8  "}
details.tip p{margin:.4rem 0 0;color:var(--muted)}
.fitnote{border-radius:12px;padding:.8rem 1rem;margin:.6rem 0 1rem}
/* ======== timetable editor ======== */
.ttcard{border:1px solid var(--line);border-radius:12px;padding:.7rem .9rem;margin:.6rem 0;background:#fff}
.ttcard h4{margin:0 0 .5rem;font-family:"Poppins","Segoe UI",sans-serif;color:var(--navy)}
.ttrow{display:flex;flex-wrap:wrap;gap:.5rem;align-items:center;margin:.3rem 0}
.ttrow input[type=time]{width:auto}.ttrow select{width:auto}
.ttrow .x{padding:.2rem .6rem}
.user-role{display:inline-block;border-radius:99px;padding:.1rem .6rem;font-size:.78rem;font-weight:700;background:var(--tint);color:var(--navy)}
.user-role.admin{background:#fde68a;color:#5a4210}
"""


TEMPLATES = {
"base.html": """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script>try{if(localStorage.getItem('view')==='desktop'){document.querySelector('meta[name=viewport]').setAttribute('content','width=1100');}}catch(e){}</script>
<script>try{if(sessionStorage.getItem('intro')==='1')document.documentElement.classList.add('introseen');}catch(e){}</script>
<title>{% block title %}{% endblock %} | {{ app_name }}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Poppins:wght@500;600;700&display=swap" rel="stylesheet">
<style>""" + CSS + ADDON_CSS + """</style></head><body>
<div id="intro" role="status" aria-label="Welcome">{% if has_logo %}<img class="i-logo" src="{{ logo_url }}" alt="">{% else %}<svg class="i-logo" viewBox="0 0 48 48" aria-hidden="true"><rect width="48" height="48" rx="12" fill="#2d32c8"/><path d="M24 12 7 20l17 8 17-8-17-8z" fill="#fff"/><path d="M14 25v7c0 2 4.5 5 10 5s10-3 10-5v-7l-10 4.6L14 25z" fill="#fff" opacity=".85"/></svg>{% endif %}
<h1>{{ app_name }}</h1><div class="i-sch">{{ cfg.school_name }}</div>
<div class="i-bar"><i></i></div><button type="button" class="i-skip">Skip</button></div>
{% if g.user %}<header class="top"><div class="in">
<a class="brand" href="{{ url_for('home') }}">{% if has_logo %}<img class="brand-logo" src="{{ logo_url }}" alt="{{ cfg.school_name }} logo">{% else %}<svg class="brand-logo" viewBox="0 0 48 48" role="img" aria-label="School"><rect width="48" height="48" rx="12" fill="#2d32c8"/><path d="M24 12 7 20l17 8 17-8-17-8z" fill="#fff"/><path d="M14 25v7c0 2 4.5 5 10 5s10-3 10-5v-7l-10 4.6L14 25z" fill="#fff" opacity=".85"/></svg>{% endif %}
<div class="brand-name">{{ app_name }}<small>San Jose Litex Senior High School</small></div></a>
<a class="bell mob {{ 'on' if request.endpoint in ('reports', 'notifications', 'signup_requests') }}" href="{{ url_for('reports') if g.user.role == 'admin' else url_for('notifications') }}" title="Notifications" aria-label="Notifications"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/></svg><span class="badge nbadge" {% if not bell %}hidden{% endif %}>{{ bell }}</span></a>
<a class="bell mob {{ 'on' if request.endpoint in ('account', 'account_settings') }}" href="{{ url_for('account') }}" title="Profile" aria-label="Profile"><svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true"><circle cx="12" cy="8" r="4"/><path d="M4 20.5c0-4.7 4-7.5 8-7.5s8 2.8 8 7.5v.5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-.5z"/></svg></a>
<button type="button" class="menubtn" id="menubtn" aria-expanded="false" aria-controls="nav" aria-label="Open menu"><span class="bars" aria-hidden="true"><i></i><i></i><i></i></span></button>
<nav id="nav">{% if g.user.role == 'admin' %}<div class="mainnav" role="navigation" aria-label="Main navigation">{{ main_nav() }}</div>
<div class="tabs admtabs"><a href="{{ url_for('account') }}" class="{{ 'on' if request.endpoint=='account' }}">My Profile</a>
<a href="{{ url_for('account_settings') }}" class="{{ 'on' if request.endpoint=='account_settings' }}">Account Settings</a></div>
{% else %}<div class="tabs">
<a href="{{ url_for('profile') }}" class="{{ 'on' if request.endpoint=='profile' }}">My Teacher's Program</a>
<a href="{{ url_for('program') }}" class="{{ 'on' if request.endpoint in ('program','entry_edit') }}">Class Programs</a>
<a href="{{ url_for('account') }}" class="{{ 'on' if request.endpoint=='account' }}">Profile</a>
<a href="{{ url_for('account_settings') }}" class="{{ 'on' if request.endpoint=='account_settings' }}">Settings</a></div>{% endif %}
<div class="acct"><a class="bell desk {{ 'on' if request.endpoint in ('reports', 'notifications', 'signup_requests') }}" href="{{ url_for('reports') if g.user.role == 'admin' else url_for('notifications') }}" title="Notifications" aria-label="Notifications"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/></svg><span class="badge nbadge" {% if not bell %}hidden{% endif %}>{{ bell }}</span></a><a class="bell desk {{ 'on' if request.endpoint in ('account', 'account_settings') }}" href="{{ url_for('account') }}" title="Profile" aria-label="Profile"><svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true"><circle cx="12" cy="8" r="4"/><path d="M4 20.5c0-4.7 4-7.5 8-7.5s8 2.8 8 7.5v.5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-.5z"/></svg></a><span class="who">{{ g.user.full_name }}</span></div>
</nav></div></header>{% endif %}
{% if g.user and g.user.role == 'admin' %}<div class="shell"><aside class="side noprint" aria-label="Main navigation"><div class="side-h">Main Navigation</div>{{ main_nav() }}<div class="side-f"><a href="{{ url_for('account') }}">My Profile</a><a href="{{ url_for('account_settings') }}">Account Settings</a><a href="{{ url_for('logout') }}">Sign out</a></div></aside><div class="shellmain">{% endif %}{% block page %}<main>
{% if g.user and bell and request.endpoint not in ('reports', 'notifications') %}<a class="msg notice noprint" href="{{ url_for('reports') if g.user.role == 'admin' else url_for('notifications') }}"><strong>{{ bell }} new notification{{ '' if bell == 1 else 's' }}</strong>{{ ' (requests and problem reports)' if g.user.role == 'admin' }}. Tap to read {{ 'it' if bell == 1 else 'them' }}.</a>{% endif %}
{% if g.user and g.user.role == 'admin' and approval and request.endpoint in ('dashboard','auto_generate','auto_conflicts','program','auto_loading','auto_reports') %}<div class="msg ok noprint"><strong>Schedule approved and locked</strong> by {{ approval.by }} on {{ approval.at|stamp12 }}. Changes are blocked until it is reopened in Validation Center.</div>{% endif %}
{% for cat, m in get_flashed_messages(with_categories=true) %}<div class="msg {{ cat }}" role="status">{{ m }}</div>{% endfor %}
{% block content %}{% endblock %}</main>
<footer>{{ cfg.school_name }} &middot; {{ app_name }}<br><a href="#" class="viewtoggle" hidden></a></footer>{% endblock %}{% if g.user and g.user.role == 'admin' %}</div></div>{% endif %}
<script>(function(){
var b=document.getElementById('menubtn'),h=document.querySelector('.top');
if(b&&h){function setMenu(o){h.classList.toggle('open',o);b.setAttribute('aria-expanded',o);b.setAttribute('aria-label',o?'Close menu':'Open menu');}
b.addEventListener('click',function(e){e.stopPropagation();setMenu(!h.classList.contains('open'));});
document.addEventListener('click',function(e){if(h.classList.contains('open')&&!h.querySelector('nav').contains(e.target))setMenu(false);});
document.addEventListener('keydown',function(e){if(e.key==='Escape')setMenu(false);});}
document.querySelectorAll('table.list').forEach(function(t){
 var hs=t.querySelectorAll('thead th');if(!hs.length)return;
 t.classList.add('stack');
 t.querySelectorAll('tbody tr').forEach(function(r){var i=0;
  Array.prototype.forEach.call(r.children,function(c){var l=hs[i]?(hs[i].getAttribute('data-label')||hs[i].textContent.trim()):'';if(l)c.setAttribute('data-label',l);i+=c.colSpan||1;});});});
document.querySelectorAll('.mobile-days').forEach(function(w){
 var tabs=w.querySelectorAll('.daytab'),pan=w.querySelectorAll('.dayp');
 var names=Array.prototype.map.call(tabs,function(x){return x.getAttribute('data-d')});
  function show(d){tabs.forEach(function(x){x.classList.toggle('on',x.getAttribute('data-d')===d)});
  pan.forEach(function(x){x.classList.toggle('on',x.getAttribute('data-dp')===d)});}
 tabs.forEach(function(x){x.addEventListener('click',function(){show(x.getAttribute('data-d'))})});
 show(names.indexOf('Monday')>=0?'Monday':names[0]);});
})();</script>
<script>(function(){
function conv(h,m,a){h=+h;m=+(m||0);a=a.toUpperCase();h=a==='AM'?h%12:(a==='PM'?h%12+12:12);return h*60+m;}
function calc(t){var f=[],re=/(\\d{1,2})(?::(\\d{2}))?\\s*(AM|PM|NN)\\b/gi,m;
 while((m=re.exec(t)))f.push(m);if(f.length<2)return null;
 var d=conv(f[1][1],f[1][2],f[1][3])-conv(f[0][1],f[0][2],f[0][3]);return d>0?d:null;}
function hrs(v){var h=Math.floor(v/60),m=v%60,p=[];if(h)p.push(h+' hr'+(h!==1?'s':''));if(m)p.push(m+' min');return p.join(' ')||'0 hrs';}
document.querySelectorAll('input[data-official]').forEach(function(i){
 if(i.closest('.assign'))return; /* no minutes hint in the Assignments table */
 var w=i.closest('.otime')||i.parentNode;
 var o=w.nextElementSibling;
 if(!o||!o.classList||!o.classList.contains('offmin')){o=document.createElement('p');o.className='hint offmin';w.parentNode.insertBefore(o,w.nextSibling);}
 function up(){var v=calc(i.value);o.textContent=v?'= '+v+' minutes ('+hrs(v)+') per day, '+hrs(v*5)+' per week':(i.value.trim()?'Set the start and end time to compute the minutes.':'');}
 i.addEventListener('input',up);up();});
})();</script>
<script>(function(){
document.querySelectorAll('[data-otime]').forEach(function(w){
 var h=w.querySelector('input[type=hidden]'),a=w.querySelector('.ot-from'),b=w.querySelector('.ot-to');
 function f(v){var p=v.split(':'),H=+p[0],ap=H>=12?'PM':'AM';H=H%12||12;return H+':'+p[1]+' '+ap;}
 function up(){h.value=(a.value&&b.value)?f(a.value)+' - '+f(b.value):'';h.dispatchEvent(new Event('input',{bubbles:true}));}
 a.addEventListener('input',up);b.addEventListener('input',up);});
})();</script>
<script>(function(){
var EYE='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z"/><circle cx="12" cy="12" r="3"/></svg>';
var OFF='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M17.94 17.94A10.9 10.9 0 0 1 12 19C5 19 1 12 1 12a18.5 18.5 0 0 1 5.06-5.94M9.9 4.24A9.1 9.1 0 0 1 12 4c7 0 11 7 11 7a18.5 18.5 0 0 1-2.16 3.19M14.12 14.12a3 3 0 1 1-4.24-4.24"/><path d="M1 1l22 22"/></svg>';
document.querySelectorAll('input[type=password]').forEach(function(i){
 var w=document.createElement('span');w.className='pwwrap';i.parentNode.insertBefore(w,i);w.appendChild(i);
 var b=document.createElement('button');b.type='button';b.className='eye';b.innerHTML=EYE;
 b.setAttribute('aria-label','Show password');b.setAttribute('aria-pressed','false');
 b.addEventListener('click',function(){var show=i.type==='password';i.type=show?'text':'password';b.innerHTML=show?OFF:EYE;
  b.setAttribute('aria-label',show?'Hide password':'Show password');b.setAttribute('aria-pressed',show?'true':'false');});
 w.appendChild(b);});
})();</script>
<script>document.querySelectorAll('.viewtoggle').forEach(function(a){
var d=false;try{d=localStorage.getItem('view')==='desktop'}catch(e){}
if(Math.max(screen.width,screen.height)>1000&&!d)return;
a.hidden=false;a.textContent=d?'Switch to mobile view':'Switch to desktop view';
a.addEventListener('click',function(e){e.preventDefault();try{localStorage.setItem('view',d?'mobile':'desktop')}catch(x){}location.reload();});});</script>
<script>(function(){
function fit(){var h=document.documentElement,L=document.querySelectorAll('.doc');if(!L.length)return;
 L.forEach(function(d){d.style.removeProperty('--zl');d.style.removeProperty('--zp');d.style.removeProperty('width');});
 h.classList.add('pm');
 [['--zl',297,210],['--zp',210,297]].forEach(function(o){
  var PW=Math.floor((o[1]-12)/25.4*96),PH=Math.floor((o[2]-12)/25.4*96)-6;
  L.forEach(function(d){var lo=.4,hi=1.2,i,z;function ok(v){d.style.setProperty('width',(PW/v)+'px','important');return d.scrollHeight*v<=PH*.95;}
   if(ok(hi)){lo=hi;}else{for(i=0;i<9;i++){z=(lo+hi)/2;if(ok(z))lo=z;else hi=z;}}
   d.style.setProperty(o[0],lo.toFixed(3));d.style.removeProperty('width');});});
 h.classList.remove('pm');}
function reset(){document.querySelectorAll('.doc').forEach(function(d){d.style.removeProperty('--zl');d.style.removeProperty('--zp');});}
window.addEventListener('beforeprint',fit);window.addEventListener('afterprint',reset);
})();</script>
<script>(function(){
if(!document.querySelector('header.top'))return; /* only inside the system, not on the login pages */
document.addEventListener('submit',function(ev){
 var f=ev.target;if(!f||f.tagName!=='FORM'||(f.getAttribute('method')||'get').toLowerCase()!=='post')return;
 if(f.hasAttribute('data-noconfirm')||f.hasAttribute('onsubmit'))return; /* already asks */
 var b=ev.submitter||f.querySelector('button[type=submit],button:not([type])');if(!b)return;
 if((b.getAttribute('onclick')||'').indexOf('confirm')>-1)return;
 var t=(b.textContent||b.value||'').trim().toLowerCase(),m=null;
 if(f.id==='addform')m='Are you sure you want to add this period?';
 else if(/delete|remove|clear|reject|decline/.test(t))m='Are you sure you want to delete this? This cannot be undone.';
 else if(/approve|reset/.test(t))m='Are you sure you want to continue?';
 else if(/\badd\b|create|^new\b/.test(t))m='Are you sure you want to add this?';
 else if(/save|update|change|apply|done/.test(t))m='Are you sure you want to save these changes?';
 if(m&&!window.confirm(m)){ev.preventDefault();ev.stopImmediatePropagation();}
},true);
})();</script>
<script>(function(){
function strip(im){var raw=new Image();raw.onload=function(){try{
 var W=raw.naturalWidth,H=raw.naturalHeight;if(!W||!H||W*H>4000000)return;
 var c=document.createElement('canvas');c.width=W;c.height=H;var x=c.getContext('2d');x.drawImage(raw,0,0);
 var d=x.getImageData(0,0,W,H),a=d.data;if(a[3]<20)return;
 var r0=a[0],g0=a[1],b0=a[2],tol=60,seen=new Uint8Array(W*H),st=[];
 function near(i){var o=i*4;return a[o+3]>0&&Math.abs(a[o]-r0)+Math.abs(a[o+1]-g0)+Math.abs(a[o+2]-b0)<tol;}
 for(var i=0;i<W;i++){st.push(i,(H-1)*W+i);}for(var j=0;j<H;j++){st.push(j*W,j*W+W-1);}
 while(st.length){var n=st.pop();if(n<0||n>=W*H||seen[n]||!near(n))continue;seen[n]=1;a[n*4+3]=0;
  var cx=n%W;if(cx>0)st.push(n-1);if(cx<W-1)st.push(n+1);st.push(n-W,n+W);}
 x.putImageData(d,0,0);im.src=c.toDataURL('image/png');}catch(e){}};
 raw.src=im.getAttribute('src');}
document.querySelectorAll('#intro img.i-logo,img.brand-logo,img.logoimg').forEach(strip);
})();</script>
<script>(function(){var el=document.getElementById('intro');if(!el)return;
if(document.documentElement.classList.contains('introseen')){el.remove();return;}
try{sessionStorage.setItem('intro','1');}catch(e){}
document.body.style.overflow='hidden';
function done(){el.classList.add('hide');document.body.style.overflow='';setTimeout(function(){if(el.parentNode)el.remove();},700);}
var t=setTimeout(done,2800);el.addEventListener('click',function(){clearTimeout(t);done();});})();</script>
<script>document.addEventListener('click',function(ev){var b=ev.target.closest?ev.target.closest('.tlink'):null;if(!b)return;
var id=b.getAttribute('data-t'),on=b.getAttribute('aria-expanded')!=='true';
document.querySelectorAll('.tlink').forEach(function(x){if(x.getAttribute('data-t')!==id)return;
var sl=x.closest('.slot'),n=sl?sl.querySelector('.tname'):null;if(!n)return;
n.classList.toggle('show',on);x.setAttribute('aria-expanded',on?'true':'false');});});</script>
<script>document.addEventListener('click',function(ev){var b=ev.target.closest?ev.target.closest('.roombtn'):null;
if(!b){document.querySelectorAll('.roompop.show').forEach(function(p){p.classList.remove('show');});
document.querySelectorAll('.roombtn[aria-expanded=true]').forEach(function(x){x.setAttribute('aria-expanded','false');});return;}
var on=b.getAttribute('aria-expanded')!=='true',pop=b.parentNode.querySelector('.roompop');if(!pop)return;
pop.classList.toggle('show',on);b.setAttribute('aria-expanded',on?'true':'false');});</script>
<script>(function(){
var SEL='button:not(.eye):not(.tlink):not(.sclear),.btn,.backbtn,.tabs a,.acct a,.daytab,.menubtn,.tresults a';
function press(ev){var b=ev.target.closest?ev.target.closest(SEL):null;if(!b||b.disabled)return;
 b.classList.add('tap');b._tapAt=Date.now();
 var r=b.getBoundingClientRect(),s=Math.max(r.width,r.height)*2.2,d=document.createElement('span');
 d.className='ripple';d.style.width=d.style.height=s+'px';
 d.style.left=(ev.clientX-r.left-s/2)+'px';d.style.top=(ev.clientY-r.top-s/2)+'px';
 b.appendChild(d);setTimeout(function(){if(d.parentNode)d.parentNode.removeChild(d);},650);}
function release(){document.querySelectorAll('.tap').forEach(function(b){
 var wait=Math.max(0,220-(Date.now()-(b._tapAt||0)));
 setTimeout(function(){b.classList.remove('tap');},wait);});}
document.addEventListener('pointerdown',press,{passive:true});
['pointerup','pointercancel','dragend'].forEach(function(n){document.addEventListener(n,release,{passive:true,capture:true});});
document.addEventListener('submit',function(ev){if(ev.defaultPrevented)return;
 var f=ev.target,b=ev.submitter||f.querySelector('button[type=submit],button:not([type])');
 if(!b||b.classList.contains('eye'))return;
 setTimeout(function(){b.classList.add('busy');b.disabled=true;
  if(b.hasAttribute('data-busy')||b.classList.contains('dark')){b.dataset.t=b.textContent;b.textContent=b.getAttribute('data-busy')||'Please wait...';}},0);});
window.addEventListener('pageshow',function(){document.querySelectorAll('button.busy').forEach(function(b){
 b.classList.remove('busy');b.disabled=false;if(b.dataset.t)b.textContent=b.dataset.t;});});
})();</script>
{% if g.user %}<div class="toast noprint" id="toast" role="status" aria-live="polite" hidden><span>{{ 'New request or problem report received.' if g.user.role == 'admin' else 'You have a new notification.' }}</span><a href="{{ url_for('reports') if g.user.role == 'admin' else url_for('notifications') }}">Open</a><button type="button" class="toastx" id="toastx" aria-label="Dismiss">&times;</button></div>
<script>(function(){
var last={{ bell }},badges=document.querySelectorAll('.nbadge'),toast=document.getElementById('toast');
function setb(n){badges.forEach(function(b){b.textContent=n;b.hidden=!n;});}
document.getElementById('toastx').addEventListener('click',function(){toast.hidden=true;});
function check(){if(document.hidden)return;
 fetch('{{ url_for('notif_count') }}',{credentials:'same-origin',cache:'no-store'}).then(function(r){return r.ok?r.json():null;}).then(function(d){
  if(!d)return;setb(d.n);if(d.n>last){toast.hidden=false;setTimeout(function(){toast.hidden=true;},12000);}last=d.n;}).catch(function(){});}
setInterval(check,30000);document.addEventListener('visibilitychange',check);
})();</script>{% endif %}
{% if g.user %}<div class="dock noprint" role="navigation" aria-label="Quick navigation"><button type="button" id="dockback" data-fallback="{{ nav_back() }}"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 6l-6 6 6 6"/></svg><span>Back</span></button><a href="{{ url_for('home') }}"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 11l9-8 9 8M5 10v10h14V10"/></svg><span>Home</span></a><button type="button" id="dockmenu"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg><span>Menu</span></button></div>
<script>(function(){function back(fb){var r=document.referrer,same=false;try{same=r&&new URL(r).origin===location.origin&&r!==location.href;}catch(e){}if(same&&history.length>1){history.back();}else{location.href=fb;}}
var d=document.getElementById('dockback');if(d)d.addEventListener('click',function(){back(d.getAttribute('data-fallback'));});
var m=document.getElementById('dockmenu'),mb=document.getElementById('menubtn');if(m&&mb)m.addEventListener('click',function(e){e.stopPropagation();window.scrollTo({top:0,behavior:'smooth'});mb.click();});
document.addEventListener('click',function(e){var a=e.target.closest&&e.target.closest('a.backbtn');if(!a)return;var r=document.referrer,same=false;try{same=r&&new URL(r).origin===location.origin&&r!==location.href;}catch(x){}if(same&&history.length>1){e.preventDefault();history.back();}});})();</script>
{% endif %}</body></html>""",

"macros.html": """{% macro back(url, label='Back') %}<a class="backbtn noprint" href="{{ url }}" title="{{ label }}" aria-label="{{ label }}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M19 12H5M12 19l-7-7 7-7"/></svg></a>{% endmacro %}

{% macro adviser_picker(teachers, selected=none, field='adviser_id', empty='Not assigned') %}
{% set cur = namespace(t=none) %}{% for t in teachers %}{% if t.id == selected %}{% set cur.t = t %}{% endif %}{% endfor %}
<div class="advpick" id="advpick"><input type="hidden" id="{{ field }}" name="{{ field }}" value="{{ selected or '' }}">
<input type="search" id="adv_q" class="advq" placeholder="Search by name or Teacher ID" autocomplete="off" aria-label="Search for a teacher by name or Teacher ID" value="{{ (tlabels.get(cur.t.id) ~ ' - ' ~ cur.t.full_name ~ ' (' ~ catname.get(cur.t.category, '') ~ ')') if cur.t else '' }}">
<ul class="advlist" id="adv_list" role="listbox" hidden>
<li data-id="" data-find="not assigned unassigned none clear" role="option">{{ empty }}</li>
{% for t in teachers %}<li data-id="{{ t.id }}" data-find="{{ (t.full_name ~ ' ' ~ tlabels.get(t.id, '') ~ ' ' ~ (t.teacher_id or '') ~ ' ' ~ t.category)|lower }}" data-text="{{ tlabels.get(t.id) }} - {{ t.full_name }} ({{ catname.get(t.category, '') }})" role="option"><strong>{{ t.full_name }}</strong><small>{{ tlabels.get(t.id) }} &middot; {{ t.teacher_id }} &middot; {{ catname.get(t.category, '') }}</small></li>{% endfor %}
<li class="advnone" id="adv_none" hidden>No teacher matches that name.</li></ul></div>
<script>(function(){
var box=document.getElementById('advpick'),q=document.getElementById('adv_q'),list=document.getElementById('adv_list'),hid=document.getElementById('{{ field }}'),none=document.getElementById('adv_none');
var items=[].slice.call(list.querySelectorAll('li[data-id]')),chosen=q.value;
function show(){var w=q.value===chosen&&hid.value?'':q.value.toLowerCase().trim().split(/\\s+/).filter(Boolean),n=0;
items.forEach(function(li){var f=li.getAttribute('data-find'),ok=!w.length||w.every(function(x){return f.indexOf(x)>-1;});li.hidden=!ok;if(ok)n++;});
none.hidden=n>0;list.hidden=false;}
function pick(li){hid.value=li.getAttribute('data-id');chosen=hid.value?li.getAttribute('data-text'):'';q.value=chosen;list.hidden=true;}
q.addEventListener('focus',function(){q.select();show();});
q.addEventListener('input',function(){if(q.value===''){hid.value='';chosen='';}show();});
list.addEventListener('mousedown',function(e){e.preventDefault();});
list.addEventListener('click',function(e){var li=e.target.closest('li[data-id]');if(li)pick(li);});
document.addEventListener('click',function(e){if(!box.contains(e.target)){list.hidden=true;q.value=chosen;}});
q.addEventListener('keydown',function(e){if(e.key==='Escape'){list.hidden=true;q.value=chosen;}
if(e.key==='Enter'){var f=items.filter(function(li){return !li.hidden;});if(!list.hidden){e.preventDefault();if(f.length)pick(f[0]);}}});
})();</script>
{% endmacro %}

{% macro class_doc(d, can_edit=false) %}
{% if d.stamp %}<p class="doc-date noprint">{{ d.stamp.label }}: {{ d.stamp.date }}</p>{% endif %}
<article class="doc">
{{ letterhead("GRADE " ~ d.cur.grade ~ " CLASS PROGRAM") }}
{% if d.cur.room %}
<p class="room"><button type="button" class="roombtn" data-room aria-expanded="false">{{ d.cur.room|upper }}</button><span class="roompop{{ '' if d.cur.building and d.cur.floor else ' nobf' }}">{% if d.cur.building and d.cur.floor %}Bldg. {{ d.cur.building }}, Floor {{ d.cur.floor }}{% else %}Building and floor not set yet.{% endif %}</span></p>
{% else %}<p class="room">Room not set</p>{% endif %}
<div class="meta"><div><b>Grade Level/Section:</b> {{ d.cur.name }}{% if d.cur.track %} ({{ d.cur.track }}){% endif %}</div>
<div><b>Adviser:</b> {{ d.adviser or 'Not assigned' }}</div></div>
{{ grid(d.rows, d.cells, 'program', can_edit) }}
{% if d.legend %}<p class="legend"><strong>Legend:</strong> {% for c, n in d.legend %}<mark class="lgc">{{ c }}</mark>-{{ n }}{{ ', ' if not loop.last }}{% endfor %}</p>{% endif %}
{% if d.tlegend %}<p class="legend"><strong>Teachers:</strong> {% for l, n in d.tlegend %}{{ l }} = {{ n }}{{ '; ' if not loop.last }}{% endfor %}</p>{% endif %}
<div class="sign cls">
<div><div class="role">Prepared by:</div><div class="name">{{ (d.adviser or '________________')|upper }}</div><div class="title">Adviser</div></div>
<div><div class="role">Checked and verified by:</div><div class="name">{{ cfg.principal_name|upper }}</div><div class="title">{{ cfg.principal_title }}</div></div>
<div><div class="role">Reviewed by:</div><div class="name">{{ cfg.psds_name|upper }}</div><div class="title">{{ cfg.psds_title }}</div></div>
<div><div class="role">Approved by:</div><div class="name">{{ cfg.sdo_name|upper }}</div><div class="title">{{ cfg.sdo_title }}</div></div>
</div></article>
{% endmacro %}

{% macro teacher_doc(d) %}{% set t = d.t %}
{% if d.stamp %}<p class="doc-date noprint">{{ d.stamp.label }}: {{ d.stamp.date }}</p>{% endif %}
<article class="doc">
{{ letterhead("TEACHER'S PROGRAM") }}
<div class="meta">
<div><div><b>Teacher:</b> {{ tlabels.get(t.id, '-') }} &ndash; {{ t.full_name|upper }}</div>
<div><b>Subject:</b> {{ t.subject_area or '-' }}</div>
<div><b>Specialization:</b> {{ t.specialization or '-' }}</div>
<div><b>Ancillary:</b> {{ d.ancillary }}</div>
<div><b>Grade level handled:</b> {{ catname.get(t.category, 'Teacher') }}</div></div>
<div><div><b>Item:</b> {{ t.item or '-' }}</div>
<div><b>No. of teaching loads:</b> {{ t.teaching_load or d.summ.loads }}</div>
<div><b>Official time:</b> {{ t.official_time or '-' }}{% if d.summ.official %} ({{ d.summ.official }} minutes / {{ d.summ.official|hrs }}){% endif %}</div>
<div><b>Weekly teaching hours:</b> {{ d.summ.teach_w|hrs }}</div>
<div><b>Weekly workload:</b> {{ d.summ.work_w|hrs }}</div>
<div class="noprint"><b>Teacher ID:</b> {{ t.teacher_id }}</div></div>
</div>
{{ grid(d.rows, d.cells, 'teacher', false, d.rowmins, d.summ) }}
<div class="sign">
<div><div class="role">Conformed:</div><div class="name">{{ t.full_name|upper }}</div><div class="title">Teacher</div></div>
<div><div class="role">Checked and verified by:</div><div class="name">{{ cfg.principal_name|upper }}</div><div class="title">{{ cfg.principal_title }}</div></div>
<div><div class="role">Reviewed by:</div><div class="name">{{ cfg.psds_name|upper }}</div><div class="title">{{ cfg.psds_title }}</div></div>
</div></article>
{% endmacro %}

{% macro otime(name, value, label) %}{% set rg = value|otimes %}<div class="otime" data-otime><input type="hidden" name="{{ name }}" value="{{ value or '' }}" data-official><input type="time" class="ot-from" value="{{ rg[0] }}" aria-label="{{ label }} start"><span>to</span><input type="time" class="ot-to" value="{{ rg[1] }}" aria-label="{{ label }} end"></div>{% endmacro %}

{% macro durselect(name, minutes, label, hi=600, k='', day='', auto='') %}<select name="{{ name }}" aria-label="{{ label }}"{% if k %} data-k="{{ k }}" data-d="{{ day }}" data-auto="{{ auto }}"{% endif %}>{% for v in dur_options(minutes, hi) %}<option value="{{ v }}" {{ 'selected' if v == (minutes or 0) }}>{{ v|durtxt }}</option>{% endfor %}</select>{% endmacro %}

{% macro specpick(name, value, label='Specialization') %}{% set picked = (value or '').split(';')|map('trim')|select|list %}
<div class="specpick"><input type="hidden" name="{{ name }}" value="{{ picked|join(spec_sep) }}"><div class="sp-text">{{ picked|join(', ') or '-' }}</div>
<details class="sp-box"><summary>{{ label }}: <span class="sp-count">{{ picked|length }}</span> selected</summary><div class="sp-list">
{% for grp, items in spec_groups %}<fieldset><legend>{{ grp }}</legend>{% for it in items %}<label><input type="checkbox" value="{{ it }}" {{ 'checked' if it in picked }}><span>{{ it }}</span></label>{% endfor %}</fieldset>{% endfor %}</div>
{% set unknown = picked|reject('in', curriculum_names)|list %}{% if unknown %}<p class="hint">Old entry that is not in the curriculum list: {{ unknown|join(', ') }}. It is dropped when you save; pick the matching choices instead.</p>{% endif %}</details></div>
<script>(function(){if(window.__specInit)return;window.__specInit=true;
function up(w){var h=w.querySelector('input[type=hidden]'),v=[];
w.querySelectorAll('.sp-list input[type=checkbox]').forEach(function(c){if(c.checked)v.push(c.value);});
h.value=v.join('; ');var n=w.querySelector('.sp-count');if(n)n.textContent=v.length;
var t=w.querySelector('.sp-text');if(t)t.textContent=v.length?v.join(', '):'-';}
document.addEventListener('change',function(e){var c=e.target;if(!c||c.type!=='checkbox')return;var w=c.closest?c.closest('.specpick'):null;if(w)up(w);});})();</script>
{% endmacro %}

{% macro hm(v) %}{% if v >= 60 %}<span class="hm">{{ v|hrs }}</span>{% endif %}{% endmacro %}

{% macro letterhead(title) %}
<div class="letterhead">{% if has_logo %}<a href="{{ url_for('home') }}" title="Home" aria-label="Home"><img class="lh-logo" src="{{ logo_url }}" alt=""></a>{% endif %}<div class="lh-text"><div class="school">{{ cfg.school_name }}</div><div class="addr">{{ cfg.school_address }}</div></div>{% if has_logo %}<img class="lh-logo lh-spacer" src="{{ logo_url }}" alt="" aria-hidden="true">{% endif %}</div>
<h2 class="doc-title">{{ title }}</h2><p class="doc-sub">{{ cfg.term }}</p>
{% endmacro %}

{% macro entry(e, mode, can_edit) %}
{% if e.kind == 'class' %}<div class="slot"><strong>{% if mode == 'teacher' %}{{ e.subject }}{% else %}{{ e.code or e.subject }}{% endif %}</strong>
{% if mode == 'teacher' %}<span>Section: <a class="seclink" href="{{ url_for('program', section=e.section_id) }}" title="Open the {{ e.section_name }} class program">{{ e.section_name }}</a></span><span>{{ ((e.end|tmin) - (e.start|tmin))|hrs }}</span>
{% elif e.other %}<span>Another teacher</span>
{% elif e.teacher_label %}<span><button type="button" class="tlink" data-t="{{ e.teacher_id }}" aria-expanded="false" title="Click to see the teacher's name">{{ e.teacher_label }}</button></span><span class="tname">{{ e.teacher_name }}</span>
{% else %}<span>No teacher assigned</span>{% endif %}{% if e.room %}<span>{{ e.room }}</span>{% endif %}
{% else %}<div class="slot rec"><strong>{{ e.subject }}</strong>{% endif %}
{% if can_edit %}<div class="acts"><a class="btn plain small" href="{{ url_for('entry_edit', eid=e.id) }}">Edit</a>
<form method="post" action="{{ url_for('entry_delete', eid=e.id) }}" onsubmit="return confirm('Remove this period?')">{{ csrf_field() }}<button class="danger">Remove</button></form></div>{% endif %}
</div>
{% endmacro %}

{% macro grid(rows, cells, mode, can_edit=false, rowmins=none, summ=none) %}
<div class="scroll gridwrap"><table class="grid">
<colgroup><col class="c-time">{% for d in days %}<col class="c-day">{% endfor %}{% if rowmins is not none %}<col class="c-min">{% endif %}</colgroup>
<thead><tr><th scope="col">Time</th>{% for d in days %}<th scope="col" data-day="{{ d }}">{{ d }}</th>{% endfor %}{% if rowmins is not none %}<th scope="col">No. of minutes</th>{% endif %}</tr></thead><tbody>
{% for r in rows %}{% set ri = loop.index0 %}{% set ns = namespace(rec=false) %}{% for d in days %}{% set c0 = cells[d][ri] %}{% if c0 and c0 != 'skip' and c0.e.kind == 'recess' %}{% set ns.rec = true %}{% endif %}{% endfor %}<tr><th scope="row"{% if ns.rec %} class="recess"{% endif %}>{{ r[0]|tm }} to {{ r[1]|tm }}</th>
{% for d in days %}{% set c = cells[d][ri] %}{% if c is none %}<td data-day="{{ d }}"></td>{% elif c != 'skip' %}<td data-day="{{ d }}" rowspan="{{ c.span }}"{% if c.e.kind == 'recess' %} class="recess"{% endif %}>{{ entry(c.e, mode, can_edit) }}{% for m in c.more %}{{ entry(m, mode, can_edit) }}{% endfor %}</td>{% endif %}{% endfor %}
{% if rowmins is not none %}<td class="num{{ ' recess' if ns.rec }}">{{ rowmins[ri] or '' }}</td>{% endif %}</tr>
{% else %}<tr><td colspan="8" class="empty">No periods have been posted yet.</td></tr>{% endfor %}
{% if summ %}
<tr class="sum a"><th scope="row">Daily actual teaching minutes</th>{% for d in days %}<td data-day="{{ d }}">{{ summ.teach[d] }} minutes{{ hm(summ.teach[d]) }}</td>{% endfor %}<td class="num">{{ summ.teach_w }}{{ hm(summ.teach_w) }}</td></tr>
<tr class="sum a"><th scope="row">Intervention / Remediation</th>{% for d in days %}<td data-day="{{ d }}">{{ summ.inter[d] }} minutes{{ hm(summ.inter[d]) }}</td>{% endfor %}<td class="num">{{ summ.inter_w }}{{ hm(summ.inter_w) }}</td></tr>
<tr class="sum a"><th scope="row">Ancillary / Adviser's minutes</th>{% for d in days %}<td data-day="{{ d }}">{{ summ.anc[d] }} minutes{{ hm(summ.anc[d]) }}</td>{% endfor %}<td class="num">{{ summ.anc_w }}{{ hm(summ.anc_w) }}</td></tr>
<tr class="sum b"><th scope="row">Total daily working minutes</th>{% for d in days %}<td data-day="{{ d }}">{{ summ.total[d] }} minutes{{ hm(summ.total[d]) }}</td>{% endfor %}<td class="num">{{ summ.total_w|string }} minutes{{ hm(summ.total_w) }}</td></tr>
{% endif %}
</tbody></table></div>
<div class="mobile-days">
<div class="daytabs" role="tablist">{% for d in days %}<button type="button" class="daytab" data-d="{{ d }}">{{ d[:3] }}</button>{% endfor %}</div>
{% for d in days %}<section class="dayp" data-dp="{{ d }}" data-day="{{ d }}"><h3>{{ d }}</h3>
{% if not (cells[d]|select('mapping')|list) %}<p class="mnone">No periods on this day.</p>{% endif %}
{% for r in rows %}{% set ri = loop.index0 %}{% set c = cells[d][ri] %}{% if c and c != 'skip' %}
<div class="mrow"><div class="mtime{{ ' recess' if c.e.kind == 'recess' }}">{{ r[0]|tm }} to {{ rows[ri + c.span - 1][1]|tm }}</div>{{ entry(c.e, mode, can_edit) }}{% for m in c.more %}{{ entry(m, mode, can_edit) }}{% endfor %}</div>
{% endif %}{% endfor %}
{% if summ %}<div class="msum"><div><span>Daily actual teaching</span><b>{{ summ.teach[d] }} min{% if summ.teach[d] >= 60 %} ({{ summ.teach[d]|hrs }}){% endif %}</b></div>
<div><span>Intervention / Remediation</span><b>{{ summ.inter[d] }} min{% if summ.inter[d] >= 60 %} ({{ summ.inter[d]|hrs }}){% endif %}</b></div>
<div><span>Ancillary / Adviser's</span><b>{{ summ.anc[d] }} min{% if summ.anc[d] >= 60 %} ({{ summ.anc[d]|hrs }}){% endif %}</b></div>
<div class="tot"><span>Total working minutes</span><b>{{ summ.total[d] }} min{% if summ.total[d] >= 60 %} ({{ summ.total[d]|hrs }}){% endif %}</b></div></div>{% endif %}
</section>{% endfor %}</div>{% endmacro %}

{% macro tsearch(list_mode=false) %}
<div class="tsearch noprint" role="search"><label for="tq">{{ "Find another teacher's program or profile" if list_mode else 'Search teachers by name or Teacher ID' }}</label>
<div class="sfield"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>
<input id="tq" type="search" placeholder="Example: Maria Santos or T-1001" autocomplete="off" maxlength="60" enterkeyhint="search"{% if list_mode %} data-list="1"{% endif %}>
<a href="#" id="tqx" class="sclear" role="button" title="Clear search" aria-label="Clear search" hidden>&times;</a></div>
<p class="hint" id="tqcount" aria-live="polite"></p></div>
<script>(function(){
function init(){
var q=document.getElementById('tq'),x=document.getElementById('tqx'),c=document.getElementById('tqcount'),
 items=document.querySelectorAll('[data-find]'),none=document.getElementById('tqnone'),lm=q.hasAttribute('data-list');
function up(){var w=q.value.toLowerCase().trim().split(' ').filter(Boolean),n=0,cat=window.__cat||'';
 items.forEach(function(el){var t=el.getAttribute('data-find'),ok=w.every(function(k){return t.indexOf(k)>-1;});
  var okc=!cat||el.getAttribute('data-cat')===cat;
  var vis=lm?(w.length>0&&ok):(ok&&okc);el.hidden=!vis;if(vis)n++;});
 x.hidden=!q.value;
 c.textContent=(w.length||cat)?(n+' of '+items.length+' teacher'+(items.length===1?'':'s')+' shown'):'';
 if(none)none.hidden=!((w.length||cat)&&!n);}
window.findApply=up;
q.addEventListener('input',up);
q.addEventListener('keydown',function(e){if(e.key==='Enter'&&lm){var a=document.querySelector('[data-find]:not([hidden]) a');if(a){e.preventDefault();location.href=a.href;}}});
x.addEventListener('click',function(e){e.preventDefault();q.value='';up();q.focus();});
up();}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();</script>
{% endmacro %}

{% macro report_form(v) %}
<form method="post" action="{{ url_for('report') }}" enctype="multipart/form-data" id="r_form">{{ csrf_field() }}
<p class="hint">Tell the administrator what went wrong. You can attach up to 5 screenshots or photos of the problem.</p>
{% if not g.user %}<label for="r_tid">Teacher ID</label><input id="r_tid" name="teacher_id" value="{{ v.get('teacher_id', '') }}" placeholder="Example: T-1001" maxlength="40" autocomplete="off" required>{% endif %}
<label for="r_msg">What is the problem?</label>
<textarea id="r_msg" name="message" rows="5" maxlength="2000" placeholder="Example: My schedule for Monday is missing a class." required>{{ v.get('message', '') }}</textarea>
<label for="r_photo">Upload screenshots (up to 5, optional)</label>
<input id="r_photo" type="file" name="photos" accept="image/*" multiple>
<p class="hint" id="r_cnt" aria-live="polite"></p>
<div class="thumbs" id="r_prevs"></div>
<p class="hint">PNG, JPG, GIF or WEBP, up to 3 MB each. Large photos are made smaller automatically.</p>
<div class="btnrow"><button type="submit" data-busy="Sending...">Send report</button></div></form>
<script>(function(){
var inp=document.getElementById('r_photo'),list=document.getElementById('r_prevs'),cnt=document.getElementById('r_cnt'),form=document.getElementById('r_form'),MAX=5,MAXB=3*1024*1024,files=[];
function sync(){if(!window.DataTransfer)return;var dt=new DataTransfer();files.forEach(function(f){dt.items.add(f);});inp.files=dt.files;}
function render(){list.innerHTML='';
 files.forEach(function(f,i){var w=document.createElement('div');w.className='thumb';
  var im=document.createElement('img');im.src=URL.createObjectURL(f);im.alt='Screenshot '+(i+1);
  var b=document.createElement('button');b.type='button';b.className='thumbx';b.setAttribute('aria-label','Remove screenshot '+(i+1));b.innerHTML='&times;';
  b.addEventListener('click',function(){files.splice(i,1);render();});
  w.appendChild(im);w.appendChild(b);list.appendChild(w);});
 cnt.textContent=files.length?files.length+' of '+MAX+' screenshots added':'';sync();}
function shrink(f,done){
 if(f.size<=1500000||f.type==='image/gif'||!HTMLCanvasElement.prototype.toBlob){done(f);return;}
 var url=URL.createObjectURL(f),img=new Image();
 img.onload=function(){var k=Math.min(1,1600/Math.max(img.width,img.height)),c=document.createElement('canvas');
  c.width=Math.round(img.width*k);c.height=Math.round(img.height*k);c.getContext('2d').drawImage(img,0,0,c.width,c.height);
  c.toBlob(function(b){done(b&&b.size<f.size?new File([b],'screenshot.jpg',{type:'image/jpeg'}):f);},'image/jpeg',0.82);};
 img.onerror=function(){done(f);};img.src=url;}
inp.addEventListener('change',function(){
 var picked=Array.prototype.slice.call(inp.files).filter(function(f){return /^image/.test(f.type);}),room=MAX-files.length;
 if(picked.length>room)alert('You can upload up to 5 screenshots only. Extra images were skipped.');
 picked=picked.slice(0,Math.max(room,0));var n=picked.length;
 if(!n){render();return;}
 picked.forEach(function(f){shrink(f,function(g){files.push(g);n--;if(n===0)render();});});});
form.addEventListener('submit',function(e){
 for(var i=0;i<files.length;i++){if(files[i].size>MAXB){e.preventDefault();alert('Screenshot '+(i+1)+' is larger than 3 MB. Remove it or choose a smaller one.');return;}}
 if(files.length>MAX){e.preventDefault();alert('You can upload up to 5 screenshots only.');}});
})();</script>
{% endmacro %}
""",

"error.html": """{% extends "base.html" %}{% from "macros.html" import back with context %}{% block title %}{{ title }}{% endblock %}
{% block content %}<div class="titlerow">{{ back(url_for('home') if g.user else url_for('login'), 'Back to my page' if g.user else 'Back to sign-in') }}<h1>{{ title }}</h1></div><div class="card"><p>{{ text }}</p></div>{% endblock %}""",

"login.html": """{% extends "base.html" %}{% block title %}Sign in{% endblock %}
{% block page %}<div class="login">
<section class="side"><svg class="arcs" viewBox="0 0 600 800" preserveAspectRatio="xMidYMid slice" aria-hidden="true"><g fill="none" stroke="#fff" stroke-opacity=".13"><circle cx="640" cy="780" r="300"/><circle cx="640" cy="780" r="380"/><circle cx="640" cy="780" r="460"/><circle cx="640" cy="780" r="540"/><circle cx="640" cy="780" r="620"/></g></svg><div class="side-in"><div class="brandrow">{% if has_logo %}<a class="logolink" href="{{ url_for('home') }}" title="Home" aria-label="Home"><img class="logo logoimg" src="{{ logo_url }}" alt="{{ cfg.school_name }} logo"></a>{% else %}<svg class="logo" viewBox="0 0 64 64" aria-hidden="true"><g stroke="#fff" stroke-width="6" stroke-linecap="round"><path d="M32 6v52M6 32h52M13.6 13.6l36.8 36.8M50.4 13.6L13.6 50.4"/></g></svg>{% endif %}<span class="brandschool">San Jose Litex Senior High School<small>School ID: 342566</small></span></div><h1>TEACHER SCHEDULING SYSTEM</h1>
<p>See your Teacher's Program and class schedules anytime, on your phone or computer. Schedules are posted and kept up to date by the school administrator.</p></div>
<small class="copy">&copy; {{ year }} {{ cfg.school_name }}. All rights reserved.</small></section>
<section class="panel"><form method="post" id="lf" class="authform">{{ csrf_field() }}
<div class="auth-body"><h2>Log in to manage your classes</h2>
<p class="auth-note">Don't have an account? <a href="{{ url_for('signup') }}">Request an account</a> now. Wait for the administrator to approve it.</p>
{% for cat, m in get_flashed_messages(with_categories=true) %}<div class="msg {{ cat }}" role="alert">{{ m }}</div>{% endfor %}
<label for="utype">User type</label>
<select id="utype" name="utype" required><option value="" disabled hidden {{ 'selected' if not sel }}>Select your user type</option>{% for k, name, note in types %}<option value="{{ k }}" {{ 'selected' if sel == k }}>{{ name }}</option>{% endfor %}</select>
<label for="username">Username</label><input id="username" name="username" autocomplete="username" required>
<div id="idbox"><label for="teacher_num">Teacher ID</label><div class="tidfield"><span class="tidfix">T-</span><input id="teacher_num" name="teacher_num" type="number" min="1" step="1" inputmode="numeric" placeholder="1001" autocomplete="off"></div></div>
<label for="password">Password</label><input id="password" type="password" name="password" autocomplete="current-password" required>
<p class="auth-foot" style="margin:.6rem 0 0"><a href="{{ url_for('forgot_password') }}">Forgot password?</a></p>
<button type="submit" class="dark" data-busy="Signing in...">Sign In</button>
<p class="auth-foot"><a href="#" class="viewtoggle" hidden></a></p></div>
<a class="helpfab" href="{{ url_for('help_center') }}" title="Help Center" aria-label="Help Center"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 13v-1a8 8 0 0 1 16 0v1"/><rect x="2" y="13" width="5" height="7" rx="2.5"/><rect x="17" y="13" width="5" height="7" rx="2.5"/><path d="M20 20a4 4 0 0 1-4 3h-2"/></svg><span class="helpfab-q">?</span></a>
</form></section></div>
<script>var s=document.getElementById('utype'),ib=document.getElementById('idbox'),ii=document.getElementById('teacher_num');
function sync(){var a=s.value==='ADMIN';ib.style.display=a?'none':'block';ii.required=!a&&s.value!=='';}
s.addEventListener('change',sync);sync();</script>{% endblock %}""",

"profile.html": """{% extends "base.html" %}{% from "macros.html" import teacher_doc, back, tsearch, durselect with context %}
{% block title %}Teacher's Program{% endblock %}
{% block content %}
<div class="head noprint"><div class="titlerow">{% if g.user.role == 'admin' %}{{ back(url_for('teachers'), 'Back to teachers') }}{% endif %}<h1>{{ "My Teacher's Program" if g.user.role == 'teacher' else t.full_name }}</h1></div>
<button type="button" class="plain" onclick="window.print()">Print</button></div>
{% if g.user.role == 'admin' and pick|length > 1 %}<div class="card noprint">{{ tsearch(true) }}
<ul class="tresults">{% for p in pick %}{% if p.id != t.id %}<li data-find="{{ (p.full_name ~ ' ' ~ p.teacher_id)|lower }}" hidden><a href="{{ url_for('teacher_view', tid=p.id) }}"><span>{{ p.full_name }}</span><small>{{ p.teacher_id }}</small></a></li>{% endif %}{% endfor %}</ul></div>{% endif %}
{% if g.user.role == 'admin' %}
<details class="card noprint" id="minedit"><summary>Edit minutes (teaching, intervention, ancillary and total)</summary>
<form method="post" action="{{ url_for('teacher_minutes', tid=t.id) }}" style="margin-top:.8rem">{{ csrf_field() }}
<p class="hint">Choose the time for each day from the lists (for example 1 hr 30 min). The total daily working time adds up by itself.</p>
<div class="scroll"><table class="minedit"><thead><tr><th></th>{% for day in days %}<th>{{ day }}</th>{% endfor %}</tr></thead><tbody>
<tr><th scope="row">Daily actual teaching minutes</th>{% for day in days %}<td>{{ durselect('teach_' ~ day, d.summ.teach[day], 'Teaching time ' ~ day, 720, 'teach', day, d.summ.auto.teach[day]) }}</td>{% endfor %}</tr>
<tr><th scope="row">Intervention / Remediation</th>{% for day in days %}<td>{{ durselect('inter_' ~ day, d.summ.inter[day], 'Intervention time ' ~ day, 720, 'inter', day, d.summ.auto.inter) }}</td>{% endfor %}</tr>
<tr><th scope="row">Ancillary / Adviser's minutes</th>{% for day in days %}<td>{{ durselect('anc_' ~ day, d.summ.anc[day], 'Ancillary time ' ~ day, 720, 'anc', day, d.summ.auto.anc) }}</td>{% endfor %}</tr>
<tr class="tot"><th scope="row">Total daily working minutes</th>{% for day in days %}<td data-total="{{ day }}">0</td>{% endfor %}</tr>
</tbody></table></div>
<div class="btnrow"><button type="submit" name="action" value="save">Save minutes</button>
<button type="submit" name="action" value="reset" class="plain" formnovalidate onclick="return confirm('Go back to the automatic minutes?')">Back to automatic</button></div></form></details>
<script>(function(){var ins=document.querySelectorAll('#minedit [data-k]');
function conv(h,m,a){h=+h;m=+(m||0);a=(a||'').toUpperCase();if(a)h=a==='AM'?h%12:(a==='PM'?h%12+12:12);return h*60+m;}
function val(t,auto){t=(t||'').trim();if(!t)return +auto||0;if(/^\\d+$/.test(t))return +t;
 var f=[],re=/(\\d{1,2})(?::(\\d{2}))?\\s*(AM|PM|NN)\\b/gi,m;while((m=re.exec(t)))f.push(m);
 if(f.length>=2){var d=conv(f[1][1],f[1][2],f[1][3])-conv(f[0][1],f[0][2],f[0][3]);return d>0?d:0;}
 m=t.match(/^(\\d{1,2}):(\\d{2})\\s*(?:-|to)\\s*(\\d{1,2}):(\\d{2})$/);
 if(m){var e=conv(m[3],m[4])-conv(m[1],m[2]);return e>0?e:0;}return 0;}
function up(){document.querySelectorAll('#minedit [data-total]').forEach(function(c){var day=c.getAttribute('data-total'),t=0;
 ins.forEach(function(i){if(i.getAttribute('data-d')===day)t+=val(i.value,i.getAttribute('data-auto'));});
 var h=Math.floor(t/60),r=t%60;c.textContent=t+' min'+(t>=60?' ('+h+' hr'+(h!==1?'s':'')+(r?' '+r+' min':'')+')':'');});}
ins.forEach(function(i){i.addEventListener('input',up)});up();})();</script>
{% endif %}
{{ teacher_doc(d) }}
{% if g.user.role == 'teacher' %}<p class="noprint" style="color:var(--muted)">Only you and the administrator can see this program. Contact the administrator to request a change.</p>{% endif %}
{% endblock %}""",

"program.html": """{% extends "base.html" %}{% from "macros.html" import class_doc, adviser_picker with context %}
{% block title %}Class Programs{% endblock %}
{% block content %}{% if g.user.role == 'admin' %}{{ subnav('schedule') }}{% endif %}
<div class="head noprint"><h1>Class Programs</h1><div class="row-acts">{% if g.user.role == 'admin' and total %}<a class="btn plain" href="{{ url_for('print_classes') }}">Choose programs to print</a>{% endif %}{% if g.user.role == 'admin' and cur and secs %}{% if editing %}<a class="btn" href="{{ url_for('program', section=cur.id, grade=grade) }}">Done editing</a>{% else %}<a class="btn plain" href="{{ url_for('program', section=cur.id, edit=1, grade=grade) }}">Edit schedule</a>{% endif %}{% endif %}{% if cur %}<button type="button" class="plain" onclick="window.print()">{{ 'Print all shown' if docs else 'Print this program' }}</button>{% endif %}</div></div>
{% if not total %}<div class="card">No sections are available yet.{% if g.user.role == 'admin' %} <a href="{{ url_for('sections') }}">Add a section</a> first.{% endif %}</div>
{% else %}
<form class="pick noprint" id="searchbar" method="get" action="{{ url_for('program') }}" role="search" style="scroll-margin-top:.6rem">
<div class="searchbox"><label for="q">Search by section or room number</label>
<div class="sfield"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>
<input id="q" type="search" name="q" value="{{ q }}" placeholder="Section or room number. Example: 11-Chef or 308" autocomplete="off" enterkeyhint="search" maxlength="60">
{% if q %}<a class="sclear" href="{{ url_for('program') }}" title="Clear search" aria-label="Clear search">&times;</a>{% endif %}</div></div>
<button type="submit">Search</button>
{% if grades|length > 1 %}<div><label for="grade">Grade level</label>
<select id="grade" name="grade" onchange="var s=this.form.elements['section'];if(s)s.disabled=true;this.form.submit()"><option value="">All grades</option>{% for gr in grades %}<option value="{{ gr }}" {{ 'selected' if grade == gr }}>{{ gr }}</option>{% endfor %}</select></div>{% endif %}
{% if ptracks|length > 1 or ptrack %}<div><label for="ptrack">Track</label>
<select id="ptrack" name="track" onchange="var s=this.form.elements['section'];if(s)s.disabled=true;this.form.submit()"><option value="">All tracks</option>{% for t in ptracks %}<option value="{{ t }}" {{ 'selected' if ptrack == t }}>{{ t }}</option>{% endfor %}</select></div>{% endif %}
{% if secs %}<div><label for="section">Section</label>
{% if editing %}<input type="hidden" name="edit" value="1">{% endif %}<select id="section" name="section" {% if docs %}onchange="var t=document.getElementById('sec-'+this.value);if(t)t.scrollIntoView({behavior:'smooth',block:'start'})"{% else %}onchange="this.form.submit()"{% endif %}>
{% for s in secs %}<option value="{{ s.id }}" {{ 'selected' if s.id == cur.id }}>{{ s.name }}{{ ' (My Advisory)' if s.is_adv }}</option>{% endfor %}</select></div>{% endif %}
</form>
{% if q %}<p class="hint noprint">{{ secs|length }} of {{ gtotal }} section{{ '' if gtotal == 1 else 's' }} match &ldquo;{{ q }}&rdquo;.</p>{% endif %}
{% if not secs %}<div class="card">No section matches your search. <a href="{{ url_for('program') }}">Show all sections</a></div>
{% else %}
{% if editing %}
<p class="editbanner noprint"><b>Edit mode is on.</b> Add a period below, or use Edit / Remove on a period. Press <b>Done editing</b> when finished.</p>
<div class="card"><h3>Add to this class program</h3>
<form method="post" action="{{ url_for('entry_add') }}" id="addform">{{ csrf_field() }}<input type="hidden" name="section_id" value="{{ cur.id }}">
<div class="formgrid">
<div><label for="kind">Type</label><select id="kind" name="kind">{% for k, v in kinds.items() %}<option value="{{ k }}">{{ v }}</option>{% endfor %}</select></div>
<div><label for="start">Start time</label><input id="start" type="time" name="start" required></div>
<div><label for="end">End time</label><input id="end" type="time" name="end" required></div>
<div><label for="subject">Subject</label><input id="subject" name="subject" placeholder="Required for class periods"></div>
<div><label for="code">Subject code</label><input id="code" name="code" placeholder="Example: GM" maxlength="12"></div>
<div><label for="adv_q">Teacher</label>{{ adviser_picker(teachers, none, 'teacher_id', 'Unassigned') }}</div>
<div class="wide"><fieldset><legend>Days</legend>{% for d in days %}<label class="chk"><input type="checkbox" name="day" value="{{ d }}"> {{ d }}</label>{% endfor %}
<button type="button" class="plain small" onclick="document.querySelectorAll('#addform input[name=day]').forEach(function(x){x.checked=true});document.getElementById('addform').dispatchEvent(new Event('change'))">Select Monday to Friday</button>
<p class="hint">Tick every day that has this period. Recess, homeroom and intervention periods do not use a teacher.</p></fieldset></div>
<div class="wide"><p class="hint" id="durout" aria-live="polite" style="font-weight:600;color:var(--navy)"></p></div>
<div><button type="submit">Save period</button></div></div></form></div>
<script>(function(){var f=document.getElementById('addform');if(!f)return;
var s=f.querySelector('[name=start]'),e=f.querySelector('[name=end]'),o=document.getElementById('durout');
function m(v){var p=(v||'').split(':');return p.length<2?NaN:(+p[0])*60+(+p[1]);}
function h(n){var a=Math.floor(n/60),b=n%60,t=[];if(a)t.push(a+(a===1?' hr':' hrs'));if(b)t.push(b+' min');return t.join(' ')||'0 min';}
function upd(){var d=m(e.value)-m(s.value),k=f.querySelectorAll('input[name=day]:checked').length;
if(isNaN(d)){o.textContent='';return;}
if(d<=0){o.textContent='End time must be later than start time.';return;}
var t='Time computed: '+h(d)+' ('+d+' minutes)';
if(k>1)t+=' x '+k+' days = '+h(d*k)+' per week';
o.textContent=t;}
f.addEventListener('input',upd);f.addEventListener('change',upd);upd();})();</script>
{% endif %}
{% if docs %}<p class="hint noprint">Showing {{ docs|length }} class program{{ '' if docs|length == 1 else 's' }}{% if grade %} for Grade {{ grade }}{% endif %}. Scroll down to see the others, or pick a section above to jump to it.</p>
{% for x in docs %}<section class="progitem" id="sec-{{ x.cur.id }}">{% if x.cur.is_adv %}<p class="advtag noprint">My Advisory</p>{% endif %}{{ class_doc(x, false) }}</section>{% endfor %}
{% else %}{% if cur.is_adv %}<p class="advtag noprint">My Advisory</p>{% endif %}{{ class_doc(d, editing) }}{% endif %}
{% endif %}{% endif %}
<button type="button" class="fabtop noprint" id="fabtop" title="Go back up to the search bar" aria-label="Go back up to the search bar" hidden><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 19V5M5 12l7-7 7 7"/></svg></button>
<script>(function(){var b=document.getElementById('fabtop'),bar=document.getElementById('searchbar');if(!b||!bar)return;
document.body.appendChild(b);
function chk(){b.hidden=(window.pageYOffset||document.documentElement.scrollTop)<250;}
window.addEventListener('scroll',chk,{passive:true});chk();
b.addEventListener('click',function(){bar.scrollIntoView({behavior:'smooth',block:'start'});var q=document.getElementById('q');if(q)setTimeout(function(){try{q.focus({preventScroll:true});}catch(e){}},500);});
})();</script>{% endblock %}""",

"printall.html": """{% extends "base.html" %}{% from "macros.html" import class_doc, teacher_doc, back with context %}
{% block title %}{{ title }}{% endblock %}
{% block content %}
<div class="head noprint"><div class="titlerow">{{ back(back_url, 'Back') }}<h1>{{ title }}</h1></div>{% if docs %}<button type="button" onclick="window.print()">Print ({{ docs|length }} page{{ '' if docs|length == 1 else 's' }})</button>{% endif %}</div>
<p class="hint noprint">Every selected program prints on its own page, one page each. <a href="{{ back_url }}">Choose different programs</a></p>
{% for d in docs %}{% if kind == 'class' %}{{ class_doc(d, false) }}{% else %}{{ teacher_doc(d) }}{% endif %}
{% else %}<div class="card">Nothing to print yet.</div>{% endfor %}
{% endblock %}""",

"printpick.html": """{% extends "base.html" %}{% from "macros.html" import back, tsearch with context %}
{% block title %}{{ title }}{% endblock %}
{% block content %}
<div class="head noprint"><div class="titlerow">{{ back(back_url, 'Back') }}<h1>{{ title }}</h1></div></div>{{ subnav('reports') }}
<form method="get" class="card noprint">
{% if searchable %}{{ tsearch() }}{% endif %}
<p class="hint">Tick the programs you want. Only those will be shown for printing.</p>
<p><button type="button" class="plain small" id="selall">Select all</button> <button type="button" class="plain small" id="selnone">Clear</button> <span class="hint" id="selcount"></span></p>
<div class="picklist">{% for pid, label, sub, find in items %}<label class="chk" data-find="{{ find }}"><input type="checkbox" name="id" value="{{ pid }}"> {{ label }}{% if sub %} <span class="hint">({{ sub }})</span>{% endif %}</label>
{% else %}<p>Nothing to print yet.</p>{% endfor %}</div>
<p style="margin-top:1rem"><button type="submit" id="goprint" disabled>Show selected to print</button></p></form>
<script>(function(){var b=document.querySelectorAll('.picklist input'),g=document.getElementById('goprint'),c=document.getElementById('selcount');
function up(){var n=0;b.forEach(function(x){if(x.checked)n++});g.disabled=!n;c.textContent=n?n+' selected':'';}
b.forEach(function(x){x.addEventListener('change',up)});
document.getElementById('selall').onclick=function(){b.forEach(function(x){if(!x.parentNode.hidden)x.checked=true});up()};
document.getElementById('selnone').onclick=function(){b.forEach(function(x){x.checked=false});up()};up();})();</script>
{% endblock %}""",

"entry_edit.html": """{% extends "base.html" %}{% from "macros.html" import back, adviser_picker with context %}{% block title %}Edit period{% endblock %}
{% block content %}
<div class="titlerow">{{ back(url_for('program', section=sec.id, edit=1), 'Back to class program') }}<h1>Edit period</h1></div>
<p style="color:var(--muted)">{{ sec.name }}</p>
<div class="card"><form method="post" id="editform">{{ csrf_field() }}<div class="formgrid">
<div><label for="kind">Type</label><select id="kind" name="kind">{% for k, v in kinds.items() %}<option value="{{ k }}" {{ 'selected' if k == (e.kind or 'class') }}>{{ v }}</option>{% endfor %}</select></div>
<div><label for="day">Day</label><select id="day" name="day">{% for d in days %}<option {{ 'selected' if d == e.day }}>{{ d }}</option>{% endfor %}</select></div>
<div><label for="start">Start time</label><input id="start" type="time" name="start" value="{{ e.start }}" required></div>
<div><label for="end">End time</label><input id="end" type="time" name="end" value="{{ e.end }}" required></div>
<div><label for="subject">Subject</label><input id="subject" name="subject" value="{{ e.subject }}"></div>
<div><label for="code">Subject code</label><input id="code" name="code" value="{{ e.code or '' }}" maxlength="12"></div>
<div><label for="adv_q">Teacher</label>{{ adviser_picker(teachers, e.teacher_id, 'teacher_id', 'Unassigned') }}</div>
<div class="wide"><p class="hint" id="durout" aria-live="polite" style="font-weight:600;color:var(--navy)"></p></div>
</div>
<div class="btnrow"><button type="submit">Save changes</button>
<a class="btn plain" href="{{ url_for('program', section=sec.id) }}">Cancel</a></div></form></div>
<script>(function(){var f=document.getElementById('editform'),s=document.getElementById('start'),e=document.getElementById('end'),o=document.getElementById('durout');
function m(v){var p=(v||'').split(':');return p.length<2?NaN:(+p[0])*60+(+p[1]);}
function h(n){var a=Math.floor(n/60),b=n%60,t=[];if(a)t.push(a+(a===1?' hr':' hrs'));if(b)t.push(b+' min');return t.join(' ')||'0 min';}
function upd(){var d=m(e.value)-m(s.value);if(isNaN(d)){o.textContent='';return;}
o.textContent=d<=0?'End time must be later than start time.':'Time computed: '+h(d)+' ('+d+' minutes)';}
f.addEventListener('input',upd);f.addEventListener('change',upd);upd();})();</script>
{% endblock %}""",

"account.html": """{% extends "base.html" %}{% from "macros.html" import back with context %}{% block title %}Profile{% endblock %}
{% block content %}<div class="titlerow">{{ back(url_for('home'), 'Back') }}<h1>Profile</h1><a class="btn plain" href="{{ url_for('account_settings') }}">Go to Settings</a><a class="btn danger signout" href="{{ url_for('logout') }}">Sign out</a></div>
<div class="card"><div class="head"><h2 style="margin:0">My profile</h2>
{% if g.user.role == 'teacher' %}<a class="btn" href="{{ url_for('profile') }}">View my teacher's program</a>{% endif %}</div>
<div class="scroll"><table class="list">
{% if g.user.role == 'teacher' %}
<tr><th scope="row">Teacher no.</th><td>{{ tlabels.get(g.user.id, '-') }}</td></tr>
<tr><th scope="row">Name</th><td>{{ g.user.full_name }}</td></tr>
<tr><th scope="row">Teacher ID / Username</th><td>{{ g.user.teacher_id }} / {{ g.user.username }}</td></tr>
<tr><th scope="row">Grade level handled</th><td>{{ catname.get(g.user.category, '-') }}</td></tr>
<tr><th scope="row">Subjects</th><td>{{ g.user.subject_area or '-' }}</td></tr>
<tr><th scope="row">Specialization</th><td>{{ g.user.specialization or '-' }}</td></tr>
<tr><th scope="row">Teaching load</th><td>{{ g.user.teaching_load or summ.loads }}</td></tr>
<tr><th scope="row">Ancillary</th><td>{{ ancillary }}</td></tr>
<tr><th scope="row">Official time</th><td>{{ g.user.official_time or '-' }}</td></tr>
{% else %}
<tr><th scope="row">Name</th><td>{{ g.user.full_name }}</td></tr>
<tr><th scope="row">Username</th><td>{{ g.user.username }}</td></tr>
<tr><th scope="row">Role</th><td>Administrator</td></tr>
{% endif %}</table></div>
{% if g.user.role == 'teacher' %}<p class="hint">Your name and username can be changed in <a href="{{ url_for('account_settings') }}">Settings</a>. The rest is set by the administrator - contact them to request a change.</p>{% endif %}</div>{% endblock %}""",

"account_settings.html": """{% extends "base.html" %}{% from "macros.html" import back with context %}{% block title %}Settings{% endblock %}
{% block content %}<div class="titlerow">{{ back(url_for('account'), 'Back') }}<h1>Settings</h1><a class="helpfab inline" href="{{ url_for('help_center') }}" title="Help Center" aria-label="Help Center"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 13v-1a8 8 0 0 1 16 0v1"/><rect x="2" y="13" width="5" height="7" rx="2.5"/><rect x="17" y="13" width="5" height="7" rx="2.5"/><path d="M20 20a4 4 0 0 1-4 3h-2"/></svg><span class="helpfab-q">?</span></a></div>
<div class="cardrow">
<div class="card narrow"><h2>Edit profile</h2><form method="post">{{ csrf_field() }}<input type="hidden" name="action" value="profile">
<label for="full_name">Name</label><input id="full_name" name="full_name" value="{{ g.user.full_name }}" required maxlength="200">
<label for="username">Username</label><input id="username" name="username" value="{{ g.user.username }}" required maxlength="40" autocomplete="username">
<p style="margin-top:1.2rem"><button type="submit">Save profile</button></p></form></div>
<div class="card narrow"><h2>Change password</h2><form method="post">{{ csrf_field() }}
<label for="current">Current password</label><input id="current" type="password" name="current" autocomplete="current-password" required>
<label for="new">New password (at least 6 characters)</label><input id="new" type="password" name="new" minlength="6" autocomplete="new-password" required>
<label for="confirm">Confirm new password</label><input id="confirm" type="password" name="confirm" minlength="6" autocomplete="new-password" required>
<p style="margin-top:1.2rem"><button type="submit">Change password</button></p></form></div>

</div>{% endblock %}""",

"signup.html": """{% extends "base.html" %}{% block title %}Request an account{% endblock %}
{% block page %}<div class="login">
<section class="side"><svg class="arcs" viewBox="0 0 600 800" preserveAspectRatio="xMidYMid slice" aria-hidden="true"><g fill="none" stroke="#fff" stroke-opacity=".13"><circle cx="640" cy="780" r="300"/><circle cx="640" cy="780" r="380"/><circle cx="640" cy="780" r="460"/><circle cx="640" cy="780" r="540"/><circle cx="640" cy="780" r="620"/></g></svg><div class="side-in"><div class="brandrow">{% if has_logo %}<a class="logolink" href="{{ url_for('home') }}" title="Home" aria-label="Home"><img class="logo logoimg" src="{{ logo_url }}" alt="{{ cfg.school_name }} logo"></a>{% else %}<svg class="logo" viewBox="0 0 64 64" aria-hidden="true"><g stroke="#fff" stroke-width="6" stroke-linecap="round"><path d="M32 6v52M6 32h52M13.6 13.6l36.8 36.8M50.4 13.6L13.6 50.4"/></g></svg>{% endif %}<span class="brandschool">San Jose Litex Senior High School<small>School ID: 342566</small></span></div><h1>Join us</h1>
<p>Send a request for a teacher account. The administrator will review it, add you to the list of teachers and set up your schedule details.</p></div>
<small class="copy">&copy; {{ year }} {{ cfg.school_name }}. All rights reserved.</small></section>
<section class="panel"><form method="post" class="authform">{{ csrf_field() }}
<div class="auth-brand">{{ app_name }}</div>
<div class="auth-body"><h2>Request an account</h2>
<p class="auth-note">Already have an account? <a href="{{ url_for('login') }}">Sign in</a>. After approval, sign in using the same user type you choose here.</p>
{% for cat, m in get_flashed_messages(with_categories=true) %}<div class="msg {{ cat }}" role="alert">{{ m }}</div>{% endfor %}
<label for="full_name">Full name</label><input id="full_name" name="full_name" value="{{ v.get('full_name','') }}" required maxlength="200">
<label for="teacher_num">Your Teacher ID</label><div class="tidfield"><span class="tidfix">T-</span><input id="teacher_num" name="teacher_num" type="number" min="1" step="1" inputmode="numeric" placeholder="1001" value="{{ v.get('teacher_num','') }}" required autocomplete="off"></div>
<p class="hint" style="margin:-.3rem 0 .8rem">Type the ID number you were given, for example 1001 for T-1001. The administrator checks it before approving.</p>
<label for="category">Grade level you handle</label><select id="category" name="category">{% for k, name in cats.items() %}<option value="{{ k }}" {{ 'selected' if v.get('category') == k }}>{{ name }}</option>{% endfor %}</select>
<label for="username">Username</label><input id="username" name="username" value="{{ v.get('username','') }}" required maxlength="40" autocomplete="username">
<label for="password">Password (at least 6 characters)</label><input id="password" type="password" name="password" minlength="6" required autocomplete="new-password">
<label for="confirm">Confirm password</label><input id="confirm" type="password" name="confirm" minlength="6" required autocomplete="new-password">
<p id="pwmatch" class="hint" aria-live="polite" style="min-height:1.3rem"></p>
<p class="hint">Tip: tap the eye icon in a password box to check what you typed.</p>
<button type="submit" class="dark" data-busy="Sending...">Send request</button>
<p class="auth-foot"><a href="#" class="viewtoggle" hidden></a></p></div>
</form></section></div>
<script>(function(){var a=document.getElementById('password'),c=document.getElementById('confirm'),m=document.getElementById('pwmatch');
function chk(){if(!c.value){m.textContent='';return;}var ok=a.value===c.value;m.textContent=ok?'Passwords match.':'Passwords do not match yet.';m.style.color=ok?'var(--ok)':'var(--bad)';}
a.addEventListener('input',chk);c.addEventListener('input',chk);})();</script>{% endblock %}""",

"help.html": """{% extends "base.html" %}{% from "macros.html" import report_form with context %}{% block title %}Help{% endblock %}
{% block content %}<div class="titlerow"><h1>Help Center</h1>{% if not g.user %}<a class="btn plain" href="{{ url_for('login') }}">Back to sign in</a>{% endif %}</div>
<p style="color:var(--muted)">A quick guide on how to use the {{ app_name }}.</p>

<div class="card"><h2>Signing in</h2>
<p>Choose your user type (Administrator, Grade 11, Grade 12 or MID teacher), enter your username and password. Teachers also enter their Teacher ID. If you don't have an account yet, use <strong>Request an account</strong> on the sign-in page and wait for the administrator to approve it. Forgot your password? Use <strong>Forgot password?</strong> on the sign-in page to ask the administrator to reset it.</p></div>

<div class="card"><h2>For teachers</h2>
<ul>
<li><strong>My Teacher's Program</strong> shows your own weekly class schedule, computed from the periods the administrator assigned you.</li>
<li><strong>Class Programs</strong> shows the class program of every section you are assigned to teach or advise.</li>
<li>Tap a room number on a class program to see which building and floor it's in.</li>
<li><strong>Profile</strong> (the person icon beside the bell) shows your account details. <strong>Settings</strong> is where you edit your name and username or change your password.</li>
<li>The bell icon shows notifications, such as new assignments or a change to your role.</li>
</ul></div>

<div class="card"><h2>For administrators</h2>
<ul>
<li><strong>Teacher Management</strong> holds teacher accounts, specialization and official time; <strong>Teacher Loading</strong> assigns who teaches each subject.</li>
<li><strong>Section Management</strong> creates sections with their track, cluster, shift, room and adviser; the <strong>Dashboard</strong> shows what still needs doing.</li>
<li><strong>Class Programs</strong> lets you add, edit or remove periods for any section. A teacher assigned in both Grade 11 and Grade 12 automatically becomes a MID teacher, and goes back to G11 or G12 when only one grade level is left.</li>
<li><strong>Requests</strong> lists new account requests and password reset requests waiting for your action.</li>
<li><strong>Document details</strong> sets the school name and logo used across the system and on printed programs.</li>
</ul></div>

<div class="card"><h2>Printing</h2>
<p>Open a class program or teacher's program and use the on-screen Print button, or your browser's own print option.</p></div>

{% if not (g.user and g.user.role == 'admin') %}<div class="card narrow" id="report"><h2>Report a problem</h2>{{ report_form({}) }}</div>{% endif %}{% endblock %}""",

"verify_code.html": """{% extends "base.html" %}{% block title %}Enter your code{% endblock %}
{% block page %}<div class="login">
<section class="side"><svg class="arcs" viewBox="0 0 600 800" preserveAspectRatio="xMidYMid slice" aria-hidden="true"><g fill="none" stroke="#fff" stroke-opacity=".13"><circle cx="640" cy="780" r="300"/><circle cx="640" cy="780" r="380"/><circle cx="640" cy="780" r="460"/><circle cx="640" cy="780" r="540"/><circle cx="640" cy="780" r="620"/></g></svg><div class="side-in"><div class="brandrow">{% if has_logo %}<a class="logolink" href="{{ url_for('home') }}" title="Home" aria-label="Home"><img class="logo logoimg" src="{{ logo_url }}" alt="{{ cfg.school_name }} logo"></a>{% else %}<svg class="logo" viewBox="0 0 64 64" aria-hidden="true"><g stroke="#fff" stroke-width="6" stroke-linecap="round"><path d="M32 6v52M6 32h52M13.6 13.6l36.8 36.8M50.4 13.6L13.6 50.4"/></g></svg>{% endif %}<span class="brandschool">San Jose Litex Senior High School<small>School ID: 342566</small></span></div><h1>Forgot your password?</h1>
<p>{% if mode == 'reset' %}Check your Gmail for the 6-digit code, then choose a new password.{% else %}Check your Gmail for the 6-digit code to finish your account request.{% endif %}</p></div>
<small class="copy">&copy; {{ year }} {{ cfg.school_name }}. All rights reserved.</small></section>
<section class="panel"><form method="post" class="authform">{{ csrf_field() }}
<div class="auth-brand">{{ app_name }}</div>
<div class="auth-body"><h2>Enter your code</h2>
<p class="auth-note">We sent a 6-digit code to <b>{{ masked }}</b>. It works for 10 minutes. <a href="{{ back }}">Go back</a>.</p>
{% for cat, m in get_flashed_messages(with_categories=true) %}<div class="msg {{ cat }}" role="alert">{{ m }}</div>{% endfor %}
<label for="code">6-digit code</label><input id="code" name="code" inputmode="numeric" pattern="[0-9 ]{6,7}" maxlength="7" autocomplete="one-time-code" required autofocus>
{% if mode == 'reset' %}<label for="new">New password (at least 6 characters)</label><input id="new" type="password" name="new" minlength="6" required autocomplete="new-password">
<label for="confirm">Confirm new password</label><input id="confirm" type="password" name="confirm" minlength="6" required autocomplete="new-password">{% endif %}
<button type="submit" class="dark" style="margin-top:1.2rem">{{ 'Change password' if mode == 'reset' else 'Verify and send request' }}</button>
<p class="auth-foot"><button type="submit" form="resendform" class="linklike">Did not get it? Send a new code</button></p></div>
</form><form id="resendform" method="post" action="{{ action }}">{{ csrf_field() }}<input type="hidden" name="action" value="resend"></form></section></div>{% endblock %}""",

"forgot_password.html": """{% extends "base.html" %}{% block title %}Forgot password{% endblock %}
{% block page %}<div class="login">
<section class="side"><svg class="arcs" viewBox="0 0 600 800" preserveAspectRatio="xMidYMid slice" aria-hidden="true"><g fill="none" stroke="#fff" stroke-opacity=".13"><circle cx="640" cy="780" r="300"/><circle cx="640" cy="780" r="380"/><circle cx="640" cy="780" r="460"/><circle cx="640" cy="780" r="540"/><circle cx="640" cy="780" r="620"/></g></svg><div class="side-in"><div class="brandrow">{% if has_logo %}<a class="logolink" href="{{ url_for('home') }}" title="Home" aria-label="Home"><img class="logo logoimg" src="{{ logo_url }}" alt="{{ cfg.school_name }} logo"></a>{% else %}<svg class="logo" viewBox="0 0 64 64" aria-hidden="true"><g stroke="#fff" stroke-width="6" stroke-linecap="round"><path d="M32 6v52M6 32h52M13.6 13.6l36.8 36.8M50.4 13.6L13.6 50.4"/></g></svg>{% endif %}<span class="brandschool">San Jose Litex Senior High School<small>School ID: 342566</small></span></div><h1>Forgot your password?</h1>
<p>Enter your username and Teacher ID. Your request goes to the administrator, who gives you a temporary password.</p></div>
<small class="copy">&copy; {{ year }} {{ cfg.school_name }}. All rights reserved.</small></section>
<section class="panel"><form method="post" class="authform">{{ csrf_field() }}
<div class="auth-brand">{{ app_name }}</div>
<div class="auth-body"><h2>Reset your password</h2>
<p class="auth-note">Remembered it after all? <a href="{{ url_for('login') }}">Back to sign in</a>.</p>
{% for cat, m in get_flashed_messages(with_categories=true) %}<div class="msg {{ cat }}" role="alert">{{ m }}</div>{% endfor %}
<label for="username">Username</label><input id="username" name="username" value="{{ v.get('username','') }}" required maxlength="40" autocomplete="username">
<label for="teacher_num">Teacher ID</label><div class="tidfield"><span class="tidfix">T-</span><input id="teacher_num" name="teacher_num" type="number" min="1" step="1" inputmode="numeric" placeholder="1001" value="{{ v.get('teacher_num','') }}" required autocomplete="off"></div>
<button type="submit" class="dark" data-busy="Sending...">Send request to administrator</button>
<p class="auth-foot">After the administrator resets it, sign in with the temporary password and change it in Settings.</p></div>
</form></section></div>{% endblock %}""",

"requests_block.html": """<h2>Account requests</h2>
<details class="tip noprint"><summary>About this page</summary><p>Teachers who asked for an account appear here. Check the name and grade level, then approve - the Teacher ID is the one the teacher typed (shown in the box); correct it before approving if it is wrong. Approved teachers are added to Teacher Management, where you set their subjects, loads, ancillary and official time.</p></details>
<div class="scroll"><table class="list"><thead><tr><th>Requested</th><th>Name</th><th>Teacher ID</th><th>Username</th><th>Grade level handled</th><th></th></tr></thead><tbody>
{% for r in signup_rows %}<tr><td>{{ r.created|stamp12 }}</td>
<td><input form="a{{ r.id }}" name="full_name" value="{{ r.full_name }}" aria-label="Name" required></td>
<td><div class="tidfield"><span class="tidfix">T-</span><input form="a{{ r.id }}" name="teacher_num" type="number" min="1" step="1" value="{{ r.teacher_id[2:] if r.teacher_id else suggested_id[2:] }}" aria-label="Teacher ID number" required></div></td>
<td>{{ r.username }}</td>
<td><select form="a{{ r.id }}" name="category" aria-label="Grade level handled">{% for k, v in cats.items() %}<option value="{{ k }}" {{ 'selected' if k == r.category }}>{{ v }}</option>{% endfor %}</select></td>
<td><div class="row-acts"><form id="a{{ r.id }}" method="post" action="{{ url_for('signup_requests') }}">{{ csrf_field() }}<input type="hidden" name="rid" value="{{ r.id }}"><input type="hidden" name="action" value="approve"><button class="small">Approve</button></form>
<form method="post" action="{{ url_for('signup_requests') }}" onsubmit="return confirm('Reject and remove this request?')">{{ csrf_field() }}<input type="hidden" name="rid" value="{{ r.id }}"><input type="hidden" name="action" value="reject"><button class="danger">Reject</button></form></div></td></tr>
{% else %}<tr><td colspan="6" class="empty">No pending requests.</td></tr>{% endfor %}</tbody></table></div>
<h2 style="margin-top:2rem">Password reset requests</h2>
<details class="tip noprint"><summary>About this page</summary><p>A teacher who forgot their password shows up here. Resetting gives them the temporary password teacher123 and notifies them in-app; ask them to change it in Settings right after.</p></details>
<div class="scroll"><table class="list"><thead><tr><th>Requested</th><th>Name</th><th>Username</th><th>Teacher ID</th><th>Note</th><th></th></tr></thead><tbody>
{% for rr in reset_rows %}<tr><td>{{ rr.created|stamp12 }}</td><td>{{ rr.full_name }}</td><td>{{ rr.username }}</td><td>{{ rr.teacher_id or '-' }}</td><td>{{ rr.note or '-' }}</td>
<td><div class="row-acts"><form method="post" action="{{ url_for('signup_requests') }}" onsubmit="return confirm('Reset this teacher\\'s password to a new temporary one?')">{{ csrf_field() }}<input type="hidden" name="rrid" value="{{ rr.id }}"><input type="hidden" name="action" value="reset_done"><button class="small">Reset password</button></form>
<form method="post" action="{{ url_for('signup_requests') }}">{{ csrf_field() }}<input type="hidden" name="rrid" value="{{ rr.id }}"><input type="hidden" name="action" value="reset_cancel"><button class="danger">Dismiss</button></form></div></td></tr>
{% else %}<tr><td colspan="6" class="empty">No pending password reset requests.</td></tr>{% endfor %}</tbody></table></div>""",

"report.html": """{% extends "base.html" %}{% from "macros.html" import back, report_form with context %}{% block title %}Report a problem{% endblock %}
{% block content %}<div class="titlerow">{{ back(url_for('help_center') if g.user else url_for('login'), 'Back') }}<h1>Report a Problem</h1></div>
<div class="card narrow">{{ report_form(v) }}</div>{% endblock %}""",

"notifications.html": """{% extends "base.html" %}{% block title %}Notifications{% endblock %}
{% block content %}<div class="head"><h1>Notifications</h1>{% if rows %}<form method="post" onsubmit="return confirm('Delete all notifications?')">{{ csrf_field() }}<input type="hidden" name="action" value="clear"><button class="danger">Clear all</button></form>{% endif %}</div>
{% for r in rows %}<article class="card note{{ ' fresh' if r.id in fresh }}"><div class="rhead"><div><p class="rmsg">{{ r.message }}</p><div class="hint">{{ r.created|stamp12 }}</div></div><div>{% if r.id in fresh %}<span class="pill new">New</span>{% endif %}</div></div>
<div class="row-acts" style="margin-top:.6rem">{% if r.link %}<a class="btn plain small" href="{{ r.link }}">View</a>{% endif %}
<form method="post">{{ csrf_field() }}<input type="hidden" name="rid" value="{{ r.id }}"><input type="hidden" name="action" value="delete"><button class="danger">Delete</button></form></div></article>
{% else %}<div class="card">No notifications yet. You will be told here when the administrator updates your Teacher's Program or assigns you to a class period or section.</div>{% endfor %}{% endblock %}""",

"reports.html": """{% extends "base.html" %}{% block title %}Notifications{% endblock %}
{% block content %}{{ subnav('users') }}<div class="head"><div><h1>Requests and Problem Reports</h1><p class="hint" style="margin-top:.6rem">Account requests, password reset requests and problem reports from teachers appear here. Delete a report once it is solved so this list stays short.</p></div>{% if any_resolved %}<form method="post" onsubmit="return confirm('Delete all resolved reports?')">{{ csrf_field() }}<input type="hidden" name="action" value="clear"><button class="danger">Clear resolved</button></form>{% endif %}</div>
{% include "requests_block.html" %}
<h2 style="margin-top:2rem">Problem reports</h2>
{% for r in rows %}<article class="card report{{ ' fresh' if r.id in fresh }}{{ ' done' if r.resolved }}">
<div class="rhead"><div><strong>{{ r.name }}</strong>{% if r.contact %} <span class="hint">({{ r.contact }})</span>{% endif %}
<div class="hint">{{ r.created|stamp12 }}</div></div>
<div>{% if r.id in fresh %}<span class="pill new">New</span>{% endif %}{% if r.resolved %}<span class="pill ok">Resolved</span>{% endif %}</div></div>
<p class="rmsg">{{ r.message }}</p>
{% if r.has_photo %}<button type="button" class="shotbtn" data-full="{{ url_for('report_photo', rid=r.id) }}"><img class="rphoto" src="{{ url_for('report_photo', rid=r.id) }}" alt="Photo attached to the report" loading="lazy"></button>{% endif %}
{% if shots.get(r.id) %}<p class="hint">{{ shots[r.id]|length }} screenshot{{ '' if shots[r.id]|length == 1 else 's' }} attached. Tap one to open it full size.</p><div class="rgallery">{% for pid in shots[r.id] %}<button type="button" class="shotbtn" data-full="{{ url_for('report_shot', pid=pid) }}"><img src="{{ url_for('report_shot', pid=pid) }}" alt="Screenshot {{ loop.index }} of the report" loading="lazy"></button>{% endfor %}</div>{% endif %}
<div class="row-acts" style="margin-top:.8rem">
<form method="post">{{ csrf_field() }}<input type="hidden" name="rid" value="{{ r.id }}"><input type="hidden" name="action" value="resolve"><button class="plain small">{{ 'Reopen' if r.resolved else 'Mark as resolved' }}</button></form>
<form method="post" onsubmit="return confirm('Delete this report?')">{{ csrf_field() }}<input type="hidden" name="rid" value="{{ r.id }}"><input type="hidden" name="action" value="delete"><button class="danger">Delete</button></form></div></article>
{% else %}<div class="card">No problem reports yet. When a user reports a problem it appears here and you get a notification.</div>{% endfor %}
<div id="shotbox" class="shotbox noprint" hidden><button type="button" class="backbtn shotback" id="shotback" title="Back" aria-label="Back"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M19 12H5M12 19l-7-7 7-7"/></svg><span>Back</span></button><img id="shotimg" src="" alt="Full size screenshot"></div>
<script>(function(){
var box=document.getElementById('shotbox'),img=document.getElementById('shotimg'),back=document.getElementById('shotback');
document.body.appendChild(box);
var pushed=false;
function open(src){img.src=src;box.hidden=false;document.body.style.overflow='hidden';back.focus();
try{history.pushState({shot:1},'');pushed=true;}catch(e){pushed=false;}}
function close(){if(box.hidden)return;box.hidden=true;img.src='';document.body.style.overflow='';
if(pushed){pushed=false;try{history.back();}catch(e){}}}
window.addEventListener('popstate',function(){if(!box.hidden){pushed=false;close();}});
document.querySelectorAll('.shotbtn').forEach(function(b){b.addEventListener('click',function(){open(b.getAttribute('data-full'));});});
back.addEventListener('click',close);
box.addEventListener('click',function(ev){if(ev.target===box)close();});
document.addEventListener('keydown',function(ev){if(ev.key==='Escape'&&!box.hidden)close();});
})();</script>
{% endblock %}""",
}
# ======================================================================================
# AUTOMATED CLASS PROGRAM GENERATION (add-on)
# Subjects -> Rooms -> Qualifications -> Teacher loading -> Generate -> Review -> Apply.
# The generator writes into the same `classes` table the manual editor uses, so Class
# Programs, Teacher's Programs, printing and notifications keep working unchanged.
# ======================================================================================
import random
from collections import defaultdict

RTYPES = ["Regular", "Computer Laboratory", "Cookery Laboratory", "Science Laboratory",
          "TechPro Workshop", "Other Laboratory"]
DEFAULT_TT = """# SHIFT start-end [recess]   (one line per period; the shift name is the first word)
AM 06:00-07:00
AM 07:00-08:00
AM 08:00-09:00
AM 09:00-09:30 recess
AM 09:30-10:30
AM 10:30-11:30
AM 11:30-12:30
PM 13:00-14:00
PM 14:00-15:00
PM 15:00-15:30 recess
PM 15:30-16:30
PM 16:30-17:30
PM 17:30-18:30
MID 09:00-10:00
MID 10:00-11:00
MID 11:00-12:00
MID 12:00-13:00 recess
MID 13:00-14:00
MID 14:00-15:00
MID 15:00-16:00
"""
STARTER_LABS = [("Cookery Laboratory 1", "Cookery Laboratory"), ("Cookery Laboratory 2", "Cookery Laboratory"),
                ("Computer Laboratory 1", "Computer Laboratory"), ("Computer Laboratory 2", "Computer Laboratory"),
                ("Science Laboratory 1", "Science Laboratory"),
                ("TechPro Workshop 1", "TechPro Workshop"), ("TechPro Workshop 2", "TechPro Workshop"),
                ("TechPro Workshop 3", "TechPro Workshop")]


def curriculum_rows():
    """The Strengthened Curriculum as database rows. Minutes are starting values the school can edit."""
    core_min = {"EC/MK": 240, "LCS": 120, "GM": 240, "GS": 240, "PKLP": 120}
    rows = [(c, n, n, 0, "", core_min[c], 60, "Regular", "core", "") for c, n in CORE_SUBJECTS]
    rows += [(c, n, n, 0, "Academic", 240, 60, rt, "cluster", ", ".join(sp)) for c, n, sp, rt in ACADEMIC_CLUSTERS]
    rows += [(c, n, n, 0, "TechPro", 240, 120, rt, "cluster", ", ".join(sp)) for c, n, sp, rt in TECHPRO_CLUSTERS]
    return rows


def seed_curriculum(conn):
    """Make sure every fixed subject and cluster exists. Minutes the school already edited are kept."""
    n = 0
    for code, name, area, grade, track, wk, se, rt, kind, detail in curriculum_rows():
        row = conn.execute("SELECT id FROM subjects WHERE lower(name)=lower(?)", (name,)).fetchone()
        if row:
            conn.execute("UPDATE subjects SET code=?, name=?, area=?, grade=0, track=?, kind=?, detail=? WHERE id=?",
                         (code, name, area, track, kind, detail, row[0]))
        else:
            conn.execute("INSERT INTO subjects(code,name,area,grade,track,weekly_min,session_min,rtype,kind,detail,offered) "
                         "VALUES(?,?,?,?,?,?,?,?,?,?,1)", (code, name, area, grade, track, wk, se, rt, kind, detail))
            n += 1
    conn.commit()
    return n


def migrate_curriculum():
    """One-time move to the fixed curriculum: remove subjects that are not part of it and map the
    free-text specializations the old example data used."""
    conn = sqlite3.connect(DB)
    conn.execute("UPDATE subjects SET offered=1 WHERE offered IS NULL")
    seed_curriculum(conn)
    done = conn.execute("SELECT 1 FROM settings WHERE k='curriculum_v2'").fetchone()
    if not done:
        keep = {n.lower() for _c, n in CORE_SUBJECTS} | {c[1].lower() for c in ACADEMIC_CLUSTERS + TECHPRO_CLUSTERS}
        for sid, name in conn.execute("SELECT id, name FROM subjects").fetchall():
            if name.lower() not in keep:
                for t in ("section_subjects", "teacher_subjects", "loads"):
                    conn.execute(f"DELETE FROM {t} WHERE subject_id=?", (sid,))
                conn.execute("DELETE FROM subjects WHERE id=?", (sid,))
        for uid, spec in conn.execute("SELECT id, specialization FROM users WHERE role='teacher'").fetchall():
            if spec and spec.strip() in LEGACY_SPEC:
                conn.execute("UPDATE users SET specialization=? WHERE id=?", (LEGACY_SPEC[spec.strip()], uid))
        conn.execute("INSERT OR REPLACE INTO settings(k,v) VALUES('curriculum_v2','1')")
    conn.execute("UPDATE sections SET shift='AM' WHERE COALESCE(shift,'')='' AND grade=11")
    conn.execute("UPDATE sections SET shift='PM' WHERE COALESCE(shift,'')='' AND grade=12")
    if not conn.execute("SELECT 1 FROM settings WHERE k='g12_cleanup'").fetchone():
        conn.execute("DELETE FROM classes WHERE section_id IN (SELECT id FROM sections WHERE grade=12)")
        conn.execute("INSERT OR REPLACE INTO settings(k,v) VALUES('g12_cleanup','1')")
    for nm, cl in list(SAMPLE_CLUSTER.items()):
        conn.execute("UPDATE sections SET cluster=? WHERE name=? AND COALESCE(cluster,'')=''", (cl, nm))
    conn.commit()
    conn.close()


def init_auto_db():
    conn = sqlite3.connect(DB)
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS subjects(
        id INTEGER PRIMARY KEY, code TEXT, name TEXT NOT NULL, area TEXT, grade INTEGER DEFAULT 0,
        track TEXT DEFAULT '', weekly_min INTEGER NOT NULL, session_min INTEGER NOT NULL,
        rtype TEXT DEFAULT 'Regular');
    CREATE TABLE IF NOT EXISTS rooms(
        id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, rtype TEXT DEFAULT 'Regular',
        building TEXT, floor TEXT);
    CREATE TABLE IF NOT EXISTS section_subjects(
        section_id INTEGER NOT NULL, subject_id INTEGER NOT NULL, PRIMARY KEY(section_id, subject_id));
    CREATE TABLE IF NOT EXISTS teacher_subjects(
        user_id INTEGER NOT NULL, subject_id INTEGER NOT NULL, PRIMARY KEY(user_id, subject_id));
    CREATE TABLE IF NOT EXISTS loads(
        section_id INTEGER NOT NULL, subject_id INTEGER NOT NULL, teacher_id INTEGER,
        PRIMARY KEY(section_id, subject_id));
    """)
    add_col(conn, "sections", "shift", "TEXT")
    add_col(conn, "sections", "cluster", "TEXT")
    add_col(conn, "subjects", "kind", "TEXT DEFAULT ''")
    add_col(conn, "subjects", "offered", "INTEGER DEFAULT 1")
    add_col(conn, "subjects", "detail", "TEXT")
    conn.execute("""CREATE TABLE IF NOT EXISTS audit_log(
        id INTEGER PRIMARY KEY, at TEXT, user_id INTEGER, who TEXT, role TEXT, action TEXT, detail TEXT, ip TEXT)""")
    add_col(conn, "classes", "room", "TEXT")
    add_col(conn, "classes", "room_id", "INTEGER")
    conn.commit()
    conn.close()


# ------------------------------------------------------------------ settings and timetable
def gset(k, d=""):
    r = query("SELECT v FROM settings WHERE k=?", (k,), one=True)
    return r["v"] if r else d


def sset(k, v):
    run("INSERT OR REPLACE INTO settings(k,v) VALUES(?,?)", (k, str(v)))


def parse_tt(text):
    """'AM 06:00-07:00' / 'AM 09:00-09:30 recess' -> {'AM': [(360, 420, 'class'), ...]}."""
    tt = {}
    for line in (text or "").splitlines():
        m = re.match(r"^\s*(\S+)\s+(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})\s*(class|recess|break)?\s*$", line, re.I)
        if not m or m[1].startswith("#"):
            continue
        s, e = int(m[2]) * 60 + int(m[3]), int(m[4]) * 60 + int(m[5])
        if e > s:
            kind = "recess" if (m[6] or "").lower() in ("recess", "break") else "class"
            tt.setdefault(m[1].upper(), []).append((s, e, kind))
    for k in tt:
        tt[k].sort()
    return tt


def tt_overlap(tt):
    for k, per in tt.items():
        for a, b in zip(per, per[1:]):
            if b[0] < a[1]:
                return f"Periods overlap in {k}: {tm(a[0])}-{tm(a[1])} and {tm(b[0])}-{tm(b[1])}."
    return None


def get_tt():
    return parse_tt(gset("tt_text", "") or DEFAULT_TT) or parse_tt(DEFAULT_TT)


def hhmm(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def g12_programs():
    """Class programs are made for Grade 12 only when this is switched on in School Setup."""
    return gset("g12_programs", "") == "1"


def sched_secs():
    """The sections that get a class program."""
    rows = query("SELECT * FROM sections ORDER BY grade, name")
    return rows if g12_programs() else [r for r in rows if r["grade"] != 12]


def teacher_shift(t, tt):
    """AM, MID or PM when the teacher's official time equals one shift; '' for a custom time."""
    a, b = official_range(t["official_time"])
    if not a:
        return ""
    for name, per in tt.items():
        if (tomin(a), tomin(b)) == (per[0][0], per[-1][1]):
            return name
    return ""


def shift_hours(tt, name):
    def f(m):
        h, mi = divmod(int(m), 60)
        ap = "NN" if (h, mi) == (12, 0) else ("AM" if h < 12 else "PM")
        return f"{(h % 12) or 12}:{mi:02d} {ap}"
    per = tt[name]
    return f"{f(per[0][0])} - {f(per[-1][1])}"


def sec_shift(s, tt):
    v = (s["shift"] or "").upper()
    if v in tt:
        return v
    want = "AM" if s["grade"] == 11 else "PM"
    if want in tt:
        return want
    keys = sorted(tt, key=lambda k: tt[k][0][0])
    return keys[0] if s["grade"] == 11 or len(keys) == 1 else keys[-1]


def teacher_window(t):
    a, b = official_range(t["official_time"])
    return (tomin(a), tomin(b)) if a and b else (0, 1440)


def session_lengths(weekly, sess):
    sess = max(10, sess)
    n, rem = divmod(weekly, sess)
    return [sess] * n + ([rem] if rem else [])


def blocks_for(periods, L):
    """Start/end of every run of back-to-back class periods that adds up to exactly L minutes."""
    out = []
    for i in range(len(periods)):
        tot, j, ok = 0, i, False
        while j < len(periods):
            s, e, kind = periods[j]
            if kind != "class" or (j > i and s != periods[j - 1][1]):
                break
            tot += e - s
            if tot == L:
                ok = True
                break
            if tot > L:
                break
            j += 1
        if ok:
            out.append((periods[i][0], periods[j][1]))
    return out


def rtype_options():
    seen = list(RTYPES)
    for r in query("SELECT rtype FROM rooms UNION SELECT rtype FROM subjects"):
        if r["rtype"] and r["rtype"] not in seen:
            seen.append(r["rtype"])
    return seen


def eligible(sub, sec):
    """A cluster belongs only to sections of its track and cluster; core subjects belong to every section."""
    if sub["offered"] is not None and not sub["offered"]:
        return False
    if (sub["kind"] or "") == "cluster":
        return (sub["track"] or "") == (sec["track"] or "") and (sec["cluster"] or "") == sub["name"]
    return (sub["grade"] in (0, None, sec["grade"])) and (not sub["track"] or sub["track"] == sec["track"])


# ------------------------------------------------------------------ the scheduling engine
class Busy:
    """Who or what is occupied when. Keys: ('t', teacher), ('s', section), ('r', room)."""

    def __init__(self):
        self.d = {}

    def add(self, key, day, s, e):
        self.d.setdefault((key, day), []).append((s, e))

    def hit(self, key, day, s, e, buf=0):
        for a, b in self.d.get((key, day), ()):
            if s < b + buf and a < e + buf:
                return True
        return False

    def total(self, key, day):
        return sum(b - a for a, b in self.d.get((key, day), ()))

    def gap(self, key, day, s, e):
        iv = self.d.get((key, day))
        if not iv:
            return 0
        return min(min(max(0, s - b, a - e) for a, b in iv), 120) / 20


def load_problem(section_ids):
    ids = set(section_ids)
    secs = {s["id"]: dict(s) for s in query("SELECT * FROM sections")}
    subs = {s["id"]: dict(s) for s in query("SELECT * FROM subjects")}
    teachers = {t["id"]: dict(t) for t in query("SELECT * FROM users WHERE role='teacher'")}
    tasks = []
    for r in query("""SELECT ss.section_id, ss.subject_id, l.teacher_id FROM section_subjects ss
                      LEFT JOIN loads l ON l.section_id=ss.section_id AND l.subject_id=ss.subject_id"""):
        if r["section_id"] in ids and r["section_id"] in secs and r["subject_id"] in subs:
            tasks.append(dict(sid=r["section_id"], sub=r["subject_id"], tid=r["teacher_id"]))
    fixed = []
    for c in query("SELECT * FROM classes WHERE kind='class'"):
        if c["section_id"] in ids:
            continue
        s, e = tomin(c["start"]), tomin(c["end"])
        if c["teacher_id"]:
            fixed.append((("t", c["teacher_id"]), c["day"], s, e))
        if c["room_id"]:
            fixed.append((("r", c["room_id"]), c["day"], s, e))
    return dict(tt=get_tt(), maxday=to_int(gset("max_teach_day", "360"), 60, 720) or 360,
                turn=to_int(gset("turnover", "0"), 0, 120) or 0, secs=secs, subs=subs,
                teachers=teachers, rooms=[dict(r) for r in query("SELECT * FROM rooms ORDER BY name")],
                tasks=tasks, fixed=fixed)


def diagnose(P, j, fail):
    sub, t = j["sub"], P["teachers"][j["tid"]]
    L, shift = j["L"], j["shift"]
    if not j["blocks"]:
        return (f"The {shift} timetable has no {L}-minute run of back-to-back class periods. "
                "Change the subject's meeting length or the timetable.")
    if not fail:
        return "No time slot was available."
    other = {k: v for k, v in fail.items() if k != "window"}
    cause = max(other, key=other.get) if other else "window"
    return {
        "section": (f"The section has no free {L}-minute block left in its {shift} timetable inside "
                    f"{t['full_name']}'s official time. Free up that time, change the teacher, or widen the official time."),
        "window": (f"No {L}-minute block of the {shift} timetable fits inside {t['full_name']}'s official time "
                   f"({t['official_time'] or 'whole day'}). Change the teacher or the official time."),
        "teacher": f"{t['full_name']} is already teaching at every time this section is free inside their official time.",
        "daycap": f"{t['full_name']} would pass the daily teaching limit of {P['maxday']} minutes.",
        "norooms": f"No room of type '{sub['rtype']}' is registered. Add one in Rooms.",
        "room": f"Every '{sub['rtype']}' room is occupied whenever the teacher and the section are free. Add a room.",
    }[cause]


def attempt(P, rnd):
    busy = Busy()
    for k, d, s, e in P["fixed"]:
        busy.add(k, d, s, e)
    by_type = defaultdict(list)
    for r in P["rooms"]:
        by_type[r["rtype"]].append(r)
    jobs, missing = [], {}
    cache = {}
    for t in P["tasks"]:
        sec, sub = P["secs"][t["sid"]], P["subs"][t["sub"]]
        if not t["tid"] or t["tid"] not in P["teachers"]:
            missing[(sec["id"], sub["id"])] = dict(
                sid=sec["id"], section=sec["name"], subject=sub["name"], teacher="-", minutes=sub["weekly_min"],
                reason="No teacher is assigned. Open Teacher Loading and choose one.")
            continue
        shift = sec_shift(sec, P["tt"])
        tw = teacher_window(P["teachers"][t["tid"]])
        for L in session_lengths(sub["weekly_min"], sub["session_min"]):
            key = (shift, L)
            if key not in cache:
                cache[key] = blocks_for(P["tt"][shift], L)
            per = P["tt"][shift]
            span = (per[0][0], per[-1][1])
            ov = max(0, min(tw[1], span[1]) - max(tw[0], span[0]))
            jobs.append(dict(sec=sec, sub=sub, tid=t["tid"], L=L, shift=shift, win=tw, blocks=cache[key],
                             tight=(span[1] - span[0] - ov) / 60))

    def hard(j):
        # labs, long meetings and teachers whose official time barely overlaps the shift go first
        return ((50 if j["sub"]["rtype"] != "Regular" else 0) + j["L"] / 10
                + j["tight"] * 4 + rnd.random() * 8)
    jobs.sort(key=hard, reverse=True)
    subday, placed, soft = defaultdict(set), [], 0.0
    for j in jobs:
        sid, tid, sub, L = j["sec"]["id"], j["tid"], j["sub"], j["L"]
        cands = by_type.get(sub["rtype"], [])
        home = (j["sec"].get("room") or "").strip().lower()
        if home:
            cands = sorted(cands, key=lambda r: r["name"].lower() != home)
        buf = P["turn"] if sub["rtype"] != "Regular" else 0
        fail, best = defaultdict(int), None
        for day in DAYS:
            for s, e in j["blocks"]:
                if s < j["win"][0] or e > j["win"][1]:
                    fail["window"] += 1
                    continue
                if busy.hit(("s", sid), day, s, e):
                    fail["section"] += 1
                    continue
                if busy.hit(("t", tid), day, s, e):
                    fail["teacher"] += 1
                    continue
                if busy.total(("t", tid), day) + L > P["maxday"]:
                    fail["daycap"] += 1
                    continue
                room = next((r for r in cands if not busy.hit(("r", r["id"]), day, s, e, buf)), None)
                if not room:
                    fail["room" if cands else "norooms"] += 1
                    continue
                sc = ((60 if day in subday[(sid, sub["id"])] else 0)
                      + busy.gap(("t", tid), day, s, e) + busy.gap(("s", sid), day, s, e)
                      + busy.total(("t", tid), day) / 60 * 2 + rnd.random() * 3)
                if best is None or sc < best[0]:
                    best = (sc, day, s, e, room)
        if best:
            sc, day, s, e, room = best
            busy.add(("s", sid), day, s, e)
            busy.add(("t", tid), day, s, e)
            busy.add(("r", room["id"]), day, s, e)
            subday[(sid, sub["id"])].add(day)
            soft += sc
            t = P["teachers"][tid]
            placed.append(dict(sid=sid, section=j["sec"]["name"], subject_id=sub["id"], subject=sub["name"],
                               code=sub["code"] or "", teacher_id=tid, teacher=t["full_name"], day=day,
                               start=hhmm(s), end=hhmm(e), room_id=room["id"], room=room["name"]))
        else:
            k = (sid, sub["id"])
            row = missing.setdefault(k, dict(sid=sid, section=j["sec"]["name"], subject=sub["name"],
                                             teacher=P["teachers"][tid]["full_name"], minutes=0,
                                             reason=diagnose(P, j, fail)))
            row["minutes"] += L
    return dict(sessions=placed, unplaced=list(missing.values()), soft=soft)


def solve(section_ids, tries=40, seed=None):
    P = load_problem(section_ids)
    rnd = random.Random(seed)
    best = None
    for _ in range(tries):
        res = attempt(P, rnd)
        if best is None or (len(res["unplaced"]), res["soft"]) < (len(best["unplaced"]), best["soft"]):
            best = res
        if not best["unplaced"] and _ >= 4:
            break
    best["sections"] = sorted(section_ids)
    best["tries"] = tries
    best["when"] = ph_stamp()
    best["maxday"], best["turn"] = P["maxday"], P["turn"]
    return best


def apply_draft(d):
    tt = get_tt()
    touched = set()
    conn = db()
    secs = {s["id"]: s for s in query("SELECT * FROM sections")}
    for sid in d["sections"]:
        if sid not in secs:
            continue
        touched |= {r["teacher_id"] for r in query(
            "SELECT DISTINCT teacher_id FROM classes WHERE section_id=? AND teacher_id IS NOT NULL", (sid,))}
        conn.execute("DELETE FROM classes WHERE section_id=?", (sid,))
        for day in DAYS:
            for s, e, kind in tt[sec_shift(secs[sid], tt)]:
                if kind == "recess":
                    conn.execute("INSERT INTO classes(section_id,day,start,end,subject,code,kind,teacher_id) "
                                 "VALUES(?,?,?,?,?,?,?,?)", (sid, day, hhmm(s), hhmm(e), "RECESS", None, "recess", None))
    for x in d["sessions"]:
        if x["sid"] in secs:
            conn.execute("INSERT INTO classes(section_id,day,start,end,subject,code,kind,teacher_id,room,room_id) "
                         "VALUES(?,?,?,?,?,?,?,?,?,?)",
                         (x["sid"], x["day"], x["start"], x["end"], x["subject"], x["code"] or None, "class",
                          x["teacher_id"], x["room"], x["room_id"]))
            touched.add(x["teacher_id"])
    conn.commit()
    for sid in d["sections"]:
        touch("section", sid)
    for tid in touched:
        if tid:
            touch("teacher", tid)
            sync_category(tid)


# ------------------------------------------------------------------ setup helpers
def load_starter_subjects():
    """Add any missing subject or cluster of the Strengthened Curriculum (edited minutes are kept)."""
    return seed_curriculum(db())


def sync_section_subjects(sid):
    """Give a section its core subjects (when it has none yet) and exactly its own cluster."""
    sec = query("SELECT * FROM sections WHERE id=?", (sid,), one=True)
    if not sec:
        return False
    have = {r["subject_id"] for r in query("SELECT subject_id FROM section_subjects WHERE section_id=?", (sid,))}
    first, changed = not have, False
    for s in query("SELECT * FROM subjects"):
        ok = eligible(s, sec)
        if (s["kind"] or "") == "cluster":
            if ok and s["id"] not in have:
                run("INSERT OR IGNORE INTO section_subjects(section_id,subject_id) VALUES(?,?)", (sid, s["id"]))
                changed = True
            elif not ok and s["id"] in have:
                run("DELETE FROM section_subjects WHERE section_id=? AND subject_id=?", (sid, s["id"]))
                run("DELETE FROM loads WHERE section_id=? AND subject_id=?", (sid, s["id"]))
                changed = True
        elif first and ok:
            run("INSERT OR IGNORE INTO section_subjects(section_id,subject_id) VALUES(?,?)", (sid, s["id"]))
            changed = True
    if changed and query("SELECT 1 FROM classes WHERE section_id=? AND kind='class'", (sid,), one=True):
        mark_stale([sid])
    return changed


def load_starter_rooms():
    n = 0
    for s in query("SELECT DISTINCT room, building, floor FROM sections WHERE COALESCE(room,'')!=''"):
        if not query("SELECT 1 FROM rooms WHERE lower(name)=lower(?)", (s["room"],), one=True):
            run("INSERT INTO rooms(name,rtype,building,floor) VALUES(?,?,?,?)",
                (s["room"], "Regular", s["building"], s["floor"]))
            n += 1
    for name, rt in STARTER_LABS:
        if not query("SELECT 1 FROM rooms WHERE name=?", (name,), one=True):
            run("INSERT INTO rooms(name,rtype,building,floor) VALUES(?,?,?,?)", (name, rt, "1", "3"))
            n += 1
    return n


def missing_room_types():
    """Room types that offered subjects need but no registered room has."""
    need = {r["rtype"] for r in query("SELECT DISTINCT rtype FROM subjects WHERE COALESCE(offered,1)=1")}
    have = {r["rtype"] for r in query("SELECT DISTINCT rtype FROM rooms")}
    return sorted(x for x in need if x and x not in have)


def ensure_room_types():
    n = 0
    for rt in missing_room_types():
        run("INSERT OR IGNORE INTO rooms(name,rtype,building,floor) VALUES(?,?,?,?)", (f"{rt} 1", rt, "1", "3"))
        n += 1
    return n


def match_quals(uid=None):
    """A teacher is qualified for a subject when its exact name (or, for a cluster, one of its
    specializations) is in the teacher's specialization, or a core subject code is in their subjects."""
    n = 0
    subs = query("SELECT * FROM subjects")
    have = {(r["user_id"], r["subject_id"]) for r in query("SELECT * FROM teacher_subjects")}
    for t in query("SELECT * FROM users WHERE role='teacher'"):
        if uid and t["id"] != uid:
            continue
        text = f"{t['subject_area'] or ''}; {t['specialization'] or ''}".lower()
        for s in subs:
            name = (s["name"] or "").strip().lower()
            terms = [name] + [x.lower() for x in CLUSTER_SPECS.get(s["name"], [])]
            hit = any(x and x in text for x in terms)
            if not hit and (s["kind"] or "") == "core":
                for tok in re.split(r"[/\s]+", (s["code"] or "").lower()):
                    if len(tok) >= 2 and re.search(r"(?<![a-z0-9])" + re.escape(tok) + r"(?![a-z0-9])", text):
                        hit = True
            if hit and (t["id"], s["id"]) not in have:
                run("INSERT INTO teacher_subjects(user_id,subject_id) VALUES(?,?)", (t["id"], s["id"]))
                have.add((t["id"], s["id"]))
                n += 1
    return n


def teacher_minutes_assigned():
    out = defaultdict(int)
    for r in query("""SELECT l.teacher_id, b.weekly_min FROM loads l JOIN subjects b ON b.id=l.subject_id
                      JOIN section_subjects ss ON ss.section_id=l.section_id AND ss.subject_id=l.subject_id
                      WHERE l.teacher_id IS NOT NULL"""):
        out[r["teacher_id"]] += r["weekly_min"]
    return out


def autofill(overwrite=False):
    """Attach every eligible subject to sections that have none, then give each unassigned
    subject the best qualified teacher (shift fit, then lightest load)."""
    tt = get_tt()
    subs = [dict(s) for s in query("SELECT * FROM subjects")]
    secs = [dict(s) for s in sched_secs()]
    added = 0
    for sec in secs:
        before = query("SELECT COUNT(*) AS n FROM section_subjects WHERE section_id=?", (sec["id"],), one=True)["n"]
        sync_section_subjects(sec["id"])
        added += query("SELECT COUNT(*) AS n FROM section_subjects WHERE section_id=?", (sec["id"],), one=True)["n"] - before
    teachers = {t["id"]: dict(t) for t in query("SELECT * FROM users WHERE role='teacher'")}
    quals = defaultdict(set)
    for r in query("SELECT * FROM teacher_subjects"):
        quals[r["subject_id"]].add(r["user_id"])
    load = teacher_minutes_assigned()
    maxday = to_int(gset("max_teach_day", "360"), 60, 720) or 360
    cap = maxday * len(DAYS)
    secd0 = {s["id"]: s for s in secs}
    subd0 = {s["id"]: s for s in subs}
    shift_load = defaultdict(int)
    for r in query("SELECT section_id, subject_id, teacher_id FROM loads WHERE teacher_id IS NOT NULL"):
        if r["section_id"] in secd0 and r["subject_id"] in subd0:
            shift_load[(r["teacher_id"], sec_shift(secd0[r["section_id"]], tt))] += subd0[r["subject_id"]]["weekly_min"]
    todo = []
    for r in query("SELECT ss.section_id, ss.subject_id FROM section_subjects ss"):
        cur = query("SELECT teacher_id FROM loads WHERE section_id=? AND subject_id=?",
                    (r["section_id"], r["subject_id"]), one=True)
        if overwrite or not cur or not cur["teacher_id"]:
            todo.append((r["section_id"], r["subject_id"]))
    secd = {s["id"]: s for s in secs}
    subd = {s["id"]: s for s in subs}
    todo.sort(key=lambda x: len(quals[x[1]]))
    given = 0
    for sid, bid in todo:
        sec, sub = secd.get(sid), subd.get(bid)
        if not sec or not sub:
            continue
        shift = sec_shift(sec, tt)
        per = tt[shift]
        span = (per[0][0], per[-1][1])
        best = None
        for tid in quals[bid]:
            t = teachers.get(tid)
            if not t or load[tid] + sub["weekly_min"] > cap:
                continue
            w = teacher_window(t)
            fit = max(0, min(span[1], w[1]) - max(span[0], w[0])) / max(1, span[1] - span[0])
            usable = sum(max(0, min(e, w[1]) - max(s, w[0])) for s, e, k in per if k == "class")
            if fit == 0 or shift_load[(tid, shift)] + sub["weekly_min"] > min(usable, maxday) * len(DAYS):
                continue
            score = (1 - fit) * 1000 + load[tid] + (150 if GRADES.get(t["category"]) and sec["grade"] not in GRADES[t["category"]] else 0)
            if best is None or score < best[0]:
                best = (score, tid)
        if best:
            run("INSERT OR REPLACE INTO loads(section_id,subject_id,teacher_id) VALUES(?,?,?)", (sid, bid, best[1]))
            load[best[1]] += sub["weekly_min"]
            shift_load[(best[1], shift)] += sub["weekly_min"]
            given += 1
    return added, given, len(todo) - given


def quick_setup():
    parts = []
    n = load_starter_subjects()
    if n:
        parts.append(f"{n} curriculum subjects restored")
    if not query("SELECT 1 FROM rooms", one=True):
        parts.append(f"{load_starter_rooms()} rooms")
    r = ensure_room_types()
    if r:
        parts.append(f"{r} laboratory/workshop room(s) added for room types that had none")
    q = match_quals()
    a, gv, left = autofill()
    parts.append(f"{q} teacher qualifications matched, {a} section subjects added, {gv} teachers assigned"
                 + (f", {left} left without a teacher (no qualified teacher has enough time in that shift)" if left else ""))
    return "Quick setup finished: " + "; ".join(parts) + "."


# ------------------------------------------------------------------ routes
@app.route("/admin/subjects")
@login_required("admin")
def auto_subjects():
    return redirect(url_for("curriculum"))


@app.route("/admin/rooms", methods=["GET", "POST"])
@login_required("admin")
def auto_rooms():
    if request.method == "POST":
        f = request.form
        act = f.get("action")
        if act == "starter":
            flash(f"{load_starter_rooms()} rooms added from your sections and the starter laboratories.", "ok")
        elif act == "add":
            name = clean(f.get("name"))
            try:
                if not name:
                    raise ValueError
                run("INSERT INTO rooms(name,rtype,building,floor) VALUES(?,?,?,?)",
                    (name, clean(f.get("rtype")) or "Regular", f.get("building") or None, f.get("floor") or None))
                flash("Room added.", "ok")
            except (ValueError, sqlite3.IntegrityError):
                flash("Enter a room name that does not exist yet.", "error")
        else:
            for r in query("SELECT * FROM rooms"):
                i = r["id"]
                if f"name_{i}" not in f:
                    continue
                if f.get(f"del_{i}"):
                    run("UPDATE classes SET room=NULL, room_id=NULL WHERE room_id=?", (i,))
                    run("DELETE FROM rooms WHERE id=?", (i,))
                    continue
                try:
                    run("UPDATE rooms SET name=?, rtype=?, building=?, floor=? WHERE id=?",
                        (clean(f.get(f"name_{i}")) or r["name"], clean(f.get(f"rtype_{i}")) or "Regular",
                         f.get(f"building_{i}") or None, f.get(f"floor_{i}") or None, i))
                except sqlite3.IntegrityError:
                    flash("Two rooms cannot share a name.", "error")
            flash("Rooms saved.", "ok")
        return redirect(url_for("auto_rooms"))
    tt = get_tt()
    cap = sum(e - s for per in tt.values() for s, e, k in per if k == "class") * len(DAYS)
    used = {r["room_id"]: r["m"] for r in query(
        "SELECT room_id, SUM((substr(end,1,2)*60+substr(end,4,2))-(substr(start,1,2)*60+substr(start,4,2))) AS m "
        "FROM classes WHERE kind='class' AND room_id IS NOT NULL GROUP BY room_id")}
    return render_template("auto_rooms.html", rows=query("SELECT * FROM rooms ORDER BY rtype, name"),
                           rtypes=rtype_options(), used=used, cap=cap or 1)


@app.route("/admin/rooms/<int:rid>")
@login_required("admin")
def auto_room(rid):
    room = query("SELECT * FROM rooms WHERE id=?", (rid,), one=True)
    if not room:
        abort(404)
    rows = [dict(r) for r in query(
        """SELECT c.*, s.name AS sname, u.full_name AS tname FROM classes c JOIN sections s ON s.id=c.section_id
           LEFT JOIN users u ON u.id=c.teacher_id WHERE c.room_id=? AND c.kind='class'""", (rid,))]
    rows.sort(key=lambda r: (DAYS.index(r["day"]), r["start"]))
    return render_template("auto_room.html", room=room, rows=rows)


@app.route("/admin/qualifications", methods=["GET", "POST"])
@login_required("admin")
def auto_quals():
    teachers_ = query("SELECT * FROM users WHERE role='teacher' ORDER BY id")
    subs = query("SELECT * FROM subjects ORDER BY grade, name")
    if request.method == "POST":
        if request.form.get("action") == "match":
            flash(f"{match_quals()} new qualifications were matched from the teachers' specialization text.", "ok")
        else:
            run("DELETE FROM teacher_subjects")
            for t in teachers_:
                for s in subs:
                    if request.form.get(f"q_{t['id']}_{s['id']}"):
                        run("INSERT INTO teacher_subjects(user_id,subject_id) VALUES(?,?)", (t["id"], s["id"]))
            flash("Qualifications saved.", "ok")
        return redirect(url_for("auto_quals"))
    have = {(r["user_id"], r["subject_id"]) for r in query("SELECT * FROM teacher_subjects")}
    return render_template("auto_quals.html", teachers_=teachers_, subs=subs, have=have)


@app.route("/admin/loading", methods=["GET", "POST"])
@login_required("admin")
def auto_loading():
    secs = sched_secs()
    if request.method == "POST":
        f = request.form
        if f.get("action") == "autofill":
            a, gv, left = autofill(overwrite=bool(f.get("overwrite")))
            flash(f"Added {a} section subjects and assigned {gv} teachers by qualification, shift fit and lightest load."
                  + (f" {left} still need a teacher: no qualified teacher has enough time in that shift." if left else ""),
                  "ok" if not left else "error")
            return redirect(url_for("auto_loading"))
        sid = f.get("section_id", type=int)
        sec = query("SELECT * FROM sections WHERE id=?", (sid,), one=True)
        if not sec:
            abort(404)
        before = {(r["subject_id"], r["teacher_id"]) for r in query("SELECT subject_id, teacher_id FROM loads WHERE section_id=?", (sid,))}
        run("DELETE FROM section_subjects WHERE section_id=?", (sid,))
        run("DELETE FROM loads WHERE section_id=?", (sid,))
        warn = 0
        for s in query("SELECT * FROM subjects"):
            if f.get(f"take_{s['id']}"):
                run("INSERT INTO section_subjects(section_id,subject_id) VALUES(?,?)", (sid, s["id"]))
                tid = f.get(f"teacher_{s['id']}", type=int)
                if tid and query("SELECT 1 FROM users WHERE id=? AND role='teacher'", (tid,), one=True):
                    run("INSERT INTO loads(section_id,subject_id,teacher_id) VALUES(?,?,?)", (sid, s["id"], tid))
                    if not query("SELECT 1 FROM teacher_subjects WHERE user_id=? AND subject_id=?", (tid, s["id"]), one=True):
                        warn += 1
        after = {(r["subject_id"], r["teacher_id"]) for r in query("SELECT subject_id, teacher_id FROM loads WHERE section_id=?", (sid,))}
        if before != after and query("SELECT 1 FROM classes WHERE section_id=? AND kind='class'", (sid,), one=True):
            mark_stale([sid])
        flash(f"Loading saved for {sec['name']}." + (f" {warn} teacher(s) are not listed as qualified." if warn else ""),
              "ok" if not warn else "error")
        return redirect(url_for("auto_loading", section=sid))
    cur = next((s for s in secs if str(s["id"]) == request.args.get("section", "")), secs[0] if secs else None)
    rows, tt = [], get_tt()
    teachers_ = query("SELECT * FROM users WHERE role='teacher' ORDER BY full_name")
    assigned = teacher_minutes_assigned()
    if cur:
        take = {r["subject_id"] for r in query("SELECT subject_id FROM section_subjects WHERE section_id=?", (cur["id"],))}
        load = {r["subject_id"]: r["teacher_id"] for r in query("SELECT * FROM loads WHERE section_id=?", (cur["id"],))}
        qs = defaultdict(set)
        for r in query("SELECT * FROM teacher_subjects"):
            qs[r["subject_id"]].add(r["user_id"])
        for s in query("SELECT * FROM subjects ORDER BY name"):
            if eligible(s, cur) or s["id"] in take:
                opts = sorted(teachers_, key=lambda t: (t["id"] not in qs[s["id"]], t["full_name"]))
                rows.append(dict(s=s, taken=s["id"] in take, tid=load.get(s["id"]), opts=opts, q=qs[s["id"]]))
    summ = []
    return render_template("auto_loading.html", secs=secs, cur=cur, rows=rows,
                           cur_shift=sec_shift(dict(cur), tt) if cur else "", summ=summ, lv=validate_loading())


@app.route("/admin/generate", methods=["GET", "POST"])
@login_required("admin")
def auto_generate():
    if request.method == "POST":
        f = request.form
        act = f.get("action")
        if act == "quick":
            flash(quick_setup(), "ok")
        elif act == "generate":
            ids = [int(x) for x in f.getlist("sec") if x.isdigit()]
            if not ids:
                flash("Select at least one section to generate.", "error")
            else:
                res = solve(ids, tries=to_int(f.get("tries"), 5, 200) or 40)
                sset("gen_draft", json.dumps(res))
                flash(f"Draft created: {len(res['sessions'])} sessions placed, {len(res['unplaced'])} subject(s) not fully scheduled. "
                      "Review it below, then apply it.", "ok" if not res["unplaced"] else "error")
        elif act == "apply":
            try:
                d = json.loads(gset("gen_draft", ""))
            except ValueError:
                d = None
            if not d:
                flash("There is no draft to apply. Generate one first.", "error")
            else:
                apply_draft(d)
                clear_stale(d["sections"])
                sset("gen_draft", "")
                chk = check_program()
                flash(f"Draft applied to {len(d['sections'])} class program(s). Conflict check: "
                      f"{len(chk['issues'])} problem(s).", "ok" if not chk["issues"] else "error")
        elif act == "regen":
            ids = [int(x) for x in f.getlist("sec") if x.isdigit()]
            if ids:
                res = solve(ids, tries=40)
                sset("gen_draft", json.dumps(res))
                flash(f"Draft created for {len(ids)} out-of-date section(s). Review it below, then apply it.", "ok")
        elif act == "discard":
            sset("gen_draft", "")
            flash("Draft discarded. The class programs were not changed.", "ok")
        return redirect(url_for("dashboard") if f.get("next") == "dashboard" else url_for("auto_generate"))
    try:
        draft = json.loads(gset("gen_draft", "") or "null")
    except ValueError:
        draft = None
    by = defaultdict(list)
    if draft:
        for x in sorted(draft["sessions"], key=lambda x: (x["section"], DAYS.index(x["day"]), x["start"])):
            by[x["section"]].append(x)
    secs = [r for r in query("""SELECT s.*, (SELECT COUNT(*) FROM section_subjects WHERE section_id=s.id) AS nsub
                    FROM sections s ORDER BY s.grade, s.name""") if g12_programs() or r["grade"] != 12]
    return render_template("auto_generate.html", secs=secs, draft=draft, by=dict(by),
                           tt_text=gset("tt_text", "") or DEFAULT_TT, max_day=gset("max_teach_day", "360"),
                           turnover=gset("turnover", "0"), max_week=gset("max_teach_week", "1800"), chk=check_program(),
                           lv=validate_loading(),
                           stale=[dict(r) for r in query("SELECT id, name FROM sections") if r["id"] in stale_ids()],
                           counts={k: query(f"SELECT COUNT(*) AS n FROM {k}", one=True)["n"]
                                   for k in ("subjects", "rooms", "teacher_subjects", "loads")})



AUTO_TEMPLATES = {
"auto_rooms.html": """{% extends "base.html" %}{% block title %}Rooms{% endblock %}
{% block content %}<h1>Room Management</h1>
<details class="tip noprint"><summary>About this page</summary><p>Rooms are shared by every shift. A room is free again as soon as its class ends, and the generator picks a free room of the type each subject needs. A section's own room is preferred for regular subjects.</p></details>
<div class="card"><h3>Add a room</h3><form method="post">{{ csrf_field() }}<input type="hidden" name="action" value="add"><div class="formgrid">
<div><label for="name">Room name</label><input id="name" name="name" placeholder="Room 308" required></div>
<div><label for="rtype">Type</label><input id="rtype" name="rtype" list="rtl" value="Regular"><datalist id="rtl">{% for r in rtypes %}<option value="{{ r }}">{% endfor %}</datalist></div>
<div><label for="building">Building</label><select id="building" name="building"><option value="">Not set</option>{% for b in buildings %}<option value="{{ b }}">Bldg. {{ b }}</option>{% endfor %}</select></div>
<div><label for="floor">Floor</label><select id="floor" name="floor"><option value="">Not set</option>{% for fl in floors %}<option value="{{ fl }}">Floor {{ fl }}</option>{% endfor %}</select></div>
<div><button type="submit" style="margin-top:.7rem">Add room</button></div></div></form>
<form method="post" style="margin-top:.8rem" data-noconfirm>{{ csrf_field() }}<input type="hidden" name="action" value="starter"><button class="plain" type="submit">Load rooms from sections and starter laboratories</button></form></div>
<form method="post">{{ csrf_field() }}<input type="hidden" name="action" value="save"><div class="scroll"><table class="list"><thead><tr><th>Room</th><th>Type</th><th>Building</th><th>Floor</th><th>Use</th><th>Program</th><th>Remove</th></tr></thead><tbody>
{% for r in rows %}{% set k = r.id %}{% set u = used.get(k, 0) %}<tr>
<td><input name="name_{{ k }}" value="{{ r.name }}" aria-label="Room name" required></td>
<td><input name="rtype_{{ k }}" list="rtl2" value="{{ r.rtype }}" aria-label="Type"></td>
<td><select name="building_{{ k }}" aria-label="Building"><option value="">-</option>{% for b in buildings %}<option value="{{ b }}" {{ 'selected' if r.building == b }}>{{ b }}</option>{% endfor %}</select></td>
<td><select name="floor_{{ k }}" aria-label="Floor"><option value="">-</option>{% for fl in floors %}<option value="{{ fl }}" {{ 'selected' if r.floor == fl }}>{{ fl }}</option>{% endfor %}</select></td>
<td><div class="bar"><i style="width:{{ [100, (u * 100 / cap)|int]|min }}%"></i></div><p class="hint">{{ u|hrs }} per week ({{ (u * 100 / cap)|int }}%)</p></td>
<td><a class="btn plain small" href="{{ url_for('auto_room', rid=k) }}">View</a></td>
<td><input class="ck" type="checkbox" name="del_{{ k }}" value="1" aria-label="Remove {{ r.name }}"></td></tr>
{% else %}<tr><td colspan="7" class="empty">No rooms yet.</td></tr>{% endfor %}</tbody></table></div>
<datalist id="rtl2">{% for r in rtypes %}<option value="{{ r }}">{% endfor %}</datalist>
{% if rows %}<div class="btnrow"><button type="submit">Save changes</button></div>{% endif %}</form>{% endblock %}""",

"auto_room.html": """{% extends "base.html" %}{% from "macros.html" import back with context %}{% block title %}{{ room.name }}{% endblock %}
{% block content %}<div class="titlerow">{{ back(url_for('auto_rooms'), 'Back to rooms') }}<h1>{{ room.name }}</h1></div>
<details class="tip noprint"><summary>About this page</summary><p>{{ room.rtype }} &middot; shared across all shifts. {{ rows|length }} class period{{ '' if rows|length == 1 else 's' }} per week.</p></details>
<div class="scroll"><table class="list"><thead><tr><th>Day</th><th>Time</th><th>Section</th><th>Subject</th><th>Teacher</th></tr></thead><tbody>
{% for r in rows %}<tr><td>{{ r.day }}</td><td>{{ r.start|t12 }} to {{ r.end|t12 }}</td><td><a href="{{ url_for('program', section=r.section_id) }}">{{ r.sname }}</a></td><td>{{ r.subject }}</td><td>{{ r.tname or '-' }}</td></tr>
{% else %}<tr><td colspan="5" class="empty">This room is free all week.</td></tr>{% endfor %}</tbody></table></div>{% endblock %}""",

"auto_quals.html": """{% extends "base.html" %}{% block title %}Qualifications{% endblock %}
{% block content %}<h1>Teacher Loading</h1>{{ subnav('loading') }}
<details class="tip noprint"><summary>About this page</summary><p>Tick the subjects each teacher may handle. Choosing a specialization in Teacher Management ticks these automatically. The generator and the auto-assign tool only use qualified teachers.</p></details>
<div class="card"><form method="post" data-noconfirm>{{ csrf_field() }}<input type="hidden" name="action" value="match"><button class="plain" type="submit">Match from teachers' specialization and subjects</button></form></div>
{% if not subs %}<div class="msg notice">Add subjects first.</div>{% else %}
<form method="post">{{ csrf_field() }}<input type="hidden" name="action" value="save"><div class="scroll"><table class="mx"><thead><tr><th class="l">Teacher</th>{% for s in subs %}<th title="{{ s.name }}">{{ s.code or s.name[:6] }}<br><small>{{ s.track or 'Core' }}</small></th>{% endfor %}</tr></thead><tbody>
{% for t in teachers_ %}<tr><td class="l"><b>{{ tlabels.get(t.id) }}</b> {{ t.full_name }}<br><small>{{ t.official_time or 'Whole day' }}</small></td>{% for s in subs %}<td><input class="ck" type="checkbox" name="q_{{ t.id }}_{{ s.id }}" value="1" {{ 'checked' if (t.id, s.id) in have }} aria-label="{{ t.full_name }} - {{ s.name }}"></td>{% endfor %}</tr>
{% else %}<tr><td class="l" colspan="{{ subs|length + 1 }}">No teachers yet.</td></tr>{% endfor %}</tbody></table></div>
<div class="btnrow"><button type="submit">Save qualifications</button></div></form>{% endif %}{% endblock %}""",

}
TEMPLATES.update(AUTO_TEMPLATES)


# ======================================================================================
# LOADING VALIDATION, TIME ALLOCATION, CONFLICTS, ADJUSTMENT ASSISTANCE, REPORTS
# ======================================================================================
import io
from flask import send_file


def daily_limit():
    return to_int(gset("max_teach_day", "360"), 60, 720) or 360


def weekly_limit():
    return to_int(gset("max_teach_week", "1800"), 60, 3000) or 1800


def hm_text(m):
    m = int(m or 0)
    h, r = divmod(m, 60)
    return (f"{h} hr{'s' if h != 1 else ''}" if h else "") + (" " if h and r else "") + (f"{r} min" if r or not h else "")


def usable_min(w, per):
    """Class minutes of one shift that fall inside a teacher's official time window."""
    return sum(max(0, min(e, w[1]) - max(s, w[0])) for s, e, k in per if k == "class")


def stale_ids():
    try:
        return [int(x) for x in json.loads(gset("stale_sections", "[]") or "[]")]
    except ValueError:
        return []


def mark_stale(ids):
    sset("stale_sections", json.dumps(sorted(set(stale_ids()) | set(ids))))


def clear_stale(ids):
    sset("stale_sections", json.dumps([i for i in stale_ids() if i not in set(ids)]))


def build_busy(exclude_ids=()):
    busy = Busy()
    ex = set(exclude_ids)
    for c in query("SELECT * FROM classes WHERE kind='class'"):
        if c["id"] in ex:
            continue
        s, e = tomin(c["start"]), tomin(c["end"])
        busy.add(("s", c["section_id"]), c["day"], s, e)
        if c["teacher_id"]:
            busy.add(("t", c["teacher_id"]), c["day"], s, e)
        if c["room_id"]:
            busy.add(("r", c["room_id"]), c["day"], s, e)
    return busy


# ------------------------------------------------------------------ 1. loading validation
def validate_loading():
    tt, maxday, maxweek = get_tt(), daily_limit(), weekly_limit()
    issues, warns = [], []
    teachers_ = {t["id"]: dict(t) for t in query("SELECT * FROM users WHERE role='teacher' ORDER BY full_name")}
    secs = {s["id"]: dict(s) for s in sched_secs()}
    subs = {s["id"]: dict(s) for s in query("SELECT * FROM subjects")}
    quals = {(r["user_id"], r["subject_id"]) for r in query("SELECT * FROM teacher_subjects")}
    mins, nsec = defaultdict(int), defaultdict(int)
    preps, unq = defaultdict(set), defaultdict(int)
    by_shift = defaultdict(int)
    have_sub = defaultdict(set)
    for o in query("""SELECT ss.section_id, ss.subject_id, l.teacher_id FROM section_subjects ss
                      LEFT JOIN loads l ON l.section_id=ss.section_id AND l.subject_id=ss.subject_id"""):
        sec, sub = secs.get(o["section_id"]), subs.get(o["subject_id"])
        if not sec or not sub:
            continue
        have_sub[sec["id"]].add(sub["name"].strip().lower())
        tid = o["teacher_id"]
        if not tid:
            issues.append(f"Incomplete loading: {sec['name']} - {sub['name']} has no teacher assigned.")
            continue
        t = teachers_.get(tid)
        if not t:
            issues.append(f"Incomplete loading: the teacher assigned to {sec['name']} - {sub['name']} no longer exists.")
            continue
        mins[tid] += sub["weekly_min"]
        nsec[tid] += 1
        preps[tid].add(sub["id"])
        by_shift[(tid, sec_shift(sec, tt))] += sub["weekly_min"]
        if (tid, sub["id"]) not in quals:
            unq[tid] += 1
            issues.append(f"Outside qualification: {t['full_name']} is assigned {sub['name']} ({sec['name']}) "
                          "but is not qualified for it.")
        if not eligible(sub, sec):
            warns.append(f"{sub['name']} is not meant for {sec['name']} (grade or track differs).")
    for sid, sec in secs.items():
        if not have_sub.get(sid):
            warns.append(f"{sec['name']} has no subjects yet.")
    # duplicates
    seen = defaultdict(list)
    for s in subs.values():
        seen[(s["name"] or "").strip().lower()].append(s)
        if s["code"]:
            seen[("code", s["code"].strip().lower())].append(s)
    for k, lst in seen.items():
        if len(lst) > 1:
            label = k if isinstance(k, str) else k[1].upper()
            issues.append(f"Duplicate subject record: '{label}' exists {len(lst)} times in the subject list.")
    taught = defaultdict(set)
    for c in query("SELECT section_id, subject, teacher_id FROM classes WHERE kind='class' AND teacher_id IS NOT NULL"):
        taught[(c["section_id"], c["subject"])].add(c["teacher_id"])
    for (sid, name), ts in taught.items():
        if len(ts) > 1 and sid in secs:
            issues.append(f"Duplicate assignment: {secs[sid]['name']} - {name} is taught by "
                          f"{len(ts)} different teachers in the class program.")
    rows = []
    for tid, t in teachers_.items():
        w = teacher_window(t)
        notes, status = [], "OK"
        if mins[tid] > maxweek:
            status = "Over limit"
            issues.append(f"Over limit: {t['full_name']} is assigned {hm_text(mins[tid])} per week; the limit is {hm_text(maxweek)}.")
        for shift, per in tt.items():
            need = by_shift.get((tid, shift), 0)
            avail = min(usable_min(w, per), maxday) * len(DAYS)
            if need > avail:
                status = "Cannot fit" if status == "OK" else status
                issues.append(f"Cannot fit: {t['full_name']} has {hm_text(need)} per week in the {shift} shift but only "
                              f"{hm_text(avail)} of official time ({t['official_time'] or 'whole day'}) overlaps it.")
        if not mins[tid]:
            status = "No load" if status == "OK" else status
            warns.append(f"{t['full_name']} has no teaching load assigned.")
        elif not t["official_time"]:
            warns.append(f"{t['full_name']} has no official time set; the whole day is assumed.")
        if unq[tid]:
            status = "Unqualified" if status == "OK" else status
        sched = query("""SELECT COALESCE(SUM((substr(end,1,2)*60+substr(end,4,2))-(substr(start,1,2)*60+substr(start,4,2))),0) AS m
                         FROM classes WHERE kind='class' AND teacher_id=?""", (tid,), one=True)["m"]
        rows.append(dict(t=t, minutes=mins[tid], nsec=nsec[tid], npre=len(preps[tid]), unq=unq[tid],
                         sched=sched, status=status, window=t["official_time"] or "Whole day"))
    for s in subs.values():
        if not any((t_id, s["id"]) in quals for t_id in teachers_):
            warns.append(f"No qualified teacher exists for {s['name']}.")
        if s["session_min"] > s["weekly_min"]:
            warns.append(f"{s['name']}: the meeting length is longer than the weekly time.")
        elif s["weekly_min"] % s["session_min"]:
            warns.append(f"{s['name']}: {hm_text(s['weekly_min'])} is not a whole number of {hm_text(s['session_min'])} meetings; "
                         "the last meeting will be shorter.")
        if not query("SELECT 1 FROM rooms WHERE rtype=?", (s["rtype"],), one=True):
            issues.append(f"No '{s['rtype']}' room is registered for {s['name']}.")
    return dict(rows=rows, issues=issues, warns=sorted(set(warns)), maxweek=maxweek, maxday=maxday)


# ------------------------------------------------------------------ 2. time allocation
def time_allocation():
    tt, maxday, maxweek = get_tt(), daily_limit(), weekly_limit()
    order = sorted(tt, key=lambda k: tt[k][0][0])
    shifts = []
    for name in order:
        per = tt[name]
        cls = sum(e - s for s, e, k in per if k == "class")
        shifts.append(dict(name=name, start=hhmm(per[0][0]), end=hhmm(per[-1][1]), day=cls, week=cls * len(DAYS),
                           periods=[(hhmm(s), hhmm(e), k) for s, e, k in per]))
    subs = []
    for s in query("SELECT * FROM subjects ORDER BY grade, name"):
        lens = session_lengths(s["weekly_min"], s["session_min"])
        blocks = {n: {L: len(blocks_for(tt[n], L)) for L in sorted(set(lens))} for n in order}
        subs.append(dict(s=s, n=len(lens), lens=lens, blocks=blocks,
                         bad=[n for n in order if any(v == 0 for v in blocks[n].values())]))
    secs = []
    for sec in sched_secs():
        sh = sec_shift(dict(sec), tt)
        need = query("""SELECT COALESCE(SUM(b.weekly_min),0) AS m FROM section_subjects ss JOIN subjects b ON b.id=ss.subject_id
                        WHERE ss.section_id=?""", (sec["id"],), one=True)["m"]
        cap = next(x["week"] for x in shifts if x["name"] == sh)
        secs.append(dict(sec=sec, shift=sh, need=need, cap=cap, pct=int(100 * need / cap) if cap else 0))
    tch = []
    for t in query("SELECT * FROM users WHERE role='teacher' ORDER BY full_name"):
        w = teacher_window(dict(t))
        union = 0
        for a, b in class_union(tt):
            union += max(0, min(b, w[1]) - max(a, w[0]))
        cap = min(min(union, maxday) * len(DAYS), maxweek)
        need = query("""SELECT COALESCE(SUM(b.weekly_min),0) AS m FROM loads l JOIN subjects b ON b.id=l.subject_id
                        JOIN section_subjects ss ON ss.section_id=l.section_id AND ss.subject_id=l.subject_id
                        WHERE l.teacher_id=?""", (t["id"],), one=True)["m"]
        tch.append(dict(t=t, need=need, cap=cap, pct=int(100 * need / cap) if cap else (100 if need else 0),
                        window=t["official_time"] or "Whole day"))
    return dict(shifts=shifts, subs=subs, secs=secs, tch=tch, maxday=maxday, maxweek=maxweek)


def class_union(tt):
    iv = sorted((s, e) for per in tt.values() for s, e, k in per if k == "class")
    out = []
    for s, e in iv:
        if out and s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out


def free_slots(kind, ident, L):
    """Every free block of L minutes for a section, teacher or room, per day."""
    tt, busy, maxday = get_tt(), build_busy(), daily_limit()
    pers, win, key = list(tt.values()), (0, 1440), (kind[0], ident)
    if kind == "section":
        sec = query("SELECT * FROM sections WHERE id=?", (ident,), one=True)
        pers = [tt[sec_shift(dict(sec), tt)]] if sec else []
    elif kind == "teacher":
        t = query("SELECT * FROM users WHERE id=? AND role='teacher'", (ident,), one=True)
        win = teacher_window(dict(t)) if t else win
    out = {d: set() for d in DAYS}
    for per in pers:
        for day in DAYS:
            for s, e in blocks_for(per, L):
                if s < win[0] or e > win[1] or busy.hit(key, day, s, e):
                    continue
                if kind == "teacher" and busy.total(key, day) + L > maxday:
                    continue
                out[day].add((s, e))
    return {d: sorted(v) for d, v in out.items()}


# ------------------------------------------------------------------ 3. conflict detection
def check_program():
    tt, maxday = get_tt(), daily_limit()
    items = []

    def add(kind, text, pid=None, sev="issue"):
        items.append(dict(kind=kind, text=text, pid=pid, sev=sev))
    secd = {s["id"]: dict(s) for s in query("SELECT * FROM sections")}
    shift_of = {i: sec_shift(s, tt) for i, s in secd.items()}
    rows = [dict(r) for r in query(
        """SELECT c.*, s.name AS sname, u.full_name AS tname, u.official_time AS otime, r.rtype AS rrtype
           FROM classes c JOIN sections s ON s.id=c.section_id
           LEFT JOIN users u ON u.id=c.teacher_id LEFT JOIN rooms r ON r.id=c.room_id WHERE c.kind='class'""")]
    groups = defaultdict(list)
    for r in rows:
        for kind, ident, label in (("section", r["section_id"], r["sname"]), ("teacher", r["teacher_id"], r["tname"]),
                                   ("room", r["room_id"], r["room"])):
            if ident:
                groups[(kind, ident, r["day"], label)].append(r)
    for (kind, _i, day, label), lst in groups.items():
        for i, a in enumerate(lst):
            for b in lst[i + 1:]:
                if tomin(a["start"]) < tomin(b["end"]) and tomin(b["start"]) < tomin(a["end"]):
                    cross = kind == "room" and shift_of.get(a["section_id"]) != shift_of.get(b["section_id"])
                    add("room-shift" if cross else kind,
                        f"{'Room conflict across shifts' if cross else kind.capitalize() + ' conflict'}: {label} on {day} - "
                        f"{a['sname']} {a['subject']} ({t12(a['start'])}-{t12(a['end'])}) overlaps {b['sname']} {b['subject']} "
                        f"({t12(b['start'])}-{t12(b['end'])}).", a["id"])
    done = defaultdict(int)
    for r in rows:
        done[(r["section_id"], r["subject"])] += tomin(r["end"]) - tomin(r["start"])
    for r in query("""SELECT ss.section_id, s.name AS sname, b.name AS bname, b.weekly_min FROM section_subjects ss
                      JOIN sections s ON s.id=ss.section_id JOIN subjects b ON b.id=ss.subject_id"""):
        got = done.get((r["section_id"], r["bname"]), 0)
        if got < r["weekly_min"]:
            pid = next((x["id"] for x in rows if x["section_id"] == r["section_id"] and x["subject"] == r["bname"]), None)
            add("hours", f"Incomplete hours: {r['sname']} - {r['bname']} has {hm_text(got)} of the required "
                         f"{hm_text(r['weekly_min'])} per week.", pid)
    sub_type = {r["name"]: r["rtype"] for r in query("SELECT name, rtype FROM subjects")}
    perday = defaultdict(int)
    for r in rows:
        s, e = tomin(r["start"]), tomin(r["end"])
        if r["teacher_id"]:
            perday[(r["tname"], r["day"])] += e - s
            w = teacher_window({"official_time": r["otime"]})
            if s < w[0] or e > w[1]:
                add("window", f"Outside teacher availability: {r['tname']} ({r['otime'] or 'whole day'}) teaches "
                              f"{r['sname']} {r['subject']} on {r['day']} {t12(r['start'])}-{t12(r['end'])}.", r["id"])
        per = tt[shift_of[r["section_id"]]]
        if s < per[0][0] or e > per[-1][1]:
            add("shift", f"Outside shift: {r['sname']} {r['subject']} on {r['day']} {t12(r['start'])} is outside "
                         f"the {shift_of[r['section_id']]} timetable.", r["id"])
        elif any(k == "recess" and s < pe and ps < e for ps, pe, k in per):
            add("shift", f"{r['sname']} {r['subject']} on {r['day']} {t12(r['start'])} overlaps recess.", r["id"])
        want = sub_type.get(r["subject"])
        if want and r["room_id"] and r["rrtype"] != want:
            add("roomtype", f"Wrong room type: {r['sname']} {r['subject']} is in a {r['rrtype']} but needs a {want}.", r["id"])
        if want and not r["room_id"]:
            add("noroom", f"No room assigned: {r['sname']} {r['subject']} ({r['day']}).", r["id"], "warn")
    for (name, day), m in perday.items():
        if m > maxday:
            add("daycap", f"{name} teaches {hm_text(m)} on {day} (limit {hm_text(maxday)}).", None, "warn")
    seen, uniq = set(), []
    for x in items:
        if x["text"] not in seen:
            seen.add(x["text"])
            uniq.append(x)
    return dict(entries=uniq, issues=[x["text"] for x in uniq if x["sev"] == "issue"],
                warns=[x["text"] for x in uniq if x["sev"] == "warn"][:40], rows=len(rows))


# ------------------------------------------------------------------ 4. adjustment assistance
def period_row(pid):
    r = query("""SELECT c.*, s.name AS sname, s.grade, s.track, s.shift AS sshift, s.room AS home FROM classes c
                 JOIN sections s ON s.id=c.section_id WHERE c.id=? AND c.kind='class'""", (pid,), one=True)
    return dict(r) if r else None


def need_rtype(p):
    sub = query("SELECT rtype FROM subjects WHERE lower(name)=lower(?)", (p["subject"],), one=True)
    if sub:
        return sub["rtype"]
    room_ = query("SELECT rtype FROM rooms WHERE id=?", (p["room_id"],), one=True) if p["room_id"] else None
    return room_["rtype"] if room_ else "Regular"


def slot_error(busy, sec, teacher, day, s, e, maxday, tt):
    L = e - s
    if (s, e) not in set(blocks_for(tt[sec_shift(sec, tt)], L)):
        return f"{t12(hhmm(s))}-{t12(hhmm(e))} is not a valid {hm_text(L)} block in the {sec_shift(sec, tt)} timetable."
    if busy.hit(("s", sec["id"]), day, s, e):
        return f"{sec['name']} already has a class then."
    if teacher:
        w = teacher_window(teacher)
        if s < w[0] or e > w[1]:
            return f"{teacher['full_name']} is outside official time then."
        if busy.hit(("t", teacher["id"]), day, s, e):
            return f"{teacher['full_name']} is already teaching then."
        if busy.total(("t", teacher["id"]), day) + L > maxday:
            return f"{teacher['full_name']} would pass the daily teaching limit."
    return None


def free_room(busy, p, day, s, e, prefer=None):
    rt = need_rtype(p)
    buf = daily_turn() if rt != "Regular" else 0
    cands = [dict(r) for r in query("SELECT * FROM rooms WHERE rtype=? ORDER BY name", (rt,))]
    cands.sort(key=lambda r: (r["id"] != prefer, (r["name"] or "").lower() != (p.get("home") or "").lower()))
    return [r for r in cands if not busy.hit(("r", r["id"]), day, s, e, buf)]


def daily_turn():
    return to_int(gset("turnover", "0"), 0, 120) or 0


def suggest_slots(p, limit=20):
    tt, maxday = get_tt(), daily_limit()
    busy = build_busy([p["id"]])
    sec = dict(query("SELECT * FROM sections WHERE id=?", (p["section_id"],), one=True))
    teacher = query("SELECT * FROM users WHERE id=?", (p["teacher_id"],), one=True) if p["teacher_id"] else None
    teacher = dict(teacher) if teacher else None
    s0, e0 = tomin(p["start"]), tomin(p["end"])
    out = []
    for day in DAYS:
        for s, e in blocks_for(tt[sec_shift(sec, tt)], e0 - s0):
            if (day, s) == (p["day"], s0) or slot_error(busy, sec, teacher, day, s, e, maxday, tt):
                continue
            rooms_ = free_room(busy, p, day, s, e, p["room_id"])
            if rooms_ or not p["room_id"]:
                out.append(dict(day=day, start=hhmm(s), end=hhmm(e), room=rooms_[0] if rooms_ else None,
                                same_day=day == p["day"], d=abs(s - s0)))
    out.sort(key=lambda x: (not x["same_day"], x["d"], DAYS.index(x["day"])))
    return out[:limit]


def meetings_of(p):
    return [dict(r) for r in query("""SELECT * FROM classes WHERE section_id=? AND subject=? AND kind='class'
                                      ORDER BY id""", (p["section_id"], p["subject"]))]


def suggest_teachers(p):
    tt, maxday = get_tt(), daily_limit()
    sub = query("SELECT * FROM subjects WHERE lower(name)=lower(?)", (p["subject"],), one=True)
    if not sub:
        return []
    meets = meetings_of(p)
    busy = build_busy([m["id"] for m in meets])
    sec = dict(query("SELECT * FROM sections WHERE id=?", (p["section_id"],), one=True))
    out = []
    for t in query("""SELECT u.* FROM users u JOIN teacher_subjects q ON q.user_id=u.id AND q.subject_id=?
                      WHERE u.role='teacher' AND u.id IS NOT ? ORDER BY u.full_name""", (sub["id"], p["teacher_id"])):
        t, ok, why = dict(t), 0, ""
        w = teacher_window(t)
        extra = defaultdict(int)
        for m in meets:
            s, e = tomin(m["start"]), tomin(m["end"])
            err = None
            if s < w[0] or e > w[1]:
                err = "outside official time"
            elif busy.hit(("t", t["id"]), m["day"], s, e):
                err = "already teaching"
            elif busy.total(("t", t["id"]), m["day"]) + extra[m["day"]] + (e - s) > maxday:
                err = "daily limit"
            if err:
                why = why or f"{m['day']} {t12(m['start'])}: {err}"
            else:
                ok += 1
                extra[m["day"]] += e - s
        out.append(dict(t=t, ok=ok, total=len(meets), why=why))
    out.sort(key=lambda x: (x["ok"] != x["total"], -x["ok"], x["t"]["full_name"]))
    return out


def suggest_rooms(p):
    busy = build_busy([p["id"]])
    s, e = tomin(p["start"]), tomin(p["end"])
    return [r for r in free_room(busy, p, p["day"], s, e, p["room_id"]) if r["id"] != p["room_id"]]


def notify_change(p, tids, text):
    touch("section", p["section_id"])
    for tid in {t for t in tids if t}:
        touch("teacher", tid)


def apply_move(p, day, s, e, room_id):
    tt, maxday = get_tt(), daily_limit()
    sec = dict(query("SELECT * FROM sections WHERE id=?", (p["section_id"],), one=True))
    teacher = query("SELECT * FROM users WHERE id=?", (p["teacher_id"],), one=True) if p["teacher_id"] else None
    busy = build_busy([p["id"]])
    err = slot_error(busy, sec, dict(teacher) if teacher else None, day, s, e, maxday, tt)
    if err:
        return False, err
    room_ = query("SELECT * FROM rooms WHERE id=?", (room_id,), one=True) if room_id else None
    if room_ and room_["id"] not in [r["id"] for r in free_room(busy, p, day, s, e)]:
        return False, f"{room_['name']} is not free then."
    run("UPDATE classes SET day=?, start=?, end=?, room=?, room_id=? WHERE id=?",
        (day, hhmm(s), hhmm(e), room_["name"] if room_ else None, room_["id"] if room_ else None, p["id"]))
    notify_change(p, [p["teacher_id"]], "moved")
    return True, f"{p['subject']} moved to {day} {t12(hhmm(s))}-{t12(hhmm(e))}."


def apply_room(p, room_id):
    busy = build_busy([p["id"]])
    s, e = tomin(p["start"]), tomin(p["end"])
    room_ = query("SELECT * FROM rooms WHERE id=?", (room_id,), one=True)
    if not room_ or room_["id"] not in [r["id"] for r in free_room(busy, p, p["day"], s, e)]:
        return False, "That room is not free or not the right type."
    run("UPDATE classes SET room=?, room_id=? WHERE id=?", (room_["name"], room_["id"], p["id"]))
    notify_change(p, [p["teacher_id"]], "room")
    return True, f"{p['subject']} now uses {room_['name']}."


def apply_teacher(p, tid):
    cand = next((x for x in suggest_teachers(p) if x["t"]["id"] == tid), None)
    if not cand or cand["ok"] != cand["total"]:
        return False, "That teacher is not free for every meeting of this subject."
    old = p["teacher_id"]
    for m in meetings_of(p):
        run("UPDATE classes SET teacher_id=? WHERE id=?", (tid, m["id"]))
    sub = query("SELECT id FROM subjects WHERE lower(name)=lower(?)", (p["subject"],), one=True)
    if sub:
        run("INSERT OR REPLACE INTO loads(section_id,subject_id,teacher_id) VALUES(?,?,?)", (p["section_id"], sub["id"], tid))
    notify_change(p, [old, tid], "teacher")
    sync_category(tid)
    return True, f"{p['subject']} for {p['sname']} is now taught by {cand['t']['full_name']} (loading updated)."


# ------------------------------------------------------------------ 5. reports and exports
def room_utilization():
    tt = get_tt()
    order = sorted(tt, key=lambda k: tt[k][0][0])
    cap = sum(e - s for per in tt.values() for s, e, k in per if k == "class") * len(DAYS) or 1
    shift_of = {s["id"]: sec_shift(dict(s), tt) for s in query("SELECT * FROM sections")}
    use = defaultdict(lambda: defaultdict(int))
    secs_in = defaultdict(set)
    for c in query("SELECT * FROM classes WHERE kind='class' AND room_id IS NOT NULL"):
        use[c["room_id"]][shift_of.get(c["section_id"], "?")] += tomin(c["end"]) - tomin(c["start"])
        secs_in[c["room_id"]].add(c["section_id"])
    rows = []
    for r in query("SELECT * FROM rooms ORDER BY rtype, name"):
        by = use[r["id"]]
        tot = sum(by.values())
        rows.append(dict(r=r, by={n: by.get(n, 0) for n in order}, total=tot, pct=int(100 * tot / cap),
                         nsec=len(secs_in[r["id"]]), shared=sum(1 for n in order if by.get(n)) > 1, free=cap - tot))
    return dict(rows=rows, order=order, cap=cap)


def entity_grids(kind, ident=None):
    """[(title, subtitle, rows, cells)] where cells[row][day] = {'text','span'} | 'skip' | None."""
    tt = get_tt()
    rows = sorted({(s, e, k) for per in tt.values() for s, e, k in per})
    table = {"sections": "sections", "teachers": "users", "rooms": "rooms"}[kind]
    where = " WHERE role='teacher'" if kind == "teachers" else ""
    ents = [dict(x) for x in query(f"SELECT * FROM {table}{where} ORDER BY {'grade, name' if kind == 'sections' else 'full_name' if kind == 'teachers' else 'name'}")]
    if ident:
        ents = [x for x in ents if x["id"] == ident]
    out = []
    cfg_ = get_cfg()
    for ent in ents:
        col = {"sections": "c.section_id", "teachers": "c.teacher_id", "rooms": "c.room_id"}[kind]
        pers = [dict(r) for r in query(f"""SELECT c.*, s.name AS sname, u.full_name AS tname FROM classes c
                   JOIN sections s ON s.id=c.section_id LEFT JOIN users u ON u.id=c.teacher_id
                   WHERE c.kind='class' AND {col}=?""", (ent["id"],))]
        cells = [[None] * len(DAYS) for _ in rows]
        for p in pers:
            s, e = tomin(p["start"]), tomin(p["end"])
            idx = [i for i, (rs, re_, rk) in enumerate(rows) if rs < e and re_ > s and rk == "class"]
            if not idx or p["day"] not in DAYS:
                continue
            di = DAYS.index(p["day"])
            txt = (f"{p['subject']}\n{p['tname'] or '-'}\n{p['room'] or ''}" if kind == "sections" else
                   f"{p['subject']}\n{p['sname']}\n{p['room'] or ''}" if kind == "teachers" else
                   f"{p['sname']}\n{p['subject']}\n{p['tname'] or '-'}").strip()
            if isinstance(cells[idx[0]][di], dict):
                cells[idx[0]][di]["text"] += "\n" + txt
            else:
                cells[idx[0]][di] = dict(text=txt, span=len(idx))
                for i in idx[1:]:
                    cells[i][di] = "skip"
        if kind == "sections":
            title, sub = f"Class Program - {ent['name']}", f"Grade {ent['grade']} {ent['track'] or ''} | Shift {sec_shift(ent, tt)} | Room {ent['room'] or '-'}"
        elif kind == "teachers":
            title, sub = f"Teacher's Program - {ent['full_name']}", f"Official time: {ent['official_time'] or 'Whole day'}"
        else:
            title, sub = f"Room Program - {ent['name']}", f"{ent['rtype']} (shared across shifts)"
        out.append((title, f"{sub} | {cfg_.get('term', '')}", rows, cells, ent["name"] if "name" in ent else ent["full_name"]))
    return out


def table_report(kind):
    if kind == "loads":
        v = validate_loading()
        head = ["Teacher", "Category", "Official time", "Classes handled", "Different subjects", "Assigned per week",
                "Scheduled per week", "Weekly limit", "Status"]
        data = [[x["t"]["full_name"], x["t"]["category"] or "", x["window"], x["nsec"], x["npre"], hm_text(x["minutes"]),
                 hm_text(x["sched"]), hm_text(v["maxweek"]), x["status"]] for x in v["rows"]]
        return "Teacher Teaching-Load Summary", head, data
    u = room_utilization()
    head = ["Room", "Type"] + [f"{n} per week" for n in u["order"]] + ["Total per week", "Utilization", "Sections", "Shared by shifts"]
    data = [[x["r"]["name"], x["r"]["rtype"]] + [hm_text(x["by"][n]) for n in u["order"]] +
            [hm_text(x["total"]), f"{x['pct']}%", x["nsec"], "Yes" if x["shared"] else "No"] for x in u["rows"]]
    return "Room Utilization Report", head, data


def build_xlsx(kind, ident):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    wb, thin = Workbook(), Side(style="thin", color="999999")
    box = Border(left=thin, right=thin, top=thin, bottom=thin)
    head_fill = PatternFill("solid", fgColor="DCE3F7")
    wb.remove(wb.active)
    names = set()

    def sheet(title):
        base = re.sub(r"[\[\]\\/*?:]", "-", title)[:28] or "Sheet"
        n, i = base, 2
        while n in names:
            n, i = f"{base[:25]}-{i}", i + 1
        names.add(n)
        return wb.create_sheet(n)
    if kind in ("loads", "utilization"):
        title, head, data = table_report(kind)
        ws = sheet(title)
        ws.append([title])
        ws["A1"].font = Font(bold=True, size=14)
        ws.append([get_cfg().get("school_name", ""), get_cfg().get("term", "")])
        ws.append([])
        ws.append(head)
        for c in ws[4]:
            c.font, c.fill, c.border = Font(bold=True), head_fill, box
        for r in data:
            ws.append(r)
        for row in ws.iter_rows(min_row=5):
            for c in row:
                c.border = box
        for i, col in enumerate(ws.columns):
            ws.column_dimensions[col[0].column_letter].width = 26 if i == 0 else 20
    else:
        for title, sub, rows, cells, name in entity_grids(kind, ident):
            ws = sheet(name)
            ws["A1"], ws["A2"] = title, sub
            ws["A1"].font = Font(bold=True, size=14)
            for j, h in enumerate(["Time"] + DAYS):
                c = ws.cell(row=4, column=j + 1, value=h)
                c.font, c.fill, c.border, c.alignment = Font(bold=True), head_fill, box, Alignment(horizontal="center")
            for i, (s, e, k) in enumerate(rows):
                r = 5 + i
                ws.cell(row=r, column=1, value=f"{t12(hhmm(s))} - {t12(hhmm(e))}").border = box
                if k == "recess":
                    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=1 + len(DAYS))
                    c = ws.cell(row=r, column=2, value="RECESS")
                    c.alignment, c.fill = Alignment(horizontal="center"), PatternFill("solid", fgColor="EEEEEE")
                    for j in range(2, 2 + len(DAYS)):
                        ws.cell(row=r, column=j).border = box
                    continue
                for d in range(len(DAYS)):
                    cell = cells[i][d]
                    c = ws.cell(row=r, column=2 + d)
                    c.border = box
                    if isinstance(cell, dict):
                        c.value = cell["text"]
                        c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
                        c.fill = PatternFill("solid", fgColor="E8F0FE")
                        if cell["span"] > 1:
                            ws.merge_cells(start_row=r, start_column=2 + d, end_row=r + cell["span"] - 1, end_column=2 + d)
                ws.row_dimensions[r].height = 48
            ws.column_dimensions["A"].width = 20
            for d in range(len(DAYS)):
                ws.column_dimensions[chr(66 + d)].width = 24
            ws.page_setup.orientation = "landscape"
            ws.page_setup.fitToWidth = 1
    if not wb.sheetnames:
        wb.create_sheet("Empty")
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def build_pdf(kind, ident):
    from xml.sax.saxutils import escape
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    st = getSampleStyleSheet()
    small = ParagraphStyle("s", parent=st["BodyText"], fontSize=7.5, leading=9, alignment=1)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=24, rightMargin=24, topMargin=24, bottomMargin=24,
                            title="Class Scheduler")
    flow = []
    base = [("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DCE3F7")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]
    if kind in ("loads", "utilization"):
        title, head, data = table_report(kind)
        flow += [Paragraph(escape(title), st["Title"]), Paragraph(escape(f"{get_cfg().get('school_name', '')} - {get_cfg().get('term', '')}"), st["Normal"]), Spacer(1, 10)]
        t = Table([[Paragraph(f"<b>{escape(str(h))}</b>", small) for h in head]] +
                  [[Paragraph(escape(str(c)), small) for c in r] for r in data], repeatRows=1)
        t.setStyle(TableStyle(base))
        flow.append(t)
    else:
        grids = entity_grids(kind, ident)
        for n, (title, sub, rows, cells, _name) in enumerate(grids):
            if n:
                flow.append(PageBreak())
            flow += [Paragraph(escape(title), st["Heading2"]), Paragraph(escape(sub), st["Normal"]), Spacer(1, 8)]
            data = [[Paragraph("<b>Time</b>", small)] + [Paragraph(f"<b>{d}</b>", small) for d in DAYS]]
            style = list(base)
            for i, (s, e, k) in enumerate(rows):
                r = i + 1
                line = [Paragraph(escape(f"{t12(hhmm(s))} - {t12(hhmm(e))}"), small)]
                if k == "recess":
                    line += [Paragraph("RECESS", small)] + [""] * (len(DAYS) - 1)
                    style += [("SPAN", (1, r), (-1, r)), ("BACKGROUND", (0, r), (-1, r), colors.HexColor("#EEEEEE"))]
                else:
                    for d in range(len(DAYS)):
                        c = cells[i][d]
                        line.append(Paragraph(escape(c["text"]).replace("\n", "<br/>"), small) if isinstance(c, dict) else "")
                        if isinstance(c, dict):
                            style.append(("BACKGROUND", (d + 1, r), (d + 1, r), colors.HexColor("#E8F0FE")))
                            if c["span"] > 1:
                                style.append(("SPAN", (d + 1, r), (d + 1, r + c["span"] - 1)))
                data.append(line)
            t = Table(data, colWidths=[85] + [145] * len(DAYS), rowHeights=[16] + [38] * len(rows))
            t.setStyle(TableStyle(style))
            flow.append(t)
    if not flow:
        flow.append(Paragraph("Nothing to export yet.", st["Normal"]))
    doc.build(flow)
    buf.seek(0)
    return buf


# ------------------------------------------------------------------ routes
@app.route("/admin/time-allocation")
@login_required("admin")
def auto_time():
    ta = time_allocation()
    res, q = None, request.args.get("find", "")
    L = to_int(request.args.get("length"), 10, 480) or 60
    if ":" in q:
        kind, _, ident = q.partition(":")
        if kind in ("section", "teacher", "room") and ident.isdigit():
            res = dict(kind=kind, id=int(ident), L=L, free=free_slots(kind, int(ident), L))
    return render_template("auto_time.html", ta=ta, res=res, q=q, L=L,
                           secs=sched_secs(),
                           tchs=query("SELECT * FROM users WHERE role='teacher' ORDER BY full_name"),
                           rooms_=query("SELECT * FROM rooms ORDER BY name"), days=DAYS)


@app.route("/admin/conflicts", methods=["GET", "POST"])
@login_required("admin")
def auto_conflicts():
    """09 Validation Center: the system detects conflicts and suggests alternatives; the administrator
    approves the corrections and finally approves (locks) the schedule."""
    if request.method == "POST":
        f = request.form
        act = f.get("action")
        if act == "approve":
            chk, lv = check_program(), validate_loading()
            if not chk["rows"]:
                flash("There is no class program to approve yet.", "error")
            elif chk["issues"] or lv["issues"]:
                flash(f"Fix the {len(chk['issues']) + len(lv['issues'])} problem(s) first, then approve.", "error")
            elif stale_ids():
                flash("Some programs are out of date. Regenerate them before approving.", "error")
            else:
                sset("approved_at", ph_stamp())
                sset("approved_by", g.user["full_name"])
                sset("approved_periods", chk["rows"])
                flash("Schedule approved and locked. Reports are now final.", "ok")
        elif act == "reopen":
            sset("approved_at", "")
            flash("The schedule was reopened. You can edit again; approve it once more when done.", "ok")
        elif act == "move":
            p = period_row(f.get("period", type=int))
            if not p:
                abort(404)
            ok, msg = apply_move(p, f.get("day"), tomin(f.get("start")), tomin(f.get("end")), f.get("room_id", type=int))
            flash(msg, "ok" if ok else "error")
        return redirect(url_for("auto_conflicts"))
    chk = check_program()
    sugg, n = {}, 0
    for x in chk["entries"]:
        if x["sev"] == "issue" and x["pid"] and x["kind"] in ("teacher", "section", "room", "room-shift", "window", "shift", "roomtype") \
                and x["pid"] not in sugg and n < 10:
            p = period_row(x["pid"])
            if p:
                sugg[x["pid"]] = dict(p=p, slots=suggest_slots(p, 3))
                n += 1
    return render_template("auto_conflicts.html", chk=chk, lv=validate_loading(), sugg=sugg)


@app.route("/admin/exports")
@login_required("admin")
def auto_reports():
    return render_template("auto_reports.html", lv=validate_loading(), ru=room_utilization(),
                           secs=sched_secs(),
                           tchs=query("SELECT * FROM users WHERE role='teacher' ORDER BY full_name"),
                           rooms_=query("SELECT * FROM rooms ORDER BY name"))


@app.route("/admin/export/<kind>.<fmt>")
@login_required("admin")
def auto_export(kind, fmt):
    if kind not in ("sections", "teachers", "rooms", "loads", "utilization") or fmt not in ("xlsx", "pdf"):
        abort(404)
    ident = request.args.get("id", type=int)
    try:
        buf = build_xlsx(kind, ident) if fmt == "xlsx" else build_pdf(kind, ident)
    except ImportError:
        flash("Exports need two extra packages. Run:  pip install openpyxl reportlab", "error")
        return redirect(url_for("auto_reports"))
    mime = ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if fmt == "xlsx" else "application/pdf")
    return send_file(buf, mimetype=mime, as_attachment=True,
                     download_name=f"{kind}{'-' + str(ident) if ident else ''}.{fmt}")



# ======================================================================================
# ADMIN MODULES: DASHBOARD, CURRICULUM MANAGEMENT, USER MANAGEMENT AND THE AUDIT TRAIL
# ======================================================================================
MIN_SQL = "((substr(end,1,2)*60+substr(end,4,2))-(substr(start,1,2)*60+substr(start,4,2)))"


def setup_status():
    """Progress of the whole scheduling process, in the same order as the main navigation."""
    cfg = get_cfg()
    tt = get_tt()
    secs = [dict(s) for s in sched_secs()]
    tchs = [dict(t) for t in query("SELECT * FROM users WHERE role='teacher' ORDER BY id")]
    lv, chk = validate_loading(), check_program()
    n_core = query("SELECT COUNT(*) AS n FROM subjects WHERE kind='core' AND COALESCE(offered,1)=1", one=True)["n"]
    n_off = query("SELECT COUNT(*) AS n FROM subjects WHERE kind='cluster' AND COALESCE(offered,1)=1", one=True)["n"]
    n_clu = query("SELECT COUNT(*) AS n FROM subjects WHERE kind='cluster'", one=True)["n"]
    rooms_n = query("SELECT COUNT(*) AS n FROM rooms", one=True)["n"]
    stale = [s for s in secs if s["id"] in stale_ids()]
    no_cluster = [s for s in secs if not s["track"] or not s["cluster"]]
    no_spec = [t for t in tchs if not (t["specialization"] or "").strip()]
    no_time = [t for t in tchs if not (t["official_time"] or "").strip()]
    with_prog = {r["section_id"] for r in query("SELECT DISTINCT section_id FROM classes WHERE kind='class'")}
    unsched = [s for s in secs if s["id"] not in with_prog]
    miss_rt = missing_room_types()
    no_subjects = [s for s in secs if not query("SELECT 1 FROM section_subjects WHERE section_id=?", (s["id"],), one=True)]
    appr = approval()
    sy_ok = bool(re.search(r"SY\s*\d{4}-\d{4}", cfg["term"] or "")) and bool(cfg["school_name"])
    tt_saved = bool(gset("tt_text", ""))
    all_sched = bool(secs) and not unsched and not stale
    all_ok = all_sched and not chk["issues"] and not lv["issues"]
    steps = [
        dict(num=1, title="Create school year", ep="settings", anchor="", done=sy_ok, text=cfg["term"] or "Not set",
             you="Inputs details", sys="Saves records"),
        dict(num=2, title="Curriculum setup", ep="curriculum", anchor="", done=n_core == len(CORE_SUBJECTS) and n_off > 0,
             text=f"{n_core} of {len(CORE_SUBJECTS)} core subjects, {n_off} of {n_clu} clusters offered",
             you="Selects subjects", sys="Validates eligibility"),
        dict(num=3, title="Section setup", ep="sections", anchor="", done=bool(secs) and not no_cluster,
             text=(f"{len(secs)} section(s)" + (f"; {len(no_cluster)} need a track and cluster" if no_cluster else "")
                   if secs else "No sections yet"), you="Encodes sections", sys="Checks duplicate records"),
        dict(num=4, title="Teacher management", ep="teachers", anchor="", done=bool(tchs) and not no_spec and not no_time,
             text=(f"{len(tchs)} teacher(s)" + (f"; {len(no_spec)} without specialization" if no_spec else "")
                   + (f"; {len(no_time)} without official time" if no_time else "") if tchs else "No teachers yet"),
             you="Encodes teacher profiles", sys="Validates information"),
        dict(num=5, title="Teacher loading", ep="auto_loading", anchor="",
             done=bool(secs) and not no_subjects and not lv["issues"] and query("SELECT 1 FROM loads", one=True) is not None,
             text=(f"{len(lv['issues'])} loading problem(s)" if lv["issues"] else
                   "Every subject has a qualified teacher" if secs else "Add sections first"),
             you="Assigns subjects and loads", sys="Calculates and checks loads"),
        dict(num=6, title="Room management", ep="auto_rooms", anchor="", done=rooms_n > 0 and not miss_rt,
             text=(f"{rooms_n} room(s)" + (f"; no room for: {', '.join(miss_rt)}" if miss_rt else "")),
             you="Registers rooms", sys="Checks availability"),
        dict(num=7, title="Timetable setup", ep="settings", anchor="#timetable", done=tt_saved,
             text=f"{len(tt)} shift(s): {', '.join(sorted(tt))}" + ("" if tt_saved else " (standard timetable, not yet saved)"),
             you="Imports or sets the time slots (Excel)", sys="Reads and validates slots"),
        dict(num=8, title="Class program", ep="auto_generate", anchor="", done=all_sched,
             text=(f"{len(secs) - len(unsched)} of {len(secs)} sections scheduled" + (f"; {len(stale)} out of date" if stale else "")),
             you="Starts generation and reviews results", sys="Generates schedules"),
        dict(num=9, title="Conflict resolution", ep="auto_conflicts", anchor="", done=all_ok,
             text=(f"{len(chk['issues'])} schedule conflict(s)" if chk["issues"] else
                   "No conflicts found" if chk["rows"] else "Nothing to check yet"),
             you="Reviews and approves corrections", sys="Detects conflicts and suggests alternatives"),
        dict(num=10, title="Final approval", ep="auto_conflicts", anchor="#approval", done=bool(appr),
             text=(f"Approved by {appr['by']} on {appr['at']}" if appr else "Not approved yet"),
             you="Approves the schedule", sys="Locks the approved version"),
        dict(num=11, title="Reports", ep="auto_reports", anchor="", done=bool(appr),
             text="Final reports are ready" if appr else "Available as drafts until the schedule is approved",
             you="Selects a report", sys="Generates it"),
    ]
    alerts = []

    def alert(level, text, ep, label):
        alerts.append(dict(level=level, text=text, href=url_for(ep), label=label))
    p = query("SELECT COUNT(*) AS n FROM signup_requests", one=True)["n"]
    if p:
        alert("warn", f"{p} teacher account request(s) are waiting for approval.", "reports", "Review")
    p = query("SELECT COUNT(*) AS n FROM reset_requests", one=True)["n"]
    if p:
        alert("warn", f"{p} password reset request(s) are waiting.", "reports", "Review")
    p = query("SELECT COUNT(*) AS n FROM reports WHERE resolved=0", one=True)["n"]
    if p:
        alert("warn", f"{p} problem report(s) are not resolved yet.", "reports", "Open")
    if no_cluster:
        alert("bad", "Set a track and cluster for: " + ", ".join(s["name"] for s in no_cluster[:6])
              + ("..." if len(no_cluster) > 6 else "") + ".", "sections", "Fix")
    if no_spec:
        alert("warn", f"{len(no_spec)} teacher(s) have no specialization, so they cannot be loaded automatically.",
              "teachers", "Fix")
    if no_time:
        alert("warn", f"{len(no_time)} teacher(s) have no official time; the whole day is assumed.", "teachers", "Fix")
    if miss_rt:
        alert("bad", "No room is registered for: " + ", ".join(miss_rt) + ".", "auto_rooms", "Add rooms")
    for i in lv["issues"][:4]:
        alert("bad", i, "auto_loading", "Fix")
    if len(lv["issues"]) > 4:
        alert("bad", f"...and {len(lv['issues']) - 4} more loading problem(s).", "auto_loading", "See all")
    if stale:
        alert("warn", "Loading changed after the program was made for: " + ", ".join(s["name"] for s in stale[:6]) + ".",
              "auto_generate", "Regenerate")
    if secs and unsched:
        alert("warn", f"{len(unsched)} section(s) have no class program yet.", "auto_generate", "Generate")
    for i in chk["issues"][:4]:
        alert("bad", i, "auto_conflicts", "Fix")
    if len(chk["issues"]) > 4:
        alert("bad", f"...and {len(chk['issues']) - 4} more schedule problem(s).", "auto_conflicts", "See all")
    if all_ok and not appr:
        alert("warn", "Everything checks out. Approve the schedule to lock this version.", "auto_conflicts", "Approve")
    done = sum(1 for s in steps if s["done"])
    nxt = next((s for s in steps if not s["done"]), None)
    prog = []
    for s in secs:
        need = query("""SELECT COALESCE(SUM(b.weekly_min),0) AS m FROM section_subjects ss
                        JOIN subjects b ON b.id=ss.subject_id WHERE ss.section_id=?""", (s["id"],), one=True)["m"]
        got = query(f"SELECT COALESCE(SUM({MIN_SQL}),0) AS m FROM classes WHERE section_id=? AND kind='class'",
                    (s["id"],), one=True)["m"]
        nsub = query("SELECT COUNT(*) AS n FROM section_subjects WHERE section_id=?", (s["id"],), one=True)["n"]
        nload = query("""SELECT COUNT(*) AS n FROM loads l JOIN section_subjects x ON x.section_id=l.section_id
                         AND x.subject_id=l.subject_id WHERE l.section_id=? AND l.teacher_id IS NOT NULL""",
                      (s["id"],), one=True)["n"]
        prog.append(dict(s=s, need=need, got=got, nsub=nsub, nload=nload,
                         pct=min(100, int(100 * got / need)) if need else 0))
    kpis = dict(sections=len(secs), teachers=len(tchs), rooms=rooms_n, subjects=n_core + n_off,
                periods=chk["rows"], conflicts=len(chk["issues"]))
    return dict(steps=steps, alerts=alerts, done=done, total=len(steps), pct=int(100 * done / len(steps)),
                nxt=nxt, prog=prog, kpis=kpis)


@app.route("/admin/dashboard")
@login_required("admin")
def dashboard():
    return render_template("dashboard.html", st=setup_status(), today=today_text())


# ---------------------------------------------------------------- curriculum
@app.route("/admin/curriculum", methods=["GET", "POST"])
@login_required("admin")
def curriculum():
    """03 Curriculum Management: the fixed Strengthened Curriculum. Names cannot be changed;
    the school sets what it offers and the time and room each subject needs."""
    if request.method == "POST":
        f = request.form
        if f.get("action") == "reset":
            for _c, name, _a, _g, _t, wk, se, rt, _k, _d in curriculum_rows():
                run("UPDATE subjects SET weekly_min=?, session_min=?, rtype=? WHERE lower(name)=lower(?)",
                    (wk, se, rt, name))
            flash("Minutes and room types were set back to the starting values.", "ok")
            return redirect(url_for("curriculum"))
        bad, blocked, changed = 0, [], set()
        for s in query("SELECT * FROM subjects"):
            i = s["id"]
            if f"wk_{i}" not in f:
                continue
            wk, se = to_int(f.get(f"wk_{i}"), 30, 2400), to_int(f.get(f"se_{i}"), 10, 480)
            if wk is None or se is None:
                bad += 1
                continue
            rt = clean(f.get(f"rtype_{i}")) or "Regular"
            off = 1 if (s["kind"] or "") == "core" or f.get(f"off_{i}") else 0
            if not off and (s["kind"] or "") == "cluster":
                users_ = [x["name"] for x in query("SELECT name FROM sections WHERE cluster=?", (s["name"],))]
                if users_:
                    blocked.append(f"{s['name']} (used by {', '.join(users_[:3])}{'...' if len(users_) > 3 else ''})")
                    off = 1
            old = (s["weekly_min"], s["session_min"], s["rtype"], 1 if s["offered"] is None else s["offered"])
            if old != (wk, se, rt, off):
                changed.add(i)
            run("UPDATE subjects SET weekly_min=?, session_min=?, rtype=?, offered=? WHERE id=?", (wk, se, rt, off, i))
        for i in changed:
            for r in query("SELECT DISTINCT section_id FROM section_subjects WHERE subject_id=?", (i,)):
                if query("SELECT 1 FROM classes WHERE section_id=? AND kind='class'", (r["section_id"],), one=True):
                    mark_stale([r["section_id"]])
        ensure_room_types()
        if bad:
            flash(f"{bad} subject(s) had invalid minutes (30-2400 per week, 10-480 per meeting) and were skipped.", "error")
        if blocked:
            flash("Kept turned on because sections use them: " + "; ".join(blocked) + ". Change those sections first.", "error")
        if not bad and not blocked:
            flash("Curriculum saved." + (" Programs of sections that use changed subjects are marked out of date."
                                         if changed else ""), "ok")
        return redirect(url_for("curriculum"))
    subs = [dict(s) for s in query("SELECT * FROM subjects ORDER BY id")]
    used = {r["subject_id"]: r["n"] for r in query(
        "SELECT subject_id, COUNT(*) AS n FROM section_subjects GROUP BY subject_id")}
    for s in subs:
        s["used"] = used.get(s["id"], 0)
        s["offered"] = 1 if s["offered"] is None else s["offered"]
    return render_template("curriculum.html", core=[s for s in subs if s["kind"] == "core"],
                           academic=[s for s in subs if s["kind"] == "cluster" and s["track"] == "Academic"],
                           techpro=[s for s in subs if s["kind"] == "cluster" and s["track"] == "TechPro"],
                           rtypes=rtype_options())



# ---------------------------------------------------------------- final approval (lock)
def approval():
    at = gset("approved_at", "")
    return dict(at=at, by=gset("approved_by", ""), periods=gset("approved_periods", "0")) if at else None


LOCKED_EP = {"entry_add", "entry_edit", "entry_delete", "auto_loading", "auto_quals", "section_edit",
             "section_delete", "teacher_delete", "curriculum", "auto_rooms"}
LOCKED_ACT = {"auto_generate": {"generate", "apply", "regen", "quick"}, "auto_conflicts": {"move"},
              "settings": {"timetable", "import_tt", "reset_tt", "g12_toggle"},
              "quick_input": {"add_sections", "add_teachers", "save_teachers", "add_mid", "run"}}


@app.before_request
def lock_guard():
    """Once the administrator approves the schedule, anything that could change it is refused."""
    if request.method != "POST" or not g.get("user") or g.user["role"] != "admin":
        return None
    ep, act = request.endpoint, request.form.get("action")
    if ep in LOCKED_EP or act in LOCKED_ACT.get(ep, ()):
        if approval():
            flash("The schedule is approved and locked. Reopen it in Validation Center (Final approval) to make changes.", "error")
            return redirect(request.referrer or url_for("dashboard"))
    return None


def parse_time_cell(v):
    import datetime
    if isinstance(v, (datetime.datetime, datetime.time)):
        return v.hour * 60 + v.minute
    if isinstance(v, (int, float)) and 0 <= v < 1:
        return int(round(v * 1440))
    m = re.match(r"^(\d{1,2}):(\d{2})(?::\d{2})?\s*(AM|PM)?$", str(v or "").strip(), re.I)
    if not m:
        return None
    h, mi, ap = int(m[1]), int(m[2]), (m[3] or "").upper()
    h = h + 12 if ap == "PM" and h < 12 else (0 if ap == "AM" and h == 12 else h)
    return h * 60 + mi if h < 24 and mi < 60 else None


def read_tt_excel(fileobj):
    """Rows of: Shift | Start | End | Type (class or recess). A header row is skipped."""
    from openpyxl import load_workbook
    ws = load_workbook(fileobj, data_only=True).active
    lines, errs = [], []
    for i, row in enumerate(ws.iter_rows(values_only=True), 1):
        row = list(row) + [None] * 4
        if all(c is None or str(c).strip() == "" for c in row[:4]):
            continue
        s, e = parse_time_cell(row[1]), parse_time_cell(row[2])
        name = re.sub(r"\s+", "", str(row[0] or "")).upper()
        if s is None or e is None:
            if i > 1:
                errs.append(f"Row {i}: the start or end time is not a time like 06:00 or 6:00 AM.")
            continue
        if not name:
            errs.append(f"Row {i}: the shift name (for example AM or PM) is missing.")
        elif e <= s:
            errs.append(f"Row {i}: the end time must be later than the start time.")
        else:
            kind = str(row[3] or "").strip().lower()
            lines.append(f"{name} {hhmm(s)}-{hhmm(e)}" + (" recess" if kind in ("recess", "break") else ""))
    return "\n".join(lines) + "\n", errs


@app.route("/admin/timetable-template.xlsx")
@login_required("admin")
def tt_template():
    try:
        from openpyxl import Workbook
    except ImportError:
        flash("Excel needs a package. Run:  pip install openpyxl", "error")
        return redirect(url_for("settings"))
    wb = Workbook()
    ws = wb.active
    ws.title = "Time slots"
    ws.append(["Shift", "Start", "End", "Type"])
    for name, per in get_tt().items():
        for s, e, k in per:
            ws.append([name, hhmm(s), hhmm(e), "recess" if k == "recess" else "class"])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="timetable-template.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")



# ---------------------------------------------------------------- quick input (the blackboard process)
def unique_username(name):
    base = re.sub(r"[^a-z0-9]", "", name.lower())[:20] or "teacher"
    u, n = base, 1
    while query("SELECT 1 FROM users WHERE lower(username)=lower(?)", (u,), one=True) or \
            query("SELECT 1 FROM signup_requests WHERE lower(username)=lower(?)", (u,), one=True):
        n += 1
        u = f"{base}{n}"
    return u


@app.route("/admin/quick-input", methods=["GET", "POST"])
@login_required("admin")
def quick_input():
    """Input: number of sections and their names, each teacher's loading (subjects to teach) and class hours
    (AM / MID / PM). The system then distributes the teachers and makes every class program."""
    tt = get_tt()
    if request.method == "POST":
        f = request.form
        act = f.get("action")
        if act == "add_mid":
            sset("tt_text", (gset("tt_text", "") or DEFAULT_TT).rstrip("\n") + "\n" + "\n".join(
                l for l in DEFAULT_TT.splitlines() if l.startswith("MID ")) + "\n")
            flash("The MID shift was added to the timetable.", "ok")
        elif act == "add_sections":
            grade = f.get("grade", type=int)
            names = [full_section(grade, n) for n in f.get("names", "").splitlines() if short_section(n)]
            sh = f.get("shift", "").upper()
            extra, err = section_fields({"track": "", "cluster": f.get("cluster", ""), "shift": sh, "grade": grade})
            if grade not in (11, 12) or not names:
                flash("Choose the grade level and type at least one section name (one per line).", "error")
            elif err:
                flash(err, "error")
            else:
                made, dup = 0, []
                for nm in dict.fromkeys(names):
                    try:
                        conn = db()
                        cur = conn.execute("INSERT INTO sections(name,grade,track,cluster,shift,room) VALUES(?,?,?,?,?,?)",
                                           (nm, grade, extra["track"], extra["cluster"], extra["shift"], ""))
                        conn.commit()
                        sync_section_subjects(cur.lastrowid)
                        made += 1
                    except sqlite3.IntegrityError:
                        dup.append(nm)
                flash(f"{made} section(s) added" + (f". Already existed: {', '.join(dup)}." if dup else "."),
                      "ok" if made else "error")
        elif act == "add_teachers":
            names = [clean(n) for n in f.get("names", "").splitlines() if clean(n)]
            cat, sh = f.get("category", "G11"), f.get("shift", "").upper()
            spec = clean(f.get("spec_new"), 800)
            if not names or cat not in CATS:
                flash("Type at least one teacher name (one per line).", "error")
            else:
                made = 0
                for nm in dict.fromkeys(names):
                    tid = next_teacher_id()
                    run("""INSERT INTO users(teacher_id,username,full_name,role,category,password_hash,specialization,
                                             official_time,intervention_min,ancillary_min)
                           VALUES(?,?,?,?,?,?,?,?,0,0)""",
                        (tid, unique_username(nm), nm, "teacher", cat, generate_password_hash(TEMP_PASSWORD), spec,
                         shift_hours(tt, sh) if sh in tt else ""))
                    made += 1
                match_quals()
                flash(f"{made} teacher(s) added. Their temporary password is {TEMP_PASSWORD}.", "ok")
        elif act == "save_teachers":
            n = 0
            for t in query("SELECT * FROM users WHERE role='teacher'"):
                i = t["id"]
                if f"spec_{i}" not in f:
                    continue
                spec, sh = clean(f.get(f"spec_{i}"), 800), f.get(f"shift_{i}", "").upper()
                ot = shift_hours(tt, sh) if sh in tt else (t["official_time"] or "")
                if spec != (t["specialization"] or "") or ot != (t["official_time"] or ""):
                    run("UPDATE users SET specialization=?, official_time=? WHERE id=?", (spec, ot, i))
                    touch("teacher", i)
                    if spec != (t["specialization"] or ""):
                        match_quals(i)
                    n += 1
            flash(f"{n} teacher(s) updated." if n else "Nothing changed.", "ok")
        elif act == "run":
            flash(run_everything(), "ok")
        return redirect(url_for("quick_input") + ("#result" if act == "run" else ""))
    secs = sched_secs()
    teachers_ = query("SELECT * FROM users WHERE role='teacher' ORDER BY id")
    offered = section_form_data()["offered_clusters"]
    return render_template("quick_input.html", shifts=sorted(tt, key=lambda k: tt[k][0][0]), tt_has_mid="MID" in tt,
                           all_secs=query("SELECT * FROM sections ORDER BY grade, name"), n_sched=len(secs),
                           teachers=teachers_, tshift={t["id"]: teacher_shift(t, tt) for t in teachers_},
                           offered_clusters=offered, g12_on=g12_programs(), approved=approval(),
                           hours={k: shift_hours(tt, k) for k in tt})


def run_everything():
    """Assign teachers to every subject, then generate all class programs without conflicts."""
    secs = sched_secs()
    if not secs:
        return "Add at least one section first."
    ensure_room_types()
    q = match_quals()
    a, gv, left = autofill()
    ids = [s["id"] for s in secs]
    res = solve(ids, tries=60)
    apply_draft(res)
    clear_stale(res["sections"])
    sset("gen_draft", "")
    chk, lv = check_program(), validate_loading()
    msg = (f"Done. {gv} teacher assignment(s) made, {len(res['sessions'])} class periods placed in {len(ids)} section(s). ")
    if res["unplaced"] or left or chk["issues"] or lv["issues"]:
        bits = []
        if left:
            bits.append(f"{left} subject(s) have no qualified teacher with enough time in that shift")
        if res["unplaced"]:
            bits.append(f"{len(res['unplaced'])} subject(s) could not be fully scheduled")
        if chk["issues"]:
            bits.append(f"{len(chk['issues'])} schedule conflict(s)")
        if lv["issues"]:
            bits.append(f"{len(lv['issues'])} loading problem(s)")
        return msg + "Needs attention: " + "; ".join(bits) + ". Open the Validation Center to see each one."
    return msg + "No overlapping times and no conflicts were found."


# ---------------------------------------------------------------- audit trail
AUDIT_LABELS = {
    "settings": {"timetable": "Changed the timetable, shifts and scheduling rules", "import_tt": "Imported the timetable from Excel", "g12_toggle": "Switched Grade 12 class programs", "reset_tt": "Reset the timetable",
                 None: "Saved school details"},
    "logo_upload": "Uploaded a school logo", "logo_remove": "Went back to the default school logo",
    "curriculum": {"reset": "Reset curriculum minutes to the starting values", None: "Saved curriculum offerings and time"},
    "sections": "Added a section", "section_edit": "Edited a section", "section_delete": "Deleted a section",
    "teachers": "Created a teacher account", "teacher_edit": "Edited a teacher", "teacher_delete": "Deleted a teacher account",
    "assignments": "Saved teacher details", "teacher_minutes": "Changed a teacher's time",
    "auto_rooms": {"starter": "Loaded starter rooms", "add": "Added a room", None: "Saved rooms"},
    "auto_quals": {"match": "Matched qualifications from specializations", None: "Saved teacher qualifications"},
    "auto_loading": {"autofill": "Auto-filled teacher loading", None: "Saved teacher loading of a section"},
    "quick_input": {"add_sections": "Added sections (Quick Input)", "add_teachers": "Added teachers (Quick Input)",
                    "save_teachers": "Saved teacher loading and class hours", "add_mid": "Added the MID shift",
                    "run": "Assigned teachers and generated all class programs"},
    "auto_conflicts": {"approve": "Approved and locked the schedule", "reopen": "Reopened the approved schedule",
                       "move": "Moved a class period to fix a conflict"},
    "auto_generate": {"quick": "Ran quick setup", "regen": "Regenerated out-of-date sections", "generate": "Generated a draft class program",
                      "apply": "Applied the draft to the class programs", "discard": "Discarded the draft",
                      None: "Used the schedule generator"},
    "entry_add": "Added a class period", "entry_edit": "Edited a class period", "entry_delete": "Deleted a class period",
    "signup_requests": {"reject": "Rejected an account request", "reset_done": "Reset a teacher's password",
                        "reset_cancel": "Dismissed a password reset request", None: "Approved a teacher account request"},
    "reports": {"resolve": "Changed a problem report's status", "delete": "Deleted a problem report",
                "clear": "Cleared resolved problem reports", None: "Updated problem reports"},
    "users": {"add_admin": "Created an administrator account", "reset_pw": "Reset an account password",
              "delete_admin": "Deleted an administrator account", None: "Changed an account"},
    "account_settings": "Changed own account settings",
}
AUDIT_DETAIL_KEYS = ("name", "full_name", "username", "school_name", "term", "grade", "track", "cluster", "room")


def audit_event(user, action, detail=""):
    """Write one line of the audit trail. Passwords and other secrets are never recorded."""
    try:
        conn = db()
        conn.execute("INSERT INTO audit_log(at,user_id,who,role,action,detail,ip) VALUES(?,?,?,?,?,?,?)",
                     (ph_stamp(), user["id"] if user else None, user["full_name"] if user else "Not signed in",
                      user["role"] if user else "", action[:120], (detail or "")[:300], (request.remote_addr or "")[:45]))
        conn.commit()
    except Exception:
        pass


@app.after_request
def audit_trail(resp):
    try:
        if (request.method == "POST" and g.get("user") and resp.status_code < 400
                and request.endpoint in AUDIT_LABELS):
            label = AUDIT_LABELS[request.endpoint]
            if isinstance(label, dict):
                label = label.get(request.form.get("action")) or label.get(None)
            if label:
                failed = any(c == "error" for c, _m in (session.get("_flashes") or []))
                bits = [f"{k}={v}" for k, v in (request.view_args or {}).items()]
                bits += [f"{k}: {request.form.get(k)[:60]}" for k in AUDIT_DETAIL_KEYS if request.form.get(k)]
                audit_event(g.user, label + (" (not completed)" if failed else ""), "; ".join(bits))
    except Exception:
        pass
    return resp


# ---------------------------------------------------------------- user management
def next_admin_id():
    n = 0
    for r in query("SELECT teacher_id FROM users WHERE role='admin'"):
        m = re.search(r"(\d+)$", r["teacher_id"] or "")
        n = max(n, int(m.group(1)) if m else 0)
    return f"ADMIN-{n + 1:03d}"


@app.route("/admin/users", methods=["GET", "POST"])
@login_required("admin")
def users():
    """11 User Management: every account, what its role may do, and a way to add or reset them."""
    if request.method == "POST":
        f = request.form
        act = f.get("action")
        uid = f.get("uid", type=int)
        target = query("SELECT * FROM users WHERE id=?", (uid,), one=True) if uid else None
        if act == "add_admin":
            name, user, pw = clean(f.get("full_name")), clean(f.get("username"), 40), f.get("password", "")
            if not name or not user or len(pw) < 6:
                flash("Enter a name, a username and a password of at least 6 characters.", "error")
            elif query("SELECT 1 FROM users WHERE lower(username)=lower(?)", (user,), one=True):
                flash("That username is already in use.", "error")
            else:
                run("""INSERT INTO users(teacher_id,username,full_name,role,category,password_hash,
                                         intervention_min,ancillary_min) VALUES(?,?,?,?,?,?,0,0)""",
                    (next_admin_id(), user, name, "admin", None, generate_password_hash(pw)))
                flash(f"Administrator account created for {name}.", "ok")
        elif act == "reset_pw" and target:
            if target["id"] == g.user["id"]:
                flash("Change your own password in Settings.", "error")
            else:
                run("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(TEMP_PASSWORD), target["id"]))
                if target["role"] == "teacher":
                    notify(target["id"], "reset", f"Your password was reset by the administrator. Temporary password: "
                           f"{TEMP_PASSWORD} - please sign in and change it in Settings.", url_for("account_settings"))
                flash(f"{target['full_name']}'s password is now the temporary password {TEMP_PASSWORD}.", "ok")
        elif act == "delete_admin" and target and target["role"] == "admin":
            if target["id"] == g.user["id"]:
                flash("You cannot delete the account you are signed in with.", "error")
            elif query("SELECT COUNT(*) AS n FROM users WHERE role='admin'", one=True)["n"] < 2:
                flash("The last administrator account cannot be deleted.", "error")
            else:
                run("DELETE FROM users WHERE id=?", (target["id"],))
                flash("Administrator account deleted.", "ok")
        return redirect(url_for("users"))
    rows = query("SELECT * FROM users ORDER BY role, id")
    return render_template("users.html", rows=rows, admins=sum(1 for r in rows if r["role"] == "admin"),
                           teachers_n=sum(1 for r in rows if r["role"] == "teacher"), temp=TEMP_PASSWORD,
                           pending=query("SELECT COUNT(*) AS n FROM signup_requests", one=True)["n"])


ROLE_RIGHTS = [  # what each role can do, as the program enforces it
    ("Administrator", "ADMIN", [
        "Sees every module in the main navigation.",
        "Sets up the school, the offered curriculum, sections, teachers, rooms and teacher loading.",
        "Generates, edits and validates class programs, and prints or downloads every report.",
        "Approves account requests, resets passwords and reads problem reports.",
        "Is the only role that can change a schedule."]),
    ("Grade 11 Teacher", "G11", [
        "Opens own Teacher's Program and the Grade 11 class programs the teacher is assigned to.",
        "Receives a notification when the administrator changes the program or assigns a section.",
        "Changes own password in Settings; can report a problem."]),
    ("Grade 12 Teacher", "G12", ["Same as a Grade 11 Teacher, for the Grade 12 class programs."]),
    ("MID Teacher", "MID", [
        "Same as a Grade 11 or Grade 12 Teacher, for both grade levels.",
        "A teacher becomes MID automatically when assigned in both grade levels, and goes back when only one remains."]),
]


@app.route("/admin/users/roles")
@login_required("admin")
def user_roles():
    counts = {r["category"] or "ADMIN": r["n"] for r in query(
        "SELECT category, COUNT(*) AS n FROM users GROUP BY category")}
    counts["ADMIN"] = query("SELECT COUNT(*) AS n FROM users WHERE role='admin'", one=True)["n"]
    return render_template("user_roles.html", roles=ROLE_RIGHTS, counts=counts)


@app.route("/admin/users/audit")
@login_required("admin")
def user_audit():
    q = request.args.get("q", "").strip()[:60]
    who = request.args.get("who", "")
    sql, args = "SELECT * FROM audit_log WHERE 1=1", []
    if who in ("admin", "teacher", ""):
        if who:
            sql += " AND role=?"
            args.append(who)
    if q:
        sql += " AND (lower(who) LIKE ? OR lower(action) LIKE ? OR lower(detail) LIKE ?)"
        args += [f"%{q.lower()}%"] * 3
    rows = query(sql + " ORDER BY id DESC LIMIT 300", args)
    total = query("SELECT COUNT(*) AS n FROM audit_log", one=True)["n"]
    return render_template("user_audit.html", rows=rows, q=q, who=who, total=total)


NEW_TEMPLATES = {
"auto_time.html": """{% extends "base.html" %}{% block title %}Time allocation{% endblock %}
{% block content %}<h1>Validation Center</h1>{{ subnav('validation') }}
<details class="tip noprint"><summary>About this page</summary><p>How the configured timetable matches each subject, section and teacher. Everything here is calculated from the timetable, subject minutes and loading.</p></details>
{% set bad_subs = ta.subs|selectattr('bad')|list %}{% set over_secs = ta.secs|selectattr('pct', 'gt', 100)|list %}{% set over_t = ta.tch|selectattr('pct', 'gt', 100)|list %}
{% if not bad_subs and not over_secs and not over_t %}<div class="msg ok fitnote"><b>Everything fits.</b> Every subject has matching class periods in {{ ta.shifts|map(attribute='name')|join(', ') }}, and no section or teacher has more hours than the timetable holds.</div>
{% else %}<div class="msg error fitnote"><b>Some things do not fit:</b><ul class="issues">{% for x in bad_subs %}<li>{{ x.s.name }} has no matching run of periods in {{ x.bad|join(', ') }}. Change its minutes in Curriculum Management or the periods in School Setup.</li>{% endfor %}{% for x in over_secs %}<li>{{ x.sec.name }} needs {{ x.need|hrs }} but the {{ x.shift }} shift has only {{ x.cap|hrs }}.</li>{% endfor %}{% for x in over_t %}<li>{{ x.t.full_name }} is given {{ x.need|hrs }} but is available {{ x.cap|hrs }}.</li>{% endfor %}</ul></div>{% endif %}
<details class="card"><summary><b>Show the shifts and periods</b></summary><h3 style="margin-top:.8rem">Configured shifts and class periods</h3><div class="scroll"><table class="list"><thead><tr><th>Shift</th><th>Runs</th><th>Class time per day</th><th>Per week</th><th>Periods</th></tr></thead><tbody>
{% for s in ta.shifts %}<tr><td><b>{{ s.name }}</b></td><td>{{ s.start|t12 }} to {{ s.end|t12 }}</td><td>{{ s.day|hrs }}</td><td>{{ s.week|hrs }}</td><td>{% for a, b, k in s.periods %}<span class="pill">{{ a|t12 }}-{{ b|t12 }}{{ ' (recess)' if k == 'recess' }}</span> {% endfor %}</td></tr>{% endfor %}</tbody></table></div></div>
</details><details class="card"><summary><b>Show the weekly time of each subject</b></summary><h3 style="margin-top:.8rem">Required weekly time and matching periods</h3><div class="scroll"><table class="list"><thead><tr><th>Subject</th><th>Required per week</th><th>Meetings</th>{% for s in ta.shifts %}<th>Free periods per day: {{ s.name }}</th>{% endfor %}</tr></thead><tbody>
{% for x in ta.subs %}<tr><td>{{ x.s.name }}<p class="hint">{{ x.s.rtype }}</p></td><td>{{ x.s.weekly_min|hrs }}</td><td>{{ x.n }} x {{ x.lens|join(' / ') }} min</td>
{% for sh in ta.shifts %}<td class="{{ 'why' if sh.name in x.bad }}">{% for L, n in x.blocks[sh.name].items() %}{{ n }} slot{{ '' if n == 1 else 's' }} of {{ L }} min{% if not loop.last %}<br>{% endif %}{% endfor %}{% if sh.name in x.bad %}<br><b>No matching run of periods</b>{% endif %}</td>{% endfor %}</tr>
{% else %}<tr><td colspan="{{ 3 + ta.shifts|length }}" class="empty">No subjects yet.</td></tr>{% endfor %}</tbody></table></div></div>
</details><details class="card"><summary><b>Show the time of each section</b></summary><h3 style="margin-top:.8rem">Section time needed vs available</h3><div class="scroll"><table class="list"><thead><tr><th>Section</th><th>Shift</th><th>Needed</th><th>Available</th><th>Filled</th></tr></thead><tbody>
{% for x in ta.secs %}<tr><td>{{ x.sec.name }}</td><td>{{ x.shift }}</td><td>{{ x.need|hrs }}</td><td>{{ x.cap|hrs }}</td><td class="{{ 'why' if x.pct > 100 }}"><div class="bar"><i style="width:{{ [100, x.pct]|min }}%"></i></div>{{ x.pct }}%{{ ' - more than the timetable holds' if x.pct > 100 }}</td></tr>{% endfor %}</tbody></table></div></div>
</details><details class="card"><summary><b>Show the time of each teacher</b></summary><h3 style="margin-top:.8rem">Teacher time needed vs available (inside official time)</h3><div class="scroll"><table class="list"><thead><tr><th>Teacher</th><th>Official time</th><th>Assigned</th><th>Available</th><th>Filled</th></tr></thead><tbody>
{% for x in ta.tch %}<tr><td>{{ x.t.full_name }}</td><td>{{ x.window }}</td><td>{{ x.need|hrs }}</td><td>{{ x.cap|hrs }}</td><td class="{{ 'why' if x.pct > 100 }}"><div class="bar"><i style="width:{{ [100, x.pct]|min }}%"></i></div>{{ x.pct }}%</td></tr>{% endfor %}</tbody></table></div></div>
</details><div class="card"><h3>Find available time slots</h3><form method="get"><div class="formgrid">
<div><label for="find">For</label><select id="find" name="find"><optgroup label="Section">{% for s in secs %}<option value="section:{{ s.id }}" {{ 'selected' if q == 'section:' ~ s.id }}>{{ s.name }}</option>{% endfor %}</optgroup><optgroup label="Teacher">{% for t in tchs %}<option value="teacher:{{ t.id }}" {{ 'selected' if q == 'teacher:' ~ t.id }}>{{ t.full_name }}</option>{% endfor %}</optgroup><optgroup label="Room">{% for r in rooms_ %}<option value="room:{{ r.id }}" {{ 'selected' if q == 'room:' ~ r.id }}>{{ r.name }}</option>{% endfor %}</optgroup></select></div>
<div><label for="length">Class length (minutes)</label><input id="length" name="length" type="number" min="10" max="480" value="{{ L }}"></div>
<div><button type="submit" style="margin-top:.7rem">Show free slots</button></div></div></form>
{% if res %}<div class="scroll" style="margin-top:.8rem"><table class="list"><thead><tr><th>Day</th><th>Free {{ res.L }}-minute slots</th></tr></thead><tbody>{% for d in days %}<tr><td>{{ d }}</td><td>{% for s, e in res.free[d] %}<span class="pill">{{ ('%02d:%02d'|format(s // 60, s % 60))|t12 }}-{{ ('%02d:%02d'|format(e // 60, e % 60))|t12 }}</span> {% else %}<span class="hint">None</span>{% endfor %}</td></tr>{% endfor %}</tbody></table></div>{% endif %}</div>{% endblock %}""",

"auto_conflicts.html": """{% extends "base.html" %}{% block title %}Conflicts{% endblock %}
{% block content %}<h1>Validation Center</h1>{{ subnav('validation') }}
<div class="card" id="approval"><h3>Final approval</h3>{% if approval %}<p class="okt"><b>Approved and locked</b> by {{ approval.by }} on {{ approval.at|stamp12 }} ({{ approval.periods }} periods). Generating, editing periods, loading, rooms, curriculum and section changes are blocked.</p>
<form method="post" onsubmit="return confirm('Reopen the schedule? It will no longer be locked.')">{{ csrf_field() }}<input type="hidden" name="action" value="reopen"><button class="danger" type="submit">Reopen for corrections</button></form>
{% else %}<p>When there are no conflicts and the loading is complete, approve the schedule. Approving locks this version so nothing changes by accident.</p>
<form method="post" onsubmit="return confirm('Approve and lock this schedule?')">{{ csrf_field() }}<input type="hidden" name="action" value="approve"><button type="submit" {{ 'disabled' if chk.issues or lv.issues or not chk.rows }}>Approve schedule</button>{% if chk.issues or lv.issues or not chk.rows %} <span class="hint">{{ 'Nothing to approve yet.' if not chk.rows else 'Fix the problems below first.' }}</span>{% endif %}</form>{% endif %}</div>
<details class="tip noprint"><summary>About this page</summary><p>Checked automatically from every period stored in the class programs ({{ chk.rows }} periods) and from the teacher loading.</p></details>
<div class="kpis"><div class="kpi {{ 'bad' if chk.issues else 'ok' }}"><b>{{ chk.issues|length }}</b><span>schedule problems</span></div><div class="kpi"><b>{{ chk.warns|length }}</b><span>schedule warnings</span></div><div class="kpi {{ 'bad' if lv.issues else 'ok' }}"><b>{{ lv.issues|length }}</b><span>loading problems</span></div></div>
<div class="card"><h3>Class program problems</h3>{% if chk.entries|selectattr('sev', 'equalto', 'issue')|list %}<div class="scroll"><table class="list"><thead><tr><th>Type</th><th>Details</th><th>Suggested fixes</th></tr></thead><tbody>
{% for x in chk.entries if x.sev == 'issue' %}<tr><td><span class="pill">{{ {'teacher':'Teacher clash','section':'Section clash','room':'Room clash','room-shift':'Room clash AM/PM','hours':'Incomplete hours','window':'Outside availability','shift':'Outside shift','roomtype':'Room type'}.get(x.kind, x.kind) }}</span></td><td class="why">{{ x.text }}</td><td>{% set sg = sugg.get(x.pid) %}{% if sg %}{% for o in sg.slots %}<form method="post" style="display:inline-block;margin:0 .3rem .3rem 0">{{ csrf_field() }}<input type="hidden" name="action" value="move"><input type="hidden" name="period" value="{{ sg.p.id }}"><input type="hidden" name="day" value="{{ o.day }}"><input type="hidden" name="start" value="{{ o.start }}"><input type="hidden" name="end" value="{{ o.end }}"><input type="hidden" name="room_id" value="{{ o.room.id if o.room else '' }}"><button class="plain small" type="submit">Move to {{ o.day[:3] }} {{ o.start|t12 }}</button></form>{% else %}<span class="hint">No free slot found.</span> {% endfor %}{% endif %}{% if x.pid %}<a class="btn plain small" href="{{ url_for('entry_edit', eid=x.pid) }}">Edit by hand</a>{% else %}<a class="btn plain small" href="{{ url_for('auto_generate') }}">Regenerate</a>{% endif %}</td></tr>{% endfor %}</tbody></table></div>
{% else %}<p class="okt"><b>No double-booked teachers, sections or rooms (including AM/PM sharing), nobody outside their availability, and all required hours are met.</b></p>{% endif %}</div>
{% if chk.warns %}<div class="card"><h3>Warnings</h3><ul class="issues">{% for w in chk.warns %}<li>{{ w }}</li>{% endfor %}</ul></div>{% endif %}
<div class="card"><h3>Teacher loading validation</h3>{% if lv.issues %}<ul class="issues">{% for w in lv.issues %}<li class="why">{{ w }}</li>{% endfor %}</ul>{% else %}<p class="okt"><b>Teacher loading is complete and within limits.</b></p>{% endif %}
{% if lv.warns %}<h3>Loading warnings</h3><ul class="issues">{% for w in lv.warns %}<li>{{ w }}</li>{% endfor %}</ul>{% endif %}</div>{% endblock %}""",

"auto_reports.html": """{% extends "base.html" %}{% block title %}Reports{% endblock %}
{% block content %}<h1>Reports and Printing</h1>{{ subnav('reports') }}
{% if not approval %}<div class="msg notice"><strong>Draft.</strong> The schedule has not been approved yet, so these reports are drafts. Approve it in Validation Center for the final version.</div>{% endif %}
<div class="card"><h3>Download</h3><div class="scroll"><table class="list"><thead><tr><th>Report</th><th>Choose</th><th>Excel</th><th>PDF</th></tr></thead><tbody>
<tr><td>Class programs per section</td><td><select id="r_sections"><option value="">All sections</option>{% for s in secs %}<option value="{{ s.id }}">{{ s.name }}</option>{% endfor %}</select></td><td><a class="btn plain small" data-rep="sections" data-fmt="xlsx" href="#">Excel</a></td><td><a class="btn plain small" data-rep="sections" data-fmt="pdf" href="#">PDF</a></td></tr>
<tr><td>Teacher schedules</td><td><select id="r_teachers"><option value="">All teachers</option>{% for t in tchs %}<option value="{{ t.id }}">{{ t.full_name }}</option>{% endfor %}</select></td><td><a class="btn plain small" data-rep="teachers" data-fmt="xlsx" href="#">Excel</a></td><td><a class="btn plain small" data-rep="teachers" data-fmt="pdf" href="#">PDF</a></td></tr>
<tr><td>Room and laboratory programs</td><td><select id="r_rooms"><option value="">All rooms</option>{% for r in rooms_ %}<option value="{{ r.id }}">{{ r.name }}</option>{% endfor %}</select></td><td><a class="btn plain small" data-rep="rooms" data-fmt="xlsx" href="#">Excel</a></td><td><a class="btn plain small" data-rep="rooms" data-fmt="pdf" href="#">PDF</a></td></tr>
<tr><td>Room utilization report</td><td>-</td><td><a class="btn plain small" href="{{ url_for('auto_export', kind='utilization', fmt='xlsx') }}">Excel</a></td><td><a class="btn plain small" href="{{ url_for('auto_export', kind='utilization', fmt='pdf') }}">PDF</a></td></tr>
<tr><td>Teacher teaching-load summary</td><td>-</td><td><a class="btn plain small" href="{{ url_for('auto_export', kind='loads', fmt='xlsx') }}">Excel</a></td><td><a class="btn plain small" href="{{ url_for('auto_export', kind='loads', fmt='pdf') }}">PDF</a></td></tr></tbody></table></div>
<p class="hint">Excel and PDF need the packages openpyxl and reportlab (pip install openpyxl reportlab).</p></div>
<script>document.querySelectorAll('[data-rep]').forEach(function(a){a.addEventListener('click',function(e){e.preventDefault();var k=a.dataset.rep,s=document.getElementById('r_'+k).value;location.href='/admin/export/'+k+'.'+a.dataset.fmt+(s?'?id='+s:'');});});</script>
<div class="card"><h3>Teacher teaching-load summary</h3><div class="scroll"><table class="list"><thead><tr><th>Teacher</th><th>Official time</th><th>Classes handled</th><th>Assigned per week</th><th>Scheduled per week</th><th>Status</th></tr></thead><tbody>
{% for x in lv.rows %}<tr><td>{{ x.t.full_name }}</td><td>{{ x.window }}</td><td>{{ x.nsec }}</td><td>{{ x.minutes|hrs }} of {{ lv.maxweek|hrs }}</td><td>{{ x.sched|hrs }}</td><td class="{{ 'okt' if x.status == 'OK' else 'why' }}">{{ x.status }}</td></tr>{% endfor %}</tbody></table></div></div>
<div class="card"><h3>Room utilization</h3><div class="scroll"><table class="list"><thead><tr><th>Room</th><th>Type</th>{% for n in ru.order %}<th>{{ n }}</th>{% endfor %}<th>Total</th><th>Used</th><th>Shared AM/PM</th></tr></thead><tbody>
{% for x in ru.rows %}<tr><td><a href="{{ url_for('auto_room', rid=x.r.id) }}">{{ x.r.name }}</a></td><td>{{ x.r.rtype }}</td>{% for n in ru.order %}<td>{{ x.by[n]|hrs }}</td>{% endfor %}<td>{{ x.total|hrs }}</td><td><div class="bar"><i style="width:{{ [100, x.pct]|min }}%"></i></div>{{ x.pct }}%</td><td>{{ 'Yes' if x.shared else 'No' }}</td></tr>{% endfor %}</tbody></table></div></div>{% endblock %}""",
}
TEMPLATES.update(NEW_TEMPLATES)

NEW2_TEMPLATES = {
"dashboard.html": r"""{% extends "base.html" %}{% block title %}Dashboard{% endblock %}
{% block content %}<div class="head"><div><h1>Dashboard</h1><p class="hint" style="margin:0">{{ cfg.school_name }} &middot; {{ cfg.term }} &middot; {{ today }}</p></div>
<a class="btn" href="{{ url_for('quick_input') }}">Quick Input</a></div>
<div class="dash-top"><div class="card"><div class="ring"><div class="pct" style="--p:{{ st.pct }}"><span>{{ st.pct }}%</span></div>
<div><h3 style="margin:0 0 .3rem">Setup progress</h3><p style="margin:0">{{ st.done }} of {{ st.total }} steps complete.</p>
{% if st.nxt %}<p style="margin:.4rem 0 0"><b>Next:</b> <a href="{{ url_for(st.nxt.ep) }}{{ st.nxt.anchor }}">Step {{ st.nxt.num }}: {{ st.nxt.title }}</a><br><span class="hint">{{ st.nxt.text }}</span></p>{% else %}<p class="okt" style="margin:.4rem 0 0"><b>Every step is complete.</b> Print or download the reports.</p>{% endif %}</div></div></div>
<div class="card"><h3>Alerts</h3>{% if st.alerts %}<ul class="alerts">{% for a in st.alerts %}<li class="{{ a.level }}"><span class="dot"></span><span class="t">{{ a.text }}</span><a class="btn plain small" href="{{ a.href }}">{{ a.label }}</a></li>{% endfor %}</ul>{% else %}<p class="okt"><b>No alerts. Nothing needs your attention.</b></p>{% endif %}</div></div>
<div class="kpis"><div class="kpi"><b>{{ st.kpis.sections }}</b><span>sections</span></div><div class="kpi"><b>{{ st.kpis.teachers }}</b><span>teachers</span></div><div class="kpi"><b>{{ st.kpis.rooms }}</b><span>rooms and labs</span></div><div class="kpi"><b>{{ st.kpis.subjects }}</b><span>subjects and clusters offered</span></div><div class="kpi"><b>{{ st.kpis.periods }}</b><span>class periods placed</span></div><div class="kpi {{ 'bad' if st.kpis.conflicts else 'ok' }}"><b>{{ st.kpis.conflicts }}</b><span>schedule conflicts</span></div></div>
<h2>Process, in order</h2><div class="stepcards">{% for s in st.steps %}<a class="stepcard {{ 'done' if s.done else 'todo' }}" href="{{ url_for(s.ep) }}{{ s.anchor }}"><span class="st">{{ 'Done' if s.done else 'To do' }}</span><b>{{ s.num }}. {{ s.title }}</b><small>{{ s.text }}</small></a>{% endfor %}</div>
<details class="card"><summary><b>Who does what in each step</b></summary><div class="scroll"><table class="list"><thead><tr><th>Step</th><th>You</th><th>The system</th></tr></thead><tbody>{% for s in st.steps %}<tr><td>{{ s.num }}. {{ s.title }}</td><td>{{ s.you }}</td><td>{{ s.sys }}</td></tr>{% endfor %}</tbody></table></div></details>
<h2>Progress by section</h2><div class="scroll"><table class="list"><thead><tr><th>Section</th><th>Track and cluster</th><th>Teachers assigned</th><th>Scheduled</th></tr></thead><tbody>
{% for p in st.prog %}<tr><td><a href="{{ url_for('program', section=p.s.id) }}">{{ p.s.name }}</a></td><td>{{ p.s.track or 'Not set' }}{{ ' - ' ~ p.s.cluster if p.s.cluster }}</td><td class="{{ 'okt' if p.nsub and p.nload == p.nsub else 'why' }}">{{ p.nload }} of {{ p.nsub }} subjects</td><td><div class="bar"><i style="width:{{ p.pct }}%"></i></div><span class="hint">{{ p.got|hrs }} of {{ p.need|hrs }} ({{ p.pct }}%)</span></td></tr>
{% else %}<tr><td colspan="4" class="empty">No sections yet. Start with Section Management.</td></tr>{% endfor %}</tbody></table></div>{% endblock %}""",

"curriculum.html": r"""{% extends "base.html" %}{% block title %}Curriculum Management{% endblock %}
{% block content %}<h1>Curriculum Management</h1>
<div class="cur-note">The subjects and clusters are fixed. Choose which clusters you offer and set their minutes and room. Minutes are starting values; change them to your approved program.</div>
<form method="post">{{ csrf_field() }}<input type="hidden" name="action" value="save">
<div class="card"><h3>5 Core Subjects <span class="hint">(every section, both grade levels)</span></h3><div class="scroll"><table class="list"><thead><tr><th>Code</th><th>Subject</th><th>Min per week</th><th>Min per meeting</th><th>Room needed</th><th>Sections</th></tr></thead><tbody>
{% for s in core %}<tr><td>{{ s.code }}</td><td class="cur-name">{{ s.name }}</td><td><input type="number" name="wk_{{ s.id }}" value="{{ s.weekly_min }}" min="30" max="2400" aria-label="Minutes per week"></td><td><input type="number" name="se_{{ s.id }}" value="{{ s.session_min }}" min="10" max="480" aria-label="Minutes per meeting"></td><td><select name="rtype_{{ s.id }}" aria-label="Room needed">{% for r in rtypes %}<option {{ 'selected' if r == s.rtype }}>{{ r }}</option>{% endfor %}</select></td><td>{{ s.used }}</td></tr>{% endfor %}</tbody></table></div></div>
{% for title, items, note in [('Academic Track - 5 clusters', academic, ''), ('TechPro Track - 10 clusters', techpro, 'The specializations in brackets are what teachers can be qualified in.')] %}
<div class="card"><h3>{{ title }}</h3>{% if note %}<p class="hint">{{ note }}</p>{% endif %}<div class="scroll"><table class="list"><thead><tr><th>Offered</th><th>Cluster</th><th>Min per week</th><th>Min per meeting</th><th>Room needed</th><th>Sections</th></tr></thead><tbody>
{% for s in items %}<tr><td><input class="ck" type="checkbox" name="off_{{ s.id }}" value="1" {{ 'checked' if s.offered }} aria-label="Offer {{ s.name }}"></td><td><span class="cur-name">{{ s.name }}</span>{% if s.detail %}<span class="cur-spec">({{ s.detail }})</span>{% endif %}</td><td><input type="number" name="wk_{{ s.id }}" value="{{ s.weekly_min }}" min="30" max="2400" aria-label="Minutes per week"></td><td><input type="number" name="se_{{ s.id }}" value="{{ s.session_min }}" min="10" max="480" aria-label="Minutes per meeting"></td><td><select name="rtype_{{ s.id }}" aria-label="Room needed">{% for r in rtypes %}<option {{ 'selected' if r == s.rtype }}>{{ r }}</option>{% endfor %}</select></td><td>{{ s.used }}</td></tr>{% endfor %}</tbody></table></div></div>{% endfor %}
<div class="btnrow"><button type="submit">Save curriculum</button></div></form>
<form method="post" style="margin-top:1rem">{{ csrf_field() }}<input type="hidden" name="action" value="reset"><button class="plain" type="submit">Reset minutes and rooms to the starting values</button></form>{% endblock %}""",

"settings.html": r"""{% extends "base.html" %}{% block title %}School Setup{% endblock %}
{% block content %}<h1>School Setup</h1>
<details class="tip noprint"><summary>About this page</summary><p>The school year and term, the details printed on every document, and the daily timetable with its shifts. The generator reads the timetable from here.</p></details>
<div class="card"><h3>School year, term and document details</h3><form method="post">{{ csrf_field() }}<input type="hidden" name="action" value="details"><div class="formgrid">
<div><label for="school_year">School year</label><input id="school_year" name="school_year" value="{{ school_year }}" placeholder="2026-2027" pattern="[0-9]{4}-[0-9]{4}" required><p class="hint">Two consecutive years, like 2026-2027.</p></div>
<div><label for="term_name">Term</label><select id="term_name" name="term_name" required><option value="">Choose</option>{% for t in terms %}<option {{ 'selected' if t == term_name }}>{{ t }}</option>{% endfor %}</select><p class="hint">Printed as: {{ cfg.term }}</p></div>
{% for k, label in fields %}<div class="{{ 'wide' if k in ('school_name','school_address') }}"><label for="{{ k }}">{{ label }}</label><input id="{{ k }}" name="{{ k }}" value="{{ cfg[k] }}"></div>{% endfor %}
</div><p style="margin-top:1.2rem"><button type="submit">Save details</button></p></form></div>
<div class="card"><h3>School logo</h3><div class="logoedit"><img class="logoprev" src="{{ logo_url }}" alt="Current school logo"><div>
<form method="post" action="{{ url_for('logo_upload') }}" enctype="multipart/form-data">{{ csrf_field() }}<label for="logo">Replace the logo (PNG, JPG, GIF or WEBP, under 2 MB)</label><input id="logo" type="file" name="logo" accept="image/png,image/jpeg,image/gif,image/webp" required><p style="margin-top:.8rem"><button type="submit">Save logo</button></p></form>
{% if custom_logo %}<form method="post" action="{{ url_for('logo_remove') }}" onsubmit="return confirm('Go back to the default school logo?')">{{ csrf_field() }}<button class="danger">Use default logo</button></form>{% endif %}</div></div></div>
<div class="card" id="grade12"><h3>Grade 12 class programs</h3><p>Status: <b>{{ 'ON' if g12_on else 'OFF' }}</b>. {% if g12_on %}Grade 12 sections get a class program like Grade 11.{% else %}No class program is made or shown for Grade 12. Grade 12 sections, teachers and loading stay in the system.{% endif %}</p>
<form method="post" {% if g12_on %}onsubmit="return confirm('Remove all Grade 12 class periods? Sections and loading stay.')"{% endif %}>{{ csrf_field() }}<input type="hidden" name="action" value="g12_toggle"><input type="hidden" name="value" value="{{ 'off' if g12_on else 'on' }}"><button class="plain" type="submit">{{ 'Turn off and remove Grade 12 class programs' if g12_on else 'Turn on Grade 12 class programs' }}</button></form></div>
<div class="card" id="timetable"><h3>Timetable and shifts (time slots)</h3><p class="hint">Classes run Monday to Friday. Each shift has its own periods; mark breaks as recess. Sections use the shift set in Section Management (Grade 11 uses the earliest shift and Grade 12 the latest when none is set).</p>
<div class="scroll"><table class="list"><thead><tr><th>Shift</th><th>Runs</th><th>Class periods</th><th>Class time per day</th><th>Per week</th></tr></thead><tbody>{% for s in shifts %}<tr><td><b>{{ s.name }}</b></td><td>{{ s.start|t12 }} to {{ s.end|t12 }}</td><td>{{ s.n }}</td><td>{{ s.day|hrs }}</td><td>{{ s.week|hrs }}</td></tr>{% endfor %}</tbody></table></div>
<div class="cur-note"><b>Import from Excel.</b> Fill in one row per period with the columns <b>Shift, Start, End, Type</b> (Type is class or recess). <a href="{{ url_for('tt_template') }}">Download the template</a> with the current timetable already filled in.
<form method="post" enctype="multipart/form-data" style="margin-top:.5rem">{{ csrf_field() }}<input type="hidden" name="action" value="import_tt"><input type="file" name="tt_file" accept=".xlsx" required> <button type="submit" class="small" data-noconfirm>Import time slots</button></form></div>
<form method="post" id="ttform" style="margin-top:1rem">{{ csrf_field() }}<input type="hidden" name="action" value="timetable">
<div id="ttedit"></div><p><button type="button" class="plain small" id="addshift">Add a shift</button></p>
<details><summary>Edit as text</summary><textarea class="tt" id="tt_text" name="tt_text" spellcheck="false">{{ tt_text }}</textarea></details>
<h4 style="margin:1rem 0 .3rem">Scheduling rules</h4><div class="formgrid"><div><label for="max_day">Daily teaching limit per teacher (minutes)</label><input id="max_day" name="max_day" type="number" min="60" max="720" value="{{ max_day }}"></div>
<div><label for="max_week">Weekly teaching limit per teacher (minutes)</label><input id="max_week" name="max_week" type="number" min="60" max="3000" value="{{ max_week }}"></div>
<div><label for="turnover">Laboratory turnover between classes (minutes)</label><input id="turnover" name="turnover" type="number" min="0" max="120" value="{{ turnover }}"></div></div>
<div class="btnrow"><button type="submit">Save timetable and rules</button></div></form>
<form method="post" style="margin-top:.6rem">{{ csrf_field() }}<input type="hidden" name="action" value="reset_tt"><button class="plain small" type="submit">Reset to the standard AM and PM shifts</button></form></div>
<script>(function(){
var ta=document.getElementById('tt_text'),box=document.getElementById('ttedit');if(!ta||!box)return;
var RE=/^\s*(\S+)\s+(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})\s*(class|recess|break)?\s*$/i,data=[];
function mn(v){var p=v.split(':');return (+p[0])*60+(+p[1]);}
function hh(n){return ('0'+Math.floor(n/60)).slice(-2)+':'+('0'+(n%60)).slice(-2);}
function parse(){data=[];var idx={};ta.value.split('\n').forEach(function(l){var m=RE.exec(l);if(!m||m[1].charAt(0)==='#')return;var n=m[1].toUpperCase();
 if(!(n in idx)){idx[n]=data.length;data.push({name:n,rows:[]});}
 data[idx[n]].rows.push({s:(+m[2])*60+(+m[3]),e:(+m[4])*60+(+m[5]),k:/recess|break/i.test(m[6]||'')?'recess':'class'});});}
function write(){var o=['# SHIFT start-end [recess]   (one line per period; the shift name is the first word)'];
 data.forEach(function(sh){sh.rows.forEach(function(r){o.push(sh.name+' '+hh(r.s)+'-'+hh(r.e)+(r.k==='recess'?' recess':''));});});ta.value=o.join('\n')+'\n';}
function el(t,c,h){var e=document.createElement(t);if(c)e.className=c;if(h!=null)e.innerHTML=h;return e;}
function render(){box.innerHTML='';data.forEach(function(sh,si){var card=el('div','ttcard');card.appendChild(el('h4',null,'Shift '+sh.name));
 sh.rows.forEach(function(r,ri){var row=el('div','ttrow'),a=el('input'),b=el('input'),k=el('select'),x=el('button','plain x','Remove');
  a.type='time';a.value=hh(r.s);a.setAttribute('aria-label','Start');b.type='time';b.value=hh(r.e);b.setAttribute('aria-label','End');
  k.innerHTML='<option value="class">Class period</option><option value="recess">Recess or break</option>';k.value=r.k;x.type='button';
  a.addEventListener('change',function(){if(a.value){r.s=mn(a.value);write();}});
  b.addEventListener('change',function(){if(b.value){r.e=mn(b.value);write();}});
  k.addEventListener('change',function(){r.k=k.value;write();});
  x.addEventListener('click',function(){sh.rows.splice(ri,1);if(!sh.rows.length)data.splice(si,1);write();render();});
  row.appendChild(a);row.appendChild(el('span',null,'to'));row.appendChild(b);row.appendChild(k);row.appendChild(x);card.appendChild(row);});
 var add=el('button','plain small','Add period');add.type='button';
 add.addEventListener('click',function(){var l=sh.rows[sh.rows.length-1],s=l?l.e:360;sh.rows.push({s:s,e:s+60,k:'class'});write();render();});
 card.appendChild(add);box.appendChild(card);});}
document.getElementById('addshift').addEventListener('click',function(){var n=(prompt('Name of the new shift (one word, for example AM or PM):')||'').replace(/\s+/g,'').toUpperCase();
 if(!n)return;data.push({name:n,rows:[{s:360,e:420,k:'class'}]});write();render();});
ta.addEventListener('input',function(){parse();render();});parse();render();})();</script>{% endblock %}""",

"sections.html": r"""{% extends "base.html" %}{% from "macros.html" import adviser_picker with context %}{% block title %}Section Management{% endblock %}
{% block content %}<h1>Section Management</h1>
<details class="tip noprint"><summary>About this page</summary><p>Each section has a grade level, a track and one cluster from the Strengthened Curriculum. A section automatically gets the 5 core subjects and its own cluster; the teachers are chosen in Teacher Loading.</p></details>
<details class="card"{{ ' open' if not rows }}><summary>Add a section</summary><form method="post" data-secform style="margin-top:.8rem">{{ csrf_field() }}<div class="formgrid">
<div><label for="grade">Grade level</label><select id="grade" name="grade"><option value="11" {{ 'selected' if s and s.grade == 11 }}>11</option><option value="12" {{ 'selected' if s and s.grade == 12 }}>12</option></select></div>
<div><label for="name">Section name</label><input id="name" name="name" value="{{ (s.name|shortsec) if s else '' }}" placeholder="Example: Chef" required></div>
<div><label for="track">Track</label><select id="track" name="track"><option value="">Not set</option>{% for tr in tracks %}<option value="{{ tr }}" {{ 'selected' if s and s.track == tr }}>{{ tr }}</option>{% endfor %}</select></div>
<div><label for="cluster">Cluster</label><select id="cluster" name="cluster"><option value="">Not set</option>{% for tr in tracks %}<optgroup label="{{ tr }}">{% for c in offered_clusters[tr] %}<option value="{{ c }}" {{ 'selected' if s and s.cluster == c }}>{{ c }}</option>{% endfor %}{% if s and s.cluster and s.cluster in track_clusters[tr] and s.cluster not in offered_clusters[tr] %}<option value="{{ s.cluster }}" selected>{{ s.cluster }} (turned off)</option>{% endif %}</optgroup>{% endfor %}</select></div>
<div><label for="shift">Shift</label><select id="shift" name="shift">{% for sh in shifts %}<option {{ 'selected' if (s and (s.shift or '')|upper == sh) or (not s and sh == 'AM') }}>{{ sh }}</option>{% endfor %}</select><p class="hint">Grade 11 is AM and Grade 12 is PM unless you change it.</p></div>
<div><label for="room">Home room</label><input id="room" name="room" list="roomnames" value="{{ (s.room or '') if s else '' }}" placeholder="Example: Room 308"><datalist id="roomnames">{% for r in room_names %}<option value="{{ r }}">{% endfor %}</datalist></div>
<div><label for="building">Building</label><select id="building" name="building"><option value="">Not set</option>{% for b in buildings %}<option value="{{ b }}" {{ 'selected' if s and s.building == b }}>Bldg. {{ b }}</option>{% endfor %}</select></div>
<div><label for="floor">Floor</label><select id="floor" name="floor"><option value="">Not set</option>{% for fl in floors %}<option value="{{ fl }}" {{ 'selected' if s and s.floor == fl }}>Floor {{ fl }}</option>{% endfor %}</select></div>
<div><label for="adv_q">Adviser</label>{{ adviser_picker(teachers, s.adviser_id if s else none) }}</div></div>
<script>(function(){document.querySelectorAll('form[data-secform]').forEach(function(f){var gr=f.querySelector('[name=grade]'),sf=f.querySelector('[name=shift]');if(!f.getAttribute('data-edit')&&gr&&sf)gr.addEventListener('change',function(){sf.value=gr.value==='12'?'PM':'AM';});var tr=f.querySelector('[name=track]'),cl=f.querySelector('[name=cluster]');
function sync(){var t=tr.value;[].forEach.call(cl.querySelectorAll('optgroup'),function(g){var on=!t||g.label===t;g.hidden=!on;g.disabled=!on;});
 var o=cl.options[cl.selectedIndex];if(o&&o.parentNode.tagName==='OPTGROUP'&&o.parentNode.disabled)cl.value='';}
tr.addEventListener('change',sync);cl.addEventListener('change',function(){var o=cl.options[cl.selectedIndex];if(o&&o.parentNode.tagName==='OPTGROUP')tr.value=o.parentNode.label;sync();});sync();});})();</script><div class="btnrow"><button type="submit">Add section</button></div></form></details>
<div class="tsearch noprint"><div class="formgrid"><div><label for="sq">Search</label><input id="sq" type="search" placeholder="Section or room" autocomplete="off"></div>
<div><label for="fg">Grade level</label><select id="fg"><option value="">All</option><option>11</option><option>12</option></select></div>
<div><label for="ft">Track</label><select id="ft"><option value="">All</option>{% for tr in tracks %}<option>{{ tr }}</option>{% endfor %}</select></div></div></div>
<div class="scroll"><table class="list" id="sectab"><thead><tr><th>Section</th><th>Grade</th><th>Track and cluster</th><th>Shift</th><th>Room</th><th>Adviser</th><th>Loading</th><th></th></tr></thead><tbody>
{% for s in rows %}<tr data-g="{{ s.grade }}" data-t="{{ s.track or '' }}" data-f="{{ (s.name ~ ' ' ~ (s.room or ''))|lower }}"><td><a href="{{ url_for('program', section=s.id) }}">{{ s.name }}</a></td><td>{{ s.grade }}</td>
<td>{% if s.track and s.cluster %}{{ s.track }}<span class="cur-spec">{{ s.cluster }}</span>{% else %}<span class="pill new">Needs track and cluster</span>{% endif %}</td><td><b>{{ s.shift or '-' }}</b></td><td>{{ s.room or '-' }}</td><td>{{ s.adviser or '-' }}</td>
<td class="{{ 'okt' if s.nsub and s.nload == s.nsub else 'why' }}">{{ s.nload }} of {{ s.nsub }} subjects have a teacher</td>
<td><div class="row-acts"><a class="btn plain small" href="{{ url_for('section_edit', sid=s.id) }}">Edit</a>
<form method="post" action="{{ url_for('section_delete', sid=s.id) }}" onsubmit="return confirm('Delete this section and its entire class program?')">{{ csrf_field() }}<button class="danger">Delete</button></form></div></td></tr>
{% else %}<tr><td colspan="8" class="empty">No sections yet.</td></tr>{% endfor %}</tbody></table></div>
<script>(function(){var q=document.getElementById('sq'),g=document.getElementById('fg'),t=document.getElementById('ft');
function up(){var w=q.value.toLowerCase().trim();document.querySelectorAll('#sectab tbody tr[data-g]').forEach(function(r){
r.hidden=!((!w||r.getAttribute('data-f').indexOf(w)>-1)&&(!g.value||r.getAttribute('data-g')===g.value)&&(!t.value||r.getAttribute('data-t')===t.value));});}
q.addEventListener('input',up);g.addEventListener('change',up);t.addEventListener('change',up);})();</script>{% endblock %}""",

"section_edit.html": r"""{% extends "base.html" %}{% from "macros.html" import back, adviser_picker with context %}{% block title %}Edit section{% endblock %}
{% block content %}<div class="titlerow">{{ back(url_for('sections'), 'Back to sections') }}<h1>Edit section</h1></div>
<div class="card"><form method="post" data-secform data-edit="1">{{ csrf_field() }}<div class="formgrid">
<div><label for="grade">Grade level</label><select id="grade" name="grade"><option value="11" {{ 'selected' if s and s.grade == 11 }}>11</option><option value="12" {{ 'selected' if s and s.grade == 12 }}>12</option></select></div>
<div><label for="name">Section name</label><input id="name" name="name" value="{{ (s.name|shortsec) if s else '' }}" placeholder="Example: Chef" required></div>
<div><label for="track">Track</label><select id="track" name="track"><option value="">Not set</option>{% for tr in tracks %}<option value="{{ tr }}" {{ 'selected' if s and s.track == tr }}>{{ tr }}</option>{% endfor %}</select></div>
<div><label for="cluster">Cluster</label><select id="cluster" name="cluster"><option value="">Not set</option>{% for tr in tracks %}<optgroup label="{{ tr }}">{% for c in offered_clusters[tr] %}<option value="{{ c }}" {{ 'selected' if s and s.cluster == c }}>{{ c }}</option>{% endfor %}{% if s and s.cluster and s.cluster in track_clusters[tr] and s.cluster not in offered_clusters[tr] %}<option value="{{ s.cluster }}" selected>{{ s.cluster }} (turned off)</option>{% endif %}</optgroup>{% endfor %}</select></div>
<div><label for="shift">Shift</label><select id="shift" name="shift">{% for sh in shifts %}<option {{ 'selected' if (s and (s.shift or '')|upper == sh) or (not s and sh == 'AM') }}>{{ sh }}</option>{% endfor %}</select><p class="hint">Grade 11 is AM and Grade 12 is PM unless you change it.</p></div>
<div><label for="room">Home room</label><input id="room" name="room" list="roomnames" value="{{ (s.room or '') if s else '' }}" placeholder="Example: Room 308"><datalist id="roomnames">{% for r in room_names %}<option value="{{ r }}">{% endfor %}</datalist></div>
<div><label for="building">Building</label><select id="building" name="building"><option value="">Not set</option>{% for b in buildings %}<option value="{{ b }}" {{ 'selected' if s and s.building == b }}>Bldg. {{ b }}</option>{% endfor %}</select></div>
<div><label for="floor">Floor</label><select id="floor" name="floor"><option value="">Not set</option>{% for fl in floors %}<option value="{{ fl }}" {{ 'selected' if s and s.floor == fl }}>Floor {{ fl }}</option>{% endfor %}</select></div>
<div><label for="adv_q">Adviser</label>{{ adviser_picker(teachers, s.adviser_id if s else none) }}</div></div>
<script>(function(){document.querySelectorAll('form[data-secform]').forEach(function(f){var gr=f.querySelector('[name=grade]'),sf=f.querySelector('[name=shift]');if(!f.getAttribute('data-edit')&&gr&&sf)gr.addEventListener('change',function(){sf.value=gr.value==='12'?'PM':'AM';});var tr=f.querySelector('[name=track]'),cl=f.querySelector('[name=cluster]');
function sync(){var t=tr.value;[].forEach.call(cl.querySelectorAll('optgroup'),function(g){var on=!t||g.label===t;g.hidden=!on;g.disabled=!on;});
 var o=cl.options[cl.selectedIndex];if(o&&o.parentNode.tagName==='OPTGROUP'&&o.parentNode.disabled)cl.value='';}
tr.addEventListener('change',sync);cl.addEventListener('change',function(){var o=cl.options[cl.selectedIndex];if(o&&o.parentNode.tagName==='OPTGROUP')tr.value=o.parentNode.label;sync();});sync();});})();</script><p class="hint">Changing the cluster replaces the cluster subject of this section. Its class program is then marked out of date.</p>
<div class="btnrow"><button type="submit">Save changes</button><a class="btn plain" href="{{ url_for('sections') }}">Cancel</a></div></form></div>{% endblock %}""",

"users.html": r"""{% extends "base.html" %}{% block title %}User Management{% endblock %}
{% block content %}<h1>User Management</h1>{{ subnav('users') }}
<details class="tip noprint"><summary>About this page</summary><p>{{ admins }} administrator(s) and {{ teachers_n }} teacher account(s). Teacher profiles are edited in Teacher Management.{% if pending %} <a href="{{ url_for('reports') }}"><b>{{ pending }} account request(s) are waiting.</b></a>{% endif %}</p></details>
<details class="card"><summary>Add an administrator</summary><form method="post" style="margin-top:.8rem">{{ csrf_field() }}<input type="hidden" name="action" value="add_admin"><div class="formgrid">
<div><label for="full_name">Full name</label><input id="full_name" name="full_name" required></div><div><label for="username">Username</label><input id="username" name="username" required></div>
<div><label for="password">Password</label><input id="password" name="password" minlength="6" required></div><div><button type="submit" style="margin-top:.7rem">Create administrator</button></div></div></form></details>
<div class="scroll"><table class="list"><thead><tr><th>Name</th><th>Username</th><th>ID</th><th>Role</th><th></th></tr></thead><tbody>
{% for u in rows %}<tr><td>{{ u.full_name }}</td><td>{{ u.username }}</td><td>{{ u.teacher_id or '-' }}</td><td><span class="user-role {{ u.role }}">{{ 'Administrator' if u.role == 'admin' else cats.get(u.category, 'Teacher') }}</span></td>
<td><div class="row-acts">{% if u.role == 'teacher' %}<a class="btn plain small" href="{{ url_for('teacher_edit', tid=u.id) }}">Edit</a>{% endif %}
{% if u.id != g.user.id %}<form method="post" onsubmit="return confirm('Set the password of {{ u.full_name }} to {{ temp }}?')">{{ csrf_field() }}<input type="hidden" name="action" value="reset_pw"><input type="hidden" name="uid" value="{{ u.id }}"><button class="plain small">Reset password</button></form>
{% if u.role == 'admin' %}<form method="post" onsubmit="return confirm('Delete this administrator account?')">{{ csrf_field() }}<input type="hidden" name="action" value="delete_admin"><input type="hidden" name="uid" value="{{ u.id }}"><button class="danger">Delete</button></form>{% endif %}{% else %}<span class="hint">You</span>{% endif %}</div></td></tr>{% endfor %}</tbody></table></div>{% endblock %}""",

"user_roles.html": r"""{% extends "base.html" %}{% block title %}Roles and permissions{% endblock %}
{% block content %}<h1>User Management</h1>{{ subnav('users') }}
<p style="color:var(--muted)">What each role can do. The program enforces these on every page.</p>
{% for name, key, rights in roles %}<div class="card"><h3>{{ name }} <span class="user-role {{ 'admin' if key == 'ADMIN' }}">{{ counts.get(key, 0) }} account(s)</span></h3><ul class="issues">{% for r in rights %}<li>{{ r }}</li>{% endfor %}</ul></div>{% endfor %}{% endblock %}""",

"user_audit.html": r"""{% extends "base.html" %}{% block title %}Audit trail{% endblock %}
{% block content %}<h1>User Management</h1>{{ subnav('users') }}
<details class="tip noprint"><summary>About this page</summary><p>Who signed in and what was changed, newest first ({{ total }} entries recorded; showing up to 300). Passwords are never recorded.</p></details>
<form method="get" class="card"><div class="formgrid"><div><label for="q">Search</label><input id="q" name="q" value="{{ q }}" placeholder="Name, action or detail"></div>
<div><label for="who">Role</label><select id="who" name="who"><option value="">All</option><option value="admin" {{ 'selected' if who == 'admin' }}>Administrators</option><option value="teacher" {{ 'selected' if who == 'teacher' }}>Teachers</option></select></div>
<div><button type="submit" style="margin-top:.7rem" data-noconfirm>Filter</button></div></div></form>
<div class="scroll"><table class="list"><thead><tr><th>When</th><th>Who</th><th>Action</th><th>Detail</th></tr></thead><tbody>
{% for r in rows %}<tr><td>{{ r.at|stamp12 }}</td><td>{{ r.who }}{% if r.role %} <span class="user-role {{ r.role }}">{{ r.role }}</span>{% endif %}</td><td>{{ r.action }}</td><td class="hint">{{ r.detail or '' }}</td></tr>
{% else %}<tr><td colspan="4" class="empty">Nothing recorded yet.</td></tr>{% endfor %}</tbody></table></div>{% endblock %}""",

"teachers.html": r"""{% extends "base.html" %}{% from "macros.html" import tsearch, otime, durselect, specpick with context %}{% block title %}Teacher Management{% endblock %}
{% block content %}<h1>Teacher Management</h1>
<details class="tip noprint"><summary>About this page</summary><p>Teacher accounts, profiles, specialization and availability (official time) in one table. Specializations are chosen from the Strengthened Curriculum and qualify the teacher for those subjects automatically. Press <b>Edit</b> at the end of a row to change that teacher; only that row is saved. Subjects as printed, ancillary duties and daily minutes are under <b>More details</b>.</p></details>
<details class="card"><summary>Add a teacher</summary><form method="post" style="margin-top:.8rem">{{ csrf_field() }}<div class="formgrid">
<div><label for="full_name">Full name</label><input id="full_name" name="full_name" required></div>
<div><label for="teacher_num">Teacher ID</label><div class="tidfield"><span class="tidfix">T-</span><input id="teacher_num" name="teacher_num" type="number" min="1" step="1" value="{{ suggested_id[2:] }}" required></div></div>
<div><label for="username">Username</label><input id="username" name="username" required></div>
<div><label for="category">Teacher type</label><select id="category" name="category">{% for k, v in cats.items() %}<option value="{{ k }}">{{ v }}</option>{% endfor %}</select></div>
<div><label for="password">Password</label><input id="password" name="password" minlength="6" required></div>
<div><button type="submit" style="margin-top:.7rem">Create account</button></div></div></form></details>
{{ tsearch() }}
<div class="typesel noprint"><label for="typesel">Filter by teacher type</label><select id="typesel"><option value="">All types</option>{% for k, v in cats.items() %}<option value="{{ k }}">{{ v }}</option>{% endfor %}</select></div>
<script>document.getElementById('typesel').addEventListener('change',function(){window.__cat=this.value;if(window.findApply)window.findApply();});</script>
<form method="post" action="{{ url_for('assignments') }}">{{ csrf_field() }}<input type="hidden" name="action" value="save">
<div class="scroll"><table class="list assign tm"><thead><tr><th>Teacher</th><th>Grade level handled</th><th>Specialization</th><th>Official time</th><th>Teaching time</th><th class="editth">Edit</th></tr></thead><tbody>
{% for t in rows %}{% set k = t.id %}<tr class="arow" data-cat="{{ t.category }}" data-find="{{ (t.full_name ~ ' ' ~ t.teacher_id)|lower }}">
<td><div class="tn">{{ tlabels.get(k) }}</div><input name="name_{{ k }}" value="{{ t.full_name }}" aria-label="Name of {{ tlabels.get(k) }}" required>
<p class="hint">{{ t.teacher_id }}<br><a href="{{ url_for('teacher_view', tid=k) }}">View program</a> &middot; <a href="{{ url_for('teacher_edit', tid=k) }}">More details</a></p></td>
<td><select name="cat_{{ k }}" aria-label="Grade level handled by {{ tlabels.get(k) }}">{% for c, v in cats.items() %}<option value="{{ c }}" {{ 'selected' if c == t.category }}>{{ catname[c] }}</option>{% endfor %}</select></td>
<td>{{ specpick('spec_' ~ k, t.specialization, 'Specialization') }}</td>
<td>{{ otime('time_' ~ k, t.official_time, 'Official time of ' ~ tlabels.get(k)) }}</td>
<td><b>{{ summ[k].teach_w|hrs }}</b> per week<p class="hint">{{ summ[k].work_w|hrs }} total workload<br>{{ summ[k].loads }}</p></td>
<td class="editcell"><div class="row-acts"><button type="button" class="plain small rowedit">Edit</button><span class="rowsave" hidden><button type="submit" class="small">Save</button><button type="button" class="plain small rowcancel">Cancel</button></span></div></td></tr>
{% else %}<tr><td colspan="6" class="empty">No teachers yet. Add one above.</td></tr>{% endfor %}<tr id="tqnone" hidden><td colspan="6" class="empty">No teacher matches your search.</td></tr></tbody></table></div>
</form>
<script>(function(){
var rows=[].slice.call(document.querySelectorAll('tr.arow'));
function ctl(r){return [].slice.call(r.querySelectorAll('input,select,textarea'));}
/* Read-only view shows plain wrapped text, so nothing is cut off or needs scrolling. */
function setup(r){
r.querySelectorAll('td:not(.editcell)').forEach(function(td){
var ot=td.querySelector('.otime');
if(ot){ot.classList.add('vc');var sp=document.createElement('span');sp.className='vtext';sp.setAttribute('data-kind','otime');ot.parentNode.insertBefore(sp,ot);}
td.querySelectorAll('input,select,textarea').forEach(function(c){
if(c.type==='hidden'||c.closest('.otime')||c.closest('.specpick'))return;
c.classList.add('vc');var sp=document.createElement('span');sp.className='vtext';sp.__c=c;c.parentNode.insertBefore(sp,c);});});}
function refresh(r){r.querySelectorAll('.vtext').forEach(function(sp){var t='',mute=false;
if(sp.getAttribute('data-kind')==='otime'){var h=sp.parentNode.querySelector('input[data-official]');t=h?h.value:'';}
else{var c=sp.__c;if(c.tagName==='SELECT'){t=c.options[c.selectedIndex]?c.options[c.selectedIndex].text:'';}
else{t=c.value;if(!t&&c.placeholder){t=c.placeholder;mute=true;}}}
sp.textContent=t||'-';sp.classList.toggle('muted',mute||!t);});}
function lock(r,on){if(on)refresh(r);r.classList.toggle('rowview',on);r.classList.toggle('rowedit-on',!on);
ctl(r).forEach(function(c){c.disabled=on;});
r.querySelector('.rowedit').hidden=!on;r.querySelector('.rowsave').hidden=on;}
rows.forEach(function(r){setup(r);lock(r,true);
r.querySelector('.rowedit').addEventListener('click',function(){lock(r,false);var f=r.querySelector('input.vc:not([disabled]),textarea.vc:not([disabled])');if(f)f.focus();});
r.querySelector('.rowcancel').addEventListener('click',function(){
ctl(r).forEach(function(c){
if(c.tagName==='SELECT'){[].forEach.call(c.options,function(o){o.selected=o.defaultSelected;});}
else if(c.type==='checkbox'){c.checked=c.defaultChecked;}else{c.value=c.defaultValue;}
c.dispatchEvent(new Event('input',{bubbles:true}));c.dispatchEvent(new Event('change',{bubbles:true}));});
lock(r,true);});});
})();</script>{% endblock %}""",

"teacher_edit.html": r"""{% extends "base.html" %}{% from "macros.html" import back, otime, durselect, specpick with context %}{% block title %}Edit teacher{% endblock %}
{% block content %}<div class="titlerow">{{ back(url_for('teachers'), 'Back to teachers') }}<h1>Edit teacher details</h1></div>
<div class="card"><form method="post">{{ csrf_field() }}
<h3>Account</h3><div class="formgrid">
<div><label for="full_name">Full name</label><input id="full_name" name="full_name" value="{{ t.full_name }}" required></div>
<div><label for="teacher_num">Teacher ID</label><div class="tidfield"><span class="tidfix">T-</span><input id="teacher_num" name="teacher_num" type="number" min="1" step="1" value="{{ (t.teacher_id or 'T-')[2:] }}" required></div></div>
<div><label for="username">Username</label><input id="username" name="username" value="{{ t.username }}" required></div>
<div><label for="category">Teacher type</label><select id="category" name="category">{% for k, v in cats.items() %}<option value="{{ k }}" {{ 'selected' if k == t.category }}>{{ v }}</option>{% endfor %}</select></div></div>
<h3 style="margin-top:1.4rem">Teacher's program details</h3><div class="formgrid">
<div><label for="item">Item</label><input id="item" name="item" value="{{ t.item or '' }}" placeholder="Example: Teacher II"></div>
<div class="wide"><label>Official time (start to end)</label>{{ otime('official_time', t.official_time, 'Official time') }}</div>
<div class="wide"><label for="subject_area">Subject</label><input id="subject_area" name="subject_area" value="{{ t.subject_area or '' }}" placeholder="Example: PR 2 / Bartending"></div>
<div class="wide"><label>Specialization (choose from the curriculum)</label>{{ specpick('specialization', t.specialization) }}</div>
<div><label for="teaching_load">Teaching load</label><input id="teaching_load" name="teaching_load" value="{{ t.teaching_load or '' }}" placeholder="Blank = count scheduled loads"></div>
<div class="wide"><label for="ancillary">Ancillary</label><input id="ancillary" name="ancillary" value="{{ t.ancillary or '' }}" placeholder="Leave blank to show the advisory sections automatically">
<p class="hint">Example: ADVISER (12-RECEPTIONIST)</p></div>
<div><label>Intervention / Remediation time per day</label>{{ durselect('intervention_min', t.intervention_min or 0, 'Intervention time per day') }}</div>
<div><label>Ancillary / Adviser's time per day</label>{{ durselect('ancillary_min', t.ancillary_min or 0, 'Ancillary time per day') }}</div>
</div>
<div class="btnrow"><button type="submit">Save changes</button>
<a class="btn plain" href="{{ url_for('teachers') }}">Cancel</a></div></form></div><div class="card"><h3>Delete this teacher</h3><p class="hint">Their class periods and advisory become unassigned.</p><form method="post" action="{{ url_for('teacher_delete', tid=t.id) }}" onsubmit="return confirm('Delete this teacher account?')">{{ csrf_field() }}<button class="danger">Delete teacher account</button></form></div>{% endblock %}""",

"auto_loading.html": r"""{% extends "base.html" %}{% block title %}Teacher loading{% endblock %}
{% block content %}<h1>Teacher Loading</h1>{{ subnav('loading') }}
<details class="tip noprint"><summary>About this page</summary><p>Choose who teaches each subject of a section. A section takes the 5 core subjects and its own cluster; the cluster, shift and room are set in Section Management. Qualified teachers are starred. Finalize loading before generating; the generator never changes who teaches what.</p></details>
<div class="card"><form method="post" data-noconfirm>{{ csrf_field() }}<input type="hidden" name="action" value="autofill">
<p><b>Auto-fill:</b> adds every eligible subject to sections that have none, then assigns the best qualified teacher to every empty slot (shift fit first, then lightest load).</p>
<label style="display:flex;gap:.5rem;align-items:center;font-weight:400"><input class="ck" type="checkbox" name="overwrite" value="1"> Also replace teachers that are already assigned</label>
<div class="btnrow"><button type="submit">Auto-fill all sections</button></div></form></div>
{% if not cur %}<div class="msg notice">Add sections first.</div>{% else %}
<div class="card"><form method="get"><label for="section">Section</label><select id="section" name="section" onchange="this.form.submit()">{% for s in secs %}<option value="{{ s.id }}" {{ 'selected' if s.id == cur.id }}>{{ s.name }} (Grade {{ s.grade }}{{ ', ' ~ s.track if s.track }})</option>{% endfor %}</select><noscript><button type="submit">Open</button></noscript></form></div>
<form method="post">{{ csrf_field() }}<input type="hidden" name="action" value="save"><input type="hidden" name="section_id" value="{{ cur.id }}">
<p class="hint">{{ cur.track or 'Track not set' }}{{ ' - ' ~ cur.cluster if cur.cluster }} &middot; shift {{ cur_shift }} &middot; room {{ cur.room or 'not set' }}. <a href="{{ url_for('section_edit', sid=cur.id) }}">Change in Section Management</a></p>
<div class="scroll"><table class="list"><thead><tr><th>Takes</th><th>Subject</th><th>Time</th><th>Room</th><th>Teacher</th></tr></thead><tbody>
{% for r in rows %}<tr><td><input class="ck" type="checkbox" name="take_{{ r.s.id }}" value="1" {{ 'checked' if r.taken }} aria-label="{{ r.s.name }}"></td>
<td>{{ r.s.name }}<p class="hint">{{ r.s.code or '' }}</p></td><td>{{ r.s.weekly_min|hrs }} per week<p class="hint">{{ r.s.session_min|hrs }} per meeting</p></td><td>{{ r.s.rtype }}</td>
<td><select name="teacher_{{ r.s.id }}" aria-label="Teacher for {{ r.s.name }}"><option value="">- not assigned -</option>{% for t in r.opts %}<option value="{{ t.id }}" {{ 'selected' if t.id == r.tid }}>{{ '★ ' if t.id in r.q else '' }}{{ tlabels.get(t.id) }} {{ t.full_name }}</option>{% endfor %}</select></td></tr>
{% else %}<tr><td colspan="5" class="empty">No subjects match this section's grade and track. Add subjects first.</td></tr>{% endfor %}</tbody></table></div>
<p class="hint">★ = qualified for this subject.</p><div class="btnrow"><button type="submit">Save {{ cur.name }}</button></div></form>{% endif %}
<h2>Teacher loading validation</h2>
{% if lv.issues %}<div class="card"><h3>Problems to fix</h3><ul class="issues">{% for i in lv.issues %}<li class="why">{{ i }}</li>{% endfor %}</ul></div>{% else %}<div class="card"><p class="okt"><b>Loading is complete: every subject has a qualified teacher and nobody is over the limit.</b></p></div>{% endif %}
{% if lv.warns %}<div class="card"><h3>Warnings</h3><ul class="issues">{% for i in lv.warns %}<li>{{ i }}</li>{% endfor %}</ul></div>{% endif %}
<h2>Teacher load summary</h2><div class="scroll"><table class="list"><thead><tr><th>Teacher</th><th>Official time</th><th>Classes handled</th><th>Different subjects</th><th>Assigned per week</th><th>Status</th></tr></thead><tbody>
{% for x in lv.rows %}<tr><td>{{ tlabels.get(x.t.id) }} {{ x.t.full_name }}</td><td>{{ x.window }}</td><td>{{ x.nsec }}</td><td>{{ x.npre }}</td><td>{{ x.minutes|hrs }} of {{ lv.maxweek|hrs }}</td><td class="{{ 'okt' if x.status == 'OK' else 'why' }}">{{ x.status }}</td></tr>{% endfor %}</tbody></table></div>{% endblock %}""",

"auto_generate.html": r"""{% extends "base.html" %}{% block title %}Auto-Generate{% endblock %}
{% block content %}<h1>Schedule Generator</h1>{{ subnav('schedule') }}
<div class="kpis"><div class="kpi"><b>{{ counts.subjects }}</b><span>subjects</span></div><div class="kpi"><b>{{ counts.rooms }}</b><span>rooms and labs</span></div><div class="kpi"><b>{{ counts.teacher_subjects }}</b><span>teacher qualifications</span></div><div class="kpi"><b>{{ counts.loads }}</b><span>teacher loads</span></div></div>
<div class="card"><h3>Quick setup</h3><p style="color:var(--muted)">One click fills whatever is empty: starter subjects, rooms from your sections, qualifications matched from specializations, subjects per section and teacher loading. Review each step afterwards.</p>
<form method="post" data-noconfirm>{{ csrf_field() }}<input type="hidden" name="action" value="quick"><button class="plain" type="submit">Run quick setup</button></form></div>
<p class="hint">The timetable, shifts and teaching limits are set in <a href="{{ url_for('settings') }}#timetable">School Setup</a>.</p>
{% if lv.issues %}<div class="msg notice">Teacher loading has {{ lv.issues|length }} problem{{ '' if lv.issues|length == 1 else 's' }} (see Teacher Loading). Fix them first for the best result.</div>{% endif %}
{% if stale %}<div class="msg notice">Changed in teacher loading since generated: {% for s in stale %}<b>{{ s.name }}</b>{{ ', ' if not loop.last }}{% endfor %}. <form method="post" data-noconfirm style="display:inline">{{ csrf_field() }}<input type="hidden" name="action" value="regen">{% for s in stale %}<input type="hidden" name="sec" value="{{ s.id }}">{% endfor %}<button type="submit" class="small">Regenerate only these</button></form></div>{% endif %}
<div class="card"><h3>Generate</h3><form method="post" data-noconfirm>{{ csrf_field() }}<input type="hidden" name="action" value="generate">
<details class="tip noprint"><summary>About this page</summary><p>Sections not selected keep their programs, and their teachers and rooms are treated as already busy. A draft is created first; nothing changes until you apply it.</p></details>
<label style="display:flex;gap:.5rem;align-items:center"><input class="ck" type="checkbox" id="all" checked> Select all sections</label>
<div class="formgrid" style="margin-top:.4rem">{% for s in secs %}<label style="display:flex;gap:.5rem;align-items:center;font-weight:400"><input class="ck sec" type="checkbox" name="sec" value="{{ s.id }}" {{ 'checked' if s.nsub }} {{ 'disabled' if not s.nsub }}> {{ s.name }}{% if not s.nsub %} <small>(no subjects)</small>{% endif %}</label>{% endfor %}</div>
<div class="formgrid"><div><label for="tries">Search effort</label><select id="tries" name="tries"><option value="20">Quick (20 attempts)</option><option value="40" selected>Standard (40 attempts)</option><option value="120">Thorough (120 attempts)</option></select></div></div>
<div class="btnrow"><button type="submit" data-busy="Generating...">Generate draft class program</button></div></form></div>
<script>(function(){var a=document.getElementById('all');if(!a)return;a.addEventListener('change',function(){document.querySelectorAll('.sec:not(:disabled)').forEach(function(c){c.checked=a.checked;});});})();</script>
{% if draft %}<div class="card"><h3>Draft ready for review</h3><p class="hint">Created {{ draft.when|stamp12 }} &middot; {{ draft.tries }} attempts &middot; daily limit {{ draft.maxday }} min.</p>
<div class="kpis"><div class="kpi ok"><b>{{ draft.sessions|length }}</b><span>class meetings placed</span></div><div class="kpi {{ 'bad' if draft.unplaced else 'ok' }}"><b>{{ draft.unplaced|length }}</b><span>subjects not fully scheduled</span></div><div class="kpi"><b>{{ draft.sections|length }}</b><span>sections</span></div></div>
{% if draft.unplaced %}<h3>Needs attention</h3><div class="scroll"><table class="list"><thead><tr><th>Section</th><th>Subject</th><th>Teacher</th><th>Missing</th><th>Why</th></tr></thead><tbody>
{% for u in draft.unplaced %}<tr><td>{{ u.section }}</td><td>{{ u.subject }}</td><td>{{ u.teacher }}</td><td>{{ u.minutes|hrs }}</td><td class="why">{{ u.reason }}</td></tr>{% endfor %}</tbody></table></div>
<p class="hint">Fix the cause (teacher, official time, rooms, subject minutes), then generate again. You can also apply the draft and place the remaining periods by hand in Class Programs.</p>{% else %}<p class="okt"><b>Every required minute was placed with no teacher, section or room conflicts.</b></p>{% endif %}
<form method="post" class="btnrow">{{ csrf_field() }}<button type="submit" name="action" value="apply" onclick="return confirm('Replace the class programs of the selected sections with this draft? Their current periods will be removed.')">Apply to class programs</button><button class="plain" type="submit" name="action" value="discard" formnovalidate onclick="return confirm('Discard this draft?')">Discard draft</button></form></div>
{% for name, items in by.items() %}<details class="card"><summary>{{ name }} &middot; {{ items|length }} meetings</summary><div class="scroll"><table class="list"><thead><tr><th>Day</th><th>Time</th><th>Subject</th><th>Teacher</th><th>Room</th></tr></thead><tbody>
{% for x in items %}<tr><td>{{ x.day }}</td><td>{{ x.start|t12 }} to {{ x.end|t12 }}</td><td>{{ x.subject }}</td><td>{{ x.teacher }}</td><td>{{ x.room }}</td></tr>{% endfor %}</tbody></table></div></details>{% endfor %}{% endif %}
<div class="card"><h3>Validation</h3>{% if chk.issues %}<p class="why"><b>{{ chk.issues|length }} problem(s) in the stored class programs.</b></p>{% else %}<p class="okt"><b>No conflicts in the {{ chk.rows }} stored periods.</b></p>{% endif %}<a class="btn plain small" href="{{ url_for('auto_conflicts') }}">Open the Validation Center</a></div>{% endblock %}""",

"quick_input.html": r"""{% extends "base.html" %}{% from "macros.html" import specpick with context %}{% block title %}Quick Input{% endblock %}
{% block content %}<h1>Quick Input</h1>{{ subnav('schedule') }}
<details class="tip noprint"><summary>About this page</summary><p>Enter the sections, then each teacher's loading (subjects to teach) and class hours (AM, MID or PM). Press the button at the end: the system distributes the teachers and makes every class program with no overlapping time and no conflicts.</p></details>
{% if approved %}<div class="msg error">The schedule is approved and locked. Reopen it in Validation Center to use Quick Input.</div>{% endif %}
{% if not g12_on %}<p class="hint">Grade 12 class programs are off (School Setup). Grade 12 sections can still be added; they get no class program.</p>{% endif %}
{% if not tt_has_mid %}<div class="cur-note">Your timetable has no <b>MID</b> shift yet. <form method="post" style="display:inline" data-noconfirm>{{ csrf_field() }}<input type="hidden" name="action" value="add_mid"><button class="small" type="submit">Add the MID shift</button></form></div>{% endif %}
<div class="card"><h3>1. Number of sections and their names</h3>
<p class="hint">Now: {{ all_secs|length }} section(s){% for g in (11, 12) %} &middot; Grade {{ g }}: {{ all_secs|selectattr('grade', 'equalto', g)|list|length }}{% endfor %}. {% if all_secs %}<a href="{{ url_for('sections') }}">See or edit them in Section Management</a>.{% endif %}</p>
<form method="post" data-qi>{{ csrf_field() }}<input type="hidden" name="action" value="add_sections"><div class="formgrid">
<div><label for="s_grade">Grade level</label><select id="s_grade" name="grade"><option>11</option><option>12</option></select></div>
<div><label for="s_cluster">Cluster</label><select id="s_cluster" name="cluster"><option value="">Not set yet</option>{% for tr, lst in offered_clusters.items() %}<optgroup label="{{ tr }}">{% for c in lst %}<option>{{ c }}</option>{% endfor %}</optgroup>{% endfor %}</select></div>
<div><label for="s_shift">Class hours</label><select id="s_shift" name="shift">{% for s in shifts %}<option value="{{ s }}">{{ s }} ({{ hours[s] }})</option>{% endfor %}</select></div>
<div class="wide"><label for="s_names">Section names, one per line <span class="hint">(<span id="s_count">0</span> section(s))</span></label><textarea id="s_names" name="names" rows="4" placeholder="Chef&#10;Baker&#10;Barista" required></textarea></div></div>
<div class="btnrow"><button type="submit">Add sections</button></div></form></div>
<div class="card"><h3>2. Teachers: name, loading (subject to teach) and class hours</h3>
<form method="post">{{ csrf_field() }}<input type="hidden" name="action" value="save_teachers"><div class="scroll"><table class="list qi"><thead><tr><th>Name</th><th>Loading (subjects to teach)</th><th>Class hours</th></tr></thead><tbody>
{% for t in teachers %}<tr><td><b>{{ t.full_name }}</b><br><span class="hint">{{ t.teacher_id }}</span></td><td>{{ specpick('spec_' ~ t.id, t.specialization, 'Subjects to teach') }}<script>document.currentScript.parentNode.querySelector('details').open=false;</script></td>
<td><select name="shift_{{ t.id }}" aria-label="Class hours of {{ t.full_name }}"><option value="">{{ 'Custom: ' ~ t.official_time if t.official_time and not tshift[t.id] else 'Not set (whole day)' }}</option>{% for s in shifts %}<option value="{{ s }}" {{ 'selected' if tshift[t.id] == s }}>{{ s }} ({{ hours[s] }})</option>{% endfor %}</select></td></tr>
{% else %}<tr><td colspan="3" class="empty">No teachers yet. Add them below.</td></tr>{% endfor %}</tbody></table></div>
{% if teachers %}<div class="btnrow"><button type="submit">Save loading and class hours</button></div>{% endif %}</form>
<details class="card" {{ 'open' if not teachers }} style="margin-top:1rem"><summary>Add teachers</summary><form method="post" style="margin-top:.8rem">{{ csrf_field() }}<input type="hidden" name="action" value="add_teachers"><div class="formgrid">
<div><label for="t_cat">Teacher type</label><select id="t_cat" name="category">{% for k, v in cats.items() %}<option value="{{ k }}">{{ v }}</option>{% endfor %}</select></div>
<div><label for="t_shift">Class hours</label><select id="t_shift" name="shift"><option value="">Not set (whole day)</option>{% for s in shifts %}<option value="{{ s }}">{{ s }} ({{ hours[s] }})</option>{% endfor %}</select></div>
<div class="wide"><label>Loading (subjects to teach), same for everyone added now</label>{{ specpick('spec_new', '', 'Subjects to teach') }}</div>
<div class="wide"><label for="t_names">Teacher names, one per line</label><textarea id="t_names" name="names" rows="4" required></textarea></div></div>
<p class="hint">Teacher ID and username are made automatically. The temporary password is {{ 'teacher123' }}; the teacher changes it in Settings.</p><div class="btnrow"><button type="submit">Add teachers</button></div></form></details></div>
<div class="card" id="result"><h3>3. Distribute teachers and generate the class programs</h3>
<p>Matches teachers to subjects and places every class with no overlaps.{% if not g12_on %} Grade 11 only.{% endif %} Replaces the programs of {{ n_sched }} section(s).</p>
<form method="post" onsubmit="return confirm('Generate all class programs now? The current programs will be replaced.')">{{ csrf_field() }}<input type="hidden" name="action" value="run"><button type="submit" {{ 'disabled' if approved or not n_sched or not teachers }} data-busy="Working, this can take a few seconds...">Assign teachers and generate all class programs</button></form>
<p class="hint">Afterwards: check the <a href="{{ url_for('auto_conflicts') }}">Validation Center</a>, then <a href="{{ url_for('program') }}">see the class programs</a>.</p></div>
<script>(function(){var g=document.getElementById('s_grade'),sh=document.getElementById('s_shift');if(g&&sh){function d(){sh.value=g.value==='12'?'PM':'AM';}g.addEventListener('change',d);d();}})();</script>
<script>(function(){var t=document.getElementById('s_names'),c=document.getElementById('s_count');if(!t)return;function u(){c.textContent=t.value.split('\n').filter(function(x){return x.trim();}).length;}t.addEventListener('input',u);u();})();</script>{% endblock %}""",

}
TEMPLATES.update(NEW2_TEMPLATES)

app.jinja_loader = DictLoader(TEMPLATES)

init_db()  # runs on import so PythonAnywhere also creates the database
init_auto_db()
migrate_curriculum()


def load_example_once():
    """Load the 10 example sections and 20 example teachers one time, automatically, the
    first time this version starts. A flag is kept so deleting them later does not bring
    them back."""
    try:
        with app.app_context():
            if query("SELECT 1 FROM settings WHERE k='example_loaded'", one=True):
                return
            sample_data()
            run("INSERT OR REPLACE INTO settings(k,v) VALUES('example_loaded','1')")
    except Exception as exc:  # never stop the site from starting
        print("Example data was not loaded:", exc)


load_example_once()


def drop_g12_programs():
    """Grade 12 has no class program unless it is switched on in School Setup."""
    conn = sqlite3.connect(DB)
    if conn.execute("SELECT 1 FROM settings WHERE k='g12_programs' AND v='1'").fetchone() is None:
        conn.execute("DELETE FROM classes WHERE section_id IN (SELECT id FROM sections WHERE grade=12)")
        conn.commit()
    conn.close()


drop_g12_programs()

if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"),
            port=int(os.environ.get("PORT", 5000)), debug=False)
