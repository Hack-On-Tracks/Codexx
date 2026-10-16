"""Controlled admin setup (admins can never register publicly).
Usage: python create_admin.py "Full Name" email@example.com
The password is prompted; an existing account with that email is never overwritten."""
import getpass
import sys
from app.database import get_db, now, ensure_indexes
from app.dependencies import hash_password

if len(sys.argv) != 3:
    sys.exit('Usage: python create_admin.py "Full Name" email@example.com')
name, email = sys.argv[1], sys.argv[2].lower()
db = get_db()
ensure_indexes(db)
if db.users.find_one({"email": email}):
    sys.exit("An account with that email already exists. Nothing was changed.")
pw = getpass.getpass("Password (min 8 chars): ")
if len(pw) < 8 or pw != getpass.getpass("Confirm: "):
    sys.exit("Passwords must match and be at least 8 characters.")
db.users.insert_one({"full_name": name, "email": email, "password_hash": hash_password(pw), "role": "admin",
                     "approval_status": "approved", "is_active": True, "created_at": now()})
print("Admin created.")
