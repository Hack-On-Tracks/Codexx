import os, io, csv, uuid, time, datetime as dt
from collections import Counter, defaultdict
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import FastAPI, Depends, HTTPException, Request, Response, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, EmailStr, Field, model_validator
from typing import Optional
from .db import *
from .providers import *

SECRET = os.getenv("SECRET_KEY", "dev-only-change-me"); UP = os.getenv("UPLOAD_DIR", "./storage"); MAXB = int(os.getenv("MAX_UPLOAD_MB", "200")) * 1024 * 1024
ALLOWED = {".jpg": "image", ".jpeg": "image", ".png": "image", ".webp": "image", ".mp4": "video", ".mov": "video"}
OBST = {"debris", "fallen tree"}; ph = PasswordHasher(); os.makedirs(UP, exist_ok=True)
app = FastAPI(title="SkySnR Vision API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","), allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def provider(): return ExternalDetectionProvider(os.getenv("MODEL_URL", ""))
def get_db():
    db = Session()
    try: yield db
    finally: db.close()
@app.on_event("startup")
def boot():
    Base.metadata.create_all(engine); db = Session(); e, p = os.getenv("ADMIN_EMAIL"), os.getenv("ADMIN_PASSWORD")
    if e and p and not db.query(User).filter_by(email=e.lower()).first():
        db.add(User(full_name="System Administrator", email=e.lower(), password_hash=ph.hash(p), role="ADMIN", approval_status="APPROVED")); db.commit()
    db.close()

def cur(request: Request, db=Depends(get_db)):
    try: uid = int(jwt.decode(request.cookies.get("token", ""), SECRET, algorithms=["HS256"])["sub"])
    except Exception: raise HTTPException(401, "Not authenticated")
    u = db.get(User, uid)
    if not u or u.approval_status != "APPROVED": raise HTTPException(403, "Account is not approved")
    return u
def need(*roles):
    def f(u=Depends(cur)):
        if u.role not in roles: raise HTTPException(403, "You do not have permission for this action")
        return u
    return f
MGR = Depends(need("MANAGER", "ADMIN")); ADM = Depends(need("ADMIN")); ANY = Depends(cur)
def log(db, u, a, et, eid=None, **m): db.add(AuditLog(actor_id=u.id if u else None, action=a, entity_type=et, entity_id=eid, meta=m))
def notify(db, uid, title, msg, typ="info"):
    if uid: db.add(Notification(recipient_id=uid, title=title, message=msg, type=typ))
def get_or_404(db, M, i):
    o = db.get(M, i)
    if not o: raise HTTPException(404, f"{M.__name__} not found")
    return o

# ---------- Auth ----------
class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120); email: EmailStr; password: str = Field(min_length=8, max_length=128); confirm_password: str
    phone: str = Field(min_length=7, max_length=40); organization: str = Field(min_length=2); role: str; reference: Optional[str] = None; accept_terms: bool
    @model_validator(mode="after")
    def chk(self):
        if self.password != self.confirm_password: raise ValueError("Passwords do not match")
        if self.role not in ("MANAGER", "OPERATOR"): raise ValueError("Role must be MANAGER or OPERATOR")
        if not self.accept_terms: raise ValueError("Terms must be accepted")
        return self
class LoginIn(BaseModel): email: EmailStr; password: str; remember: bool = False
_hits = defaultdict(list)
@app.post("/api/auth/register", status_code=201)
def register(b: RegisterIn, db=Depends(get_db)):
    if db.query(User).filter_by(email=b.email.lower()).first(): raise HTTPException(409, "Email already registered")
    u = User(full_name=b.full_name, email=b.email.lower(), password_hash=ph.hash(b.password), phone=b.phone, organization=b.organization, role=b.role, reference=b.reference)
    db.add(u); db.flush(); log(db, u, "REGISTER", "user", u.id, role=b.role); db.commit()
    return {"message": "Registration submitted. Your account is awaiting administrator approval."}
@app.post("/api/auth/login")
def login(b: LoginIn, request: Request, response: Response, db=Depends(get_db)):
    ip = request.client.host if request.client else "x"; _hits[ip] = [t for t in _hits[ip] if time.time() - t < 60]
    if len(_hits[ip]) >= 10: raise HTTPException(429, "Too many attempts. Try again in a minute.")
    _hits[ip].append(time.time()); u = db.query(User).filter_by(email=b.email.lower()).first()
    try: ok = bool(u) and ph.verify(u.password_hash, b.password)
    except VerifyMismatchError: ok = False
    if not ok: raise HTTPException(401, "Invalid email or password")
    msg = {"PENDING": "Your account is awaiting administrator approval.", "REJECTED": "Your registration was rejected.", "SUSPENDED": "Your account is suspended."}.get(u.approval_status)
    if msg: raise HTTPException(403, msg)
    life = 30 * 86400 if b.remember else 8 * 3600
    tok = jwt.encode({"sub": str(u.id), "exp": int(time.time()) + life}, SECRET, algorithm="HS256")
    response.set_cookie("token", tok, httponly=True, samesite="lax", max_age=life if b.remember else None, secure=os.getenv("COOKIE_SECURE") == "1")
    log(db, u, "LOGIN", "user", u.id); db.commit(); return d(u)
@app.post("/api/auth/logout")
def logout(response: Response): response.delete_cookie("token"); return {"ok": True}
@app.get("/api/auth/me")
def me(u=ANY): return d(u)

# ---------- Admin ----------
@app.get("/api/admin/registrations")
def regs(status: str = "PENDING", u=ADM, db=Depends(get_db)): return [d(x) for x in db.query(User).filter_by(approval_status=status).order_by(User.created_at)]
@app.get("/api/admin/users")
def users(q: str = "", role: str = "", status: str = "", page: int = 1, size: int = 25, u=ADM, db=Depends(get_db)):
    qs = db.query(User)
    if q: qs = qs.filter(User.full_name.ilike(f"%{q}%") | User.email.ilike(f"%{q}%"))
    if role: qs = qs.filter_by(role=role)
    if status: qs = qs.filter_by(approval_status=status)
    return {"total": qs.count(), "items": [d(x) for x in qs.order_by(User.created_at.desc()).offset((page - 1) * size).limit(size)]}
def setstatus(db, adm, uid, new, allowed, action):
    t = get_or_404(db, User, uid)
    if t.role == "ADMIN" or t.id == adm.id: raise HTTPException(400, "Administrator accounts cannot be changed here")
    if t.approval_status not in allowed: raise HTTPException(409, f"Cannot move {t.approval_status} to {new}")
    t.approval_status = new
    if new == "APPROVED": t.approved_by, t.approved_at = adm.id, now()
    log(db, adm, action, "user", t.id, role=t.role); notify(db, t.id, "Account update", f"Your account is now {new}.", "account"); db.commit(); return d(t)
@app.patch("/api/admin/users/{uid}/approve")
def approve(uid: int, u=ADM, db=Depends(get_db)): return setstatus(db, u, uid, "APPROVED", ("PENDING", "SUSPENDED", "REJECTED"), "APPROVE")
@app.patch("/api/admin/users/{uid}/reject")
def reject(uid: int, u=ADM, db=Depends(get_db)): return setstatus(db, u, uid, "REJECTED", ("PENDING",), "REJECT")
@app.patch("/api/admin/users/{uid}/suspend")
def suspend(uid: int, u=ADM, db=Depends(get_db)): return setstatus(db, u, uid, "SUSPENDED", ("APPROVED",), "SUSPEND")
@app.get("/api/admin/audit-logs")
def audits(action: str = "", limit: int = 100, u=ADM, db=Depends(get_db)):
    qs = db.query(AuditLog)
    if action: qs = qs.filter_by(action=action)
    return [d(x) for x in qs.order_by(AuditLog.timestamp.desc()).limit(min(limit, 500))]

# ---------- Missions ----------
class MissionIn(BaseModel): title: str = Field(min_length=3); location_name: str; disaster_type: str; description: Optional[str] = None
class MissionPatch(BaseModel): title: Optional[str] = None; location_name: Optional[str] = None; description: Optional[str] = None
@app.get("/api/missions")
def missions(origin: str = "", u=ANY, db=Depends(get_db)):
    qs = db.query(Mission)
    if u.role == "OPERATOR": qs = qs.filter(Mission.id.in_(db.query(RescueCase.mission_id).filter_by(assigned_operator_id=u.id)))
    if origin: qs = qs.filter_by(data_origin=origin)
    return [d(m) for m in qs.order_by(Mission.started_at.desc())]
@app.post("/api/missions", status_code=201)
def new_mission(b: MissionIn, u=MGR, db=Depends(get_db)):
    m = Mission(**b.model_dump(), created_by=u.id); db.add(m); db.flush(); log(db, u, "MISSION_CREATE", "mission", m.id); db.commit(); return d(m)
@app.get("/api/missions/{mid}")
def mission(mid: int, u=MGR, db=Depends(get_db)):
    m = get_or_404(db, Mission, mid); r = d(m); cs = db.query(RescueCase).filter_by(mission_id=mid).all()
    r.update(evidence_count=db.query(Evidence).filter_by(mission_id=mid).count(), cases=Counter(c.status for c in cs)); return r
@app.patch("/api/missions/{mid}")
def edit_mission(mid: int, b: MissionPatch, u=MGR, db=Depends(get_db)):
    m = get_or_404(db, Mission, mid)
    for k, v in b.model_dump(exclude_none=True).items(): setattr(m, k, v)
    log(db, u, "MISSION_UPDATE", "mission", mid); db.commit(); return d(m)
@app.post("/api/missions/{mid}/close")
def close_mission(mid: int, acknowledge_unresolved: bool = False, u=MGR, db=Depends(get_db)):
    m = get_or_404(db, Mission, mid); open_ = db.query(RescueCase).filter(RescueCase.mission_id == mid, RescueCase.status.notin_(["CLOSED"])).count()
    if open_ and not acknowledge_unresolved: raise HTTPException(409, f"{open_} unresolved case(s). Set acknowledge_unresolved=true to close anyway.")
    m.status, m.ended_at = "CLOSED", now(); log(db, u, "MISSION_CLOSE", "mission", mid, unresolved=open_); db.commit(); return d(m)

# ---------- Simulation (separate data_origin='simulation') ----------
LABEL = "SIMULATION — NOT LIVE RESCUE DATA"
@app.get("/api/simulations/scenarios")
def scenarios(u=ANY): return [{"key": k, "name": v[0], "disaster_type": v[1], "difficulty": v[2], "frames": 6, "label": LABEL} for k, v in SCENARIOS.items()]
class SimIn(BaseModel): scenario: str
@app.post("/api/simulations/start", status_code=201)
def sim_start(b: SimIn, u=MGR, db=Depends(get_db)):
    if b.scenario not in SCENARIOS: raise HTTPException(404, "Unknown scenario")
    n, t, _ = SCENARIOS[b.scenario]; m = Mission(title=f"[SIMULATION] {n}", location_name="Simulated site", disaster_type=t, description=LABEL, created_by=u.id, data_origin="simulation"); db.add(m); db.flush()
    ev = Evidence(mission_id=m.id, uploaded_by=u.id, original_filename=f"{b.scenario}-fixture", mime_type="application/x-simulation", file_size=0, description=LABEL, data_origin="simulation"); db.add(ev); db.flush()
    job = AnalysisJob(evidence_id=ev.id, provider_type="demo", model_version="simulation-fixtures", status="completed", completed_at=now()); db.add(job); db.flush()
    for x in DemoDetectionProvider().fixtures(b.scenario)["detections"]:
        db.add(Detection(analysis_job_id=job.id, evidence_id=ev.id, class_name=x["class_name"], confidence=x["confidence"], bbox_coordinates=x["bbox"], track_id=x["track_id"], frame_index=x["frame_index"], timestamp_seconds=x["timestamp_seconds"], source="simulation"))
    log(db, u, "SIMULATION_START", "mission", m.id, scenario=b.scenario); db.commit(); return {"simulation_id": m.id, "evidence_id": ev.id, "label": LABEL}
def det_out(db, x): e = db.get(Evidence, x.evidence_id); r = d(x); r.update(data_origin=e.data_origin, mission_id=e.mission_id, filename=e.original_filename); return r
@app.get("/api/simulations/{sid}")
def sim_get(sid: int, u=MGR, db=Depends(get_db)):
    m = get_or_404(db, Mission, sid)
    if m.data_origin != "simulation": raise HTTPException(404, "Simulation not found")
    ev = db.query(Evidence).filter_by(mission_id=sid).first(); ds = db.query(Detection).filter_by(evidence_id=ev.id).order_by(Detection.frame_index).all()
    return {"label": LABEL, "mission": d(m), "evidence_id": ev.id, "detections": [d(x) for x in ds], "summary": dict(Counter(x.class_name for x in ds)), "reviewed": sum(x.review_status != "PENDING" for x in ds)}
@app.post("/api/simulations/{sid}/finish")
def sim_finish(sid: int, u=MGR, db=Depends(get_db)):
    m = sim_get(sid, u, db)["mission"]; mm = db.get(Mission, sid); mm.status, mm.ended_at = "COMPLETED", now(); log(db, u, "SIMULATION_FINISH", "mission", sid); db.commit(); return sim_get(sid, u, db)
@app.post("/api/simulations/{sid}/reset")
def sim_reset(sid: int, u=MGR, db=Depends(get_db)):
    sim_get(sid, u, db); mm = db.get(Mission, sid); mm.status, mm.ended_at = "ACTIVE", None
    ev = db.query(Evidence).filter_by(mission_id=sid).first()
    for x in db.query(Detection).filter_by(evidence_id=ev.id): x.review_status, x.review_notes = "PENDING", None
    log(db, u, "SIMULATION_RESET", "mission", sid); db.commit(); return sim_get(sid, u, db)

# ---------- Evidence & analysis ----------
@app.post("/api/evidence/upload", status_code=201)
async def upload(mission_id: int = Form(...), description: str = Form(""), file: UploadFile = File(...), u=MGR, db=Depends(get_db)):
    m = get_or_404(db, Mission, mission_id)
    if m.data_origin != "real": raise HTTPException(400, "Cannot upload real evidence into a simulation")
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED: raise HTTPException(400, f"Unsupported file type. Allowed: {', '.join(ALLOWED)}")
    data = await file.read()
    if len(data) > MAXB: raise HTTPException(413, "File too large")
    if not data: raise HTTPException(400, "Empty file")
    name = uuid.uuid4().hex + ext; path = os.path.join(UP, name)
    with open(path, "wb") as f: f.write(data)
    ev = Evidence(mission_id=mission_id, uploaded_by=u.id, original_filename=os.path.basename(file.filename)[:255], stored_filename=name, mime_type=file.content_type, file_size=len(data), storage_path=path, description=description)
    db.add(ev); db.flush(); log(db, u, "EVIDENCE_UPLOAD", "evidence", ev.id, mission_id=mission_id); db.commit(); return d(ev, skip=("storage_path",))
@app.get("/api/evidence")
def evidence_list(mission_id: Optional[int] = None, origin: str = "", u=MGR, db=Depends(get_db)):
    qs = db.query(Evidence)
    if mission_id: qs = qs.filter_by(mission_id=mission_id)
    if origin: qs = qs.filter_by(data_origin=origin)
    return [d(e, skip=("storage_path",)) for e in qs.order_by(Evidence.uploaded_at.desc())]
@app.get("/api/evidence/{eid}")
def evidence_get(eid: int, u=MGR, db=Depends(get_db)): return d(get_or_404(db, Evidence, eid), skip=("storage_path",))
@app.get("/api/evidence/{eid}/file")
def evidence_file(eid: int, u=ANY, db=Depends(get_db)):
    e = get_or_404(db, Evidence, eid)
    if u.role == "OPERATOR" and not db.query(RescueCase).filter_by(mission_id=e.mission_id, assigned_operator_id=u.id).first(): raise HTTPException(403, "Not assigned to this mission")
    if not e.storage_path or not os.path.abspath(e.storage_path).startswith(os.path.abspath(UP)) or not os.path.exists(e.storage_path): raise HTTPException(404, "No file stored for this evidence")
    return FileResponse(e.storage_path, media_type=e.mime_type, filename=e.original_filename)
class RunIn(BaseModel): evidence_id: int
@app.get("/api/model/status")
def model_status(u=ANY): p = provider(); return {**p.get_model_status(), "classes": p.get_supported_classes() if p.url else [], "provider": "external"}
@app.post("/api/analysis/run")
def run(b: RunIn, u=MGR, db=Depends(get_db)):
    e = get_or_404(db, Evidence, b.evidence_id)
    if e.data_origin != "real": raise HTTPException(400, "Simulation evidence uses fixtures only")
    j = db.query(AnalysisJob).filter(AnalysisJob.evidence_id == e.id, AnalysisJob.status.in_(["processing", "completed"])).first()
    if j: return d(j)  # no duplicate processing
    p = provider(); st = p.get_model_status(); j = AnalysisJob(evidence_id=e.id, provider_type="external", model_version=st.get("model_version")); db.add(j); db.flush()
    if st["state"] != "ready": j.status = "not_configured" if st["state"] == "not_configured" else "failed"; j.error_message = st["message"]; j.completed_at = now()
    else:
        try:
            r = (p.predict_video if ALLOWED[os.path.splitext(e.stored_filename)[1]] == "video" else p.predict_image)(e.storage_path)
            j.model_version = r.get("model_version", j.model_version)
            for x in r["detections"]: db.add(Detection(analysis_job_id=j.id, evidence_id=e.id, class_name=x["class_name"], confidence=x["confidence"], bbox_coordinates=x["bbox"], track_id=x.get("track_id"), frame_index=x.get("frame_index"), timestamp_seconds=x.get("timestamp_seconds")))
            j.status = "completed"
        except ProviderError as ex: j.status, j.error_message = "failed", str(ex)  # never falls back to simulation
        j.completed_at = now()
    log(db, u, "ANALYSIS_RUN", "analysis", j.id, status=j.status); db.commit(); return d(j)
@app.get("/api/analysis/{jid}")
def job(jid: int, u=MGR, db=Depends(get_db)): return d(get_or_404(db, AnalysisJob, jid))
@app.get("/api/analysis/{jid}/detections")
def job_dets(jid: int, u=MGR, db=Depends(get_db)): return [det_out(db, x) for x in db.query(Detection).filter_by(analysis_job_id=jid)]

# ---------- Detection review ----------
class ReviewIn(BaseModel): status: str; notes: Optional[str] = None; class_name: Optional[str] = None
@app.get("/api/detections")
def detections(status: str = "", class_name: str = "", mission_id: Optional[int] = None, origin: str = "", q: str = "", u=MGR, db=Depends(get_db)):
    qs = db.query(Detection).join(Evidence, Evidence.id == Detection.evidence_id)
    if status: qs = qs.filter(Detection.review_status == status)
    if class_name: qs = qs.filter(Detection.class_name == class_name)
    if mission_id: qs = qs.filter(Evidence.mission_id == mission_id)
    if origin: qs = qs.filter(Evidence.data_origin == origin)
    if q: qs = qs.filter(Detection.class_name.ilike(f"%{q}%") | (Detection.id == (int(q) if q.isdigit() else -1)))
    return [det_out(db, x) for x in qs.order_by(Detection.id.desc()).limit(500)]
@app.get("/api/detections/{did}")
def detection(did: int, u=MGR, db=Depends(get_db)):
    x = get_or_404(db, Detection, did); r = det_out(db, x)
    r["history"] = [d(a) for a in db.query(AuditLog).filter_by(entity_type="detection", entity_id=did).order_by(AuditLog.timestamp)]; return r
@app.patch("/api/detections/{did}/review")
def review(did: int, b: ReviewIn, u=MGR, db=Depends(get_db)):
    if b.status not in ("CONFIRMED", "REJECTED", "UNCERTAIN", "PENDING"): raise HTTPException(400, "Invalid review status")
    x = get_or_404(db, Detection, did); old = x.review_status
    if x.review_status == "CONVERTED": raise HTTPException(409, "Already converted to a rescue case")
    x.review_status, x.reviewed_by, x.reviewed_at = b.status, u.id, now()
    if b.notes: x.review_notes = ((x.review_notes + "\n") if x.review_notes else "") + b.notes
    if b.class_name: x.class_name = b.class_name
    log(db, u, "DETECTION_REVIEW", "detection", did, previous=old, new=b.status, class_name=b.class_name); db.commit(); return det_out(db, x)
class CaseIn(BaseModel): title: str = Field(min_length=3); description: Optional[str] = None; priority: str = "MEDIUM"; urgency: int = Field(1, ge=1, le=3); danger: bool = False; detection_ids: list[int] = []
PRI = ("CRITICAL", "HIGH", "MEDIUM", "LOW")
def mkcase(db, u, mission_id, b, dets, confirm_merge=False):
    if b.priority not in PRI: raise HTTPException(400, "Invalid priority")
    if any(x.review_status not in ("CONFIRMED",) for x in dets): raise HTTPException(400, "Only human-confirmed detections can become rescue cases")
    if len({db.get(Evidence, x.evidence_id).mission_id for x in dets}) > 1: raise HTTPException(400, "Detections belong to different missions")
    c = RescueCase(mission_id=mission_id, title=b.title, description=b.description, priority=b.priority, urgency=b.urgency, danger=b.danger, created_by=u.id); db.add(c); db.flush()
    for x in dets: db.add(CaseDetection(case_id=c.id, detection_id=x.id)); x.review_status = "CONVERTED"
    db.add(CaseUpdate(case_id=c.id, updated_by=u.id, previous_status=None, new_status="OPEN", notes="Case created")); log(db, u, "CASE_CREATE", "case", c.id, detections=[x.id for x in dets]); return c
@app.post("/api/detections/{did}/create-case", status_code=201)
def det_case(did: int, b: CaseIn, u=MGR, db=Depends(get_db)):
    x = get_or_404(db, Detection, did); ids = set(b.detection_ids) - {did}; extra = [get_or_404(db, Detection, i) for i in ids]
    c = mkcase(db, u, db.get(Evidence, x.evidence_id).mission_id, b, [x] + extra); db.commit(); return d(c)

# ---------- Cases ----------
TRANS = {"ASSIGNED": {"ACKNOWLEDGED"}, "ACKNOWLEDGED": {"IN_PROGRESS", "BLOCKED"}, "IN_PROGRESS": {"RESOLVED", "BLOCKED", "ESCALATED"}, "BLOCKED": {"IN_PROGRESS", "ESCALATED"}, "ESCALATED": {"IN_PROGRESS", "RESOLVED"}, "RESOLVED": {"CLOSED", "IN_PROGRESS"}}
def suggest(db, c):
    s, why = 0, []
    if c.danger: s += 3; why.append("Reviewer/operator reported danger (+3)")
    if (c.urgency or 1) > 1: s += c.urgency - 1; why.append(f"Operator-specified urgency {c.urgency} (+{c.urgency - 1})")
    evs = {db.get(Evidence, x.evidence_id).id for x in db.query(Detection).join(CaseDetection, CaseDetection.detection_id == Detection.id).filter(CaseDetection.case_id == c.id)}
    ob = db.query(Detection).filter(Detection.evidence_id.in_(evs or [0]), Detection.class_name.in_(OBST), Detection.review_status == "CONFIRMED").count() if evs else 0
    if ob: s += 1; why.append(f"{ob} verified obstacle(s) in same evidence (+1)")
    age = (now() - c.created_at).total_seconds() / 3600
    if age > 6 and c.status not in ("RESOLVED", "CLOSED"): s += 1; why.append(f"Unresolved for {age:.0f} h (+1)")
    return {"suggested_priority": "CRITICAL" if s >= 5 else "HIGH" if s >= 3 else "MEDIUM" if s >= 1 else "LOW", "score": s, "reasons": why or ["No escalating factors"], "note": "Suggestion only; not a medical assessment."}
def case_out(db, c):
    r = d(c); r["detection_ids"] = [x.detection_id for x in db.query(CaseDetection).filter_by(case_id=c.id)]; r["priority_assessment"] = suggest(db, c)
    r["updates"] = [d(x) for x in db.query(CaseUpdate).filter_by(case_id=c.id).order_by(CaseUpdate.created_at)]; return r
def can_see(u, c): return u.role != "OPERATOR" or c.assigned_operator_id == u.id
@app.get("/api/cases")
def cases(status: str = "", mission_id: Optional[int] = None, u=ANY, db=Depends(get_db)):
    qs = db.query(RescueCase)
    if u.role == "OPERATOR": qs = qs.filter_by(assigned_operator_id=u.id)
    if status: qs = qs.filter_by(status=status)
    if mission_id: qs = qs.filter_by(mission_id=mission_id)
    return [d(c) for c in qs.order_by(RescueCase.created_at.desc())]
@app.post("/api/cases", status_code=201)
def new_case(b: CaseIn, mission_id: int, u=MGR, db=Depends(get_db)):
    get_or_404(db, Mission, mission_id); c = mkcase(db, u, mission_id, b, [get_or_404(db, Detection, i) for i in b.detection_ids]); db.commit(); return d(c)
@app.get("/api/cases/{cid}")
def case(cid: int, u=ANY, db=Depends(get_db)):
    c = get_or_404(db, RescueCase, cid)
    if not can_see(u, c): raise HTTPException(403, "Not your assignment")
    return case_out(db, c)
class CasePatch(BaseModel): title: Optional[str] = None; description: Optional[str] = None; priority: Optional[str] = None; priority_reason: Optional[str] = None; instructions: Optional[str] = None
@app.patch("/api/cases/{cid}")
def edit_case(cid: int, b: CasePatch, u=MGR, db=Depends(get_db)):
    c = get_or_404(db, RescueCase, cid)
    if b.priority:
        if b.priority not in PRI: raise HTTPException(400, "Invalid priority")
        if not b.priority_reason: raise HTTPException(400, "priority_reason is required when overriding priority")
    for k, v in b.model_dump(exclude_none=True).items(): setattr(c, k, v)
    log(db, u, "CASE_UPDATE" if not b.priority else "PRIORITY_OVERRIDE", "case", cid, priority=b.priority, reason=b.priority_reason); db.commit(); return case_out(db, c)
class AssignIn(BaseModel): operator_id: Optional[int] = None; team_id: Optional[int] = None; instructions: Optional[str] = None; deadline: Optional[dt.datetime] = None
@app.post("/api/cases/{cid}/assign")
def assign(cid: int, b: AssignIn, u=MGR, db=Depends(get_db)):
    c = get_or_404(db, RescueCase, cid); op = b.operator_id
    if b.team_id: t = get_or_404(db, Team, b.team_id); c.assigned_team_id = t.id; op = op or (db.query(TeamMember).filter_by(team_id=t.id).first() or TeamMember(user_id=None)).user_id
    if not op: raise HTTPException(400, "Provide an operator or a team with members")
    o = get_or_404(db, User, op)
    if o.role != "OPERATOR" or o.approval_status != "APPROVED": raise HTTPException(400, "Assignee must be an approved operator")
    if c.status in ("CLOSED", "RESOLVED"): raise HTTPException(409, "Case is already resolved/closed")
    prev = c.status; c.assigned_operator_id, c.status = op, "ASSIGNED"; c.instructions = b.instructions or c.instructions; c.deadline = b.deadline
    db.add(CaseUpdate(case_id=c.id, updated_by=u.id, previous_status=prev, new_status="ASSIGNED", notes=f"Assigned to {o.full_name}"))
    notify(db, op, "New assignment", f"You were assigned: {c.title}", "assignment"); log(db, u, "CASE_ASSIGN", "case", cid, operator_id=op, team_id=b.team_id); db.commit(); return case_out(db, c)
class UpdIn(BaseModel): new_status: Optional[str] = None; notes: str = Field(min_length=1)
@app.post("/api/cases/{cid}/updates", status_code=201)
def add_update(cid: int, b: UpdIn, u=ANY, db=Depends(get_db)):
    c = get_or_404(db, RescueCase, cid)
    if not can_see(u, c): raise HTTPException(403, "Not your assignment")
    ns = b.new_status
    if ns:
        if ns not in TRANS.get(c.status, set()): raise HTTPException(409, f"Transition {c.status} -> {ns} is not allowed")
        if ns == "CLOSED" and u.role not in ("MANAGER", "ADMIN"): raise HTTPException(403, "Only managers can close cases")
        if u.role == "OPERATOR" and ns == "IN_PROGRESS" and c.status == "RESOLVED": raise HTTPException(403, "Only managers can reopen")
    up = CaseUpdate(case_id=c.id, updated_by=u.id, previous_status=c.status, new_status=ns or c.status, notes=b.notes); db.add(up)
    if ns:
        c.status = ns; c.resolved_at = now() if ns == "RESOLVED" else c.resolved_at
        if ns in ("BLOCKED", "ESCALATED", "RESOLVED") and u.role == "OPERATOR": notify(db, c.created_by, f"Case {ns.title()}", f"{c.title}: {b.notes[:120]}", "case")
    log(db, u, "CASE_STATUS" if ns else "CASE_NOTE", "case", cid, new=ns); db.commit(); return d(up)

# ---------- Teams ----------
class TeamIn(BaseModel): name: str; code: str; specialty: Optional[str] = None; availability_status: str = "AVAILABLE"; notes: Optional[str] = None; leader_id: Optional[int] = None; member_ids: list[int] = []
@app.get("/api/teams")
def teams(u=MGR, db=Depends(get_db)):
    out = []
    for t in db.query(Team):
        r = d(t); r["members"] = [m.user_id for m in db.query(TeamMember).filter_by(team_id=t.id)]
        r["open_cases"] = db.query(RescueCase).filter(RescueCase.assigned_team_id == t.id, RescueCase.status.notin_(["RESOLVED", "CLOSED"])).count(); out.append(r)
    return out
@app.post("/api/teams", status_code=201)
def new_team(b: TeamIn, u=Depends(need("MANAGER")), db=Depends(get_db)):
    if db.query(Team).filter_by(code=b.code).first(): raise HTTPException(409, "Team code already exists")
    t = Team(**b.model_dump(exclude={"member_ids"}), created_by=u.id); db.add(t); db.flush()
    for i in b.member_ids:
        if (m := db.get(User, i)) and m.role == "OPERATOR" and m.approval_status == "APPROVED": db.add(TeamMember(team_id=t.id, user_id=i))
    log(db, u, "TEAM_CREATE", "team", t.id); db.commit(); return d(t)
@app.patch("/api/teams/{tid}")
def edit_team(tid: int, b: dict, u=Depends(need("MANAGER")), db=Depends(get_db)):
    t = get_or_404(db, Team, tid)
    for k in ("name", "specialty", "availability_status", "notes", "leader_id"):
        if k in b: setattr(t, k, b[k])
    if "member_ids" in b:
        db.query(TeamMember).filter_by(team_id=tid).delete()
        for i in b["member_ids"]: db.add(TeamMember(team_id=tid, user_id=i))
    log(db, u, "TEAM_UPDATE", "team", tid); db.commit(); return d(t)
@app.get("/api/teams/{tid}/assignments")
def team_assign(tid: int, u=MGR, db=Depends(get_db)): return [d(c) for c in db.query(RescueCase).filter_by(assigned_team_id=tid)]

# ---------- Analytics, reports, notifications ----------
@app.get("/api/analytics/overview")
def overview(mission_id: Optional[int] = None, origin: str = "", u=MGR, db=Depends(get_db)):
    ms = db.query(Mission); ev = db.query(Evidence); cs = db.query(RescueCase).join(Mission, Mission.id == RescueCase.mission_id)
    ds = db.query(Detection).join(Evidence, Evidence.id == Detection.evidence_id)
    if mission_id: ms = ms.filter(Mission.id == mission_id); ev = ev.filter(Evidence.mission_id == mission_id); cs = cs.filter(RescueCase.mission_id == mission_id); ds = ds.filter(Evidence.mission_id == mission_id)
    if origin: ms = ms.filter(Mission.data_origin == origin); ev = ev.filter(Evidence.data_origin == origin); cs = cs.filter(Mission.data_origin == origin); ds = ds.filter(Evidence.data_origin == origin)
    ds, cs = ds.all(), cs.all(); rev = [x for x in ds if x.review_status in ("CONFIRMED", "REJECTED", "CONVERTED")]; ack = []
    for c in cs:
        a = db.query(CaseUpdate).filter_by(case_id=c.id, new_status="ACKNOWLEDGED").first()
        if a: ack.append((a.created_at - c.created_at).total_seconds() / 60)
    return {"data_origin_filter": origin or "all", "missions": ms.count(), "evidence": ev.count(), "detections": len(ds), "verified": sum(x.review_status in ("CONFIRMED", "CONVERTED") for x in ds),
            "verification_rate": round(len(rev) / len(ds), 3) if ds else None, "open_cases": sum(c.status not in ("RESOLVED", "CLOSED") for c in cs), "completed_cases": sum(c.status in ("RESOLVED", "CLOSED") for c in cs),
            "avg_ack_minutes": round(sum(ack) / len(ack), 1) if ack else None, "by_class": dict(Counter(x.class_name for x in ds)), "by_priority": dict(Counter(c.priority for c in cs)),
            "case_status": dict(Counter(c.status for c in cs)), "review_status": dict(Counter(x.review_status for x in ds)), "team_workload": dict(Counter(c.assigned_team_id for c in cs if c.assigned_team_id))}
@app.get("/api/analytics/missions/{mid}")
def mission_an(mid: int, u=MGR, db=Depends(get_db)): get_or_404(db, Mission, mid); return overview(mid, "", u, db)
def report_rows(db, mid):
    m = get_or_404(db, Mission, mid); rows = [(x.id, x.class_name, x.confidence, x.review_status, x.timestamp_seconds, db.get(Evidence, x.evidence_id).original_filename) for x in db.query(Detection).join(Evidence).filter(Evidence.mission_id == mid)]
    return m, rows
@app.get("/api/reports/missions/{mid}/csv")
def rep_csv(mid: int, u=MGR, db=Depends(get_db)):
    m, rows = report_rows(db, mid); s = io.StringIO(); w = csv.writer(s); w.writerow(["# " + (LABEL if m.data_origin == "simulation" else "REAL DATA"), m.title, "exported " + now().isoformat() + "Z"])
    w.writerow(["detection_id", "class", "confidence", "review_status", "timestamp_s", "evidence"]); w.writerows(rows); log(db, u, "REPORT_GENERATE", "mission", mid, fmt="csv"); db.commit()
    return Response(s.getvalue(), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="mission-{mid}.csv"'})
@app.get("/api/reports/missions/{mid}/pdf")
def rep_pdf(mid: int, u=MGR, db=Depends(get_db)):
    from reportlab.pdfgen import canvas
    m, rows = report_rows(db, mid); a = overview(mid, "", u, db); buf = io.BytesIO(); c = canvas.Canvas(buf); y = 800
    def line(t, f="Helvetica", s=10):
        nonlocal y
        if y < 50: c.showPage(); y = 800
        c.setFont(f, s); c.drawString(50, y, str(t)[:110]); y -= s + 6
    line("SkySnR Vision - Mission Report", "Helvetica-Bold", 16)
    if m.data_origin == "simulation": line(LABEL, "Helvetica-Bold", 11)
    for t in (f"Mission #{m.id}: {m.title}", f"Category: {m.disaster_type}  Location: {m.location_name}", f"Status: {m.status}  Started: {m.started_at}  Ended: {m.ended_at}",
              f"Detections: {a['detections']}  Verified: {a['verified']}  Open cases: {a['open_cases']}  Completed: {a['completed_cases']}", f"By class: {a['by_class']}", f"Case status: {a['case_status']}", f"Exported: {now()} UTC", "", "Detections"): line(t)
    for r in rows: line(f"#{r[0]} {r[1]} {r[2]:.2f} {r[3]} {r[5]}")
    c.save(); buf.seek(0); log(db, u, "REPORT_GENERATE", "mission", mid, fmt="pdf"); db.commit()
    return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="mission-{mid}.pdf"'})
@app.get("/api/notifications")
def notes(u=ANY, db=Depends(get_db)): return [d(n) for n in db.query(Notification).filter_by(recipient_id=u.id).order_by(Notification.created_at.desc()).limit(50)]
@app.patch("/api/notifications/{nid}/read")
def read(nid: int, u=ANY, db=Depends(get_db)):
    n = get_or_404(db, Notification, nid)
    if n.recipient_id != u.id: raise HTTPException(403, "Forbidden")
    n.is_read = True; db.commit(); return d(n)

@app.get("/api/operators")
def operators(u=MGR, db=Depends(get_db)):
    return [{"id": x.id, "full_name": x.full_name, "organization": x.organization} for x in db.query(User).filter_by(role="OPERATOR", approval_status="APPROVED")]
