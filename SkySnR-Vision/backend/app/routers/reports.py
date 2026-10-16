from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..config import get_settings
from ..database import get_db, now, oid, ser
from ..dependencies import require_manager
from ..services.report_service import build_report

router = APIRouter(prefix="/api/reports", tags=["reports"])


class ReportIn(BaseModel):
    mission_id: str
    incident_id: Optional[str] = None


@router.get("")
def list_reports(_=Depends(require_manager), db=Depends(get_db)):
    return ser(list(db.reports.find().sort("generated_at", -1).limit(200)))


@router.post("/generate", status_code=201)
def generate(body: ReportIn, user=Depends(require_manager), db=Depends(get_db)):
    mid = oid(body.mission_id, "mission id")
    mission = db.missions.find_one({"_id": mid})
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    iq = {"mission_id": mid}
    if body.incident_id:
        iq["_id"] = oid(body.incident_id, "incident id")
    incidents = list(db.incidents.find(iq))
    if body.incident_id and not incidents:
        raise HTTPException(status_code=404, detail="Incident not found in this mission")
    detections = list(db.detections.find({"mission_id": mid}))
    events = {}
    for inc in incidents:
        events[str(inc["_id"])] = list(db.incident_events.find({"incident_id": inc["_id"]}).sort("timestamp", 1))
    ids = {user["_id"]} | {i.get("assigned_member_id") for i in incidents if i.get("assigned_member_id")}
    ids |= {e["performed_by"] for evs in events.values() for e in evs}
    users = {str(u["_id"]): u for u in db.users.find({"_id": {"$in": list(ids)}})}
    ts = now()
    res = db.reports.insert_one({"mission_id": mid, "incident_id": iq.get("_id"), "generated_by": user["_id"],
                                 "generated_at": ts, "file_reference": None, "status": "generating"})
    path = get_settings().reports_dir / f"{res.inserted_id}.pdf"
    try:
        build_report(path, mission=mission, detections=detections, incidents=incidents,
                     events_by_incident=events, users=users,
                     generated_by={"name": user["full_name"], "at": ts})
    except Exception:
        db.reports.delete_one({"_id": res.inserted_id})
        raise HTTPException(status_code=500, detail="The report could not be generated")
    if not path.is_file():
        db.reports.delete_one({"_id": res.inserted_id})
        raise HTTPException(status_code=500, detail="The report could not be generated")
    db.reports.update_one({"_id": res.inserted_id}, {"$set": {"file_reference": path.name, "status": "ready"}})
    return ser(db.reports.find_one({"_id": res.inserted_id}))


@router.get("/{report_id}/download")
def download(report_id: str, _=Depends(require_manager), db=Depends(get_db)):
    r = db.reports.find_one({"_id": oid(report_id, "report id")})
    if not r or not r.get("file_reference"):
        raise HTTPException(status_code=404, detail="Report not found")
    path = (get_settings().reports_dir / r["file_reference"]).resolve()
    if not path.is_file():
        raise HTTPException(status_code=404, detail="The report file is missing")
    return FileResponse(path, media_type="application/pdf", filename=f"skysnr-report-{report_id}.pdf")
