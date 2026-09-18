"""
C3. Demo Golden Path — Automated Rehearsal with Timing
PS ID26047 — Final Phase Demo Prep

Runs the complete 5-minute golden path demo flow via API calls.
Times each segment and reports total duration.
Run 3 times to verify consistency.
"""

import time

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


DEMO_ANSWERS = [
    # Chief complaint: chest pain → triggers red flag + SOCRATES
    "seene mein dard ho raha hai",
    # SOCRATES axis (after red flag pause/resume)
    "बाईं तरफ (Left)",
    # PMH
    "हाँ, अभी भी है (Ongoing)",
    # Medications — Smart Recall: "Doctor ne 1000mg kar di" (contradiction!)
    "डोज़ बदल गई है (Dose changed)",
    # Allergies
    "नहीं",
    # Family history
    "हाँ, पिताजी को शुगर है",
    # Personal history
    "कोई नशा नहीं",
    # ROS
    "कभी कभी चक्कर आते हैं",
]


@pytest.mark.asyncio
async def test_golden_path_demo_run():
    """
    Execute the complete golden path demo:
    1. Session start with ABHA → 2. Consent → 3. Interview flow → 4. Summary → 5. FHIR push → 6. Session end

    Runs 3 times and records timing for each.
    """
    timings = []

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:

        for run in range(3):
            run_start = time.time()
            segment_times = {}

            # ── SEGMENT 1: ABHA Verify + Session Start (0:00 - 0:30) ──
            t0 = time.time()
            verify_resp = await client.post("/api/session/verify-abha", json={
                "abha_id": "rajesh.kumar@abdm"
            })
            assert verify_resp.status_code == 200
            demographics = verify_resp.json()
            assert demographics["name"] == "Rajesh Kumar"
            assert demographics["dob"] == "1968-05-14"

            start_resp = await client.post("/api/session/start", json={
                "abha_id": "rajesh.kumar@abdm",
                "patient_name": "Rajesh Kumar",
                "language": "hi",
                "interview_mode": "allopathic",
            })
            assert start_resp.status_code == 200
            session_id = start_resp.json()["session_id"]
            segment_times["1_identity"] = time.time() - t0

            # ── SEGMENT 2: Consent (0:30 - 0:45) ──
            t0 = time.time()
            consent_resp = await client.post("/api/session/consent", json={
                "session_id": session_id,
                "consents": [
                    {"action": "share_doctor", "granted": True},
                    {"action": "store_abdm", "granted": True},
                    {"action": "anonymized_research", "granted": True},
                ],
                "voice_confirmation_ref": "haan_voice_demo_001",
            })
            assert consent_resp.status_code == 200
            segment_times["2_consent"] = time.time() - t0

            # ── SEGMENT 3: ABDM Auto-Fetch (0:45 - 1:00) ──
            t0 = time.time()
            fhir_records = await client.get(
                f"/api/session/{session_id}/fhir",
                params={"abha_id": "rajesh.kumar@abdm"},
            )
            assert fhir_records.status_code == 200
            bundles = fhir_records.json()
            assert len(bundles) >= 2, "Expected 2 historical FHIR bundles"
            segment_times["3_abdm_fetch"] = time.time() - t0

            # ── SEGMENT 4: Interview (1:00 - 2:30) ──
            t0 = time.time()
            iv_start = await client.post("/api/interview/start", json={
                "session_id": session_id,
                "language": "hi",
            })
            assert iv_start.status_code == 200

            for answer in DEMO_ANSWERS:
                step_resp = await client.post("/api/interview/step", json={
                    "session_id": session_id,
                    "answer_text": answer,
                })
                assert step_resp.status_code == 200
            segment_times["4_interview"] = time.time() - t0

            # ── SEGMENT 5: Summary Generation (3:00 - 3:15) ──
            t0 = time.time()
            summary_resp = await client.post("/api/summary/generate", json={
                "session_id": session_id,
            })
            assert summary_resp.status_code == 200
            segment_times["5_summary"] = time.time() - t0

            # ── SEGMENT 6: FHIR Push (3:45 - 4:15) ──
            t0 = time.time()
            push_resp = await client.post("/api/fhir/push", json={
                "session_id": session_id,
                "patient_abha_id": "rajesh.kumar@abdm",
            })
            assert push_resp.status_code == 200
            segment_times["6_fhir_push"] = time.time() - t0

            # ── SEGMENT 7: Session End + Privacy Wipe (4:30) ──
            t0 = time.time()
            end_resp = await client.post("/api/session/end", json={
                "session_id": session_id,
            })
            assert end_resp.status_code == 200
            assert end_resp.json()["status"] == "wiped"
            segment_times["7_session_end"] = time.time() - t0

            total_time = time.time() - run_start
            timings.append({
                "run": run + 1,
                "total_seconds": round(total_time, 2),
                "segments": {k: round(v, 3) for k, v in segment_times.items()},
            })

    # ── Report ──
    print(f"\n{'='*60}")
    print(f"GOLDEN PATH DEMO REHEARSAL -- 3 Runs")
    print(f"{'='*60}")

    for t in timings:
        print(f"\n  Run {t['run']}: {t['total_seconds']}s total")
        for seg, dur in t["segments"].items():
            status = "[SLOW]" if dur > 15 else "[OK]"
            print(f"    {seg}: {dur:.3f}s {status}")

    avg_time = sum(t["total_seconds"] for t in timings) / len(timings)
    print(f"\n  Average: {avg_time:.2f}s")
    print(f"  Target: < 300s (5 minutes)")

    # All runs should complete (API-side is near-instant without real Gemini)
    for t in timings:
        assert t["total_seconds"] < 300, f"Run {t['run']} took {t['total_seconds']}s > 5 minutes"

    # No segment should take > 15 seconds
    for t in timings:
        for seg, dur in t["segments"].items():
            assert dur < 15, f"Run {t['run']}, segment {seg} took {dur:.1f}s > 15s"
