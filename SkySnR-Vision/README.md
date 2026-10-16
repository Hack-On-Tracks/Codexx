# SkySnR Vision

Drone-image rescue decision-support app. **Frontend:** React + Vite. **Backend:** FastAPI + MongoDB (`skysnr_vision`).
It supports human decisions; it never replaces rescue professionals.

## What has and has not been verified
- Verified: 20 backend tests (in-memory MongoDB mock), frontend production build, and the full workflow
  (register -> approve -> mission -> analyse -> score -> confirm -> incident -> assign -> acknowledge -> start -> resolve -> PDF)
  driven through the Vite dev proxy with cookie sessions.
- **Not verified:** real Roboflow inference (the smoke test used a stand-in that returns Roboflow-shaped data), your real MongoDB data,
  and the UI in a real browser (no browser was available; pages were checked by build only).
- Images in `frontend/public/images/incidents/` are **labelled illustrations**, not photographs. Replace them with licensed
  Indian aerial photos using the same file names (or update `LandingPage.jsx`).

## Windows PowerShell setup
Open two terminals in VS Code.

**Terminal 1 - backend**
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -c "import secrets;print(secrets.token_urlsafe(48))"   # paste into JWT_SECRET in .env
python create_admin.py "Aarav Sharma" admin@example.com      # first admin (prompts for password)
uvicorn app.main:app --reload --port 8000
```
**Terminal 2 - frontend**
```powershell
cd frontend
npm install
npm run dev
```
Open http://localhost:5173 . API docs: http://localhost:8000/docs . Health: http://localhost:8000/api/health

## Existing database
Set `MONGODB_URI` in `backend/.env`; keep `MONGODB_DATABASE=skysnr_vision`. The app only creates missing indexes and never resets or edits users.
Existing accounts must use fields `full_name, email, password_hash (bcrypt), role (admin|rescue_manager|rescue_member), approval_status, is_active`.
If yours differ, adapt before use. A unique email index is created; a warning prints if existing duplicates block it.

## Roboflow
In `backend/.env` set `ROBOFLOW_API_KEY`, `ROBOFLOW_MODEL_ID`, and `PERSON_CLASSES` / `OBSTACLE_CLASSES` using the exact class names your
model returns. Until then Mission analysis shows "Inference is not configured" and stores nothing. Images only; video is rejected.

## Test each role
1. Register a manager and a team member at `/register` (they cannot sign in yet).
2. Sign in as admin, open **User approvals**, approve both.
3. Manager: **Mission analysis** -> create mission -> upload image -> review detections -> confirm -> create incident -> **Incidents** -> assign.
4. Member: **My incidents** -> acknowledge -> start -> mark resolved.
5. Manager: **Reports** -> generate -> download PDF.

## Optional demo data
```powershell
$env:SEED_PASSWORD = "choose-a-password"
python seed_demo.py --yes
```
Adds missing sample users/missions flagged `is_sample`. No fake detections or images.

## Tests / build
```powershell
cd backend; pytest -q
cd ../frontend; npm run build
```

## Design notes
- Only the five brand colours (plus opacity variations) are used; checked by script across `src/` and `public/`.
- The palette has no light neutral, so all text is Balsam Green on light tints. Contrast is moderate, not WCAG-AAA.
  Allowing one extra dark neutral for body text would improve readability.
- Sessions use an httpOnly cookie (SameSite=Lax); the Vite proxy keeps frontend and API on one origin. Set `COOKIE_SECURE=true` behind HTTPS.
- Not included: the Three.js landing scene, live telemetry, video analysis, "simulation mode" (it would require fake predictions).
