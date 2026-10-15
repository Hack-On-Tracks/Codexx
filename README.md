# SkySnR Vision — Backend (FastAPI + SQLAlchemy + SQLite)

## Setup (Windows PowerShell shown; use `source .venv/bin/activate` on Linux/Mac)
```
cd backend
python -m venv .venv ; .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env        # then edit SECRET_KEY, ADMIN_EMAIL, ADMIN_PASSWORD
```
Load env vars (PowerShell): `Get-Content .env | % { if ($_ -match '^([^#=]+)=(.*)$') { [Environment]::SetEnvironmentVariable($matches[1], $matches[2]) } }`

## Run
`uvicorn app.main:app --reload --port 8000` → API docs at http://localhost:8000/docs
Tables are created automatically on startup. The admin is created once from ADMIN_EMAIL / ADMIN_PASSWORD (never hardcoded).

## Workflow
1. Register Manager/Operator via `POST /api/auth/register` → status PENDING (cannot sign in).
2. Admin signs in, `GET /api/admin/registrations`, then `PATCH /api/admin/users/{id}/approve`.
3. Simulation: `POST /api/simulations/start {"scenario":"flood"}` (data_origin=simulation, labeled "SIMULATION — NOT LIVE RESCUE DATA").
4. Upload: `POST /api/evidence/upload` (multipart: mission_id, file). Files get generated names and are served only via `GET /api/evidence/{id}/file` with authorization.
5. Review a detection (`PATCH /api/detections/{id}/review` CONFIRMED) → `create-case` → `assign` → operator posts `/updates`.

## Connect a real model later
Set `MODEL_URL` to a Python service exposing `GET /health`, `GET /classes`, `POST /predict/image`, `POST /predict/video` (multipart field `file`) returning
`{"model_version": "...", "detections":[{"class_name":"person","confidence":0.9,"bbox":[x1,y1,x2,y2],"track_id":null,"frame_index":null,"timestamp_seconds":null}]}`.
bbox = [x1,y1,x2,y2] source pixels, top-left origin. With MODEL_URL empty, `/api/analysis/run` returns status `not_configured`; failures never fall back to simulation.

## Tests
`pip install pytest` then `pytest tests -q`

## Not included yet
Websocket progress/queued video jobs (video runs synchronously with a timeout), operator evidence attachments, frame extraction with OpenCV/FFmpeg, rate limiting beyond login, DB migrations (Alembic).
