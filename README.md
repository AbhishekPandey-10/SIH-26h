# 🏥 MediKiosk — AI Clinical History-Taking Software for Indian Hospital OPDs

> **Smart India Hackathon (SIH) · Problem Statement ID: 26047**  
> **Master Documentation:** For the exhaustive, single-source-of-truth master document containing all clinical frameworks, judge Q&A defense, hospital economics, database schemas, and demo scripts, see [ALL_CONTEXT.md](file:///w:/SIH/ALL_CONTEXT.md).

---

## 📌 What is MediKiosk?

**MediKiosk** is an intelligent, patient-facing AI triage kiosk and clinical history-taking system designed specifically for high-volume Indian Outpatient Departments (OPDs). Operating directly in crowded waiting areas, MediKiosk transforms **2 to 3 hours of dead queue time** into **3 to 5 minutes of structured, voice-and-touch clinical pre-intake**.

> ⚖️ **The Golden Clinical Axiom:**  
> *"MediKiosk NEVER diagnoses. It never suggests treatments or drug prescriptions. It functions strictly as an Intelligent Clinical Clerk and Scribe. It drafts, flags, and surfaces evidence. The registered medical practitioner (RMP) remains the sole clinical authority who verifies, edits, and confirms everything."*

---

## 🚀 Core Pillars & Capabilities

1. **Smart Recall (Zero-Repeat Interview)**: Injects historical records from past visits and scanned slips into LangGraph state; confirms known facts rather than re-asking them.
2. **Evidence-Linked Click-to-Source**: Every fact in the doctor summary is linked to an exact verbatim quote or a magnified bounding-box crop of the original doctor's handwriting with 10% safety margin padding.
3. **Real-Time Red-Flag Escalation Engine**: Two-stage safety detector (keyword matching + Gemini confirmation) that pauses the interview on high-acuity triggers, reassures the patient, and fires instant priority alerts to triage nurses and doctor queue.
4. **AYUSH Dual-Lens Architecture**: Supports the classical Dashavidha Pariksha interview branch for Ayurvedic OPDs with a 1-click doctor toggle between Allopathic (SOAP) and Ayurvedic clinical assessments.
5. **DPDP Act 2023 & ABDM Compliant**:
   - Section 6 granular consent with verbal voice confirmation saved to an append-only PostgreSQL audit table.
   - 3-minute idle reset and session memory wipe.
   - Milestone 1, 2, 3 ABDM compliance with standardized FHIR R4 Bundles (`krama-core`).

---

## 🏗️ Repository Architecture

```
Proj/
├── docker-compose.yml       # Multi-container orchestration (Backend + Frontend + Postgres)
├── .env.example             # Configuration variables
├── backend/                 # FastAPI + LangGraph Python 3.11 Backend
│   ├── app/
│   │   ├── main.py          # Entrypoint & diagnostics
│   │   ├── routes/          # REST & WebSocket endpoints (interview, session, docs, summary)
│   │   ├── services/        # LangGraph engine, OCR processor, Red-flag detector, FHIR builder
│   │   ├── db/              # Async SQLAlchemy models (all 8 tables) & engine
│   │   └── shared/schemas.py# Strict Pydantic v2 API contracts
│   └── data/                # red_flags.json, indian_drug_map.json, lab_ranges.json
└── frontend/                # React 18 + Vite Kiosk Progressive Web App (PWA)
    ├── src/styles/tokens.css# High-contrast accessible design tokens
    ├── src/contexts/        # SessionContext (ABHA, consent, privacy wipe), OfflineContext
    └── src/components/      # Kiosk shell, Document camera, Doctor portal, Body map
```

---

## ⚡ Quick Start Guide

### Option 1: Docker Compose (Recommended)
```bash
# 1. From the Proj directory
cd w:/SIH/Proj

# 2. Set up environment
cp .env.example .env

# 3. Launch all services
docker-compose up --build
```
- **Backend API & Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Frontend Kiosk PWA:** [http://localhost:5173](http://localhost:5173)

### Option 2: Local Development (Without Docker)

#### Backend (FastAPI)
```bash
cd w:/SIH/Proj/backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install uv
uv pip install -e .
$env:USE_SQLITE_FALLBACK="true"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Frontend (React + Vite)
```bash
cd w:/SIH/Proj/frontend
npm install
npm run dev
```

---

## 📖 Key Reference Documents
- [ALL_CONTEXT.md](file:///w:/SIH/ALL_CONTEXT.md) — Comprehensive Master Technical Blueprint & Defense Bible
- [DEV1_ROADMAP.md](file:///w:/SIH/DEV1_ROADMAP.md) — Conversation & Intelligence Track Roadmap
- [DEV2_ROADMAP.md](file:///w:/SIH/DEV2_ROADMAP.md) — Documents, Data & Infrastructure Track Roadmap
- [Docs/Questions.pdf](file:///w:/SIH/Docs/Questions.pdf) — Senior Hackathon Judge Q&A Masterclass (Top 30 Questions)
- [demo-website/](file:///w:/SIH/demo-website) — Standalone interactive kiosk simulation
