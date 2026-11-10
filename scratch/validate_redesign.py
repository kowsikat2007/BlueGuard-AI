import re, json, urllib.request

print("=== 1. VERIFYING LOGIN.HTML ===")
with open("frontend/login.html", "r", encoding="utf-8") as f:
    login_html = f.read()

assert "Demo Credentials" not in login_html, "Demo Credentials still in login.html!"
assert "Blue Guard" in login_html, "Credentials logic missing!"
assert "BG6511" in login_html, "Password logic missing!"
assert "SMART MANGROVE" in login_html, "Brand missing!"
assert "Intelligent Blue Carbon" in login_html, "Subtitle missing!"
print("PASS: login.html credentials, branding, and clean UI verified.")

print("=== 2. VERIFYING INDEX.HTML ===")
with open("frontend/index.html", "r", encoding="utf-8") as f:
    index_html = f.read()

assert 'id="appSidebar"' in index_html, "Sidebar missing!"
assert 'id="navToggleBtn"' in index_html, "Toggle button missing!"
assert 'data-view="view-dashboard"' in index_html, "Dashboard nav missing!"
assert 'data-view="view-history"' in index_html, "History nav missing!"
assert 'data-view="view-monitoring"' in index_html, "Monitoring nav missing!"
assert 'data-view="view-environmental"' in index_html, "Environmental nav missing!"
assert 'data-view="view-sensors"' in index_html, "Sensors nav missing!"
assert 'data-view="view-blue-carbon"' in index_html, "Blue Carbon nav missing!"
assert 'data-view="view-anchoring"' in index_html, "Anchoring nav missing!"
assert 'data-view="view-simulator"' in index_html, "Simulator nav missing!"
assert 'data-view="view-alerts"' in index_html, "Alerts nav missing!"
assert 'data-view="view-reports"' in index_html, "Reports nav missing!"

views = [
    "view-dashboard",
    "view-history",
    "view-monitoring",
    "view-environmental",
    "view-sensors",
    "view-blue-carbon",
    "view-anchoring",
    "view-simulator",
    "view-alerts",
    "view-reports",
]
for v in views:
    assert f'id="{v}"' in index_html, f"View {v} missing!"

assert 'class="app-view active"' in index_html, "Default active view missing!"
assert "Backend Online" not in index_html, "Backend Online text found in index.html!"
assert "Backend Offline" not in index_html, "Backend Offline text found in index.html!"
assert "Phase" not in index_html, "Phase label found in index.html!"
print("PASS: index.html 10 independent views, left sidebar, zero phase labels verified.")

print("=== 3. VERIFYING SCRIPT.JS ===")
with open("frontend/script.js", "r", encoding="utf-8") as f:
    script_js = f.read()

assert "function switchView(" in script_js, "switchView missing!"
sim_panel_code = script_js.split("function initSimulatorPanel()")[1].split("function ")[0]
assert "startSimulation();" not in sim_panel_code, "Simulator should not auto-start!"
assert "Backend Online" not in script_js, "Backend Online string in script.js!"
assert "Backend Offline" not in script_js, "Backend Offline string in script.js!"
print("PASS: script.js view switching, simulator stopped state, clean text verified.")

print("=== 4. VERIFYING FASTAPI BACKEND ===")
with urllib.request.urlopen("http://127.0.0.1:8000/status") as r:
    assert r.status == 200, "Status failed!"
with urllib.request.urlopen("http://127.0.0.1:8000/api/readings?limit=5") as r:
    readings = json.loads(r.read())
    assert len(readings) > 0, "No readings in database!"
with urllib.request.urlopen("http://127.0.0.1:8000/api/telemetry") as r:
    telemetry = json.loads(r.read())
    assert telemetry["connected"] == False, "Should be disconnected!"
    assert telemetry["source"] == "NONE", "Source should be NONE when disconnected!"
    assert "tilt_angle" not in telemetry, "Fake tilt angle in disconnected telemetry!"
print("PASS: FastAPI backend healthy, SQLite database verified, telemetry clean.")

print("=== ALL 4 VALIDATION SUITES PASSED PERFECTLY ===")
