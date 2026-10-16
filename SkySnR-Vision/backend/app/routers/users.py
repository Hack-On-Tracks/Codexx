from typing import Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..database import get_db, oid, ser
from ..dependencies import require_admin, require_roles

router = APIRouter(prefix="/api", tags=["users"])


class StatusIn(BaseModel):
    is_active: bool


@router.get("/users")
def list_users(approval_status: Optional[Literal["pending", "approved", "rejected"]] = None,
               role: Optional[Literal["rescue_manager", "rescue_member", "admin"]] = None,
               skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500),
               _=Depends(require_admin), db=Depends(get_db)):
    q = {}
    if approval_status:
        q["approval_status"] = approval_status
    if role:
        q["role"] = role
    return ser(list(db.users.find(q).sort("created_at", -1).skip(skip).limit(limit)))


@router.get("/users/pending")
def pending(_=Depends(require_admin), db=Depends(get_db)):
    return ser(list(db.users.find({"approval_status": "pending"}).sort("created_at", 1)))


@router.get("/users/{user_id}")
def get_user(user_id: str, _=Depends(require_admin), db=Depends(get_db)):
    u = db.users.find_one({"_id": oid(user_id, "user id")})
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return ser(u)


def _decide(db, user_id: str, new_status: str, active: bool):
    # Atomic: only a pending account can be decided, so double-clicks cannot double-approve.
    res = db.users.find_one_and_update(
        {"_id": oid(user_id, "user id"), "approval_status": "pending"},
        {"$set": {"approval_status": new_status, "is_active": active}}, return_document=True)
    if not res:
        if not db.users.find_one({"_id": oid(user_id)}):
            raise HTTPException(status_code=404, detail="User not found")
        raise HTTPException(status_code=409, detail="This request has already been decided")
    return ser(res)


@router.patch("/users/{user_id}/approve")
def approve(user_id: str, _=Depends(require_admin), db=Depends(get_db)):
    return _decide(db, user_id, "approved", True)


@router.patch("/users/{user_id}/reject")
def reject(user_id: str, _=Depends(require_admin), db=Depends(get_db)):
    return _decide(db, user_id, "rejected", False)


@router.patch("/users/{user_id}/status")
def set_status(user_id: str, body: StatusIn, admin=Depends(require_admin), db=Depends(get_db)):
    if str(admin["_id"]) == user_id:
        raise HTTPException(status_code=400, detail="You cannot change your own active status")
    u = db.users.find_one({"_id": oid(user_id, "user id")})
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    if u.get("approval_status") != "approved":
        raise HTTPException(status_code=409, detail="Only approved accounts can be activated or deactivated")
    db.users.update_one({"_id": u["_id"]}, {"$set": {"is_active": body.is_active}})
    return ser(db.users.find_one({"_id": u["_id"]}))


@router.get("/stats")
def stats(user=Depends(require_roles("admin", "rescue_manager", "rescue_member")), db=Depends(get_db)):
    """Role-scoped dashboard numbers, all computed from the database."""
    if user["role"] == "admin":
        return {"total_managers": db.users.count_documents({"role": "rescue_manager"}),
                "total_members": db.users.count_documents({"role": "rescue_member"}),
                "pending_approvals": db.users.count_documents({"approval_status": "pending"}),
                "approved_accounts": db.users.count_documents({"approval_status": "approved"}),
                "rejected_accounts": db.users.count_documents({"approval_status": "rejected"})}
    if user["role"] == "rescue_manager":
        inc = db.incidents
        return {"total_missions": db.missions.count_documents({}),
                "detections_awaiting_review": db.detections.count_documents({"review_status": "unreviewed"}),
                "incidents": inc.count_documents({}),
                "pending_assignment": inc.count_documents({"status": "pending_assignment"}),
                "assigned": inc.count_documents({"status": "assigned"}),
                "in_progress": inc.count_documents({"status": "in_progress"}),
                "resolved": inc.count_documents({"status": "resolved"}),
                "high": inc.count_documents({"priority_level": "high"}),
                "medium": inc.count_documents({"priority_level": "medium"}),
                "low": inc.count_documents({"priority_level": "low"})}
    mine = {"assigned_member_id": user["_id"]}
    inc = db.incidents
    return {"assigned_total": inc.count_documents(mine),
            "awaiting_acknowledgement": inc.count_documents({**mine, "status": "assigned", "acknowledged_at": None}),
            "in_progress": inc.count_documents({**mine, "status": "in_progress"}),
            "resolved": inc.count_documents({**mine, "status": "resolved"})}
