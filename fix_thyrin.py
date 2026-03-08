"""Fix: Replace Thyrin 50mcg (1.5 tabs) with Thyrox 50 + Thyrox 25 in live DB."""
import database as db

db.init_db()

# Find and delete old Thyrin entry
meds = db.get_all_medicines()
for m in meds:
    if "thyrin" in m["name"].lower() or "থাইরিন" in (m.get("name_bn") or ""):
        db.delete_medicine(m["id"])
        print(f"  ❌ Deleted: {m['name']} (id={m['id']})")

# Add the two Thyrox entries
START = "2026-03-08"
db.add_medicine("Thyrox 50mg", "থাইরক্স ৫০", "১টা", "shokal", "age", "খালি পেটে", START, None, None)
print("  ✅ Added: Thyrox 50mg (1 tab)")

db.add_medicine("Thyrox 25mg", "থাইরক্স ২৫", "১টা", "shokal", "age", "খালি পেটে", START, None, None)
print("  ✅ Added: Thyrox 25mg (1 tab)")

print("\n🎉 Done!")
