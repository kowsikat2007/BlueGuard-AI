import sys
import time
import json
import urllib.request
import urllib.error
import subprocess

BASE_URL = "http://127.0.0.1:8001"

print("=================================================================")
print(" VERIFYING SMART MANGROVE SYSTEM — ESP8266 HARDWARE INTEGRATION")
print("=================================================================")

# 1. Start uvicorn server in subprocess
proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8001"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

try:
    print("[1/10] Waiting for server to initialize on port 8001...")
    server_ready = False
    for _ in range(20):
        try:
            with urllib.request.urlopen(f"{BASE_URL}/status", timeout=1) as r:
                if r.status == 200:
                    server_ready = True
                    break
        except Exception:
            time.sleep(0.5)

    assert server_ready, "Server failed to start on port 8001!"
    print("PASS: FastAPI backend is online and serving requests.")

    # 2. Verify Initial Hardware Status (Disconnected)
    print("\n[2/10] Verifying initial hardware connection status...")
    with urllib.request.urlopen(f"{BASE_URL}/api/hardware/status") as r:
        hw_status = json.loads(r.read().decode())
        print("Hardware Status:", hw_status)
        assert hw_status["connected"] is False, "Initial hardware should be disconnected!"
        assert hw_status["is_real_hardware"] is False, "Initial is_real_hardware should be False!"
        assert hw_status["data_source_label"] == "SIMULATION", "Data source label should be SIMULATION!"
    print("PASS: Hardware is properly reported as disconnected initially.")

    # 3. Verify Existing Test-Connect / Test-Disconnect Functionality
    print("\n[3/10] Verifying existing test-connect functionality...")
    req = urllib.request.Request(f"{BASE_URL}/api/hardware/test-connect", data=b"{}", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        res = json.loads(r.read().decode())
        assert res["status"] == "ok"
        assert res["is_test_mode"] is True
        assert res["connection_type"] == "TEST_MOCK"
    
    with urllib.request.urlopen(f"{BASE_URL}/api/hardware/status") as r:
        status_after_test = json.loads(r.read().decode())
        assert status_after_test["connected"] is True
        assert status_after_test["is_real_hardware"] is False, "Test-connect must NOT be marked as real hardware!"
        assert status_after_test["data_source_label"] == "TEST CONNECTION"
    print("PASS: Test-connect functions as software test mock without spoofing real hardware.")

    # Test disconnect
    req_disc = urllib.request.Request(f"{BASE_URL}/api/hardware/test-disconnect", data=b"{}", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req_disc) as r:
        res = json.loads(r.read().decode())
        assert res["status"] == "ok"
    print("PASS: Test-disconnect returns system to simulation baseline.")

    # 4. Ingest Normal ESP8266 Telemetry
    print("\n[4/10] Ingesting normal ESP8266 hardware telemetry...")
    normal_payload = {
        "device_id": "ESP8266-001",
        "source": "HARDWARE",
        "tilt": 0,
        "soil_moisture": 68.5,
        "servo_state": "NORMAL"
    }
    req_hw = urllib.request.Request(
        f"{BASE_URL}/api/hardware/data",
        data=json.dumps(normal_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req_hw) as r:
        res_hw = json.loads(r.read().decode())
        print("Hardware Ingest Response:", res_hw)
        assert res_hw["status"] == "success"
        assert res_hw["source"] == "HARDWARE"
        assert res_hw["device_id"] == "ESP8266-001"
        assert res_hw["tilt"] == 0
        assert res_hw["soil_moisture"] == 68.5
        assert res_hw["servo_state"] == "NORMAL"
    print("PASS: Normal ESP8266 hardware telemetry successfully ingested.")

    # 5. Verify Hardware Connected state
    print("\n[5/10] Verifying automatic hardware detection...")
    with urllib.request.urlopen(f"{BASE_URL}/api/hardware/status") as r:
        hw_status_live = json.loads(r.read().decode())
        assert hw_status_live["connected"] is True
        assert hw_status_live["is_real_hardware"] is True
        assert hw_status_live["data_source_label"] == "REAL HARDWARE"
        assert hw_status_live["device_id"] == "ESP8266-001"
    print("PASS: System automatically detects REAL HARDWARE from ESP8266 telemetry.")

    # 6. Ingest Tilt Detection & Anchoring Event
    print("\n[6/10] Ingesting tilt detection & anchoring activation event...")
    tilt_payload = {
        "device_id": "ESP8266-001",
        "source": "HARDWARE",
        "tilt": 1,
        "soil_moisture": 69.2,
        "servo_state": "ANCHORING",
        "event": "TILT_DETECTED"
    }
    req_tilt = urllib.request.Request(
        f"{BASE_URL}/api/hardware/data",
        data=json.dumps(tilt_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req_tilt) as r:
        res_tilt = json.loads(r.read().decode())
        print("Tilt Event Response:", res_tilt)
        assert res_tilt["status"] == "success"
        assert res_tilt["event"] == "TILT_DETECTED"
        assert res_tilt["servo_state"] == "ANCHORING"
    print("PASS: Tilt detection and anchoring event successfully received.")

    # 7. Verify Telemetry Architecture Endpoint
    print("\n[7/10] Verifying GET /api/telemetry returns authentic hardware data...")
    with urllib.request.urlopen(f"{BASE_URL}/api/telemetry") as r:
        telem = json.loads(r.read().decode())
        print("Unified Telemetry:", telem)
        assert telem["connected"] is True
        assert telem["is_real_hardware"] is True
        assert telem["data_source_label"] == "REAL HARDWARE"
        assert telem["device_id"] == "ESP8266-001"
        assert telem["event"] == "TILT_DETECTED"
    print("PASS: Unified telemetry endpoint delivers authentic live hardware data.")

    # 8. Verify SQLite Storage and History Integration
    print("\n[8/10] Verifying SQLite persistence and history retrieval...")
    with urllib.request.urlopen(f"{BASE_URL}/api/readings/latest?source=HARDWARE") as r:
        latest_hw = json.loads(r.read().decode())
        print("Latest Stored Hardware Reading:", latest_hw)
        assert latest_hw["source"] == "HARDWARE"
        assert latest_hw["device_id"] == "ESP8266-001"
        assert latest_hw["event"] == "TILT_DETECTED"
        assert latest_hw["anchor_status"] == "ANCHORING"

    with urllib.request.urlopen(f"{BASE_URL}/api/readings?limit=10&source=HARDWARE") as r:
        hw_readings = json.loads(r.read().decode())
        assert len(hw_readings) >= 2, "Should have at least 2 hardware readings"
        print(f"PASS: Stored {len(hw_readings)} hardware records retrieved from database.")

    # 9. Verify Input Validation (Handling Malformed / Invalid Data)
    print("\n[9/10] Verifying backend validation on invalid hardware payloads...")
    # Missing soil moisture
    bad_req1 = urllib.request.Request(
        f"{BASE_URL}/api/hardware/data",
        data=b'{"device_id":"ESP8266-001","tilt":0}',
        headers={"Content-Type": "application/json"}
    )
    try:
        urllib.request.urlopen(bad_req1)
        assert False, "Should have failed on missing soil_moisture!"
    except urllib.error.HTTPError as e:
        assert e.code == 422
        print("PASS: Correctly rejected missing soil_moisture with HTTP 422.")

    # Out of range soil moisture (> 100%)
    bad_req2 = urllib.request.Request(
        f"{BASE_URL}/api/hardware/data",
        data=b'{"device_id":"ESP8266-001","tilt":0,"soil_moisture":250}',
        headers={"Content-Type": "application/json"}
    )
    try:
        urllib.request.urlopen(bad_req2)
        assert False, "Should have failed on out-of-range soil_moisture!"
    except urllib.error.HTTPError as e:
        assert e.code == 422
        print("PASS: Correctly rejected out-of-range soil moisture with HTTP 422.")

    # 10. Verify Frontend Files & Static Serving
    print("\n[10/10] Verifying static frontend routes and auth...")
    with urllib.request.urlopen(f"{BASE_URL}/login.html") as r:
        assert r.status == 200
        html = r.read().decode("utf-8")
        assert "SMART MANGROVE" in html
        assert "loginForm" in html
    with urllib.request.urlopen(f"{BASE_URL}/index.html") as r:
        assert r.status == 200
        html = r.read().decode("utf-8")
        assert "view-dashboard" in html
        assert "view-simulator" in html
    with urllib.request.urlopen(f"{BASE_URL}/api/environmental-data") as r:
        assert r.status == 200
    print("PASS: Login page, dashboard layout, and environmental data are 100% intact.")

    print("\n=================================================================")
    print(" ALL 10 VERIFICATION CHECKS COMPLETED WITH 100% SUCCESS!")
    print("=================================================================")

finally:
    proc.terminate()
    proc.wait()
