import sqlite3
from datetime import datetime

import pytz
from config import DATABASE
from config import TIMEZONE


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        c = conn.cursor()

        # Recipients — family members who receive reminders
        c.execute("""
            CREATE TABLE IF NOT EXISTS recipients (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                name     TEXT    NOT NULL,
                chat_id  TEXT    NOT NULL UNIQUE,
                active   INTEGER NOT NULL DEFAULT 1,
                platform TEXT    NOT NULL DEFAULT 'telegram',
                added_at TEXT    DEFAULT (datetime('now','+6 hours'))
            )
        """)

        # Medicines
        c.execute("""
            CREATE TABLE IF NOT EXISTS medicines (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                name    TEXT    NOT NULL,
                name_bn TEXT,
                dose    TEXT    NOT NULL DEFAULT '১টা',
                session TEXT    NOT NULL CHECK(session IN ('shokal','dupur','rater')),
                timing  TEXT    NOT NULL CHECK(timing  IN ('age','por')),
                active  INTEGER NOT NULL DEFAULT 1,
                note    TEXT,
                start_date TEXT,
                end_date   TEXT,
                dose_plan  TEXT
            )
        """)

        # Backward-compatible migration for old databases.
        cols = {row[1] for row in c.execute("PRAGMA table_info(medicines)").fetchall()}
        if "start_date" not in cols:
            c.execute("ALTER TABLE medicines ADD COLUMN start_date TEXT")
        if "end_date" not in cols:
            c.execute("ALTER TABLE medicines ADD COLUMN end_date TEXT")
        if "dose_plan" not in cols:
            c.execute("ALTER TABLE medicines ADD COLUMN dose_plan TEXT")

        # Migration: add platform column to recipients
        rcols = {row[1] for row in c.execute("PRAGMA table_info(recipients)").fetchall()}
        if "platform" not in rcols:
            c.execute("ALTER TABLE recipients ADD COLUMN platform TEXT NOT NULL DEFAULT 'telegram'")

        # Settings — store reminder times
        c.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # Reminders — one-off date-based reminders (e.g. follow-up)
        c.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT NOT NULL,
                message     TEXT NOT NULL,
                remind_date TEXT NOT NULL,
                sent        INTEGER NOT NULL DEFAULT 0
            )
        """)

        # Seed default reminder times if not present
        for key, val in [("shokal_time","08:00"),("dupur_time","14:00"),("rater_time","21:00"),("message_style","table")]:
            c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (key, val))

        conn.commit()


# ── Medicines ────────────────────────────────

def _today_date():
    return datetime.now(pytz.timezone(TIMEZONE)).date()


def _parse_ymd(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_dose_plan(plan: str):
    """
    Format:
      3:3, 3:2, 3:1
      or one entry per line.
    Means: first 3 days dose 3, next 3 days dose 2, next 3 days dose 1.
    """
    if not plan:
        return []

    parts = []
    for raw in plan.replace("\n", ",").split(","):
        item = raw.strip()
        if not item:
            continue
        if ":" not in item:
            continue
        days_raw, dose_raw = item.split(":", 1)
        try:
            days = int(days_raw.strip())
        except ValueError:
            continue
        dose = dose_raw.strip()
        if days > 0 and dose:
            parts.append((days, dose))
    return parts


def _effective_dose_for_today(med: dict):
    today = _today_date()

    start = _parse_ymd(med.get("start_date"))
    end = _parse_ymd(med.get("end_date"))

    if start and today < start:
        return None, "upcoming"
    if end and today > end:
        return None, "expired"

    plan = _parse_dose_plan(med.get("dose_plan") or "")
    if not plan:
        return med.get("dose", "১টা"), "active"

    if not start:
        return med.get("dose", "১টা"), "active"

    day_index = (today - start).days + 1
    if day_index < 1:
        return None, "upcoming"

    upto = 0
    for days, dose in plan:
        upto += days
        if day_index <= upto:
            return dose, "active"
    return None, "expired"


def get_all_medicines():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM medicines ORDER BY session, timing, name").fetchall()
        medicines = [dict(r) for r in rows]
        for med in medicines:
            eff_dose, status = _effective_dose_for_today(med)
            med["effective_dose"] = eff_dose
            med["schedule_status"] = status
        return medicines


def get_medicines_for_session(session):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM medicines WHERE session=? AND active=1 ORDER BY timing, name",
            (session,)
        ).fetchall()
        medicines = []
        for row in rows:
            med = dict(row)
            eff_dose, status = _effective_dose_for_today(med)
            if status == "active" and eff_dose:
                med["effective_dose"] = eff_dose
                med["schedule_status"] = status
                medicines.append(med)
        return medicines


def add_medicine(name, name_bn, dose, session, timing, note="", start_date=None, end_date=None, dose_plan=None):
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO medicines(name,name_bn,dose,session,timing,note,start_date,end_date,dose_plan)
            VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (name, name_bn, dose, session, timing, note, start_date, end_date, dose_plan)
        )
        conn.commit()


def toggle_medicine(med_id):
    with get_db() as conn:
        conn.execute("UPDATE medicines SET active = 1 - active WHERE id=?", (med_id,))
        conn.commit()


def delete_medicine(med_id):
    with get_db() as conn:
        conn.execute("DELETE FROM medicines WHERE id=?", (med_id,))
        conn.commit()


def update_medicine(med_id, name, name_bn, dose, session, timing, note, start_date=None, end_date=None, dose_plan=None):
    with get_db() as conn:
        conn.execute(
            """
            UPDATE medicines
            SET name=?,name_bn=?,dose=?,session=?,timing=?,note=?,start_date=?,end_date=?,dose_plan=?
            WHERE id=?
            """,
            (name, name_bn, dose, session, timing, note, start_date, end_date, dose_plan, med_id)
        )
        conn.commit()


# ── Recipients ───────────────────────────────

def get_all_recipients():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM recipients ORDER BY name").fetchall()
        return [dict(r) for r in rows]


def add_recipient(name, chat_id, platform="telegram"):
    with get_db() as conn:
        try:
            conn.execute("INSERT INTO recipients(name,chat_id,platform) VALUES(?,?,?)", (name, chat_id, platform))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False   # duplicate chat_id


def toggle_recipient(rec_id):
    with get_db() as conn:
        conn.execute("UPDATE recipients SET active = 1 - active WHERE id=?", (rec_id,))
        conn.commit()


def delete_recipient(rec_id):
    with get_db() as conn:
        conn.execute("DELETE FROM recipients WHERE id=?", (rec_id,))
        conn.commit()


def get_active_recipients(platform=None):
    with get_db() as conn:
        if platform:
            rows = conn.execute("SELECT * FROM recipients WHERE active=1 AND platform=?", (platform,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM recipients WHERE active=1").fetchall()
        return [dict(r) for r in rows]


def recipient_exists(chat_id):
    with get_db() as conn:
        row = conn.execute("SELECT id FROM recipients WHERE chat_id=?", (chat_id,)).fetchone()
        return row is not None


# ── Settings ─────────────────────────────────

def get_settings():
    with get_db() as conn:
        rows = conn.execute("SELECT key,value FROM settings").fetchall()
        return {r["key"]: r["value"] for r in rows}


def save_settings(shokal, dupur, rater, message_style="table"):
    with get_db() as conn:
        for key, val in [("shokal_time", shokal), ("dupur_time", dupur), ("rater_time", rater), ("message_style", message_style)]:
            conn.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=?", (key, val, val))
        conn.commit()


# ── Reminders ────────────────────────────────

def add_reminder(title, message, remind_date):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO reminders(title, message, remind_date) VALUES(?,?,?)",
            (title, message, remind_date)
        )
        conn.commit()


def get_all_reminders():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM reminders ORDER BY remind_date").fetchall()
        return [dict(r) for r in rows]


def get_pending_reminders(date_str):
    """Return unsent reminders whose remind_date <= date_str."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM reminders WHERE sent=0 AND remind_date<=? ORDER BY remind_date",
            (date_str,)
        ).fetchall()
        return [dict(r) for r in rows]


def mark_reminder_sent(rem_id):
    with get_db() as conn:
        conn.execute("UPDATE reminders SET sent=1 WHERE id=?", (rem_id,))
        conn.commit()


def delete_reminder(rem_id):
    with get_db() as conn:
        conn.execute("DELETE FROM reminders WHERE id=?", (rem_id,))
        conn.commit()
