import os
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
#  Timezone — always Dhaka, Bangladesh
# ─────────────────────────────────────────────
TIMEZONE = "Asia/Dhaka"

# ─────────────────────────────────────────────
#  Telegram Bot API
# ─────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API_BASE  = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# ─────────────────────────────────────────────
#  Facebook Messenger API
# ─────────────────────────────────────────────
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN", "")
FB_VERIFY_TOKEN      = os.environ.get("FB_VERIFY_TOKEN", "")

# ─────────────────────────────────────────────
#  Daily Reminder Times  (24-hr, Asia/Dhaka)
# ─────────────────────────────────────────────
SHOKAL_TIME = os.environ.get("SHOKAL_TIME", "08:00")   # সকাল
DUPUR_TIME  = os.environ.get("DUPUR_TIME",  "14:00")   # দুপুর
RATER_TIME  = os.environ.get("RATER_TIME",  "21:00")   # রাত

# ─────────────────────────────────────────────
#  App
# ─────────────────────────────────────────────
SECRET_KEY         = os.environ.get("SECRET_KEY", "change-me-in-production")
DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "admin123")
DATABASE           = os.environ.get("DATABASE", "medicine_bot.db")
PORT               = int(os.environ.get("PORT", 5000))
