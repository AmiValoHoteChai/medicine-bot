# Medicine Reminder Bot — Installation Guide

A Telegram bot that sends daily medicine reminders to your family members in Bengali.

---

## What You Need

- A Linux VPS (Ubuntu 20.04 or newer)
- A domain name (recommended) or just your server IP
- A Telegram account

---

## Step 1 — Create Your Telegram Bot

1. Open Telegram, search for **@BotFather**
2. Send the message: `/newbot`
3. Give your bot a name (e.g. `Family Medicine Reminder`)
4. Give it a username (e.g. `my_medicine_bot`) — must end in `bot`
5. BotFather will give you a **token** that looks like:
   ```
   123456789:ABCDEFabcdef-xYzXyz
   ```
   **Copy and save this token.** You'll need it shortly.

---

## Step 2 — Upload the Project to Your VPS

**SSH into your server:**
```bash
ssh root@YOUR_SERVER_IP
```

**Create a folder for the bot:**
```bash
mkdir -p /opt/medicine-bot
```

**Upload the project files.** From your local Windows PC, open PowerShell and run:
```powershell
scp -r "C:\Users\Hy\Downloads\medicine-bot\medicine-bot\*" root@YOUR_SERVER_IP:/opt/medicine-bot/
```

---

## Step 3 — Install Dependencies

Back in your VPS terminal:

```bash
# Install Python if not already installed
sudo apt update && sudo apt install python3 python3-venv python3-pip -y

# Go to the project folder
cd /opt/medicine-bot

# Create a virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install Python packages
pip install -r requirements.txt
```

---

## Step 4 — Configure the Bot

```bash
cp .env.example .env
nano .env
```

Fill in these values:

```
TELEGRAM_BOT_TOKEN=paste-your-token-here
SECRET_KEY=any-random-long-string
DASHBOARD_PASSWORD=choose-a-password
```

Save and exit: press `Ctrl+O`, then `Enter`, then `Ctrl+X`.

---

## Step 5 — Set Up Nginx (Reverse Proxy)

**Install Nginx:**
```bash
sudo apt install nginx -y
```

**Create a config file:**
```bash
sudo nano /etc/nginx/sites-available/medicine-bot
```

**Paste this** (replace `your-domain.com` with your actual domain or server IP):
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**Enable it:**
```bash
sudo ln -s /etc/nginx/sites-available/medicine-bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## Step 6 — Enable HTTPS (SSL)

> Skip this if you don't have a domain name. You'll need HTTPS for the Telegram webhook.

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```

Follow the prompts. Certbot will auto-configure HTTPS for you.

---

## Step 7 — Set Up the Telegram Webhook

This tells Telegram where to send messages to your bot.

Replace `<TOKEN>` and `<your-domain.com>` in the command below:
```bash
curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://your-domain.com/webhook"
```

You should see: `{"ok":true,"result":true}`

---

## Step 8 — Keep the Bot Running 24/7

This step sets up the bot as a **background service** that:
- Starts **automatically when your server boots**
- **Restarts itself** if it ever crashes
- Keeps running forever without you needing to do anything

**Edit the service file — set your Linux username:**
```bash
nano /opt/medicine-bot/medicine-bot.service
```

Find `YOUR_LINUX_USERNAME` and replace it with your actual username (e.g. `root` or `ubuntu`). Save with `Ctrl+O` → `Enter` → `Ctrl+X`.

**Install and enable the service:**
```bash
sudo cp /opt/medicine-bot/medicine-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable medicine-bot   # auto-start on every reboot
sudo systemctl start medicine-bot    # start right now
```

**Confirm it's running:**
```bash
sudo systemctl status medicine-bot
```

You should see `Active: active (running)` in green. From this point on, **the bot runs 24/7** — you never need to manually start it again, even after a server reboot.

---

## Step 9 — Use the Dashboard

Open your browser and go to:
```
https://your-domain.com
```

Login with the `DASHBOARD_PASSWORD` you set in `.env`.

From the dashboard you can:
- **Add medicines** — name, dose, session (morning/noon/night), timing (before/after food)
- **Add recipients** — family members who receive reminders
- **Change reminder times**
- **Send a test message** anytime

---

## Step 10 — Register Family Members

Tell your family members to:
1. Open Telegram
2. Search for your bot by its username
3. Press **Start** or send `/start`

They will be **automatically registered** and will start receiving reminders.

---

## Useful Commands

| Task | Command |
|---|---|
| View logs | `sudo journalctl -u medicine-bot -f` |
| Restart bot | `sudo systemctl restart medicine-bot` |
| Stop bot | `sudo systemctl stop medicine-bot` |
| Check status | `sudo systemctl status medicine-bot` |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Messages not sending | Check your `TELEGRAM_BOT_TOKEN` in `.env` is correct |
| Dashboard not loading | Run `sudo systemctl status medicine-bot` and check for errors |
| Webhook not working | Re-run the `curl` command in Step 7, make sure HTTPS is set up |
| `/start` not registering | Make sure the webhook is set and the bot is running |
| Forgot dashboard password | Edit `.env`, change `DASHBOARD_PASSWORD`, restart the service |
