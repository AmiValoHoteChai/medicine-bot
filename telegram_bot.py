import requests
import logging
from datetime import datetime
import pytz
from config import TELEGRAM_API_BASE, TIMEZONE

logger = logging.getLogger(__name__)

SESSION_INFO = {
    "shokal": ("🌅", "সকালের ওষুধ"),
    "dupur":  ("☀️", "দুপুরের ওষুধ"),
    "rater":  ("🌙", "রাতের ওষুধ"),
}


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def _dhaka_time() -> str:
    tz  = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    return now.strftime("%I:%M %p")


# ─────────────────────────────────────────────
#  Message builder
# ─────────────────────────────────────────────

def build_bangla_message(session: str, medicines: list) -> str:
    """
    One message per session showing BOTH খাওয়ার আগে and খাওয়ার পরে.
    Uses numbered list format with clean section dividers.
    """
    icon, label = SESSION_INFO.get(session, ("💊", "ওষুধ"))
    now_str     = _dhaka_time()

    age_meds = [m for m in medicines if m["timing"] == "age"]
    por_meds = [m for m in medicines if m["timing"] == "por"]

    lines = [
        f"💊 {label} — {now_str}",
        "",
        "━━━━━━━━━━━━━━━━━━",
    ]

    if age_meds:
        lines.append("🍽️ খাওয়ার আগে")
        lines.append("")
        for i, m in enumerate(age_meds, 1):
            display = m["name_bn"] if m.get("name_bn") else m["name"]
            dose    = m.get("effective_dose") or m.get("dose", "১টা")
            lines.append(f"{i}. {display}  ·  {dose}")
            if m.get("note"):
                lines.append(f"   ⚠️ {m['note']}")
        lines.append("")

    if age_meds and por_meds:
        lines.append("━━━━━━━━━━━━━━━━━━")

    if por_meds:
        lines.append("✅ খাওয়ার পরে")
        lines.append("")
        for i, m in enumerate(por_meds, 1):
            display = m["name_bn"] if m.get("name_bn") else m["name"]
            dose    = m.get("effective_dose") or m.get("dose", "১টা")
            lines.append(f"{i}. {display}  ·  {dose}")
            if m.get("note"):
                lines.append(f"   ⚠️ {m['note']}")
            lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━")

    if not age_meds and not por_meds:
        lines.append("আজকের জন্য কোনো ওষুধ নেই।")
    else:
        lines.append("🤲 সুস্থ থাকুন!")

    return "\n".join(lines)


# ─────────────────────────────────────────────
#  API calls
# ─────────────────────────────────────────────

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
            # Retry without markdown if parsing failed
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

def broadcast_reminder(session: str, medicines: list, recipients: list) -> list:
    """
    Send the session reminder to all active recipients.
    Returns a list of {name, chat_id, result} dicts.
    """
    if not medicines or not recipients:
        return []

    message = build_bangla_message(session, medicines)
    results = []

    for rec in recipients:
        result = send_plain_message(rec["chat_id"], message)
        status = "✅ sent" if result.get("ok") else f"❌ {result}"
        logger.info(f"[Broadcast] {rec['name']} ({rec['chat_id']}) → {status}")
        results.append({"name": rec["name"], "chat_id": rec["chat_id"], "result": result})

    return results
