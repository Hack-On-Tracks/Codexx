from bson import ObjectId
from conftest import add_user, login, png
from app.services.priority_service import compute_priority, level_for
from app.services import detection_service


# ---- auth / registration ----
def reg(**kw):
    base = {"full_name": "Rohan Patil", "email": "rohan@x.in", "password": "Password123",
            "confirm_password": "Password123", "role": "rescue_manager"}
    return {**base, **kw}


def test_registration_is_pending_and_blocked(client, db):
    assert client.post("/api/auth/register", json=reg()).status_code == 201
    u = db.users.find_one({"email": "rohan@x.in"})
    assert u["approval_status"] == "pending" and u["password_hash"] != "Password123"
    r = client.post("/api/auth/login", json={"email": "rohan@x.in", "password": "Password123"})
    assert r.status_code == 403 and "approval" in r.json()["detail"]


def test_public_admin_registration_rejected(client):
    assert client.post("/api/auth/register", json=reg(role="admin")).status_code == 422


def test_password_mismatch_and_duplicate(client):
    assert client.post("/api/auth/register", json=reg(confirm_password="nope12345")).status_code == 422
    client.post("/api/auth/register", json=reg())
    assert client.post("/api/auth/register", json=reg()).status_code == 409


def test_wrong_password_and_no_hash_leak(client, people):
    assert client.post("/api/auth/login", json={"email": "priya@x.in", "password": "bad"}).status_code == 401
    me = client.get("/api/auth/me", headers=people["mgr"]).json()
    assert "password_hash" not in me and me["role"] == "rescue_manager"


def test_inactive_and_rejected_cannot_login(client, db):
    add_user(db, "A", "rej@x.in", "rescue_member", status="rejected", active=False)
    add_user(db, "B", "off@x.in", "rescue_member", active=False)
    assert client.post("/api/auth/login", json={"email": "rej@x.in", "password": "Password123"}).status_code == 403
    assert client.post("/api/auth/login", json={"email": "off@x.in", "password": "Password123"}).status_code == 403


def test_unauthenticated_blocked(client):
    assert client.get("/api/incidents").status_code == 401


# ---- admin approvals ----
def test_admin_approve_reject_persist_and_no_double(client, people, db):
    client.post("/api/auth/register", json=reg())
    client.post("/api/auth/register", json=reg(email="s@x.in", full_name="Sneha Iyer", role="rescue_member"))
    a = str(db.users.find_one({"email": "rohan@x.in"})["_id"])
    b = str(db.users.find_one({"email": "s@x.in"})["_id"])
    assert client.patch(f"/api/users/{a}/approve", headers=people["admin"]).status_code == 200
    assert client.patch(f"/api/users/{a}/approve", headers=people["admin"]).status_code == 409
    assert client.patch(f"/api/users/{b}/reject", headers=people["admin"]).status_code == 200
    assert db.users.find_one({"email": "rohan@x.in"})["approval_status"] == "approved"
    assert db.users.find_one({"email": "s@x.in"})["approval_status"] == "rejected"
    assert login(client, "rohan@x.in")  # now eligible
    assert client.post("/api/auth/login", json={"email": "s@x.in", "password": "Password123"}).status_code == 403


def test_roles_are_enforced_on_backend(client, people, db):
    client.post("/api/auth/register", json=reg())
    uid = str(db.users.find_one({"email": "rohan@x.in"})["_id"])
    for who in ("m1", "mgr"):
        assert client.patch(f"/api/users/{uid}/approve", headers=people[who]).status_code == 403
        assert client.get("/api/users", headers=people[who]).status_code == 403
    assert client.post("/api/missions", headers=people["m1"], json={}).status_code == 403
    assert client.post("/api/missions", headers=people["admin"], json={}).status_code == 403
    assert client.get("/api/missions", headers=people["m1"]).status_code == 403
    assert client.post("/api/reports/generate", headers=people["m1"], json={"mission_id": "x"}).status_code == 403


def test_existing_accounts_untouched(db):
    before = add_user(db, "Existing Manager", "keep@x.in", "rescue_manager")
    snap = dict(db.users.find_one({"_id": before}))
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app):
        pass  # startup (index creation) must not alter data
    assert db.users.find_one({"_id": before}) == snap and db.users.count_documents({}) == 1


# ---- missions / inference ----
MISSION = {"mission_name": "Pune Building Collapse Assessment", "disaster_type": "earthquake_building_collapse",
           "terrain_type": "urban_earthquake", "location_description": "Pune"}


def test_mission_persists(client, people, db):
    r = client.post("/api/missions", headers=people["mgr"], json=MISSION)
    assert r.status_code == 201 and db.missions.count_documents({}) == 1
    assert r.json()["guidance"]


def test_upload_validation(client, people):
    mid = client.post("/api/missions", headers=people["mgr"], json=MISSION).json()["id"]
    url = f"/api/missions/{mid}/analyze"
    h = people["mgr"]
    assert client.post(url, headers=h, files={"file": ("a.txt", b"hi", "text/plain")}).status_code == 415
    assert client.post(url, headers=h, files={"file": ("a.mp4", b"x", "video/mp4")}).status_code == 415
    assert client.post(url, headers=h, files={"file": ("a.png", b"notanimage", "image/png")}).status_code == 422
    assert client.post(url, headers=h, files={"file": ("a.png", b"", "image/png")}).status_code == 422


def test_inference_not_configured_returns_503_and_stores_nothing(client, people, db):
    mid = client.post("/api/missions", headers=people["mgr"], json=MISSION).json()["id"]
    r = client.post(f"/api/missions/{mid}/analyze", headers=people["mgr"],
                    files={"file": ("a.png", png(), "image/png")})
    assert r.status_code == 503 and "not configured" in r.json()["detail"]
    assert db.detections.count_documents({}) == 0


def test_parse_rejects_bad_payload_and_converts_boxes():
    import pytest
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        detection_service.parse_roboflow_response({"oops": 1}, 10, 10)
    out = detection_service.parse_roboflow_response(
        {"predictions": [{"x": 100, "y": 50, "width": 20, "height": 10, "confidence": .5, "class": "person"},
                         {"bad": True}]}, 200, 100)
    assert len(out) == 1 and out[0]["bounding_box"] == {"x": 90.0, "y": 45.0, "width": 20, "height": 10}


def test_analyze_pipeline_stores_detections(analysed, db):
    mid, res = analysed
    assert res["detection_count"] == 4 and db.detections.count_documents({}) == 4
    assert db.missions.find_one({"_id": ObjectId(mid)})["status"] == "analyzed"
    assert all(d["review_status"] == "unreviewed" for d in db.detections.find())


# ---- priority scoring ----
def _d(cls, x, y, w=40, h=80):
    return {"_id": ObjectId(), "object_class": cls, "bounding_box": {"x": x, "y": y, "width": w, "height": h}}


KW = dict(person_classes={"person"}, obstacle_classes={"debris"}, proximity_factor=3.0)


def test_scoring_rules():
    p = _d("person", 0, 0)
    assert compute_priority(p, [p], **KW)["score"] == 20
    assert compute_priority(p, [p], urgent=True, **KW)["score"] == 45
    near = [_d("debris", 50, 0) for _ in range(5)]
    r = compute_priority(p, [p] + near, **KW)
    assert r["score"] == 20 + 45  # obstacle cap
    other = _d("person", 60, 0)
    r = compute_priority(p, [p, other] + near, urgent=True, **KW)
    assert r["score"] == 100 and r["level"] == "high"  # 20+45+10+25
    far = _d("debris", 5000, 5000)
    assert compute_priority(p, [p, far], **KW)["score"] == 20  # not nearby -> not counted
    assert compute_priority(_d("debris", 0, 0), [], **KW)["score"] == 0
    assert compute_priority(p, [p] + near, person_classes={"person"}, obstacle_classes=set())["score"] == 20


def test_levels():
    assert [level_for(s) for s in (0, 39, 40, 69, 70, 100)] == ["low", "low", "medium", "medium", "high", "high"]


def test_priority_override_requires_justification_and_keeps_calculated(client, people, analysed, db):
    mid, res = analysed
    person = next(d for d in res["detections"] if d["object_class"] == "person")
    url = f"/api/detections/{person['id']}/priority"
    assert client.post(url, headers=people["mgr"], json={"override_level": "high"}).status_code == 422
    r = client.post(url, headers=people["mgr"], json={"urgent_flag": False, "override_level": "high",
                                                      "override_justification": "Visible waving"})
    d = r.json()
    assert r.status_code == 200 and d["final_priority_level"] == "high"
    assert d["priority_score"] == person["priority_score"] and d["override"]["justification"]


# ---- full workflow ----
def make_incident(client, people, analysed):
    mid, res = analysed
    person = next(d for d in res["detections"] if d["object_class"] == "person")
    h = people["mgr"]
    assert client.post("/api/incidents", headers=h, json={"detection_id": person["id"]}).status_code == 409
    assert client.post(f"/api/detections/{person['id']}/review", headers=h,
                       json={"decision": "confirmed", "notes": "Clearly a person"}).status_code == 200
    r = client.post("/api/incidents", headers=h, json={"detection_id": person["id"], "manager_notes": "Roof"})
    assert r.status_code == 201, r.text
    assert client.post("/api/incidents", headers=h, json={"detection_id": person["id"]}).status_code == 409
    return r.json()


def test_full_incident_lifecycle(client, people, analysed, db):
    inc = make_incident(client, people, analysed)
    iid, mgr, m1, m2 = inc["id"], people["mgr"], people["m1"], people["m2"]
    assert inc["status"] == "pending_assignment"
    ana = str(db.users.find_one({"email": "ananya@x.in"})["_id"])

    team = client.get("/api/team", headers=mgr).json()
    assert len(team) == 2 and all(t["assigned_total"] == 0 for t in team)
    assert client.post(f"/api/incidents/{iid}/assign", headers=mgr, json={"member_id": str(ObjectId())}).status_code == 422
    mgr_id = str(db.users.find_one({"email": "priya@x.in"})["_id"])
    assert client.post(f"/api/incidents/{iid}/assign", headers=mgr, json={"member_id": mgr_id}).status_code == 422
    assert client.post(f"/api/incidents/{iid}/assign", headers=m1, json={"member_id": ana}).status_code == 403
    assert client.post(f"/api/incidents/{iid}/assign", headers=mgr, json={"member_id": ana}).status_code == 200

    # visibility: assigned member sees it, other member does not
    assert [i["id"] for i in client.get("/api/incidents", headers=m1).json()] == [iid]
    assert client.get("/api/incidents", headers=m2).json() == []
    assert client.get(f"/api/incidents/{iid}", headers=m2).status_code == 404
    assert client.post(f"/api/incidents/{iid}/acknowledge", headers=m2).status_code == 404
    assert client.get(f"/api/incidents/{iid}/events", headers=m2).status_code == 404
    assert client.get(f"/api/incidents/{iid}", headers=m1).json()["evidence_url"]

    # transitions enforced
    assert client.post(f"/api/incidents/{iid}/start", headers=m1).status_code == 409  # not acknowledged
    assert client.post(f"/api/incidents/{iid}/resolve", headers=m1, data={"outcome": "done"}).status_code == 409
    assert client.post(f"/api/incidents/{iid}/acknowledge", headers=m1).status_code == 200
    assert client.post(f"/api/incidents/{iid}/acknowledge", headers=m1).status_code == 409
    assert client.post(f"/api/incidents/{iid}/start", headers=mgr).status_code == 403
    assert client.post(f"/api/incidents/{iid}/start", headers=m1).status_code == 200
    assert client.post(f"/api/incidents/{iid}/assign", headers=mgr, json={"member_id": ana}).status_code == 409

    assert client.post(f"/api/incidents/{iid}/events", headers=m1, json={"notes": "On site"}).status_code == 201
    # manager sees member progress
    seen = client.get(f"/api/incidents/{iid}", headers=mgr).json()
    assert seen["status"] == "in_progress"

    r = client.post(f"/api/incidents/{iid}/resolve", headers=m1,
                    data={"outcome": "Person assisted to safety", "field_observations": "Water waist-deep"},
                    files={"file": ("e.png", png(), "image/png")})
    assert r.status_code == 200 and r.json()["status"] == "resolved" and r.json()["resolution_evidence"]
    assert client.post(f"/api/incidents/{iid}/start", headers=m1).status_code == 409

    types = [e["event_type"] for e in client.get(f"/api/incidents/{iid}/events", headers=mgr).json()]
    assert types == ["created", "assigned", "acknowledged", "response_started", "note", "resolved"]
    stats = client.get("/api/stats", headers=m1).json()
    assert stats["resolved"] == 1 and stats["assigned_total"] == 1
    assert client.get("/api/team", headers=mgr).json()[0]["assigned_total"] in (0, 1)
    assert client.get("/api/incidents?status=resolved", headers=mgr).json()[0]["outcome"].startswith("Person")

    # media is protected
    ref = client.get(f"/api/incidents/{iid}", headers=m1).json()["evidence_url"]
    assert client.get(ref, headers=m1).status_code == 200
    assert client.get(ref, headers=m2).status_code == 404
    assert client.get(ref).status_code == 401
    assert client.get("/api/media/%2e%2e/%2e%2e/etc/passwd", headers=mgr).status_code in (404, 422)


def test_pdf_report_generated_and_downloadable(client, people, analysed, db):
    inc = make_incident(client, people, analysed)
    mid = analysed[0]
    mgr = people["mgr"]
    r = client.post("/api/reports/generate", headers=mgr, json={"mission_id": mid})
    assert r.status_code == 201 and r.json()["status"] == "ready"
    d = client.get(f"/api/reports/{r.json()['id']}/download", headers=mgr)
    assert d.status_code == 200 and d.content[:5] == b"%PDF-" and len(d.content) > 2000
    assert len(client.get("/api/reports", headers=mgr).json()) == 1
    assert client.get(f"/api/reports/{r.json()['id']}/download", headers=people["m1"]).status_code == 403
    assert client.post("/api/reports/generate", headers=mgr, json={"mission_id": str(ObjectId())}).status_code == 404


def test_dismissed_detection_cannot_become_incident(client, people, analysed):
    _, res = analysed
    det = res["detections"][0]
    client.post(f"/api/detections/{det['id']}/review", headers=people["mgr"],
                json={"decision": "dismissed", "notes": "Shadow"})
    assert client.post("/api/incidents", headers=people["mgr"], json={"detection_id": det["id"]}).status_code == 409
