from typing import Literal, Optional
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from ..config import get_settings
from ..database import get_db, now, oid, ser
from ..dependencies import require_manager
from ..services import detection_service
from ..services.priority_service import compute_priority
from ..utils.files import read_image_upload, save_media

router = APIRouter(prefix="/api/missions", tags=["missions"])

TERRAIN_GUIDANCE = {
    "flood": ["Possible water-related access issues", "Verify water depth and routes",
              "Water-rescue resources may be needed"],
    "mountain": ["Possible steep terrain and limited approach", "Verify slope stability",
                 "Specialist mountain-rescue resources may be needed"],
    "urban_earthquake": ["Visible debris and blocked approaches may be present",
                         "Verify structural safety before entry"],
    "forest": ["Restricted visibility and vegetation may obstruct view",
               "Difficult ground access; additional visual inspection may be needed"],
}


class MissionIn(BaseModel):
    mission_name: str = Field(min_length=3, max_length=150)
    disaster_type: Literal["flood", "fire", "earthquake_building_collapse", "landslide"]
    terrain_type: Literal["flood", "urban_earthquake", "forest", "mountain"]
    location_description: str = Field(default="", max_length=300)


@router.post("", status_code=201)
def create_mission(body: MissionIn, user=Depends(require_manager), db=Depends(get_db)):
    doc = {**body.model_dump(), "created_by": user["_id"], "status": "created",
           "created_at": now(), "media_reference": None}
    doc["_id"] = db.missions.insert_one(doc).inserted_id
    return ser({**doc, "guidance": TERRAIN_GUIDANCE[body.terrain_type]})


@router.get("")
def list_missions(status: Optional[str] = None, _=Depends(require_manager), db=Depends(get_db)):
    q = {"status": status} if status else {}
    return ser(list(db.missions.find(q).sort("created_at", -1).limit(200)))


@router.get("/{mission_id}")
def get_mission(mission_id: str, _=Depends(require_manager), db=Depends(get_db)):
    m = db.missions.find_one({"_id": oid(mission_id, "mission id")})
    if not m:
        raise HTTPException(status_code=404, detail="Mission not found")
    m["guidance"] = TERRAIN_GUIDANCE.get(m.get("terrain_type"), [])
    return ser(m)


@router.post("/{mission_id}/analyze")
async def analyze(mission_id: str, file: UploadFile = File(...), user=Depends(require_manager),
                  db=Depends(get_db)):
    m = db.missions.find_one({"_id": oid(mission_id, "mission id")})
    if not m:
        raise HTTPException(status_code=404, detail="Mission not found")
    if m.get("status") == "analyzed":
        raise HTTPException(status_code=409, detail="This mission already has an analysed image. Create a new mission.")
    data, ext, w, h = await read_image_upload(file)
    # Inference first: if the service is unavailable, nothing is stored and nothing is faked.
    payload = detection_service.call_roboflow(data)
    preds = detection_service.parse_roboflow_response(payload, w, h)
    ref = save_media(str(m["_id"]), data, ext)
    s = get_settings()
    ts = now()
    docs = [{**p, "mission_id": m["_id"], "frame_or_image_reference": ref, "review_status": "unreviewed",
             "urgent_flag": False, "source": "model", "created_at": ts} for p in preds]
    if docs:
        ids = db.detections.insert_many(docs).inserted_ids
        for d, i in zip(docs, ids):
            d["_id"] = i
        for d in docs:
            r = compute_priority(d, docs, person_classes=s.person_class_set,
                                 obstacle_classes=s.obstacle_class_set, proximity_factor=s.proximity_factor)
            if r["breakdown"]:
                upd = {"priority_score": r["score"], "priority_level": r["level"],
                       "score_breakdown": r["breakdown"], "score_explanation": r["explanation"]}
                db.detections.update_one({"_id": d["_id"]}, {"$set": upd})
                d.update(upd)
    db.missions.update_one({"_id": m["_id"]}, {"$set": {"status": "analyzed", "media_reference": ref,
                                                         "analyzed_at": ts, "analyzed_by": user["_id"],
                                                         "image_width": w, "image_height": h}})
    return {"mission_id": str(m["_id"]), "image_reference": ref, "image_width": w, "image_height": h,
            "detection_count": len(docs), "detections": ser(docs),
            "message": "No objects were detected." if not docs else "Analysis complete."}


@router.get("/{mission_id}/detections")
def mission_detections(mission_id: str, _=Depends(require_manager), db=Depends(get_db)):
    mid = oid(mission_id, "mission id")
    if not db.missions.find_one({"_id": mid}):
        raise HTTPException(status_code=404, detail="Mission not found")
    return ser(list(db.detections.find({"mission_id": mid}).sort("confidence", -1)))
