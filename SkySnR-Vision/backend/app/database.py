"""MongoDB access. Never drops or resets collections; only creates missing indexes."""
from bson import ObjectId
from bson.errors import InvalidId
from datetime import datetime, timezone
from fastapi import HTTPException
from pymongo import MongoClient, ASCENDING, DESCENDING

from .config import get_settings

_db = None


def get_db():
    global _db
    if _db is None:
        s = get_settings()
        client = MongoClient(s.mongodb_uri, serverSelectionTimeoutMS=5000)
        _db = client[s.mongodb_database]
    return _db


def set_db(db):
    """Used by tests to inject a different database."""
    global _db
    _db = db


def ensure_indexes(db) -> None:
    # Existing data is untouched. Unique email index is skipped if existing
    # duplicate emails would make it fail (reported, not fatal).
    try:
        db.users.create_index("email", unique=True)
    except Exception as exc:  # pragma: no cover
        print(f"[warn] could not create unique email index: {exc}")
    db.users.create_index([("approval_status", ASCENDING), ("role", ASCENDING)])
    db.missions.create_index([("created_at", DESCENDING)])
    db.detections.create_index("mission_id")
    db.incidents.create_index([("status", ASCENDING), ("priority_level", ASCENDING)])
    db.incidents.create_index("assigned_member_id")
    db.incidents.create_index("mission_id")
    db.incidents.create_index("detection_id", unique=True)
    db.incident_events.create_index([("incident_id", ASCENDING), ("timestamp", ASCENDING)])
    db.reports.create_index("mission_id")


def now() -> datetime:
    return datetime.now(timezone.utc)


def oid(value: str, label: str = "id") -> ObjectId:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=422, detail=f"Invalid {label}")


def ser(doc):
    """Make a Mongo document JSON-safe. Never leaks password hashes."""
    if doc is None:
        return None
    if isinstance(doc, list):
        return [ser(d) for d in doc]
    if isinstance(doc, dict):
        out = {}
        for k, v in doc.items():
            if k == "password_hash":
                continue
            out["id" if k == "_id" else k] = ser(v)
        return out
    if isinstance(doc, ObjectId):
        return str(doc)
    if isinstance(doc, datetime):
        if doc.tzinfo is None:
            doc = doc.replace(tzinfo=timezone.utc)
        return doc.isoformat()
    return doc
