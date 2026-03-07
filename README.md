# 💊 Medicine Reminder Bot

A Telegram bot that sends daily medicine reminders to family members in Bengali.

## Features
- 🤖 Telegram bot — family members send `/start` to auto-register
- 📋 Web dashboard to manage medicines, recipients, and reminder times
- ⏰ Three sessions: morning (সকাল), noon (দুপুর), night (রাত)
- 🍽️ Medicines grouped by before/after meals
- 🔒 Password-protected dashboard

## Tech Stack
Python · Flask · SQLite · APScheduler · Telegram Bot API

## Installation
See **[INSTALL.md](INSTALL.md)** for the full step-by-step guide.

## Quick Reference
```bash
# Start manually
source venv/bin/activate && python app.py

# View logs
sudo journalctl -u medicine-bot -f

# Restart service
sudo systemctl restart medicine-bot
```
