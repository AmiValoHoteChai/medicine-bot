"""
One-time script to seed all 10 prescribed medicines and the follow-up reminder.

Prescription date: 2026-03-07 (printed)
Start date:       2026-03-08 (today — first day of doses)

Run:  python seed_medicines.py
"""

import database as db

db.init_db()

START = "2026-03-08"

# ─────────────────────────────────────────────
#  MEDICINES
#  db.add_medicine(name, name_bn, dose, session, timing, note,
#                  start_date, end_date, dose_plan)
#
#  session: "shokal" | "dupur" | "rater"
#  timing:  "age" (before meal) | "por" (after meal)
# ─────────────────────────────────────────────

medicines = [
    # 1. Pantonix 20mg — 1+0+1, before meal, 21 days → end 2026-03-28
    ("Pantonix 20mg", "প্যানটোনিক্স ২০", "১টা", "shokal", "age", "", START, "2026-03-28", None),
    ("Pantonix 20mg", "প্যানটোনিক্স ২০", "১টা", "rater",  "age", "", START, "2026-03-28", None),

    # 2. Emistat 8mg — 1+0+1, before meal, 5 days → end 2026-03-12
    ("Emistat 8mg", "ইমিস্ট্যাট ৮", "১টা", "shokal", "age", "পরে বমি ভাব হলে", START, "2026-03-12", None),
    ("Emistat 8mg", "ইমিস্ট্যাট ৮", "১টা", "rater",  "age", "পরে বমি ভাব হলে", START, "2026-03-12", None),

    # 3. Napa 500mg — 1+1+1, after meal, as needed (no end date)
    ("Napa 500mg", "নাপা ৫০০", "১টা", "shokal", "por", "মাথা ব্যথা হলে", START, None, None),
    ("Napa 500mg", "নাপা ৫০০", "১টা", "dupur",  "por", "মাথা ব্যথা হলে", START, None, None),
    ("Napa 500mg", "নাপা ৫০০", "১টা", "rater",  "por", "মাথা ব্যথা হলে", START, None, None),

    # 4. Sonexa 4mg — ½+0+0, after meal, ongoing
    ("Sonexa 4mg", "সোনেক্সা ৪", "½টা", "shokal", "por", "৩ দিন, তারপর চলবে", START, None, None),

    # 5. Oradexon 0.5mg — morning only, after meal, 9-day taper
    #    3 tabs × 3 days, 2 tabs × 3 days, 1 tab × 3 days → end 2026-03-16
    ("Oradexon 0.5mg", "ওরাডেক্সন ০.৫", "৩টা", "shokal", "por", "টেপারিং ডোজ", START, "2026-03-16", "3:৩টা, 3:২টা, 3:১টা"),

    # 6. Iracet 500mg — 1+0+1, after meal, ongoing
    ("Iracet 500mg", "ইরাসেট ৫০০", "১টা", "shokal", "por", "চলবে", START, None, None),
    ("Iracet 500mg", "ইরাসেট ৫০০", "১টা", "rater",  "por", "চলবে", START, None, None),

    # 7. Thyrox 50mcg + Thyrox 25mcg — (1+0+0), BEFORE meal (empty stomach), ongoing
    ("Thyrox 50mcg", "থাইরক্স ৫০", "১টা", "shokal", "age", "খালি পেটে", START, None, None),
    ("Thyrox 25mcg", "থাইরক্স ২৫", "১টা", "shokal", "age", "খালি পেটে", START, None, None),

    # 8. Arlin 400mg — 1+0+1, after meal, until 2026-03-13
    ("Arlin 400mg", "আরলিন ৪০০", "১টা", "shokal", "por", "", START, "2026-03-13", None),
    ("Arlin 400mg", "আরলিন ৪০০", "১টা", "rater",  "por", "", START, "2026-03-13", None),

    # 9. Viglimet 50/850 — 1+0+1, after meal, ongoing
    ("Viglimet 50/850", "ভিগলিমেট ৫০/৮৫০", "১টা", "shokal", "por", "চলবে", START, None, None),
    ("Viglimet 50/850", "ভিগলিমেট ৫০/৮৫০", "১টা", "rater",  "por", "চলবে", START, None, None),

    # 10. Mezest 160mg — 0+1+0, after meal, 10 days → end 2026-03-17
    ("Mezest 160mg", "মেজেস্ট ১৬০", "১টা", "dupur", "por", "", START, "2026-03-17", None),
]

print("🔄 Inserting medicines...")
for i, med in enumerate(medicines, 1):
    db.add_medicine(*med)
    session_label = {"shokal": "সকাল", "dupur": "দুপুর", "rater": "রাত"}[med[3]]
    print(f"  ✅ {i:2d}. {med[0]} ({session_label})")

print(f"\n📋 Total medicine entries: {len(medicines)}")

# ─────────────────────────────────────────────
#  FOLLOW-UP REMINDER — 28 days from start
#  2026-03-08 + 28 = 2026-04-05
# ─────────────────────────────────────────────

print("\n🔔 Adding follow-up reminder...")
db.add_reminder(
    title="🏥 ফলো-আপ (Follow-up)",
    message="ফলো-আপের সময় হয়েছে! ডাক্তারের কাছে যান। (Time for your follow-up visit!)",
    remind_date="2026-04-05",
)
print("  ✅ Follow-up reminder set for 2026-04-05 (28 days)")

print("\n🎉 Done! All medicines and reminders are set up.")
