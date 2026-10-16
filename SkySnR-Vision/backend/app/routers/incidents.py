from typing import Literal, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from ..database import get_db, now, oid, ser
from ..dependencies import get_current_user, require_manager, require_member, require_roles
from ..utils.events import log_event
from ..utils.files import read_image_upload, save_media

router = APIRouter(prefix="/api", tags=["incidents"])

# Allowed status transitions. Anything else is rejected by the server.
TRANSITIONS = {"pending_assignment": {"assigned"}, "assigned": {"in_progress"},
               "in_progress": {"resolved"}, "resolved": set()}


class IncidentIn(BaseModel):
    detection_id: str
    manager_notes: str = Field(default="", max_length=1000)


class AssignIn(BaseModel):
    member_id: str
    notes: str = Field(default="", max_length=500)


class NoteIn(BaseModel):
    notes: str = Field(min_length=2, max_length=1000)


class NotesPatch(BaseModel):
    manager_notes: str = Field(max_length=1000)


def _own_filter(user, incident_id: str) -> dict:
    f = {"_id": oid(incident_id, "incident id")}
    if user["role"] == "rescue_member":
        f["assigned_member_id"] = user["_id"]  # other members' incidents look like they don't exist
    return f


def _get(db, user, incident_id):
    inc = db.incidents.find_one(_own_filter(user, incident_id))
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    return inc


@router.get("/team")
def team(_=Depends(require_manager), db=Depends(get_db)):
    members = list(db.users.find({"role": "rescue_member", "approval_status": "approved", "is_active": True}))
    out = []
    for m in members:
        out.append({**ser(m),
                    "assigned_total": db.incidents.count_documents({"assigned_member_id": m["_id"]}),
                    "open_assignments": db.incidents.count_documents(
                        {"assigned_member_id": m["_id"], "status": {"$in": ["assigned", "in_progress"]}})})
    return out


@router.post("/incidents", status_code=201)
def create_incident(body: IncidentIn, user=Depends(require_manager), db=Depends(get_db)):
    d = db.detections.find_one({"_id": oid(body.detection_id, "detection id")})
    if not d:
        raise HTTPException(status_code=404, detail="Detection not found")
    if d.get("review_status") != "confirmed":
        raise HTTPException(status_code=409, detail="Only a manager-confirmed detection can become an incident")
    if db.incidents.find_one({"detection_id": d["_id"]}):
        raise HTTPException(status_code=409, detail="An incident already exists for this detection")
    m = db.missions.find_one({"_id": d["mission_id"]})
    ts = now()
    doc = {"mission_id": d["mission_id"], "detection_id": d["_id"],
           "priority_score": d.get("priority_score", 0), "priority_level": d.get("priority_level", "low"),
           "final_priority_level": d.get("final_priority_level") or d.get("priority_level", "low"),
           "explanation": d.get("score_explanation", "No score factors recorded."),
           "terrain_type": (m or {}).get("terrain_type"), "manager_notes": body.manager_notes.strip(),
           "verification_status": "confirmed", "assigned_member_id": None, "status": "pending_assignment",
           "outcome": None, "acknowledged_at": None, "created_by": user["_id"],
           "created_at": ts, "updated_at": ts}
    doc["_id"] = db.incidents.insert_one(doc).inserted_id
    log_event(db, doc["_id"], "created", user["_id"], "Incident created from confirmed detection")
    return ser(doc)


@router.get("/incidents")
def list_incidents(status: Optional[Literal["pending_assignment", "assigned", "in_progress", "resolved"]] = None,
                   priority_level: Optional[Literal["high", "medium", "low"]] = None,
                   mission_id: Optional[str] = None, skip: int = Query(0, ge=0),
                   limit: int = Query(100, ge=1, le=500),
                   user=Depends(require_roles("rescue_manager", "rescue_member")), db=Depends(get_db)):
    q = {}
    if user["role"] == "rescue_member":
        q["assigned_member_id"] = user["_id"]
    if status:
        q["status"] = status
    if priority_level:
        q["priority_level"] = priority_level
    if mission_id:
        q["mission_id"] = oid(mission_id, "mission id")
    return ser(list(db.incidents.find(q).sort("created_at", -1).skip(skip).limit(limit)))


@router.get("/incidents/{incident_id}")
def get_incident(incident_id: str, user=Depends(require_roles("rescue_manager", "rescue_member")),
                 db=Depends(get_db)):
    inc = _get(db, user, incident_id)
    mission = db.missions.find_one({"_id": inc["mission_id"]}) or {}
    det = db.detections.find_one({"_id": inc["detection_id"]})
    member = db.users.find_one({"_id": inc.get("assigned_member_id")}) if inc.get("assigned_member_id") else None
    return ser({**inc,
                "mission": {"id": mission.get("_id"), "mission_name": mission.get("mission_name"),
                            "disaster_type": mission.get("disaster_type"),
                            "location_description": mission.get("location_description")},
                "detection": det,
                "evidence_url": f"/api/media/{det['frame_or_image_reference']}" if det else None,
                "assigned_member": {"id": member["_id"], "full_name": member["full_name"]} if member else None})


@router.patch("/incidents/{incident_id}")
def update_notes(incident_id: str, body: NotesPatch, user=Depends(require_manager), db=Depends(get_db)):
    inc = _get(db, user, incident_id)
    db.incidents.update_one({"_id": inc["_id"]}, {"$set": {"manager_notes": body.manager_notes.strip(),
                                                           "updated_at": now()}})
    log_event(db, inc["_id"], "manager_notes_updated", user["_id"], body.manager_notes.strip())
    return ser(db.incidents.find_one({"_id": inc["_id"]}))


@router.post("/incidents/{incident_id}/assign")
def assign(incident_id: str, body: AssignIn, user=Depends(require_manager), db=Depends(get_db)):
    inc = _get(db, user, incident_id)
    member = db.users.find_one({"_id": oid(body.member_id, "member id")})
    if (not member or member.get("role") != "rescue_member" or member.get("approval_status") != "approved"
            or not member.get("is_active")):
        raise HTTPException(status_code=422, detail="Choose an approved, active rescue team member")
    ts = now()
    # Reassignment is only possible before the member has acknowledged.
    res = db.incidents.find_one_and_update(
        {"_id": inc["_id"], "$or": [{"status": "pending_assignment"},
                                    {"status": "assigned", "acknowledged_at": None}]},
        {"$set": {"assigned_member_id": member["_id"], "status": "assigned", "assigned_at": ts,
                  "assigned_by": user["_id"], "updated_at": ts}}, return_document=True)
    if not res:
        raise HTTPException(status_code=409, detail="This incident can no longer be assigned or reassigned")
    log_event(db, inc["_id"], "assigned", user["_id"], body.notes or f"Assigned to {member['full_name']}",
              {"member_id": str(member["_id"])})
    return ser(res)


def _transition(db, user, incident_id, *, from_status, to_status, extra=None, require_ack=False):
    inc = _get(db, user, incident_id)
    flt = {"_id": inc["_id"], "status": from_status}
    if require_ack:
        flt["acknowledged_at"] = {"$ne": None}
    res = db.incidents.find_one_and_update(flt, {"$set": {**(extra or {}), "status": to_status,
                                                          "updated_at": now()}}, return_document=True)
    if not res:
        raise HTTPException(status_code=409, detail=f"Cannot move this incident from '{inc['status']}' to '{to_status}'")
    return res


@router.post("/incidents/{incident_id}/acknowledge")
def acknowledge(incident_id: str, user=Depends(require_member), db=Depends(get_db)):
    inc = _get(db, user, incident_id)
    ts = now()
    res = db.incidents.find_one_and_update(
        {"_id": inc["_id"], "status": "assigned", "acknowledged_at": None},
        {"$set": {"acknowledged_at": ts, "updated_at": ts}}, return_document=True)
    if not res:
        raise HTTPException(status_code=409, detail="This assignment cannot be acknowledged")
    log_event(db, inc["_id"], "acknowledged", user["_id"], "Assignment acknowledged")
    return ser(res)


@router.post("/incidents/{incident_id}/start")
def start(incident_id: str, user=Depends(require_member), db=Depends(get_db)):
    res = _transition(db, user, incident_id, from_status="assigned", to_status="in_progress",
                      extra={"started_at": now()}, require_ack=True)
    log_event(db, res["_id"], "response_started", user["_id"], "Response started")
    return ser(res)


@router.post("/incidents/{incident_id}/resolve")
async def resolve(incident_id: str, outcome: str = Form(..., min_length=3, max_length=1500),
                  field_observations: str = Form("", max_length=1500), file: Optional[UploadFile] = File(None),
                  user=Depends(require_member), db=Depends(get_db)):
    inc = _get(db, user, incident_id)
    if inc["status"] != "in_progress":
        raise HTTPException(status_code=409, detail="Only an in-progress incident can be resolved")
    extra = {"outcome": outcome.strip(), "field_observations": field_observations.strip(),
             "resolved_at": now()}
    if file is not None and file.filename:
        data, ext, _, _ = await read_image_upload(file)
        extra["resolution_evidence"] = save_media(f"incident-{inc['_id']}", data, ext)
    res = _transition(db, user, incident_id, from_status="in_progress", to_status="resolved", extra=extra)
    log_event(db, res["_id"], "resolved", user["_id"], extra["outcome"])
    return ser(res)


@router.post("/incidents/{incident_id}/events", status_code=201)
def add_note(incident_id: str, body: NoteIn, user=Depends(require_roles("rescue_manager", "rescue_member")),
             db=Depends(get_db)):
    inc = _get(db, user, incident_id)
    log_event(db, inc["_id"], "note", user["_id"], body.notes.strip())
    db.incidents.update_one({"_id": inc["_id"]}, {"$set": {"updated_at": now()}})
    return {"message": "Note saved"}


@router.get("/incidents/{incident_id}/events")
def events(incident_id: str, user=Depends(require_roles("rescue_manager", "rescue_member")), db=Depends(get_db)):
    inc = _get(db, user, incident_id)
    evs = list(db.incident_events.find({"incident_id": inc["_id"]}).sort("timestamp", 1))
    names = {u["_id"]: u["full_name"] for u in db.users.find({"_id": {"$in": [e["performed_by"] for e in evs]}})}
    return ser([{**e, "performed_by_name": names.get(e["performed_by"], "Unknown")} for e in evs])
