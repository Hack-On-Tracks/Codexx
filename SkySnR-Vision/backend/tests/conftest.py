import io, os, tempfile
import mongomock, pytest
from PIL import Image

os.environ["JWT_SECRET"] = "test-secret-" + "x" * 40
os.environ["STORAGE_DIR"] = tempfile.mkdtemp()
os.environ["OBSTACLE_CLASSES"] = "debris"
os.environ["PERSON_CLASSES"] = "person"
os.environ["ROBOFLOW_API_KEY"] = ""
os.environ["ROBOFLOW_MODEL_ID"] = ""

from fastapi.testclient import TestClient
from app import database
from app.config import get_settings
from app.dependencies import hash_password
from app.main import app
from app.services import detection_service


@pytest.fixture()
def db():
    get_settings.cache_clear()
    d = mongomock.MongoClient()["skysnr_vision"]
    database.set_db(d)
    return d


@pytest.fixture()
def client(db):
    with TestClient(app) as c:
        yield c


def add_user(db, name, email, role, status="approved", active=True, pw="Password123"):
    return db.users.insert_one({"full_name": name, "email": email, "password_hash": hash_password(pw),
                                "role": role, "approval_status": status, "is_active": active,
                                "created_at": database.now()}).inserted_id


def login(client, email, pw="Password123"):
    r = client.post("/api/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    client.cookies.clear()  # tests authenticate per-request with Bearer headers
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def people(db, client):
    add_user(db, "Aarav Sharma", "admin@x.in", "admin")
    add_user(db, "Priya Deshmukh", "priya@x.in", "rescue_manager")
    add_user(db, "Ananya Kulkarni", "ananya@x.in", "rescue_member")
    add_user(db, "Neha Joshi", "neha@x.in", "rescue_member")
    return {"admin": login(client, "admin@x.in"), "mgr": login(client, "priya@x.in"),
            "m1": login(client, "ananya@x.in"), "m2": login(client, "neha@x.in")}


def png(w=800, h=600):
    b = io.BytesIO()
    Image.new("RGB", (w, h), (120, 130, 125)).save(b, "PNG")
    return b.getvalue()


# Roboflow-shaped payload (centre-based boxes). Used ONLY to exercise our pipeline;
# it is not evidence that the real model works.
ROBOFLOW_SHAPED = {"image": {"width": 800, "height": 600}, "predictions": [
    {"x": 400, "y": 300, "width": 40, "height": 80, "confidence": 0.91, "class": "person", "detection_id": "a"},
    {"x": 440, "y": 320, "width": 40, "height": 80, "confidence": 0.85, "class": "person", "detection_id": "b"},
    {"x": 450, "y": 340, "width": 60, "height": 40, "confidence": 0.70, "class": "debris", "detection_id": "c"},
    {"x": 700, "y": 100, "width": 60, "height": 40, "confidence": 0.60, "class": "debris", "detection_id": "d"}]}


@pytest.fixture()
def analysed(client, people, monkeypatch):
    monkeypatch.setattr(detection_service, "call_roboflow", lambda data: ROBOFLOW_SHAPED)
    m = client.post("/api/missions", headers=people["mgr"], json={
        "mission_name": "Mumbai Urban Flood Response", "disaster_type": "flood", "terrain_type": "flood",
        "location_description": "Kurla, Mumbai"}).json()
    r = client.post(f"/api/missions/{m['id']}/analyze", headers=people["mgr"],
                    files={"file": ("a.png", png(), "image/png")})
    assert r.status_code == 200, r.text
    return m["id"], r.json()
