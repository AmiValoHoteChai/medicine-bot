import requests
import logging
import html as html_lib
from datetime import datetime, date
import pytz
from config import TELEGRAM_API_BASE, TIMEZONE

logger = logging.getLogger(__name__)

SESSION_INFO = {
    "shokal": ("🌅", "সকালের ওষুধ"),
    "dupur":  ("☀️", "দুপুরের ওষুধ"),
    "rater":  ("🌙", "রাতের ওষুধ"),
}

BANGLA_MONTHS = {
    1: "জানুয়ারি", 2: "ফেব্রুয়ারি", 3: "মার্চ", 4: "এপ্রিল",
    5: "মে", 6: "জুন", 7: "জুলাই", 8: "আগস্ট",
    9: "সেপ্টেম্বর", 10: "অক্টোবর", 11: "নভেম্বর", 12: "ডিসেম্বর",
}

BANGLA_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")

SHORT_MONTHS = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def _dhaka_time() -> str:
    tz  = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    return now.strftime("%I:%M %p")


def _short_end(end_date_str):
    """Convert '2026-03-10' → 'Mar 10' for table display."""
    if not end_date_str:
        return ""
    try:
        d = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        return f"{SHORT_MONTHS.get(d.month, '')} {d.day}"
    except ValueError:
        return ""


ASCII_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")

def _dose_ascii(dose_str):
    """Convert Bangla dose to ASCII for table alignment. ১টা→1, ½টা→0.5"""
    s = dose_str.replace("টা", "").strip()
    s = s.translate(ASCII_DIGITS)
    if s == "½":
        s = "0.5"
    return s


def _ascii_table(headers, rows):
    """Build an ASCII table like SQLite output."""
    widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            widths[i] = max(widths[i], len(val))

    sep = "+" + "+".join("-" * (w + 2) for w in widths) + "+"

    def fmt(vals):
        return "|" + "|".join(f" {v.ljust(w)} " for v, w in zip(vals, widths)) + "|"

    lines = [sep, fmt(headers), sep]
    for row in rows:
        lines.append(fmt(row))
    lines.append(sep)
    return "\n".join(lines)


def _med_table(medicines):
    """Build a medicine table for a timing group."""
    headers = ("#", "Medicine", "Dose", "End", "Note")
    rows = []
    for i, m in enumerate(medicines, 1):
        name = m["name"] if m.get("name") else m["name_bn"]
        dose = _dose_ascii(m.get("effective_dose") or m.get("dose", ""))
        end  = _short_end(m.get("end_date")) or "-"
        note = m.get("note", "") or ""
        rows.append((str(i), name, dose, end, note))
    return _ascii_table(headers, rows)



# ─────────────────────────────────────────────
#  Message builders — 3 styles
# ─────────────────────────────────────────────

def _format_end_bangla(end_date_str):
    """'2026-03-10' → '📅 শেষ: ১০ মার্চ'"""
    if not end_date_str:
        return None
    try:
        d = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        day = str(d.day).translate(BANGLA_DIGITS)
        month = BANGLA_MONTHS.get(d.month, "")
        return f"📅 শেষ: {day} {month}"
    except ValueError:
        return None


def _build_list(session, medicines):
    """Original list style with numbered items and end dates."""
    icon, label = SESSION_INFO.get(session, ("💊", "ওষুধ"))
    now_str = _dhaka_time()

    age_meds = [m for m in medicines if m["timing"] == "age"]
    por_meds = [m for m in medicines if m["timing"] == "por"]

    lines = [f"{icon} {label} — {now_str}", "", "━━━━━━━━━━━━━━━━━━"]

    if age_meds:
        lines.append("🍽️ খাওয়ার আগে")
        lines.append("")
        for i, m in enumerate(age_meds, 1):
            display = m["name"] if m.get("name") else m["name_bn"]
            dose = m.get("effective_dose") or m.get("dose", "১টা")
            lines.append(f"{i}. {display}  ·  {dose}")
            end_label = _format_end_bangla(m.get("end_date"))
            if end_label:
                lines.append(f"   {end_label}")
            lines.append("")

    if age_meds and por_meds:
        lines.append("━━━━━━━━━━━━━━━━━━")

    if por_meds:
        lines.append("✅ খাওয়ার পরে")
        lines.append("")
        for i, m in enumerate(por_meds, 1):
            display = m["name"] if m.get("name") else m["name_bn"]
            dose = m.get("effective_dose") or m.get("dose", "১টা")
            lines.append(f"{i}. {display}  ·  {dose}")
            end_label = _format_end_bangla(m.get("end_date"))
            if end_label:
                lines.append(f"   {end_label}")
            lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━")
    if not age_meds and not por_meds:
        lines.append("আজকের জন্য কোনো ওষুধ নেই।")
    else:
        lines.append("🤲 সুস্থ থাকুন!")

    return "\n".join(lines), False  # (message, is_html)


def _build_table(session, medicines):
    """SQLite-style ASCII table with monospace rendering."""
    icon, label = SESSION_INFO.get(session, ("💊", "ওষুধ"))
    now_str = _dhaka_time()

    age_meds = [m for m in medicines if m["timing"] == "age"]
    por_meds = [m for m in medicines if m["timing"] == "por"]

    parts = [f"{icon} <b>{label}</b> — {now_str}", ""]

    if age_meds:
        parts.append("🍽️ <b>খাওয়ার আগে</b>")
        table = html_lib.escape(_med_table(age_meds))
        parts.append(f"<pre>{table}</pre>")

    if por_meds:
        parts.append("✅ <b>খাওয়ার পরে</b>")
        table = html_lib.escape(_med_table(por_meds))
        parts.append(f"<pre>{table}</pre>")

    if not age_meds and not por_meds:
        parts.append("আজকের জন্য কোনো ওষুধ নেই।")
    else:
        parts.append("🤲 সুস্থ থাকুন!")

    return "\n".join(parts), True  # (message, is_html)


def _build_card(session, medicines):
    """Card style with box borders and bullet points."""
    icon, label = SESSION_INFO.get(session, ("💊", "ওষুধ"))
    now_str = _dhaka_time()

    age_meds = [m for m in medicines if m["timing"] == "age"]
    por_meds = [m for m in medicines if m["timing"] == "por"]

    lines = [
        "╔══════════════════════╗",
        f"   {icon} {label}",
        f"   ⏰ {now_str}",
        "╚══════════════════════╝",
        "",
    ]

    if age_meds:
        lines.append("🍽️ খাওয়ার আগে")
        lines.append("┌─────────────────────────┐")
        for m in age_meds:
            display = m["name"] if m.get("name") else m["name_bn"]
            dose = m.get("effective_dose") or m.get("dose", "১টা")
            end = _short_end(m.get("end_date"))
            line = f"  💊 {display} — {dose}"
            if end:
                line += f" ({end})"
            lines.append(line)
        lines.append("└─────────────────────────┘")
        lines.append("")

    if por_meds:
        lines.append("✅ খাওয়ার পরে")
        lines.append("┌─────────────────────────┐")
        for m in por_meds:
            display = m["name"] if m.get("name") else m["name_bn"]
            dose = m.get("effective_dose") or m.get("dose", "১টা")
            end = _short_end(m.get("end_date"))
            line = f"  💊 {display} — {dose}"
            if end:
                line += f" ({end})"
            lines.append(line)
        lines.append("└─────────────────────────┘")
        lines.append("")

    if not age_meds and not por_meds:
        lines.append("আজকের জন্য কোনো ওষুধ নেই।")
    else:
        lines.append("🤲 সুস্থ থাকুন!")

    return "\n".join(lines), False  # (message, is_html)


STYLE_BUILDERS = {
    "list":  _build_list,
    "table": _build_table,
    "card":  _build_card,
}


def build_bangla_message(session: str, medicines: list, style: str = "table"):
    """
    Build a reminder message using the chosen style.
    Returns (message_text, is_html) tuple.
    """
    builder = STYLE_BUILDERS.get(style, _build_table)
    return builder(session, medicines)


# ─────────────────────────────────────────────
#  API calls
# ─────────────────────────────────────────────

def send_html_message(chat_id, html_text: str) -> dict:
    """Send an HTML-formatted message to a Telegram chat."""
    url = f"{TELEGRAM_API_BASE}/sendMessage"
    payload = {
        "chat_id":    chat_id,
        "text":       html_text,
        "parse_mode": "HTML",
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        data = r.json()
        if not data.get("ok"):
            logger.error(f"[Telegram] HTML send error → {data}")
            payload["parse_mode"] = ""
            r = requests.post(url, json=payload, timeout=10)
            data = r.json()
        return data
    except Exception as e:
        logger.error(f"[Telegram] Request failed → {e}")
        return {"ok": False, "error": str(e)}


def send_text_message(chat_id, text: str) -> dict:
    """Send a text message to a Telegram chat."""
    url = f"{TELEGRAM_API_BASE}/sendMessage"
    payload = {
        "chat_id":    chat_id,
        "text":       text,
        "parse_mode": "MarkdownV2",
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        data = r.json()
        if not data.get("ok"):
            logger.error(f"[Telegram] API error → {data}")
            if "can't parse" in str(data.get("description", "")).lower():
                payload["parse_mode"] = ""
                payload["text"] = text
                r = requests.post(url, json=payload, timeout=10)
                data = r.json()
        return data
    except Exception as e:
        logger.error(f"[Telegram] Request failed → {e}")
        return {"ok": False, "error": str(e)}


def send_plain_message(chat_id, text: str) -> dict:
    """Send a plain text message (no markdown)."""
    url = f"{TELEGRAM_API_BASE}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text":    text,
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.json()
    except Exception as e:
        logger.error(f"[Telegram] Request failed → {e}")
        return {"ok": False, "error": str(e)}


# ─────────────────────────────────────────────
#  Broadcast
# ─────────────────────────────────────────────

def broadcast_reminder(session: str, medicines: list, recipients: list, style: str = "table") -> list:
    """
    Send the session reminder to all active recipients.
    Returns a list of {name, chat_id, result} dicts.
    """
    if not medicines or not recipients:
        return []

    message, is_html = build_bangla_message(session, medicines, style)
    send_fn = send_html_message if is_html else send_plain_message
    results = []

    for rec in recipients:
        result = send_fn(rec["chat_id"], message)
        status = "✅ sent" if result.get("ok") else f"❌ {result}"
        logger.info(f"[Broadcast] {rec['name']} ({rec['chat_id']}) → {status}")
        results.append({"name": rec["name"], "chat_id": rec["chat_id"], "result": result})

    return results
