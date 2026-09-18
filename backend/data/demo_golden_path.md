# MediKiosk Golden Path Demo Script — 5 Minutes

## Demo Patient
- **Name**: Rajesh Kumar
- **Age**: 58 years, Male
- **ABHA**: rajesh.kumar@abdm (91-1024-5829-1482)
- **History**: Type 2 DM, Hypertension, Mild Anemia

---

## Timeline Script

### 0:00 — Language Select & Identity *(Dev 2)*
1. Kiosk displays **LanguageSelector** — tap **हिंदी (Hindi)**
2. Voice-Only Mode toggle visible but leave OFF for demo
3. **IdentityScreen** appears → enter ABHA: `rajesh.kumar@abdm`
4. System verifies → demographics auto-fill: "Rajesh Kumar, Male, 58Y"

### 0:30 — Consent Flow *(Dev 2)*
1. **ConsentFlow** screen reads 3 consent items aloud (TTS)
2. Patient says **"Haan"** (voice confirmation captured)
3. All 3 consents granted → append-only audit log entry

### 0:45 — ABDM Auto-Fetch *(Dev 1 + Dev 2)*
1. Banner: **"2 existing records found linked to your ABHA"**
   - Visit 1 (Jun 2026): Prescription — Metformin 500mg, Ecosprin 75mg, Telmisartan 40mg
   - Visit 2 (Aug 2026): Lab Report — HbA1c 6.8%, Hb 9.2 g/dL (Low)
2. Records feed into Smart Recall context

### 1:00 — Interview Starts *(Dev 1)*
1. Kiosk asks: **"नमस्ते, आज आपको अस्पताल किस तकलीफ या समस्या के कारण आना पड़ा?"**
2. Patient says: **"Seene mein dard ho raha hai"** (chest pain)

### 1:15 — 🚨 Red Flag Triggers *(Dev 1)*
1. Red-flag detector matches: `RF-CARD-001` — chest pain
2. **Kiosk pauses interview** → calm message: "Please wait, alerting staff"
3. **Staff notification** sent via WebSocket → StaffAlertPanel lights up
4. **Presenter clicks "Acknowledge"** on staff dashboard

### 1:30 — Staff Acknowledges → SOCRATES Resumes *(Dev 1)*
1. Interview resumes with SOCRATES pain framework
2. **"यह दर्द छाती में ठीक किस तरफ महसूस हो रहा है?"** → "बाईं तरफ (Left)"

### 2:00 — Smart Recall: Contradiction Detected! *(Dev 1 + Dev 2)*
1. Medications step: **"Your records show Metformin 500mg — is that still current?"**
2. Patient: **"Doctor ne 1000mg kar di"** (Dose changed!)
3. 💥 **Contradiction detected**: Metformin 500mg (Prescription) → 1000mg (Patient verbal)
4. This gets flagged in the summary with `"conflicting"` verification

### 2:30 — Document Scan *(Dev 2)*
1. Patient shows new prescription
2. Kiosk camera captures → OCR runs → entities extracted
3. New entities appear in real-time via WebSocket progress

### 3:00 — Summary Generation *(Dev 1 → Dev 2 UI)*
1. **SummaryView** renders structured clinical summary
2. Dual-lens toggle visible (Allopathic / Ayurvedic)
3. Each field shows source citations (interview Q&A / document crop links)

### 3:15 — Click-to-Source *(Dev 2)*
1. Doctor clicks a medication field → **ClickToSource modal** opens
2. Shows the original prescription image with bounding box highlight
3. Side panel shows zoomed crop of the entity

### 3:30 — Contradiction Panel *(Dev 2)*
1. **ContradictionPanel** shows: "Metformin 500mg → 1000mg — confirm change?"
2. Doctor selects "Use Patient's Value" → resolves contradiction
3. Resolution logged in `summary_resolutions` audit table

### 3:45 — Doctor Confirms & ABDM Push *(Dev 1 + Dev 2)*
1. Doctor reviews final summary → clicks **"Confirm & Push to ABDM"**
2. FHIR R4 bundle generated → pushed to ABDM sandbox gateway
3. Success banner: "ABDM Reference: ABDM-REF-XXXXXXXXXX"

### 4:15 — Patient After-Visit Summary *(Dev 1)*
1. **PatientSummaryCard** renders in simple Hindi language
2. QR code links to ABHA digital record
3. Card can be printed or shown on phone

### 4:30 — Session End & Privacy Wipe *(Dev 2)*
1. **Session end** triggered → kiosk resets
2. Backend: session status → "completed", in-memory caches purged
3. InterviewEngine session state cleaned up (no memory leak)
4. Kiosk returns to **KioskDashboard** — ready for next patient

---

## Talking Points for Judges

| Feature | Where to Highlight |
|---------|-------------------|
| **Multilingual Voice** | Hindi voice input at 1:00, TTS at consent |
| **Red Flag Safety** | Emergency pause at 1:15, staff notification |
| **Smart Recall** | Known medications confirmed at 2:00 |
| **Contradiction Detection** | Dosage discrepancy at 2:00 & 3:30 |
| **Document OCR** | Live scan at 2:30, bounding boxes |
| **Click-to-Source** | Evidence traceability at 3:15 |
| **FHIR/ABDM Integration** | Standards-compliant push at 3:45 |
| **Privacy by Design** | Complete wipe at 4:30 |
| **AYUSH Dual-Lens** | Toggle available at 3:00 (show if time) |
