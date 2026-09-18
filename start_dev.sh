#!/usr/bin/env bash
set -e

echo "============================================================"
echo "  MediKiosk AI Clinical Intake - Starting Local Dev Servers"
echo "============================================================"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[1/3] Seeding demo patient data (Rajesh Kumar)..."
cd "$PROJECT_ROOT/backend"
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi
python scripts/seed_demo_patient.py || true

echo "[2/3] Starting FastAPI Backend on http://localhost:8000 ..."
python -m uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

echo "[3/3] Starting React Frontend on http://localhost:5173 ..."
cd "$PROJECT_ROOT/frontend"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "============================================================"
echo "  MediKiosk is running!"
echo "  Kiosk UI:    http://localhost:5173"
echo "  API Docs:    http://localhost:8000/docs"
echo "  Press Ctrl+C to terminate both servers."
echo "============================================================"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
