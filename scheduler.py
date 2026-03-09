import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

import database as db
import telegram_bot
from config import TIMEZONE

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _fire_reminder(session: str):
    logger.info(f"[Scheduler] Firing reminder: {session}")
    medicines = db.get_medicines_for_session(session)

    if not medicines:
        logger.info(f"[Scheduler] No active medicines for {session}, skipping.")
        return

    # Telegram recipients
    tg_recipients = db.get_active_recipients()
    if tg_recipients:
        results = telegram_bot.broadcast_reminder(session, medicines, tg_recipients)
        for r in results:
            logger.info(f"  → [TG] {r['name']}: {r['result']}")


def _check_reminders():
    """Check and send any pending date-based reminders (e.g. follow-up)."""
    import pytz
    from datetime import datetime as _dt
    today_str = _dt.now(pytz.timezone(TIMEZONE)).strftime("%Y-%m-%d")
    pending = db.get_pending_reminders(today_str)
    if not pending:
        return

    recipients = db.get_active_recipients()
    if not recipients:
        logger.info("[Reminders] No active recipients, skipping.")
        return

    for rem in pending:
        msg = f"🔔 *{rem['title']}*\n\n{rem['message']}"
        for rec in recipients:
            telegram_bot.send_plain_message(rec["chat_id"], msg)
            logger.info(f"[Reminder] Sent '{rem['title']}' → {rec['name']}")
        db.mark_reminder_sent(rem["id"])


def _time_to_hm(t: str):
    """Parse 'HH:MM' → (int hour, int minute)."""
    h, m = t.split(":")
    return int(h), int(m)


def start_scheduler():
    global _scheduler
    settings = db.get_settings()

    sh, sm = _time_to_hm(settings.get("shokal_time", "08:00"))
    dh, dm = _time_to_hm(settings.get("dupur_time",  "14:00"))
    rh, rm = _time_to_hm(settings.get("rater_time",  "21:00"))

    _scheduler = BackgroundScheduler(timezone=TIMEZONE)

    _scheduler.add_job(
        lambda: _fire_reminder("shokal"),
        CronTrigger(hour=sh, minute=sm),
        id="shokal", replace_existing=True
    )
    _scheduler.add_job(
        lambda: _fire_reminder("dupur"),
        CronTrigger(hour=dh, minute=dm),
        id="dupur", replace_existing=True
    )
    _scheduler.add_job(
        lambda: _fire_reminder("rater"),
        CronTrigger(hour=rh, minute=rm),
        id="rater", replace_existing=True
    )

    # Daily reminder checker at 07:00 AM (before medicine reminders)
    _scheduler.add_job(
        _check_reminders,
        CronTrigger(hour=7, minute=0),
        id="reminder_check", replace_existing=True
    )

    _scheduler.start()
    logger.info(f"[Scheduler] Started — সকাল {settings['shokal_time']}, "
                f"দুপুর {settings['dupur_time']}, রাত {settings['rater_time']}")
    return _scheduler


def reschedule(settings: dict):
    """Re-apply cron times after settings update."""
    global _scheduler
    if not _scheduler:
        return

    for session, key in [("shokal","shokal_time"),("dupur","dupur_time"),("rater","rater_time")]:
        h, m = _time_to_hm(settings.get(key, "08:00"))
        _scheduler.reschedule_job(
            session,
            trigger=CronTrigger(hour=h, minute=m)
        )
    logger.info("[Scheduler] Rescheduled successfully.")
