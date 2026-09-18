# MediKiosk — Production Deployment Guide
**PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs**

This document describes how to deploy MediKiosk across various environments:
1. **Local / On-Premise Kiosk Machine** (Hospital hardware running Windows or Ubuntu Linux)
2. **Containerized Production** (`docker-compose.prod.yml` with Nginx reverse proxy)
3. **Cloud PaaS / VPS** (AWS EC2, DigitalOcean, Render, Railway)

---

## 1. Environment Configuration

Create a `.env` file in the project root based on [`.env.example`](file:///.env.example):

```env
# General
ENVIRONMENT=production
DEBUG=false
KIOSK_ID=KIOSK-DELHI-OPD-01

# Gemini API (Primary Clinical Reasoning & Fallback Handling)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# Bhashini API (Indian Multilingual TTS / ASR)
BHASHINI_USER_ID=your_bhashini_user_id
BHASHINI_API_KEY=your_bhashini_api_key
BHASHINI_PIPELINE_ID=your_pipeline_id

# Database (PostgreSQL with SQLite offline fallback)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/medikiosk
DATABASE_URL_SYNC=postgresql+psycopg2://postgres:postgres@localhost:5432/medikiosk
USE_SQLITE_FALLBACK=true
SQLITE_DB_PATH=./medikiosk_dev.db

# ABDM / National Health Stack
ABDM_CLIENT_ID=mock-abdm-client-id
ABDM_CLIENT_SECRET=mock-abdm-client-secret
ABDM_BASE_URL=https://dev.abdm.gov.in/gateway/v0.5

# CORS Configuration
CORS_ORIGINS=http://localhost:5173,http://localhost:80,http://localhost:3000
```

---

## 2. Deployment Option A: Docker Compose (Recommended for Production)

Docker Compose deploys the complete stack (FastAPI Backend, PostgreSQL 16, and Nginx-powered React Frontend) in isolated containers with automated healthchecks.

### Quick Start
```bash
# 1. Build and launch all production containers in background
docker compose -f docker-compose.prod.yml up --build -d

# 2. Seed the demo patient (Rajesh Kumar)
docker compose -f docker-compose.prod.yml exec backend python scripts/seed_demo_patient.py

# 3. View running container status
docker compose -f docker-compose.prod.yml ps
```

### URLs
- **Web Kiosk & Doctor Interface**: `http://localhost:80` (or `http://<server-ip>`)
- **FastAPI REST API & Docs**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/health`

### Teardown
```bash
docker compose -f docker-compose.prod.yml down
```

---

## 3. Deployment Option B: Bare-Metal / Kiosk Hardware

For direct installation on hospital touchscreen kiosks or laptop workstations:

### Prerequisites
- Python 3.12+
- Node.js 20+
- SQLite or PostgreSQL

### One-Click Launchers
- **Windows**: Double-click [`start_dev.bat`](file:///w:/SIH/Proj/start_dev.bat)
- **Linux/macOS**: Run `./start_dev.sh`

### Manual Execution

```bash
# 1. Backend Setup
cd backend
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -e .
python scripts/seed_demo_patient.py
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# 2. Frontend Setup
cd ../frontend
npm install
npm run build
# Serve via Vite preview or static web server
npm run preview -- --host 0.0.0.0 --port 5173
```

---

## 4. Deployment Option C: Cloud VPS (AWS EC2 / DigitalOcean)

To deploy on a standard Ubuntu 22.04 LTS instance:

1. **Install Docker & Compose**:
   ```bash
   sudo apt-get update
   sudo apt-get install -y docker.io docker-compose-v2
   sudo systemctl enable --now docker
   ```

2. **Clone & Configure**:
   ```bash
   git clone <repo-url> /opt/medikiosk
   cd /opt/medikiosk
   cp .env.example .env
   # Edit .env with your Gemini API key
   nano .env
   ```

3. **Start Service**:
   ```bash
   docker compose -f docker-compose.prod.yml up -d --build
   docker compose -f docker-compose.prod.yml exec backend python scripts/seed_demo_patient.py
   ```

4. **Firewall / Security Group**:
   - Allow Port `80` (HTTP)
   - Allow Port `443` (HTTPS with Certbot / Let's Encrypt)
   - Allow Port `8000` (API & WebSocket traffic if accessed directly)

---

## 5. Pre-Flight Verification Checklist

Run these commands before handing over the system or demonstrating to evaluators:

| Check | Command | Expected Result |
| :--- | :--- | :--- |
| **Backend Unit & E2E Tests** | `pytest tests/ -v` | `96 passed` (100% pass) |
| **Frontend Unit Tests** | `npm test` | `8 passed` |
| **Frontend Build** | `npm run build` | Zero build errors |
| **Database Seed** | `python scripts/seed_demo_patient.py` | `[OK] Demo patient seeded` |
| **Golden Path Rehearsal** | `pytest tests/test_demo_golden_path.py -s` | `< 1s` per run |
| **Offline Health Check** | `curl http://localhost:8000/health` | `status: healthy` |
