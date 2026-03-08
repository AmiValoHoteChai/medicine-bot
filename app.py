import logging
from datetime import datetime
from flask import (Flask, render_template, request, redirect,
                   url_for, flash, jsonify, session)
from functools import wraps

import config
import database as db
import telegram_bot
import messenger_bot
import scheduler as sched

# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("medicine_bot.log")]
)

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

db.init_db()
sched.start_scheduler()

TRANSLATIONS = {
    "bn": {
        "wrong_password": "ভুল পাসওয়ার্ড!",
        "fill_all_fields": "সব তথ্য সঠিকভাবে পূরণ করুন।",
        "medicine_added": "✅ '{name}' যোগ করা হয়েছে।",
        "medicine_deleted": "ওষুধ মুছে ফেলা হয়েছে।",
        "medicine_updated": "ওষুধ আপডেট হয়েছে।",
        "recipient_name_chatid_required": "নাম এবং Chat ID দিন।",
        "recipient_added": "✅ {name} যোগ করা হয়েছে।",
        "recipient_exists": "এই Chat ID আগে থেকে আছে।",
        "recipient_deleted": "প্রাপক মুছে ফেলা হয়েছে।",
        "settings_updated": "⏰ সময় আপডেট হয়েছে।",
        "test_sent": "টেস্ট বার্তা পাঠানো হয়েছে ({count} জনকে)।",
        "invalid_schedule_dates": "তারিখ সঠিক নয়।",
        "invalid_dose_plan": "ডোজ পরিকল্পনা ভুল। উদাহরণ: 3:3, 3:2, 3:1",
        "invalid_end_before_start": "শেষ তারিখ শুরুর তারিখের আগে হতে পারবে না।",
    },
    "en": {
        "wrong_password": "Wrong password!",
        "fill_all_fields": "Please fill all required fields correctly.",
        "medicine_added": "✅ '{name}' added.",
        "medicine_deleted": "Medicine deleted.",
        "medicine_updated": "Medicine updated.",
        "recipient_name_chatid_required": "Name and Chat ID are required.",
        "recipient_added": "✅ {name} added.",
        "recipient_exists": "This Chat ID already exists.",
        "recipient_deleted": "Recipient deleted.",
        "settings_updated": "⏰ Reminder times updated.",
        "test_sent": "Test message sent ({count} recipients).",
        "invalid_schedule_dates": "Invalid date format.",
        "invalid_dose_plan": "Invalid dose plan. Example: 3:3, 3:2, 3:1",
        "invalid_end_before_start": "End date cannot be earlier than start date.",
    },
}


def current_lang():
    lang = session.get("lang", "bn")
    return lang if lang in ("bn", "en") else "bn"


def tr(key, **kwargs):
    lang = current_lang()
    msg = TRANSLATIONS.get(lang, TRANSLATIONS["bn"]).get(key, key)
    return msg.format(**kwargs)


@app.context_processor
def inject_i18n():
    return {"lang": current_lang(), "t": lambda key: tr(key)}


def _valid_date_ymd(value: str | None) -> bool:
    if not value:
        return True
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _dose_plan_is_valid(plan: str | None) -> bool:
    if not plan:
        return True
    for raw in plan.replace("\n", ",").split(","):
        item = raw.strip()
        if not item:
            continue
        if ":" not in item:
            return False
        days_raw, dose_raw = item.split(":", 1)
        try:
            days = int(days_raw.strip())
        except ValueError:
            return False
        if days <= 0 or not dose_raw.strip():
            return False
    return True


# ═══════════════════════════════════════════════════════
#  AUTH — simple password login
# ═══════════════════════════════════════════════════════

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == config.DASHBOARD_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        flash(tr("wrong_password"), "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("login"))


@app.route("/language/<lang_code>")
def set_language(lang_code):
    session["lang"] = "en" if lang_code == "en" else "bn"
    return redirect(request.referrer or url_for("dashboard"))


# ═══════════════════════════════════════════════════════
#  DASHBOARD
# ═══════════════════════════════════════════════════════

@app.route("/")
@login_required
def dashboard():
    medicines  = db.get_all_medicines()
    recipients = db.get_all_recipients()
    settings   = db.get_settings()
    reminders  = db.get_all_reminders()

    grouped = {"shokal": [], "dupur": [], "rater": []}
    for m in medicines:
        grouped[m["session"]].append(m)

    return render_template(
        "index.html",
        grouped=grouped,
        recipients=recipients,
        settings=settings,
        medicines=medicines,
        reminders=reminders,
    )


# ═══════════════════════════════════════════════════════
#  MEDICINES
# ═══════════════════════════════════════════════════════

@app.route("/medicine/add", methods=["POST"])
@login_required
def add_medicine():
    name    = request.form.get("name", "").strip()
    name_bn = request.form.get("name_bn", "").strip()
    dose    = request.form.get("dose", "১টা").strip()
    sess    = request.form.get("session")
    timing  = request.form.get("timing")
    note    = request.form.get("note", "").strip()
    start_date = request.form.get("start_date", "").strip() or None
    end_date = request.form.get("end_date", "").strip() or None
    dose_plan = request.form.get("dose_plan", "").strip() or None

    if not name or sess not in ("shokal","dupur","rater") or timing not in ("age","por"):
        flash(tr("fill_all_fields"), "danger")
        return redirect(url_for("dashboard"))
    if not _valid_date_ymd(start_date) or not _valid_date_ymd(end_date):
        flash(tr("invalid_schedule_dates"), "danger")
        return redirect(url_for("dashboard"))
    if start_date and end_date and end_date < start_date:
        flash(tr("invalid_end_before_start"), "danger")
        return redirect(url_for("dashboard"))
    if not _dose_plan_is_valid(dose_plan):
        flash(tr("invalid_dose_plan"), "danger")
        return redirect(url_for("dashboard"))

    if dose_plan and not start_date:
        start_date = datetime.now().strftime("%Y-%m-%d")

    db.add_medicine(name, name_bn, dose, sess, timing, note, start_date, end_date, dose_plan)
    flash(tr("medicine_added", name=(name_bn or name)), "success")
    return redirect(url_for("dashboard"))


@app.route("/medicine/toggle/<int:med_id>", methods=["POST"])
@login_required
def toggle_medicine(med_id):
    db.toggle_medicine(med_id)
    return redirect(url_for("dashboard"))


@app.route("/medicine/delete/<int:med_id>", methods=["POST"])
@login_required
def delete_medicine(med_id):
    db.delete_medicine(med_id)
    flash(tr("medicine_deleted"), "info")
    return redirect(url_for("dashboard"))


@app.route("/medicine/edit/<int:med_id>", methods=["POST"])
@login_required
def edit_medicine(med_id):
    start_date = request.form.get("start_date", "").strip() or None
    end_date = request.form.get("end_date", "").strip() or None
    dose_plan = request.form.get("dose_plan", "").strip() or None
    if not _valid_date_ymd(start_date) or not _valid_date_ymd(end_date):
        flash(tr("invalid_schedule_dates"), "danger")
        return redirect(url_for("dashboard"))
    if start_date and end_date and end_date < start_date:
        flash(tr("invalid_end_before_start"), "danger")
        return redirect(url_for("dashboard"))
    if not _dose_plan_is_valid(dose_plan):
        flash(tr("invalid_dose_plan"), "danger")
        return redirect(url_for("dashboard"))
    if dose_plan and not start_date:
        start_date = datetime.now().strftime("%Y-%m-%d")

    db.update_medicine(
        med_id,
        request.form.get("name","").strip(),
        request.form.get("name_bn","").strip(),
        request.form.get("dose","১টা").strip(),
        request.form.get("session"),
        request.form.get("timing"),
        request.form.get("note","").strip(),
        start_date,
        end_date,
        dose_plan,
    )
    flash(tr("medicine_updated"), "success")
    return redirect(url_for("dashboard"))


# ═══════════════════════════════════════════════════════
#  RECIPIENTS
# ═══════════════════════════════════════════════════════

@app.route("/recipient/add", methods=["POST"])
@login_required
def add_recipient():
    name    = request.form.get("name","").strip()
    chat_id = request.form.get("chat_id","").strip()

    if not name or not chat_id:
        flash(tr("recipient_name_chatid_required"), "danger")
        return redirect(url_for("dashboard"))

    ok = db.add_recipient(name, chat_id)
    if ok:
        flash(tr("recipient_added", name=name), "success")
    else:
        flash(tr("recipient_exists"), "warning")
    return redirect(url_for("dashboard"))


@app.route("/recipient/toggle/<int:rec_id>", methods=["POST"])
@login_required
def toggle_recipient(rec_id):
    db.toggle_recipient(rec_id)
    return redirect(url_for("dashboard"))


@app.route("/recipient/delete/<int:rec_id>", methods=["POST"])
@login_required
def delete_recipient(rec_id):
    db.delete_recipient(rec_id)
    flash(tr("recipient_deleted"), "info")
    return redirect(url_for("dashboard"))


# ═══════════════════════════════════════════════════════
#  SETTINGS
# ═══════════════════════════════════════════════════════

@app.route("/settings/save", methods=["POST"])
@login_required
def save_settings():
    shokal = request.form.get("shokal_time","08:00")
    dupur  = request.form.get("dupur_time","14:00")
    rater  = request.form.get("rater_time","21:00")

    db.save_settings(shokal, dupur, rater)
    sched.reschedule({"shokal_time": shokal, "dupur_time": dupur, "rater_time": rater})
    flash(tr("settings_updated"), "success")
    return redirect(url_for("dashboard"))


# ═══════════════════════════════════════════════════════
#  TEST SEND
# ═══════════════════════════════════════════════════════

@app.route("/test/send/<sess>", methods=["POST"])
@login_required
def test_send(sess):
    if sess not in ("shokal","dupur","rater"):
        return jsonify({"error": "invalid session"}), 400

    medicines  = db.get_medicines_for_session(sess)

    # Send to Telegram recipients
    tg_recipients = db.get_active_recipients(platform="telegram")
    tg_results    = telegram_bot.broadcast_reminder(sess, medicines, tg_recipients)

    # Send to Messenger recipients
    fb_recipients = db.get_active_recipients(platform="messenger")
    fb_results    = messenger_bot.broadcast_reminder(sess, medicines, fb_recipients)

    total = len(tg_results) + len(fb_results)
    flash(tr("test_sent", count=total), "info")
    return redirect(url_for("dashboard"))


# ═══════════════════════════════════════════════════════
#  TELEGRAM WEBHOOK
# ═══════════════════════════════════════════════════════

@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    """
    Receive Telegram updates.
    When someone sends /start, auto-register them as a recipient.
    """
    data = request.get_json(silent=True)
    if not data:
        return "OK", 200

    try:
        message = data.get("message", {})
        if not message:
            return "OK", 200

        chat_id   = str(message["chat"]["id"])
        text      = message.get("text", "").strip()
        first     = message["chat"].get("first_name", "")
        last      = message["chat"].get("last_name", "")
        full_name = f"{first} {last}".strip() or "Unknown"

        logging.info(f"[Telegram] Message from {full_name} ({chat_id}): {text}")

        if text.lower() == "/start":
            # Auto-register the user
            if not db.recipient_exists(chat_id):
                db.add_recipient(full_name, chat_id)
                telegram_bot.send_plain_message(
                    chat_id,
                    f"আস্সালামু আলাইকুম {first}! 👋\n"
                    "আপনি ওষুধের রিমাইন্ডার তালিকায় যোগ হয়েছেন। ✅\n"
                    "প্রতিদিন সকাল, দুপুর ও রাতে আপনি ওষুধের রিমাইন্ডার পাবেন। 💊"
                )
            else:
                telegram_bot.send_plain_message(
                    chat_id,
                    f"আপনি ইতিমধ্যে তালিকায় আছেন, {first}! ✅\n"
                    "রিমাইন্ডার আসতে থাকবে। 💊"
                )
        else:
            telegram_bot.send_plain_message(
                chat_id,
                "আস্সালামু আলাইকুম! 👋\n"
                "এই বট আপনাকে ওষুধের রিমাইন্ডার পাঠাবে।\n"
                "/start চাপুন তালিকায় যোগ হতে।"
            )
    except Exception as e:
        logging.error(f"[Telegram Webhook] Error: {e}")

    return "OK", 200


# ═══════════════════════════════════════════════════════
#  MESSENGER WEBHOOK
# ═══════════════════════════════════════════════════════

@app.route("/messenger/webhook", methods=["GET"])
def messenger_verify():
    """Facebook webhook verification (GET request)."""
    mode      = request.args.get("hub.mode")
    token     = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == config.FB_VERIFY_TOKEN:
        logging.info("[Messenger] Webhook verified!")
        return challenge, 200
    else:
        logging.warning("[Messenger] Webhook verification failed.")
        return "Forbidden", 403


@app.route("/messenger/webhook", methods=["POST"])
def messenger_webhook():
    """
    Receive Messenger messages.
    When someone sends a message, auto-register them as a recipient.
    """
    data = request.get_json(silent=True)
    if not data or data.get("object") != "page":
        return "OK", 200

    try:
        for entry in data.get("entry", []):
            for event in entry.get("messaging", []):
                sender_id = event["sender"]["id"]
                message   = event.get("message", {})
                text      = message.get("text", "").strip()

                logging.info(f"[Messenger] Message from {sender_id}: {text}")

                if text.lower() in ("start", "/start", "hi", "hello", "হাই"):
                    if not db.recipient_exists(sender_id):
                        db.add_recipient(f"FB_{sender_id}", sender_id, platform="messenger")
                        messenger_bot.send_plain_message(
                            sender_id,
                            "আস্সালামু আলাইকুম! 👋\n"
                            "আপনি ওষুধের রিমাইন্ডার তালিকায় যোগ হয়েছেন। ✅\n"
                            "প্রতিদিন সকাল, দুপুর ও রাতে আপনি ওষুধের রিমাইন্ডার পাবেন। 💊"
                        )
                    else:
                        messenger_bot.send_plain_message(
                            sender_id,
                            "আপনি ইতিমধ্যে তালিকায় আছেন! ✅\n"
                            "রিমাইন্ডার আসতে থাকবে। 💊"
                        )
                else:
                    messenger_bot.send_plain_message(
                        sender_id,
                        "আস্সালামু আলাইকুম! 👋\n"
                        "এই বট আপনাকে ওষুধের রিমাইন্ডার পাঠাবে।\n"
                        '"start" লিখুন তালিকায় যোগ হতে।'
                    )
    except Exception as e:
        logging.error(f"[Messenger Webhook] Error: {e}")

    return "OK", 200


# ═══════════════════════════════════════════════════════
#  HEALTH CHECK
# ═══════════════════════════════════════════════════════

@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


# ═══════════════════════════════════════════════════════
#  REMINDERS
# ═══════════════════════════════════════════════════════

@app.route("/reminder/add", methods=["POST"])
@login_required
def add_reminder():
    title   = request.form.get("title", "").strip()
    message = request.form.get("message", "").strip()
    remind_date = request.form.get("remind_date", "").strip()

    if not title or not message or not remind_date:
        flash(tr("fill_all_fields"), "danger")
        return redirect(url_for("dashboard"))
    if not _valid_date_ymd(remind_date):
        flash(tr("invalid_schedule_dates"), "danger")
        return redirect(url_for("dashboard"))

    db.add_reminder(title, message, remind_date)
    flash("✅ রিমাইন্ডার যোগ হয়েছে।" if current_lang() == "bn" else "✅ Reminder added.", "success")
    return redirect(url_for("dashboard"))


@app.route("/reminder/delete/<int:rem_id>", methods=["POST"])
@login_required
def delete_reminder(rem_id):
    db.delete_reminder(rem_id)
    flash("রিমাইন্ডার মুছে ফেলা হয়েছে।" if current_lang() == "bn" else "Reminder deleted.", "info")
    return redirect(url_for("dashboard"))


# ─────────────────────────────────────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config.PORT, debug=False)
