import urllib.request, json

BASE_URL = "http://127.0.0.1:8001"

print("==================================================")
print("VERIFYING UNIFIED FASTAPI + FRONTEND CONFIGURATION")
print(f"TARGET: {BASE_URL}")
print("==================================================")

# 1. Test Swagger docs
with urllib.request.urlopen(f"{BASE_URL}/docs") as r:
    assert r.status == 200, f"/docs failed with status {r.status}"
    print("[PASS] 1. Swagger UI (/docs) is ONLINE (status 200)")

# 2. Test status endpoint
with urllib.request.urlopen(f"{BASE_URL}/status") as r:
    assert r.status == 200, f"/status failed with status {r.status}"
    data = json.loads(r.read())
    assert data.get("status") == "online", f"Unexpected status: {data}"
    print("[PASS] 2. Backend Health (/status) is ONLINE:", data)

# 3. Test root endpoint with HTML Accept header (Browser access)
req_html = urllib.request.Request(f"{BASE_URL}/", headers={"Accept": "text/html,application/xhtml+xml"})
with urllib.request.urlopen(req_html) as r:
    assert r.status == 200, f"Root HTML request failed with status {r.status}"
    content = r.read().decode("utf-8", errors="ignore")
    assert "SMART MANGROVE" in content, "Branding missing in root HTML"
    assert "loginForm" in content, "Login form missing in root HTML"
    print("[PASS] 3. Browser Root (GET /) correctly serves login.html (status 200)")

# 4. Test root endpoint with JSON Accept header (API client access)
req_json = urllib.request.Request(f"{BASE_URL}/", headers={"Accept": "application/json"})
with urllib.request.urlopen(req_json) as r:
    assert r.status == 200, f"Root JSON request failed with status {r.status}"
    data = json.loads(r.read())
    assert data.get("status") == "connected", f"Unexpected API root response: {data}"
    print("[PASS] 4. API Client Root (GET / with JSON) preserves original response:", data)

# 5. Test direct /login.html
with urllib.request.urlopen(f"{BASE_URL}/login.html") as r:
    assert r.status == 200, f"/login.html failed with status {r.status}"
    print("[PASS] 5. Entry file /login.html is served (status 200)")

# 6. Test direct /index.html
with urllib.request.urlopen(f"{BASE_URL}/index.html") as r:
    assert r.status == 200, f"/index.html failed with status {r.status}"
    content = r.read().decode("utf-8", errors="ignore")
    assert "appSidebar" in content, "Sidebar missing in index.html"
    assert "view-dashboard" in content, "Dashboard view missing in index.html"
    print("[PASS] 6. Dashboard /index.html is served (status 200)")

# 7. Test /style.css
with urllib.request.urlopen(f"{BASE_URL}/style.css") as r:
    assert r.status == 200, f"/style.css failed with status {r.status}"
    css = r.read().decode("utf-8", errors="ignore")
    assert len(css) > 1000, "style.css appears empty"
    print(f"[PASS] 7. Static Stylesheet (/style.css) is served (status 200, {len(css)} bytes)")

# 8. Test /script.js
with urllib.request.urlopen(f"{BASE_URL}/script.js") as r:
    assert r.status == 200, f"/script.js failed with status {r.status}"
    js = r.read().decode("utf-8", errors="ignore")
    assert "BACKEND_URL" in js, "BACKEND_URL missing in script.js"
    assert "http://127.0.0.1:8000" not in js, "Old port 8000 still hardcoded in script.js!"
    assert "window.location.origin" in js, "Dynamic origin missing in script.js"
    print("[PASS] 8. Client Script (/script.js) is served with dynamic origin support (status 200)")

# 9. Test /api/readings
with urllib.request.urlopen(f"{BASE_URL}/api/readings?limit=5") as r:
    assert r.status == 200, f"/api/readings failed with status {r.status}"
    readings = json.loads(r.read())
    assert len(readings) > 0, "No readings returned from database"
    print(f"[PASS] 9. Telemetry API (/api/readings) returned {len(readings)} records from SQLite")

# 10. Test /api/environmental-data
with urllib.request.urlopen(f"{BASE_URL}/api/environmental-data") as r:
    assert r.status == 200, f"/api/environmental-data failed with status {r.status}"
    env = json.loads(r.read())
    assert "location" in env, "Missing location in environmental data"
    print(f"[PASS] 10. Environmental Data API (/api/environmental-data): {env.get('location')}")

# 11. Test /api/telemetry
with urllib.request.urlopen(f"{BASE_URL}/api/telemetry") as r:
    assert r.status == 200, f"/api/telemetry failed with status {r.status}"
    telem = json.loads(r.read())
    print("[PASS] 11. Telemetry Architecture API (/api/telemetry):", telem)

print("==================================================")
print("ALL 11 VERIFICATION CHECKS PASSED WITH 100% SUCCESS")
print("==================================================")
