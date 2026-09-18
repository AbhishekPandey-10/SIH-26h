"""
Verification script for live WebSocket connection to /ws/interview
"""

import asyncio
import json
import sys

import websockets

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


async def test_live_interview():
    uri = "ws://127.0.0.1:8000/ws/interview?session_id=live_test_kiosk_01"
    print(f"Connecting to {uri}...")

    async with websockets.connect(uri) as ws:
        # Turn 1: Welcome / Chief Complaint
        msg1_raw = await ws.recv()
        msg1 = json.loads(msg1_raw)
        print(f"[TURN 1 RECEIVED] Section: {msg1.get('section')} | Q: {msg1.get('text')}")
        assert msg1.get("section") == "chief_complaint"

        # Turn 2: Send CC answer
        print("[TURN 2 SENDING] Answer: 'मुझे पेट में दर्द है'")
        await ws.send(json.dumps({"answer": "मुझे पेट में दर्द है"}))
        msg2_raw = await ws.recv()
        msg2 = json.loads(msg2_raw)
        print(f"[TURN 2 RECEIVED] Section: {msg2.get('section')} | Q: {msg2.get('text')}")
        assert msg2.get("section") == "socrates"
        assert msg2.get("is_red_flag_warning") is False

        # Turn 3: Send Red-Flag trigger
        print("[TURN 3 SENDING] Red flag answer: 'Now chest pain with breathlessness'")
        await ws.send(json.dumps({"answer": "Now chest pain with breathlessness"}))
        msg3_raw = await ws.recv()
        msg3 = json.loads(msg3_raw)
        print(f"[TURN 3 RECEIVED] Section: {msg3.get('section')} | Alert: {msg3.get('is_red_flag_warning')}")
        assert msg3.get("is_red_flag_warning") is True
        print(f"Red flag details: {msg3.get('red_flag_details')}")

    print("\n>>> LIVE WEBSOCKET VERIFICATION PASSED SUCCESSFULLY! <<<\n")


if __name__ == "__main__":
    asyncio.run(test_live_interview())
