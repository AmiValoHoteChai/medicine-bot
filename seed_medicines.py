"""
Seed script — wipes all medicines & reminders, then inserts fresh data.
Safe to run multiple times.

Run:  python3 seed_medicines.py
"""

import database as db

db.init_db()

START_7 = "2026-03-07"  # Pantonix, Emistat, Napa, Mezest
START_8 = "2026-03-08"  # Sonexa, Oradexon, Iracet, Thyrox, Arlin, Viglimet

# ─────────────────────────────────────────────
#  WIPE existing data
# ─────────────────────────────────────────────

print("🗑️ Clearing old medicines and reminders...")
conn = db.get_db()
conn.execute("DELETE FROM medicines")
conn.execute("DELETE FROM reminders")
conn.commit()
conn.close()
print("  ✅ Cleared.")

# ─────────────────────────────────────────────
#  MEDICINES
#  (name, name_bn, dose, session, timing, note, start, end, dose_plan)
# ─────────────────────────────────────────────

medicines = [
    # 1. Pantonix 20mg — 1+0+1, before meal, 21 days
    ("Pantonix 20mg", "Pantonix 20mg", "1", "shokal", "age", "", START_7, "2026-03-27", None),
    ("Pantonix 20mg", "Pantonix 20mg", "1", "rater",  "age", "", START_7, "2026-03-27", None),

    # 2. Emistat 8mg — 1+0+1, before meal, 5 days
    ("Emistat 8mg", "Emistat 8mg", "1", "shokal", "age", "Take if nauseous", START_7, "2026-03-11", None),
    ("Emistat 8mg", "Emistat 8mg", "1", "rater",  "age", "Take if nauseous", START_7, "2026-03-11", None),

    # 3. Napa 500mg — 1+1+1, after meal, until consultation
    ("Napa 500mg", "Napa 500mg", "1", "shokal", "por", "Take for headache", START_7, "2026-04-05", None),
    ("Napa 500mg", "Napa 500mg", "1", "dupur",  "por", "Take for headache", START_7, "2026-04-05", None),
    ("Napa 500mg", "Napa 500mg", "1", "rater",  "por", "Take for headache", START_7, "2026-04-05", None),

    # 4. Sonexa 4mg — ½+0+0, after meal, 3 days only
    ("Sonexa 4mg", "Sonexa 4mg", "0.5", "shokal", "por", "3 days only", START_8, "2026-03-10", None),

    # 5. Oradexon 0.5mg — morning, after meal, 9-day taper (starts after Sonexa ends)
    ("Oradexon 0.5mg", "Oradexon 0.5mg", "3", "shokal", "por", "Tapering dose", "2026-03-11", "2026-03-19", "3:3, 3:2, 3:1"),

    # 6. Iracet 500mg — 1+0+1, after meal, ongoing
    ("Iracet 500mg", "Iracet 500mg", "1", "shokal", "por", "Ongoing", START_8, None, None),
    ("Iracet 500mg", "Iracet 500mg", "1", "rater",  "por", "Ongoing", START_8, None, None),

    # 7. Thyrox 50mg + Thyrox 25mg — morning, before meal (empty stomach), ongoing
    ("Thyrox 50mg", "Thyrox 50mg", "1", "shokal", "age", "Empty stomach", START_8, None, None),
    ("Thyrox 25mg", "Thyrox 25mg", "1", "shokal", "age", "Empty stomach", START_8, None, None),

    # 8. Arlin 400mg — 1+0+1, after meal, until 2026-03-13
    ("Arlin 400mg", "Arlin 400mg", "1", "shokal", "por", "", START_8, "2026-03-13", None),
    ("Arlin 400mg", "Arlin 400mg", "1", "rater",  "por", "", START_8, "2026-03-13", None),

    # 9. Viglimet 50/850 — 1+0+1, after meal, ongoing
    ("Viglimet 50/850", "Viglimet 50/850", "1", "shokal", "por", "Ongoing", START_8, None, None),
    ("Viglimet 50/850", "Viglimet 50/850", "1", "rater",  "por", "Ongoing", START_8, None, None),

    # 10. Mezest 160mg — 0+1+0, after meal, 10 days
    ("Mezest 160mg", "Mezest 160mg", "1", "dupur", "por", "", START_7, "2026-03-16", None),
]

print("🔄 Inserting medicines...")
for i, med in enumerate(medicines, 1):
    db.add_medicine(*med)
    session_label = {"shokal": "Morning", "dupur": "Noon", "rater": "Night"}[med[3]]
    print(f"  ✅ {i:2d}. {med[0]} ({session_label})")

print(f"\n📋 Total: {len(medicines)} entries")

# ─────────────────────────────────────────────
#  FOLLOW-UP REMINDER — 28 days from start
# ─────────────────────────────────────────────

print("\n🔔 Adding follow-up reminder...")
db.add_reminder(
    title="🏥 Follow-up",
    message="Time for your follow-up visit!",
    remind_date="2026-04-05",
)
print("  ✅ Follow-up: 2026-04-05 (28 days)")

print("\n🎉 Done!")
