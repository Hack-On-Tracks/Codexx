from pathlib import Path
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from ..config import get_settings
from ..database import get_db
from ..dependencies import get_current_user

router = APIRouter(prefix="/api/media", tags=["media"])


@router.get("/{folder}/{filename}")
def media(folder: str, filename: str, user=Depends(get_current_user), db=Depends(get_db)):
    if user["role"] not in ("rescue_manager", "rescue_member"):
        raise HTTPException(status_code=403, detail="You do not have permission for this action")
    base = get_settings().media_dir.resolve()
    path = (base / folder / filename).resolve()
    if base not in path.parents or not path.is_file():  # blocks ../ traversal
        raise HTTPException(status_code=404, detail="File not found")
    if user["role"] == "rescue_member":
        try:
            if folder.startswith("incident-"):
                q = {"_id": ObjectId(folder[9:])}
            else:
                q = {"mission_id": ObjectId(folder)}
        except Exception:
            raise HTTPException(status_code=404, detail="File not found")
        if not db.incidents.find_one({**q, "assigned_member_id": user["_id"]}):
            raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path)
