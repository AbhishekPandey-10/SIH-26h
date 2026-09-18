@echo off
echo ============================================================
echo   MediKiosk AI Clinical Intake - Starting Local Dev Servers
echo ============================================================

echo [1/3] Seeding demo patient data (Rajesh Kumar)...
cd /d "%~dp0backend"
call .venv\Scripts\python scripts\seed_demo_patient.py

echo [2/3] Starting FastAPI Backend on http://localhost:8000 ...
start "MediKiosk-Backend" cmd /k ".venv\Scripts\python -m uvicorn app.main:app --reload --port 8000"

echo [3/3] Starting React Frontend on http://localhost:5173 ...
cd /d "%~dp0frontend"
start "MediKiosk-Frontend" cmd /k "npm run dev"

echo.
echo ============================================================
echo   MediKiosk is launching!
echo   Kiosk UI:    http://localhost:5173
echo   API Docs:    http://localhost:8000/docs
echo ============================================================
