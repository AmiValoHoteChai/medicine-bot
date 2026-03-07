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
    medicines  = db.get_medicines_for_session(session)
    recipients = db.get_active_recipients()

    if not medicines:
        logger.info(f"[Scheduler] No active medicines for {session}, skipping.")
        return
    if not recipients:
        logger.info(f"[Scheduler] No active recipients, skipping.")
        return

    results = telegram_bot.broadcast_reminder(session, medicines, recipients)
    for r in results:
        logger.info(f"  → {r['name']}: {r['result']}")


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
