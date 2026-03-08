import requests
import logging
from config import FB_PAGE_ACCESS_TOKEN

logger = logging.getLogger(__name__)

FB_GRAPH_URL = "https://graph.facebook.com/v19.0/me/messages"


# ─────────────────────────────────────────────
#  API calls
# ─────────────────────────────────────────────

def send_plain_message(recipient_id: str, text: str) -> dict:
    """Send a plain text message to a Messenger user."""
    if not FB_PAGE_ACCESS_TOKEN:
        logger.error("[Messenger] FB_PAGE_ACCESS_TOKEN not set!")
        return {"ok": False, "error": "No page access token"}

    payload = {
        "recipient": {"id": recipient_id},
        "message":   {"text": text},
        "messaging_type": "UPDATE",
    }
    headers = {
        "Authorization": f"Bearer {FB_PAGE_ACCESS_TOKEN}",
        "Content-Type":  "application/json",
    }
    try:
        r = requests.post(FB_GRAPH_URL, json=payload, headers=headers, timeout=10)
        data = r.json()
        if r.status_code != 200:
            logger.error(f"[Messenger] API error → {data}")
            return {"ok": False, "error": data}
        return {"ok": True, "result": data}
    except Exception as e:
        logger.error(f"[Messenger] Request failed → {e}")
        return {"ok": False, "error": str(e)}


# ─────────────────────────────────────────────
#  Broadcast  (uses the same message builder from telegram_bot)
# ─────────────────────────────────────────────

def broadcast_reminder(session: str, medicines: list, recipients: list) -> list:
    """
    Send the session reminder to all active Messenger recipients.
    Reuses telegram_bot.build_bangla_message for the text.
    """
    from telegram_bot import build_bangla_message

    if not medicines or not recipients:
        return []

    message = build_bangla_message(session, medicines)
    results = []

    for rec in recipients:
        result = send_plain_message(rec["chat_id"], message)
        status = "✅ sent" if result.get("ok") else f"❌ {result}"
        logger.info(f"[Messenger Broadcast] {rec['name']} ({rec['chat_id']}) → {status}")
        results.append({"name": rec["name"], "chat_id": rec["chat_id"], "result": result})

    return results
