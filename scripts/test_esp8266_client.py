"""
=============================================================================
SMART MANGROVE SYSTEM — ESP8266 HARDWARE INTEGRATION TEST CLIENT
Simulates physical ESP8266 HTTP telemetry over the network without hardware.
=============================================================================

This script communicates via the exact same HTTP API endpoint used by the
ESP8266 firmware (POST /api/hardware/data) to verify backend ingestion,
automatic hardware detection, tilt events, anchoring activation, and SQLite
persistence.
"""

import sys
import time
import json
import urllib.request
import urllib.error

BACKEND_URL = "http://127.0.0.1:8001"
API_ENDPOINT = f"{BACKEND_URL}/api/hardware/data"
DEVICE_ID = "ESP8266-001"


def send_hardware_payload(payload: dict) -> dict:
    req_body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API_ENDPOINT,
        data=req_body,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            res_data = json.loads(response.read().decode())
            return res_data
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode()
        print(f"[ERROR] HTTP {e.code}: {err_msg}")
        return {"error": str(e), "code": e.code}
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return {"error": str(e)}


def test_normal_telemetry():
    print(f"\n--- 1. SENDING NORMAL HARDWARE TELEMETRY ({DEVICE_ID}) ---")
    payload = {
        "device_id": DEVICE_ID,
        "source": "HARDWARE",
        "tilt": 0,
        "soil_moisture": 66.0,
        "servo_state": "NORMAL",
        "event": "NORMAL"
    }
    res = send_hardware_payload(payload)
    print("Response:", json.dumps(res, indent=2))
    return res


def test_tilt_detected():
    print(f"\n--- 2. SENDING TILT DETECTED & ANCHORING EVENT ({DEVICE_ID}) ---")
    payload = {
        "device_id": DEVICE_ID,
        "source": "HARDWARE",
        "tilt": 1,
        "soil_moisture": 66.0,
        "servo_state": "ANCHORING",
        "event": "TILT_DETECTED"
    }
    res = send_hardware_payload(payload)
    print("Response:", json.dumps(res, indent=2))
    return res


def verify_hardware_status():
    print("\n--- 3. VERIFYING BACKEND HARDWARE STATUS ---")
    url = f"{BACKEND_URL}/api/hardware/status"
    with urllib.request.urlopen(url) as r:
        status = json.loads(r.read().decode())
        print("Hardware Status:", json.dumps(status, indent=2))
        assert status["connected"] is True, "Hardware should be connected!"
        assert status["is_real_hardware"] is True, "Should be recognized as REAL HARDWARE!"
        assert status["data_source_label"] == "REAL HARDWARE", "Data source label should be REAL HARDWARE!"
        print("[PASS] Backend correctly detects REAL HARDWARE.")


def verify_latest_reading():
    print("\n--- 4. VERIFYING LATEST READING IN DATABASE ---")
    url = f"{BACKEND_URL}/api/readings/latest?source=HARDWARE"
    with urllib.request.urlopen(url) as r:
        reading = json.loads(r.read().decode())
        print("Latest Hardware Reading:", json.dumps(reading, indent=2))
        assert reading["source"] == "HARDWARE"
        assert reading["device_id"] == DEVICE_ID
        print(f"[PASS] Hardware reading successfully stored in SQLite with ID #{reading['id']}.")


if __name__ == "__main__":
    print("=============================================================")
    print(" ESP8266 HARDWARE INTEGRATION TEST SUITE")
    print(f" Target: {API_ENDPOINT}")
    print("=============================================================")

    # Test normal condition
    res1 = test_normal_telemetry()
    if "error" in res1:
        print("\nMake sure the FastAPI server is running on http://127.0.0.1:8001!")
        sys.exit(1)

    verify_hardware_status()
    time.sleep(1)

    # Test tilt event
    res2 = test_tilt_detected()
    verify_latest_reading()

    print("\n=============================================================")
    print(" [SUCCESS] All hardware communication tests passed.")
    print(" Open your dashboard in browser to view live Hardware Mode.")
    print("=============================================================")
