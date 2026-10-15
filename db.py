import os, datetime as dt
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker
URL = os.getenv("DATABASE_URL", "sqlite:///./skysnr.db")
engine = create_engine(URL, connect_args={"check_same_thread": False} if URL.startswith("sqlite") else {})
Session = sessionmaker(bind=engine, autoflush=False)
Base = declarative_base()
now = lambda: dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)  # UTC
def fk(t, **k): return Column(Integer, ForeignKey(t + ".id"), **k)
class User(Base):
    __tablename__ = "users"; id = Column(Integer, primary_key=True)
    full_name = Column(String(120), nullable=False); email = Column(String(200), unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False); phone = Column(String(40)); organization = Column(String(160)); reference = Column(String(120))
    role = Column(String(20), nullable=False); approval_status = Column(String(20), default="PENDING", index=True)
    created_at = Column(DateTime, default=now); approved_by = fk("users"); approved_at = Column(DateTime)
class Mission(Base):
    __tablename__ = "missions"; id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False); location_name = Column(String(200)); disaster_type = Column(String(40))
    description = Column(Text); status = Column(String(20), default="ACTIVE", index=True); created_by = fk("users")
    started_at = Column(DateTime, default=now); ended_at = Column(DateTime); data_origin = Column(String(12), default="real", index=True)
class Team(Base):
    __tablename__ = "teams"; id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False); code = Column(String(30), unique=True, nullable=False); specialty = Column(String(120))
    availability_status = Column(String(20), default="AVAILABLE"); notes = Column(Text); leader_id = fk("users"); created_by = fk("users")
class TeamMember(Base):
    __tablename__ = "team_members"; id = Column(Integer, primary_key=True)
    team_id = fk("teams", nullable=False); user_id = fk("users", nullable=False); __table_args__ = (UniqueConstraint("team_id", "user_id"),)
class Evidence(Base):
    __tablename__ = "evidence"; id = Column(Integer, primary_key=True)
    mission_id = fk("missions", nullable=False, index=True); uploaded_by = fk("users"); original_filename = Column(String(255))
    stored_filename = Column(String(80)); mime_type = Column(String(80)); file_size = Column(Integer); storage_path = Column(String(300))
    description = Column(Text); data_origin = Column(String(12), default="real", index=True); uploaded_at = Column(DateTime, default=now)
class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"; id = Column(Integer, primary_key=True)
    evidence_id = fk("evidence", nullable=False, index=True); provider_type = Column(String(20)); model_version = Column(String(80))
    status = Column(String(20), default="processing"); error_message = Column(Text); created_at = Column(DateTime, default=now); completed_at = Column(DateTime)
class Detection(Base):
    __tablename__ = "detections"; id = Column(Integer, primary_key=True)
    analysis_job_id = fk("analysis_jobs", index=True); evidence_id = fk("evidence", nullable=False, index=True)
    class_name = Column(String(60), index=True); confidence = Column(Float); bbox_coordinates = Column(JSON)  # [x1,y1,x2,y2] pixels, top-left origin
    track_id = Column(String(40)); frame_index = Column(Integer); timestamp_seconds = Column(Float); source = Column(String(12), default="model")
    review_status = Column(String(20), default="PENDING", index=True); review_notes = Column(Text); reviewed_by = fk("users"); reviewed_at = Column(DateTime)
class RescueCase(Base):
    __tablename__ = "rescue_cases"; id = Column(Integer, primary_key=True)
    mission_id = fk("missions", nullable=False, index=True); title = Column(String(200)); description = Column(Text)
    priority = Column(String(12), default="MEDIUM"); priority_reason = Column(Text); urgency = Column(Integer, default=1); danger = Column(Boolean, default=False)
    status = Column(String(20), default="OPEN", index=True); created_by = fk("users"); assigned_team_id = fk("teams"); assigned_operator_id = fk("users", index=True)
    instructions = Column(Text); deadline = Column(DateTime); created_at = Column(DateTime, default=now); resolved_at = Column(DateTime)
class CaseDetection(Base):
    __tablename__ = "case_detections"; id = Column(Integer, primary_key=True)
    case_id = fk("rescue_cases", nullable=False); detection_id = fk("detections", nullable=False); __table_args__ = (UniqueConstraint("case_id", "detection_id"),)
class CaseUpdate(Base):
    __tablename__ = "case_updates"; id = Column(Integer, primary_key=True)
    case_id = fk("rescue_cases", nullable=False, index=True); updated_by = fk("users"); previous_status = Column(String(20)); new_status = Column(String(20))
    notes = Column(Text); created_at = Column(DateTime, default=now)
class Notification(Base):
    __tablename__ = "notifications"; id = Column(Integer, primary_key=True)
    recipient_id = fk("users", nullable=False, index=True); title = Column(String(200)); message = Column(Text); type = Column(String(30))
    is_read = Column(Boolean, default=False); created_at = Column(DateTime, default=now)
class AuditLog(Base):
    __tablename__ = "audit_logs"; id = Column(Integer, primary_key=True)
    actor_id = fk("users"); action = Column(String(60), index=True); entity_type = Column(String(40)); entity_id = Column(Integer)
    meta = Column("metadata", JSON); timestamp = Column(DateTime, default=now, index=True)
def d(o, skip=("password_hash",)):
    out = {}
    for c in o.__table__.columns:
        if c.name in skip: continue
        v = o.meta if c.name == "metadata" else getattr(o, c.key)
        out[c.name] = v.isoformat() + "Z" if isinstance(v, dt.datetime) else v
    return out
