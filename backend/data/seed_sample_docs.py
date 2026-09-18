"""
Generator script for 17 realistic Indian clinical sample documents with ground-truth JSON.
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs
"""

import json
from pathlib import Path

SAMPLE_DOCS_DIR = Path(__file__).resolve().parent / "sample_docs"
SAMPLE_DOCS_DIR.mkdir(parents=True, exist_ok=True)

DOCUMENTS = [
    # --------------------------------------------------------------------------
    # 1. PRINTED PRESCRIPTIONS (5)
    # --------------------------------------------------------------------------
    {
        "id": "doc_01_prescription_printed",
        "doc_type": "prescription",
        "title": "AIIMS New Delhi — Department of Medicine OPD Prescription",
        "text": """================================================================================
ALL INDIA INSTITUTE OF MEDICAL SCIENCES (AIIMS), NEW DELHI
अखिल भारतीय आयुर्विज्ञान संस्थान, नई दिल्ली
DEPARTMENT OF GENERAL MEDICINE — OPD PRESCRIPTION
Date: 2025-03-15 | UHID: 105829148 | OPD Reg No: MED-2025-08912
Patient Name: Rajesh Kumar | Age: 52 Y / Male | ABHA: rajesh.kumar@abdm
Dr. S. K. Sharma, MD (Med), FICP | Reg No: MCI-29184
================================================================================
CLINICAL DIAGNOSIS:
  1. Type 2 Diabetes Mellitus (Uncontrolled)
  2. Essential Systemic Hypertension (Grade 1)
  3. Dyslipidemia

Rx (MEDICATIONS):
  1. Tab. Glycomet GP 1 (Metformin 500mg + Glimepiride 1mg)
     Sig: 1 tab orally twice daily, before meals (OD morning + OD night)
     Duration: 30 days | Generic: Metformin + Glimepiride

  2. Tab. Telma 40 (Telmisartan 40mg)
     Sig: 1 tab orally once daily, morning after breakfast
     Duration: 30 days | Generic: Telmisartan

  3. Tab. Rosuvas 10 (Rosuvastatin 10mg)
     Sig: 1 tab orally once daily at bedtime
     Duration: 30 days | Generic: Rosuvastatin

ADVICE / INSTRUCTIONS:
  - Diabetic diet, low salt intake (< 5g/day), brisk walk 30 mins daily
  - Review in OPD after 1 month with Fasting Blood Sugar & Serum Creatinine
================================================================================
""",
        "entities": [
            {"type": "diagnosis", "value": "Type 2 Diabetes Mellitus", "date": "2025-03-15", "bbox": [0.12, 0.22, 0.45, 0.03], "confidence": 0.98},
            {"type": "diagnosis", "value": "Essential Systemic Hypertension", "date": "2025-03-15", "bbox": [0.12, 0.25, 0.48, 0.03], "confidence": 0.97},
            {"type": "diagnosis", "value": "Dyslipidemia", "date": "2025-03-15", "bbox": [0.12, 0.28, 0.25, 0.03], "confidence": 0.96},
            {"type": "medication", "value": "Tab. Glycomet GP 1", "generic": "Metformin + Glimepiride", "date": "2025-03-15", "bbox": [0.08, 0.35, 0.65, 0.06], "confidence": 0.99},
            {"type": "medication", "value": "Tab. Telma 40", "generic": "Telmisartan", "date": "2025-03-15", "bbox": [0.08, 0.43, 0.55, 0.06], "confidence": 0.99},
            {"type": "medication", "value": "Tab. Rosuvas 10", "generic": "Rosuvastatin", "date": "2025-03-15", "bbox": [0.08, 0.51, 0.55, 0.06], "confidence": 0.99}
        ]
    },
    {
        "id": "doc_02_prescription_printed",
        "doc_type": "prescription",
        "title": "Safdarjung Hospital — OPD Prescription (Acute Respiratory Infection)",
        "text": """================================================================================
VARDHMAN MAHAVIR MEDICAL COLLEGE & SAFDARJUNG HOSPITAL, NEW DELHI
DEPARTMENT OF INTERNAL MEDICINE
Date: 2025-03-10 | CR No: 202503100412 | OPD Room: 14
Patient: Sunita Devi | 44 Y / Female | ABHA: sunita.devi@abdm
Dr. Anita Verma, MBBS, MD (Medicine) | DMC Reg: 44102
================================================================================
CHIEF COMPLAINTS:
  - High grade fever with chills x 4 days
  - Productive cough with yellowish sputum x 3 days
  - Sore throat & body ache

Rx:
  1. Tab. Augmentin 625mg (Amoxicillin 500mg + Clavulanic Acid 125mg)
     Dosage: 1 tablet TDS (thrice daily) after food x 5 days
     Generic: Amoxicillin + Clavulanate Potassium

  2. Tab. Dolo 650 (Paracetamol 650mg)
     Dosage: 1 tablet SOS for fever > 100°F (max 3 tabs/day)
     Generic: Paracetamol

  3. Tab. Pantocid 40 (Pantoprazole 40mg)
     Dosage: 1 tablet OD empty stomach in the morning x 5 days
     Generic: Pantoprazole
================================================================================
""",
        "entities": [
            {"type": "diagnosis", "value": "Acute Bronchitis / Lower Respiratory Infection", "date": "2025-03-10", "bbox": [0.10, 0.22, 0.60, 0.04], "confidence": 0.95},
            {"type": "medication", "value": "Tab. Augmentin 625mg", "generic": "Amoxicillin + Clavulanate", "date": "2025-03-10", "bbox": [0.08, 0.36, 0.62, 0.06], "confidence": 0.99},
            {"type": "medication", "value": "Tab. Dolo 650", "generic": "Paracetamol", "date": "2025-03-10", "bbox": [0.08, 0.44, 0.58, 0.06], "confidence": 0.99},
            {"type": "medication", "value": "Tab. Pantocid 40", "generic": "Pantoprazole", "date": "2025-03-10", "bbox": [0.08, 0.52, 0.58, 0.06], "confidence": 0.98}
        ]
    },
    {
        "id": "doc_03_prescription_printed",
        "doc_type": "prescription",
        "title": "Apollo Hospitals — Cardiology Outpatient Prescription",
        "text": """================================================================================
INDRAPRASTHA APOLLO HOSPITALS, SARITA VIHAR, NEW DELHI
CARDIOLOGY CLINICAL SERVICES
Date: 2025-02-28 | MRN: APL-902184 | ABHA: amit.sharma@abdm
Patient Name: Amit Sharma | Age: 58 Y | Sex: M
Consultant: Dr. Rajiv Malhotra, MD, DM (Cardiology) | Reg No: DMC-18920
================================================================================
DIAGNOSIS:
  Coronary Artery Disease (Post PTCA Stent to LAD in 2023)
  Hypertension / Left Ventricular Diastolic Dysfunction

MEDICATIONS:
  1. Tab. Ecosprin AV 75/20 (Aspirin 75mg + Atorvastatin 20mg)
     1 capsule once daily post dinner | Generic: Aspirin + Atorvastatin

  2. Tab. Brilinta 90mg (Ticagrelor 90mg)
     1 tab twice daily with or without food | Generic: Ticagrelor

  3. Tab. Metolar XR 25 (Metoprolol Succinate 25mg)
     1 tab once daily in morning | Generic: Metoprolol Succinate

  4. Tab. Ramistar 2.5 (Ramipril 2.5mg)
     1 tab once daily at bedtime | Generic: Ramipril
================================================================================
""",
        "entities": [
            {"type": "diagnosis", "value": "Coronary Artery Disease (Post PTCA Stent to LAD)", "date": "2025-02-28", "bbox": [0.10, 0.20, 0.65, 0.04], "confidence": 0.99},
            {"type": "medication", "value": "Tab. Ecosprin AV 75/20", "generic": "Aspirin + Atorvastatin", "date": "2025-02-28", "bbox": [0.08, 0.32, 0.65, 0.05], "confidence": 0.99},
            {"type": "medication", "value": "Tab. Brilinta 90mg", "generic": "Ticagrelor", "date": "2025-02-28", "bbox": [0.08, 0.39, 0.55, 0.05], "confidence": 0.99},
            {"type": "medication", "value": "Tab. Metolar XR 25", "generic": "Metoprolol Succinate", "date": "2025-02-28", "bbox": [0.08, 0.46, 0.58, 0.05], "confidence": 0.98},
            {"type": "medication", "value": "Tab. Ramistar 2.5", "generic": "Ramipril", "date": "2025-02-28", "bbox": [0.08, 0.53, 0.52, 0.05], "confidence": 0.98}
        ]
    },
    {
        "id": "doc_04_prescription_printed",
        "doc_type": "prescription",
        "title": "Max Super Speciality Hospital — Pulmonology OPD Prescription",
        "text": """================================================================================
MAX HEALTHCARE — PULMONOLOGY & CHEST MEDICINE
Date: 2025-01-20 | Patient: Priya Patel | Age: 36 Y / F | ABHA: priya.patel@abdm
Dr. Arvind Tandon, MD (Chest Medicine) | Reg: DMC-33921
================================================================================
DIAGNOSIS:
  Bronchial Asthma (Moderate Persistent) with Allergic Rhinitis

PRESCRIPTION:
  1. Inhaler Foracort 200 (Formoterol 6mcg + Budesonide 200mcg)
     2 puffs twice daily with spacer, rinse mouth after inhalation
     Generic: Formoterol Fumarate + Budesonide

  2. Tab. Montair LC (Montelukast 10mg + Levocetirizine 5mg)
     1 tablet daily at bedtime x 14 days
     Generic: Montelukast + Levocetirizine

  3. Nasal Spray Flomist (Fluticasone Propionate 50mcg)
     2 sprays in each nostril once daily in morning x 1 month
================================================================================
""",
        "entities": [
            {"type": "diagnosis", "value": "Bronchial Asthma (Moderate Persistent)", "date": "2025-01-20", "bbox": [0.10, 0.19, 0.58, 0.03], "confidence": 0.97},
            {"type": "diagnosis", "value": "Allergic Rhinitis", "date": "2025-01-20", "bbox": [0.10, 0.22, 0.35, 0.03], "confidence": 0.96},
            {"type": "medication", "value": "Inhaler Foracort 200", "generic": "Formoterol + Budesonide", "date": "2025-01-20", "bbox": [0.08, 0.30, 0.65, 0.06], "confidence": 0.99},
            {"type": "medication", "value": "Tab. Montair LC", "generic": "Montelukast + Levocetirizine", "date": "2025-01-20", "bbox": [0.08, 0.38, 0.62, 0.05], "confidence": 0.99},
            {"type": "medication", "value": "Nasal Spray Flomist", "generic": "Fluticasone Propionate", "date": "2025-01-20", "bbox": [0.08, 0.45, 0.60, 0.05], "confidence": 0.97}
        ]
    },
    {
        "id": "doc_05_prescription_printed",
        "doc_type": "prescription",
        "title": "Fortis Escorts — Endocrinology Prescription (Triple Therapy)",
        "text": """================================================================================
FORTIS ESCORTS HEART INSTITUTE & RESEARCH CENTRE, OKHLA, NEW DELHI
DEPARTMENT OF ENDOCRINOLOGY & METABOLISM
Date: 2025-03-02 | Patient: Ramesh Chand | Age: 61 Y / M | UHID: FEHI-77291
Dr. Vikram Saxena, MD, DM (Endocrinology) | Reg: MCI-55214
================================================================================
CLINICAL SUMMARY: T2DM with Microalbuminuria & Obesity (BMI 31.4)
Rx:
  1. Tab. Forxiga 10mg (Dapagliflozin 10mg)
     1 tab once daily morning with breakfast | Generic: Dapagliflozin

  2. Tab. Janumet 50/500 (Sitagliptin 50mg + Metformin 500mg)
     1 tab BD after meals | Generic: Sitagliptin + Metformin

  3. Tab. Volibo 0.3 (Voglibose 0.3mg)
     1 tab just before lunch and dinner | Generic: Voglibose
================================================================================
""",
        "entities": [
            {"type": "diagnosis", "value": "Type 2 Diabetes with Microalbuminuria", "date": "2025-03-02", "bbox": [0.10, 0.18, 0.60, 0.03], "confidence": 0.97},
            {"type": "medication", "value": "Tab. Forxiga 10mg", "generic": "Dapagliflozin", "date": "2025-03-02", "bbox": [0.08, 0.25, 0.55, 0.05], "confidence": 0.99},
            {"type": "medication", "value": "Tab. Janumet 50/500", "generic": "Sitagliptin + Metformin", "date": "2025-03-02", "bbox": [0.08, 0.32, 0.62, 0.05], "confidence": 0.99},
            {"type": "medication", "value": "Tab. Volibo 0.3", "generic": "Voglibose", "date": "2025-03-02", "bbox": [0.08, 0.39, 0.52, 0.05], "confidence": 0.98}
        ]
    },

    # --------------------------------------------------------------------------
    # 2. HANDWRITTEN PRESCRIPTIONS (3)
    # --------------------------------------------------------------------------
    {
        "id": "doc_06_prescription_handwritten",
        "doc_type": "prescription",
        "title": "Community Health Centre Clinic Slip (Handwritten Format)",
        "text": """[COMMUNITY CLINIC RX - HANDWRITTEN DOCTOR SLIP]
Patient: Meena Devi, 29/F | Date: 12/03/2025 | OPD No: 341
C/o: Loose motions x 2 days, vomiting, crampy abd pain.
O/E: Dehydration mild, P 94/min, BP 106/70, Abd soft, non-tender.

Rx:
  1. Tab Ciplox TZ (Ciprofloxacin 500mg + Tinidazole 600mg)
     1 tab BD x 5 days
  2. Tab Ondem 4mg (Ondansetron)
     1 tab TDS SOS for vomiting
  3. Electral sachet (Oral Rehydration Salts)
     1 pkt in 1L boiled cooled water, sip frequently
  4. Tab Pantocid 40 OD AC x 5 days

Dr. R. P. Gupta, MBBS (Reg: 19824/UP)
""",
        "entities": [
            {"type": "diagnosis", "value": "Acute Gastroenteritis / Loose stools", "date": "2025-03-12", "bbox": [0.05, 0.15, 0.50, 0.06], "confidence": 0.92},
            {"type": "medication", "value": "Tab Ciplox TZ", "generic": "Ciprofloxacin + Tinidazole", "date": "2025-03-12", "bbox": [0.05, 0.32, 0.60, 0.06], "confidence": 0.94},
            {"type": "medication", "value": "Tab Ondem 4mg", "generic": "Ondansetron", "date": "2025-03-12", "bbox": [0.05, 0.40, 0.55, 0.06], "confidence": 0.93},
            {"type": "medication", "value": "Electral sachet", "generic": "Oral Rehydration Salts (ORS)", "date": "2025-03-12", "bbox": [0.05, 0.48, 0.58, 0.06], "confidence": 0.95}
        ]
    },
    {
        "id": "doc_07_prescription_handwritten",
        "doc_type": "prescription",
        "title": "Orthopaedic Clinic Slip (Handwritten Format - Lumbar Spondylosis)",
        "text": """[SHARMA ORTHO CLINIC - HANDWRITTEN SLIP]
Pt: Harish Kumar, 48/M | Dt: 05/03/2025
Complaint: Low back ache radiating to right buttock x 3 weeks.
Diagnosis: Lumbar Radiculopathy / Muscle Spasm (L4-L5)

Rx:
  1. Tab Zerodol TH 4 (Aceclofenac 100mg + Thiocolchicoside 4mg)
     1 tab BD pc x 7 days
  2. Tab Rabekind 20 (Rabeprazole 20mg)
     1 tab OD bbf x 7 days
  3. Tab Pregabalin 75mg + Methylcobalamin 1500mcg
     1 tab at night x 15 days
  4. Local Volini gel application TDS

Adv: Lumbar belt, avoid forward bending, physio.
Dr. V. K. Sharma, MS Ortho (Reg: 41092)
""",
        "entities": [
            {"type": "diagnosis", "value": "Lumbar Radiculopathy / Muscle Spasm", "date": "2025-03-05", "bbox": [0.06, 0.16, 0.60, 0.05], "confidence": 0.91},
            {"type": "medication", "value": "Tab Zerodol TH 4", "generic": "Aceclofenac + Thiocolchicoside", "date": "2025-03-05", "bbox": [0.06, 0.30, 0.65, 0.06], "confidence": 0.93},
            {"type": "medication", "value": "Tab Rabekind 20", "generic": "Rabeprazole", "date": "2025-03-05", "bbox": [0.06, 0.38, 0.55, 0.06], "confidence": 0.92},
            {"type": "medication", "value": "Tab Pregabalin + Methylcobalamin", "generic": "Pregabalin + Methylcobalamin", "date": "2025-03-05", "bbox": [0.06, 0.46, 0.68, 0.06], "confidence": 0.91}
        ]
    },
    {
        "id": "doc_08_prescription_handwritten",
        "doc_type": "prescription",
        "title": "Neurology Clinic Slip (Handwritten Format - Generalized Seizure)",
        "text": """[CITY NEURO CLINIC - HANDWRITTEN SLIP]
Patient: Kavita Rao, 26/F | Date: 18/02/2025 | Ref: Dr. S. Rao
Known case of GTCS (Epilepsy). Last episode 3 days back.
EEG: Generalized spike-wave discharges.

Rx:
  1. Tab Levepsy 500 (Levetiracetam 500mg)
     1 tab twice daily (1-0-1) regularly. Do not skip doses.
  2. Tab Frisium 10 (Clobazam 10mg)
     1 tab at night (0-0-1) x 1 month
  3. Tab Shelcal 500 (Calcium + Vitamin D3)
     1 tab OD after lunch x 30 days

Review after 1 month. Emergency SOS in case of repeated convulsions.
Dr. Deepa Nair, DM Neurology (Reg: 31084)
""",
        "entities": [
            {"type": "diagnosis", "value": "Generalized Tonic-Clonic Seizures (GTCS / Epilepsy)", "date": "2025-02-18", "bbox": [0.05, 0.15, 0.65, 0.05], "confidence": 0.95},
            {"type": "medication", "value": "Tab Levepsy 500", "generic": "Levetiracetam", "date": "2025-02-18", "bbox": [0.05, 0.32, 0.60, 0.06], "confidence": 0.96},
            {"type": "medication", "value": "Tab Frisium 10", "generic": "Clobazam", "date": "2025-02-18", "bbox": [0.05, 0.40, 0.55, 0.06], "confidence": 0.94},
            {"type": "medication", "value": "Tab Shelcal 500", "generic": "Calcium + Vitamin D3", "date": "2025-02-18", "bbox": [0.05, 0.48, 0.58, 0.06], "confidence": 0.95}
        ]
    },

    # --------------------------------------------------------------------------
    # 3. LAB REPORTS (4)
    # --------------------------------------------------------------------------
    {
        "id": "doc_09_lab_cbc",
        "doc_type": "lab_report",
        "title": "Dr. Lal PathLabs — Complete Blood Count (CBC) with ESR",
        "text": """================================================================================
DR. LAL PATHLABS — NATIONAL REFERENCE LABORATORY, NEW DELHI
LABORATORY INVESTIGATION REPORT: COMPLETE BLOOD COUNT (CBC)
Patient: Rajesh Kumar | 52 Y / M | Date: 2025-03-14 | Lab No: 91823101
Ref By: Dr. S. K. Sharma (AIIMS)
================================================================================
TEST NAME                    RESULT    FLAG      UNIT        REFERENCE RANGE
--------------------------------------------------------------------------------
Hemoglobin (Hb)              9.8       LOW       g/dL        13.0 - 17.0
Total Leukocyte Count (TLC) 12,400     HIGH      /cumm       4,000 - 10,000
Neutrophils                  78        HIGH      %           40 - 70
Lymphocytes                  16        LOW       %           20 - 45
Eosinophils                  3                   %           1 - 6
Monocytes                    3                   %           2 - 8
Platelet Count               185,000             /cumm       150,000 - 410,000
Packed Cell Volume (PCV)     31.2      LOW       %           40.0 - 50.0
Mean Corpuscular Volume      74.0      LOW       fL          80.0 - 100.0
ESR (Westergren)             42        HIGH      mm/1st hr   0 - 15
--------------------------------------------------------------------------------
INTERPRETATION: Microcytic hypochromic anemia with neutrophilic leukocytosis.
================================================================================
""",
        "entities": [
            {"type": "lab_value", "value": "9.8", "generic": "Hemoglobin", "unit": "g/dL", "reference_range": "13.0 - 17.0", "is_abnormal": True, "date": "2025-03-14", "bbox": [0.10, 0.28, 0.60, 0.03], "confidence": 0.99},
            {"type": "lab_value", "value": "12400", "generic": "Total Leukocyte Count", "unit": "/cumm", "reference_range": "4000 - 10000", "is_abnormal": True, "date": "2025-03-14", "bbox": [0.10, 0.32, 0.60, 0.03], "confidence": 0.99},
            {"type": "lab_value", "value": "185000", "generic": "Platelet Count", "unit": "/cumm", "reference_range": "150000 - 410000", "is_abnormal": False, "date": "2025-03-14", "bbox": [0.10, 0.44, 0.60, 0.03], "confidence": 0.99},
            {"type": "lab_value", "value": "74.0", "generic": "MCV", "unit": "fL", "reference_range": "80.0 - 100.0", "is_abnormal": True, "date": "2025-03-14", "bbox": [0.10, 0.52, 0.60, 0.03], "confidence": 0.98},
            {"type": "lab_value", "value": "42", "generic": "ESR", "unit": "mm/1st hr", "reference_range": "0 - 15", "is_abnormal": True, "date": "2025-03-14", "bbox": [0.10, 0.56, 0.60, 0.03], "confidence": 0.98}
        ]
    },
    {
        "id": "doc_10_lab_lft",
        "doc_type": "lab_report",
        "title": "SRL Diagnostics — Liver Function Test (LFT) Profile",
        "text": """================================================================================
SRL DIAGNOSTICS — LIVER FUNCTION TEST (LFT) REPORT
Patient: Ramesh Chand | 61 Y / M | Date: 2025-03-01 | Sample: Serum
================================================================================
TEST NAME                    RESULT    FLAG      UNIT        BIOLOGICAL REF
--------------------------------------------------------------------------------
Bilirubin Total              1.8       HIGH      mg/dL       0.2 - 1.2
Bilirubin Direct             0.6       HIGH      mg/dL       0.0 - 0.3
SGOT / AST                   88        HIGH      U/L         10 - 40
SGPT / ALT                   104       HIGH      U/L         10 - 45
Alkaline Phosphatase (ALP)   180                 U/L         40 - 240
Total Protein                6.8                 g/dL        6.0 - 8.3
Serum Albumin                3.4                 g/dL        3.5 - 5.0
A/G Ratio                    1.0                 ratio       1.0 - 2.1
--------------------------------------------------------------------------------
IMPRESSION: Mild transaminitis with indirect predominant hyperbilirubinemia.
================================================================================
""",
        "entities": [
            {"type": "lab_value", "value": "1.8", "generic": "Bilirubin Total", "unit": "mg/dL", "reference_range": "0.2 - 1.2", "is_abnormal": True, "date": "2025-03-01", "bbox": [0.10, 0.28, 0.60, 0.03], "confidence": 0.99},
            {"type": "lab_value", "value": "88", "generic": "SGOT", "unit": "U/L", "reference_range": "10 - 40", "is_abnormal": True, "date": "2025-03-01", "bbox": [0.10, 0.36, 0.60, 0.03], "confidence": 0.99},
            {"type": "lab_value", "value": "104", "generic": "SGPT", "unit": "U/L", "reference_range": "10 - 45", "is_abnormal": True, "date": "2025-03-01", "bbox": [0.10, 0.40, 0.60, 0.03], "confidence": 0.99},
            {"type": "lab_value", "value": "180", "generic": "Alkaline Phosphatase", "unit": "U/L", "reference_range": "40 - 240", "is_abnormal": False, "date": "2025-03-01", "bbox": [0.10, 0.44, 0.60, 0.03], "confidence": 0.98}
        ]
    },
    {
        "id": "doc_11_lab_kft",
        "doc_type": "lab_report",
        "title": "Max Labs — Kidney Function Test (KFT) & Electrolytes",
        "text": """================================================================================
MAX LAB — BIOCHEMISTRY DEPARTMENT
REPORT: RENAL / KIDNEY FUNCTION TEST (KFT)
Patient: Amit Sharma | 58 Y / M | Date: 2025-02-27 | Barcode: MXKFT-99120
================================================================================
TEST                         RESULT    FLAG      UNIT        NORMAL RANGE
--------------------------------------------------------------------------------
Blood Urea                   48.0      HIGH      mg/dL       15.0 - 40.0
Serum Creatinine             1.65      HIGH      mg/dL       0.70 - 1.20
Estimated GFR (CKD-EPI)      48        LOW       mL/min/1.73m2 >= 60
Serum Uric Acid              7.8       HIGH      mg/dL       3.5 - 7.2
Sodium (Na+)                 138                 mEq/L       135 - 145
Potassium (K+)               4.7                 mEq/L       3.5 - 5.1
Chloride (Cl-)               101                 mEq/L       96 - 106
--------------------------------------------------------------------------------
REMARKS: Reduced eGFR consistent with CKD Stage 3a. Serum Creatinine elevated.
================================================================================
""",
        "entities": [
            {"type": "lab_value", "value": "48.0", "generic": "Blood Urea", "unit": "mg/dL", "reference_range": "15.0 - 40.0", "is_abnormal": True, "date": "2025-02-27", "bbox": [0.10, 0.28, 0.60, 0.03], "confidence": 0.99},
            {"type": "lab_value", "value": "1.65", "generic": "Serum Creatinine", "unit": "mg/dL", "reference_range": "0.70 - 1.20", "is_abnormal": True, "date": "2025-02-27", "bbox": [0.10, 0.32, 0.60, 0.03], "confidence": 0.99},
            {"type": "lab_value", "value": "48", "generic": "eGFR", "unit": "mL/min/1.73m2", "reference_range": ">= 60", "is_abnormal": True, "date": "2025-02-27", "bbox": [0.10, 0.36, 0.60, 0.03], "confidence": 0.98},
            {"type": "lab_value", "value": "4.7", "generic": "Potassium", "unit": "mEq/L", "reference_range": "3.5 - 5.1", "is_abnormal": False, "date": "2025-02-27", "bbox": [0.10, 0.48, 0.60, 0.03], "confidence": 0.98}
        ]
    },
    {
        "id": "doc_12_lab_hba1c",
        "doc_type": "lab_report",
        "title": "Thyrocare — Glycated Hemoglobin (HbA1c) & Blood Glucose",
        "text": """================================================================================
THYROCARE TECHNOLOGIES LTD — CENTRAL PROCESSING LABORATORY
TEST: HbA1c (GLYCATED HEMOGLOBIN) BY HPLC METHOD
Patient: Rajesh Kumar | 52 Y / M | Date: 2025-03-14 | Acc No: TC-882194
================================================================================
TEST NAME                    RESULT    FLAG      UNIT        TARGET / RANGE
--------------------------------------------------------------------------------
HbA1c (Glycated Hb)          9.2       HIGH      %           < 5.7 (Normal)
                                                             5.7 - 6.4 (Prediabetes)
                                                             >= 6.5 (Diabetes)
Estimated Average Glucose    217       HIGH      mg/dL       100 - 140
Blood Glucose Fasting (FBS)  184       HIGH      mg/dL       70 - 100
Blood Glucose PP (Post-Meal) 262       HIGH      mg/dL       < 140
--------------------------------------------------------------------------------
CLINICAL COMMENT: HbA1c > 8.0 indicates poor glycemic control over past 90 days.
================================================================================
""",
        "entities": [
            {"type": "lab_value", "value": "9.2", "generic": "HbA1c", "unit": "%", "reference_range": "< 5.7", "is_abnormal": True, "date": "2025-03-14", "bbox": [0.10, 0.28, 0.60, 0.03], "confidence": 0.99},
            {"type": "lab_value", "value": "184", "generic": "Fasting Blood Sugar", "unit": "mg/dL", "reference_range": "70 - 100", "is_abnormal": True, "date": "2025-03-14", "bbox": [0.10, 0.40, 0.60, 0.03], "confidence": 0.99},
            {"type": "lab_value", "value": "262", "generic": "Post Prandial Blood Sugar", "unit": "mg/dL", "reference_range": "< 140", "is_abnormal": True, "date": "2025-03-14", "bbox": [0.10, 0.44, 0.60, 0.03], "confidence": 0.99}
        ]
    },

    # --------------------------------------------------------------------------
    # 4. DISCHARGE SUMMARIES (3)
    # --------------------------------------------------------------------------
    {
        "id": "doc_13_discharge_summary",
        "doc_type": "discharge_summary",
        "title": "Safdarjung Hospital — Inpatient Discharge Summary (Acute Diarrheal Illness)",
        "text": """================================================================================
VMMC & SAFDARJUNG HOSPITAL, NEW DELHI — CLINICAL DISCHARGE SUMMARY
Ward: Medicine Male Ward-8 | Bed: 14 | IPD No: IPD-2025-019284
Patient Name: Suresh Pal | Age: 42 Y / Male | ABHA: suresh.pal@abdm
Date of Admission: 2025-02-10 | Date of Discharge: 2025-02-13
================================================================================
FINAL DIAGNOSIS:
  Acute Infectious Gastroenteritis with Moderate Dehydration & Hypokalemia (Resolved)

HOSPITAL COURSE:
  Patient admitted with 15-20 episodes of watery stools and severe cramping.
  IV Ringer Lactate and KCL rehydration administered. Stool hanging drop negative.
  Vitals normalized on day 3. Tolerating soft oral diet.

DISCHARGE MEDICATIONS:
  1. Tab. Ofloxacin 200mg + Ornidazole 500mg (1 tab BD x 3 days)
  2. Tab. Racecadotril 100mg (1 cap TDS x 2 days)
  3. Cap. Darolac (Probiotic) 1 cap BD x 7 days
  4. ORS ad libitum

FOLLOW UP: Medical OPD on 2025-02-20.
Dr. Manoj Gupta, MD (Assistant Professor)
================================================================================
""",
        "entities": [
            {"type": "diagnosis", "value": "Acute Infectious Gastroenteritis with Moderate Dehydration", "date": "2025-02-10", "bbox": [0.10, 0.22, 0.70, 0.03], "confidence": 0.98},
            {"type": "medication", "value": "Tab. Ofloxacin + Ornidazole", "generic": "Ofloxacin + Ornidazole", "date": "2025-02-13", "bbox": [0.08, 0.42, 0.60, 0.05], "confidence": 0.97},
            {"type": "medication", "value": "Tab. Racecadotril 100mg", "generic": "Racecadotril", "date": "2025-02-13", "bbox": [0.08, 0.48, 0.55, 0.05], "confidence": 0.96},
            {"type": "procedure", "value": "IV Hydration & Electrolyte Correction", "date": "2025-02-10", "bbox": [0.10, 0.32, 0.55, 0.03], "confidence": 0.95}
        ]
    },
    {
        "id": "doc_14_discharge_summary",
        "doc_type": "discharge_summary",
        "title": "Fortis Escorts — Discharge Summary (Anterior Wall STEMI / PTCA)",
        "text": """================================================================================
FORTIS ESCORTS HEART INSTITUTE — DISCHARGE SUMMARY
Cardiology Unit II | IPD No: FE-2024-99821 | Room: 412
Patient: Amit Sharma | Age: 58 Y / M | ABHA: amit.sharma@abdm
Admission: 2024-11-12 | Discharge: 2024-11-16
Consultant: Dr. Rajiv Malhotra, MD, DM (Cardiology)
================================================================================
FINAL DIAGNOSIS:
  1. Acute Anterior Wall Myocardial Infarction (STEMI)
  2. Coronary Angiography: Critical 95% Proximal LAD Stenosis
  3. Status Post Primary PTCA + Drug Eluting Stent (DES) to LAD

PROCEDURAL SUMMARY:
  Primary PTCA done via right radial artery approach on 2024-11-12.
  Deployed Resolute Onyx 3.5 x 28mm DES at 14 atm. TIMI III flow achieved.
  Echocardiography: LVEF 45%, regional wall motion abnormality in LAD territory.

DISCHARGE ADVICE:
  1. Tab. Ticagrelor 90mg (1 tab BD - DO NOT STOP)
  2. Tab. Aspirin 75mg (1 tab OD after lunch)
  3. Tab. Atorvastatin 40mg (1 tab OD at night)
  4. Tab. Metoprolol Succinate 25mg (1 tab OD morning)
  5. Tab. Ramipril 2.5mg (1 tab OD bedtime)
================================================================================
""",
        "entities": [
            {"type": "diagnosis", "value": "Acute Anterior Wall Myocardial Infarction (STEMI)", "date": "2024-11-12", "bbox": [0.10, 0.20, 0.65, 0.03], "confidence": 0.99},
            {"type": "procedure", "value": "Primary PTCA with Drug Eluting Stent to LAD", "date": "2024-11-12", "bbox": [0.10, 0.26, 0.65, 0.03], "confidence": 0.99},
            {"type": "medication", "value": "Tab. Ticagrelor 90mg", "generic": "Ticagrelor", "date": "2024-11-16", "bbox": [0.08, 0.44, 0.55, 0.05], "confidence": 0.99},
            {"type": "medication", "value": "Tab. Aspirin 75mg", "generic": "Aspirin", "date": "2024-11-16", "bbox": [0.08, 0.50, 0.50, 0.05], "confidence": 0.99},
            {"type": "medication", "value": "Tab. Atorvastatin 40mg", "generic": "Atorvastatin", "date": "2024-11-16", "bbox": [0.08, 0.56, 0.55, 0.05], "confidence": 0.99}
        ]
    },
    {
        "id": "doc_15_discharge_summary",
        "doc_type": "discharge_summary",
        "title": "AIIMS New Delhi — Discharge Summary (Cellulitis with Uncontrolled T2DM)",
        "text": """================================================================================
AIIMS NEW DELHI — INPATIENT DISCHARGE SUMMARY
Department: Surgery Unit III | IP No: 2025-0038102
Patient: Baldev Singh | Age: 64 Y / M | ABHA: baldev.singh@abdm
Adm: 2025-01-04 | Disch: 2025-01-11
================================================================================
DIAGNOSIS:
  Right Lower Extremity Cellulitis with Diabetic Foot Ulcer (Wagner Grade II)
  Underlying T2DM with Peripheral Neuropathy

OPERATIVE INTERVENTION:
  Wound debridement under local anesthesia on 2025-01-05. Pus culture: Staph aureus.

DISCHARGE MEDS:
  1. Tab. Linezolid 600mg (1 tab BD x 7 days)
  2. Tab. Cefuroxime Axetil 500mg (1 tab BD x 7 days)
  3. Inj. Mixtard 30/70 (18 units morning, 12 units night before food)
  4. Tab. Pregabalin 75mg (1 tab at night)
  5. Daily sterile saline dressing.
================================================================================
""",
        "entities": [
            {"type": "diagnosis", "value": "Right Lower Extremity Cellulitis with Diabetic Foot Ulcer", "date": "2025-01-04", "bbox": [0.10, 0.20, 0.70, 0.03], "confidence": 0.98},
            {"type": "procedure", "value": "Wound Debridement Right Foot", "date": "2025-01-05", "bbox": [0.10, 0.28, 0.55, 0.03], "confidence": 0.97},
            {"type": "medication", "value": "Tab. Linezolid 600mg", "generic": "Linezolid", "date": "2025-01-11", "bbox": [0.08, 0.38, 0.55, 0.05], "confidence": 0.98},
            {"type": "medication", "value": "Inj. Mixtard 30/70", "generic": "Human Biphasic Insulin", "date": "2025-01-11", "bbox": [0.08, 0.50, 0.65, 0.05], "confidence": 0.99}
        ]
    },

    # --------------------------------------------------------------------------
    # 5. IMAGING & RADIOLOGY REPORTS (2)
    # --------------------------------------------------------------------------
    {
        "id": "doc_16_radiology_xray",
        "doc_type": "radiology_report",
        "title": "Mahajan Imaging — Digital Chest X-Ray (PA View)",
        "text": """================================================================================
MAHAJAN IMAGING & DIAGNOSTIC CENTRE, HAUZ KHAS, NEW DELHI
DIGITAL RADIOGRAPHY REPORT: CHEST PA VIEW
Patient: Sunita Devi | 44 Y / F | Date: 2025-03-10 | Ref ID: RAD-X-90184
Ref By: Dr. Anita Verma (Safdarjung Hospital)
================================================================================
FINDINGS:
  - Patchy alveolar consolidation seen in the right lower lung zone.
  - Costophrenic and cardiophrenic angles are clear bilaterally.
  - Cardiac shadow is within normal limits in size and configuration (CTR < 0.5).
  - Trachea is midline. Hilar shadows appear normal.
  - Bony cage and visualized soft tissues show no significant abnormality.

IMPRESSION:
  Right lower lobe consolidation consistent with acute bacterial pneumonia /
  bronchopneumonia. Recommend clinical correlation.
Dr. Alok Sen, MD (Radiodiagnosis) | Reg: DMC-20981
================================================================================
""",
        "entities": [
            {"type": "diagnosis", "value": "Right Lower Lobe Pneumonia / Consolidation", "date": "2025-03-10", "bbox": [0.10, 0.35, 0.70, 0.05], "confidence": 0.98},
            {"type": "procedure", "value": "Digital Chest Radiography (PA View)", "date": "2025-03-10", "bbox": [0.10, 0.15, 0.60, 0.03], "confidence": 0.99}
        ]
    },
    {
        "id": "doc_17_radiology_usg",
        "doc_type": "radiology_report",
        "title": "Focus Imaging — Ultrasound Whole Abdomen & Pelvis",
        "text": """================================================================================
FOCUS IMAGING & RESEARCH CENTRE, GREEN PARK, NEW DELHI
ULTRASONOGRAPHY: WHOLE ABDOMEN & PELVIS
Patient: Ramesh Chand | 61 Y / M | Date: 2025-03-01 | Case No: USG-33918
================================================================================
LIVER:
  Enlarged (16.2 cm). Shows diffuse increase in parenchymal echogenicity with
  attenuation of sound waves and poor visualization of portal vein walls.
  Features suggestive of Fatty Infiltration (Grade II Heposteatosis).

GALL BLADDER:
  Well distended. Single echogenic focus of size 8.5mm seen in the GB lumen
  with acoustic shadowing, suggestive of Cholelithiasis (Calculus). No wall edema.

KIDNEYS:
  Both kidneys normal in size, position and shape. Corticomedullary differentiation
  preserved. No calculus or hydronephrosis.

IMPRESSION:
  1. Hepatomegaly with Grade II Fatty Liver.
  2. Cholelithiasis (single 8.5mm calculus, asymptomatic).
Dr. Neha Kapoor, DMRD, DNB (Radiology)
================================================================================
""",
        "entities": [
            {"type": "diagnosis", "value": "Grade II Fatty Liver (Hepatosteatosis)", "date": "2025-03-01", "bbox": [0.10, 0.42, 0.65, 0.04], "confidence": 0.98},
            {"type": "diagnosis", "value": "Cholelithiasis (Gallbladder Stone)", "date": "2025-03-01", "bbox": [0.10, 0.47, 0.60, 0.04], "confidence": 0.97},
            {"type": "procedure", "value": "Ultrasonography Whole Abdomen", "date": "2025-03-01", "bbox": [0.10, 0.14, 0.55, 0.03], "confidence": 0.99}
        ]
    }
]


def seed_docs():
    count = 0
    for doc in DOCUMENTS:
        doc_id = doc["id"]
        # 1. Text document file
        txt_path = SAMPLE_DOCS_DIR / f"{doc_id}.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(doc["text"])

        # 2. Ground-truth annotation JSON
        gt_data = {
            "document_id": doc_id,
            "document_type": doc["doc_type"],
            "title": doc["title"],
            "entities": doc["entities"]
        }
        json_path = SAMPLE_DOCS_DIR / f"{doc_id}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(gt_data, f, indent=2, ensure_ascii=False)

        count += 1

    print(f"Successfully generated {count} realistic Indian clinical documents with ground-truth JSON in {SAMPLE_DOCS_DIR}")


if __name__ == "__main__":
    seed_docs()
