"""OPTIONAL, opt-in demo data. Never runs automatically. Idempotent: inserts only what is missing.
Every record is flagged is_sample=True. No detections or images are invented.

  $env:SEED_PASSWORD = "choose-a-password"
  python seed_demo.py --yes
"""
import os
import sys
from app.database import get_db, now, ensure_indexes
from app.dependencies import hash_password

if "--yes" not in sys.argv:
    sys.exit("Refusing to seed without --yes. See the docstring in this file.")
pw = os.environ.get("SEED_PASSWORD", "")
if len(pw) < 8:
    sys.exit("Set SEED_PASSWORD (8+ characters) in the environment first.")

db = get_db(); ensure_indexes(db)
USERS = [("Priya Deshmukh", "priya.deshmukh@sample.skysnr", "rescue_manager"), ("Rohan Patil", "rohan.patil@sample.skysnr", "rescue_manager"),
         ("Ananya Kulkarni", "ananya.kulkarni@sample.skysnr", "rescue_member"), ("Neha Joshi", "neha.joshi@sample.skysnr", "rescue_member"),
         ("Rahul Verma", "rahul.verma@sample.skysnr", "rescue_member"), ("Sneha Iyer", "sneha.iyer@sample.skysnr", "rescue_member"),
         ("Arjun Nair", "arjun.nair@sample.skysnr", "rescue_member")]
added = 0
for name, email, role in USERS:
    if not db.users.find_one({"email": email}):
        db.users.insert_one({"full_name": name, "email": email, "password_hash": hash_password(pw), "role": role,
                             "approval_status": "approved", "is_active": True, "created_at": now(), "is_sample": True}); added += 1
mgr = db.users.find_one({"email": USERS[0][1]})
for n, d, t, loc in [("Mumbai Urban Flood Response", "flood", "flood", "Kurla, Mumbai"), ("Pune Building Collapse Assessment", "earthquake_building_collapse", "urban_earthquake", "Pune"),
                     ("Thane Waterlogged Road Inspection", "flood", "flood", "Thane"), ("Chennai Flood-Affected Neighbourhood Survey", "flood", "flood", "Chennai")]:
    if not db.missions.find_one({"mission_name": n, "is_sample": True}):
        db.missions.insert_one({"mission_name": n, "disaster_type": d, "terrain_type": t, "location_description": loc, "created_by": mgr["_id"],
                                "status": "created", "created_at": now(), "media_reference": None, "is_sample": True}); added += 1
print(f"Inserted {added} missing sample record(s). Existing records were not modified.")
