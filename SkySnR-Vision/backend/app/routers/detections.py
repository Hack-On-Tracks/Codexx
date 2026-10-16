from typing import Literal, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator

from ..config import get_settings
from ..database import get_db, now, oid, ser
from ..dependencies import require_manager
from ..services.priority_service import compute_priority

router = APIRouter(prefix="/api/detections", tags=["detections"])


class PriorityIn(BaseModel):
    urgent_flag: bool = False
    override_level: Optional[Literal["high", "medium", "low"]] = None
    override_justification: Optional[str] = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def need_reason(self):
        if self.override_level and not (self.override_justification or "").strip():
            raise ValueError("A justification is required to override the priority level")
        return self


class ReviewIn(BaseModel):
    decision: Literal["confirmed", "dismissed"]
    notes: str = Field(min_length=3, max_length=500)


def _load(db, detection_id):
    d = db.detections.find_one({"_id": oid(detection_id, "detection id")})
    if not d:
        raise HTTPException(status_code=404, detail="Detection not found")
    return d


@router.post("/{detection_id}/priority")
def set_priority(detection_id: str, body: PriorityIn, user=Depends(require_manager), db=Depends(get_db)):
    d = _load(db, detection_id)
    s = get_settings()
    siblings = list(db.detections.find({"mission_id": d["mission_id"]}))
    r = compute_priority(d, siblings, person_classes=s.person_class_set, obstacle_classes=s.obstacle_class_set,
                         proximity_factor=s.proximity_factor, urgent=body.urgent_flag)
    if not r["breakdown"]:
        raise HTTPException(status_code=422, detail="Priority scoring applies only to person detections")
    upd = {"priority_score": r["score"], "priority_level": r["level"], "score_breakdown": r["breakdown"],
           "score_explanation": r["explanation"], "urgent_flag": body.urgent_flag,
           "final_priority_level": body.override_level or r["level"],
           "override": ({"level": body.override_level, "justification": body.override_justification.strip(),
                         "by": user["_id"], "at": now()} if body.override_level else None)}
    db.detections.update_one({"_id": d["_id"]}, {"$set": upd})
    return ser(db.detections.find_one({"_id": d["_id"]}))


@router.post("/{detection_id}/review")
def review(detection_id: str, body: ReviewIn, user=Depends(require_manager), db=Depends(get_db)):
    d = _load(db, detection_id)
    if db.incidents.find_one({"detection_id": d["_id"]}):
        raise HTTPException(status_code=409, detail="An incident already exists for this detection")
    db.detections.update_one({"_id": d["_id"]}, {"$set": {
        "review_status": body.decision, "review_notes": body.notes.strip(),
        "reviewed_by": user["_id"], "reviewed_at": now()}})
    return ser(db.detections.find_one({"_id": d["_id"]}))
