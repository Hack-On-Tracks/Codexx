from ..database import now


def log_event(db, incident_id, event_type: str, user_id, notes: str = "", meta: dict | None = None):
    doc = {"incident_id": incident_id, "event_type": event_type, "performed_by": user_id,
           "timestamp": now(), "notes": notes}
    if meta:
        doc["meta"] = meta
    db.incident_events.insert_one(doc)
