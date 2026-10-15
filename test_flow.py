import os, tempfile
t = tempfile.mkdtemp(); os.environ.update(DATABASE_URL=f"sqlite:///{t}/t.db", UPLOAD_DIR=t, ADMIN_EMAIL="a@x.org", ADMIN_PASSWORD="Admin-Pass-123")
from fastapi.testclient import TestClient
from app.main import app
def reg(c, em, role): return c.post("/api/auth/register", json=dict(full_name="Test User", email=em, password="Passw0rd!!", confirm_password="Passw0rd!!", phone="9999999999", organization="Org", role=role, accept_terms=True))
def test_flow():
    with TestClient(app) as A, TestClient(app) as M, TestClient(app) as O:
        assert A.post("/api/auth/login", json=dict(email="a@x.org", password="Admin-Pass-123")).status_code == 200
        assert reg(M, "m@x.org", "MANAGER").status_code == 201 and reg(O, "o@x.org", "OPERATOR").status_code == 201
        assert M.post("/api/auth/login", json=dict(email="m@x.org", password="Passw0rd!!")).status_code == 403
        for r in A.get("/api/admin/registrations").json(): assert A.patch(f"/api/admin/users/{r['id']}/approve").status_code == 200
        for c, e in ((M, "m@x.org"), (O, "o@x.org")): assert c.post("/api/auth/login", json=dict(email=e, password="Passw0rd!!")).status_code == 200
        assert O.get("/api/admin/users").status_code == 403 and O.get("/api/detections").status_code == 403
        mid = M.post("/api/missions", json=dict(title="Flood A", location_name="Known site", disaster_type="flood")).json()["id"]
        up = M.post("/api/evidence/upload", data=dict(mission_id=mid), files=dict(file=("a.png", b"\x89PNG\r\n", "image/png"))); assert up.status_code == 201
        assert M.post("/api/evidence/upload", data=dict(mission_id=mid), files=dict(file=("a.exe", b"x", "x/y"))).status_code == 400
        j = M.post("/api/analysis/run", json=dict(evidence_id=up.json()["id"])).json(); assert j["status"] == "not_configured"
        s = M.post("/api/simulations/start", json=dict(scenario="flood")).json(); assert "SIMULATION" in s["label"]
        ds = M.get("/api/detections?origin=simulation").json(); assert ds and all(x["data_origin"] == "simulation" for x in ds)
        p = next(x for x in ds if x["class_name"] == "person")
        assert M.post(f"/api/detections/{p['id']}/create-case", json=dict(title="Person sighting")).status_code == 400  # must verify first
        assert M.patch(f"/api/detections/{p['id']}/review", json=dict(status="CONFIRMED")).status_code == 200
        c = M.post(f"/api/detections/{p['id']}/create-case", json=dict(title="Person sighting", danger=True)).json()
        oid = [u for u in A.get("/api/admin/users").json()["items"] if u["role"] == "OPERATOR"][0]["id"]
        assert M.post(f"/api/cases/{c['id']}/assign", json=dict(operator_id=oid)).status_code == 200
        assert O.get("/api/cases").json()[0]["id"] == c["id"]
        assert O.post(f"/api/cases/{c['id']}/updates", json=dict(new_status="RESOLVED", notes="x")).status_code == 409
        for st in ("ACKNOWLEDGED", "IN_PROGRESS", "RESOLVED"): assert O.post(f"/api/cases/{c['id']}/updates", json=dict(new_status=st, notes="ok")).status_code == 201
        assert O.post(f"/api/cases/{c['id']}/updates", json=dict(new_status="CLOSED", notes="x")).status_code == 403
        assert M.post(f"/api/cases/{c['id']}/updates", json=dict(new_status="CLOSED", notes="done")).status_code == 201
        assert M.patch(f"/api/cases/{c['id']}", json=dict(priority="LOW")).status_code == 400
        assert M.get("/api/analytics/overview").json()["detections"] > 0
        assert M.get(f"/api/reports/missions/{s['simulation_id']}/pdf").content[:4] == b"%PDF" and "SIMULATION" in M.get(f"/api/reports/missions/{s['simulation_id']}/csv").text
        assert len(A.get("/api/admin/audit-logs").json()) > 5
