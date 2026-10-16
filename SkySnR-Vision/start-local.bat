@echo off
start "SkySnR Backend" cmd /k "cd backend && .venv\Scripts\activate && uvicorn app.main:app --reload --port 8000"
timeout /t 3 >nul
start "SkySnR Frontend" cmd /k "cd frontend && npm run dev"
