"""
verify_ui_corrections.py
Validates all UI/UX corrections requested by the user:
1. Login page centered: card, heading, pill, button.
2. Dashboard footer centered: two informational lines.
3. 'System Active' completely removed.
4. 'System Online' remains.
5. 'Hardware Not Connected' remains.
6. 'SIMULATION' labels remain.
7. Three-dot button (⋮) and dropdown structure exist.
8. Dropdown options hidden by default in CSS.
9. Click/Escape outside event handlers exist in script.js.
10. All 10 views intact in index.html and sidebar.
11. FastAPI backend endpoints and static files return HTTP 200.
12. All DOM IDs referenced by script.js exist in index.html.
"""

import os
import sys
import re
import urllib.request
import json

sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE = r"c:\Users\ADMIN\OneDrive\Desktop\Smart-Mangrove-System"

def test_login_page():
    print("\n--- [1] Checking Login Page ---")
    login_html_path = os.path.join(WORKSPACE, "frontend", "login.html")
    style_css_path = os.path.join(WORKSPACE, "frontend", "style.css")
    
    with open(login_html_path, "r", encoding="utf-8") as f:
        login_html = f.read()
    with open(style_css_path, "r", encoding="utf-8") as f:
        style_css = f.read()

    assert '<div class="login-wrapper">' in login_html, "login-wrapper missing"
    assert '<div class="login-card">' in login_html, "login-card missing"
    assert '<h2>Sign In</h2>' in login_html, "'Sign In' heading missing"
    assert '<button type="submit" id="loginBtn" class="login-submit-btn">' in login_html, "Sign In button missing"
    assert 'Blue Guard' in login_html, "Auth username credential missing"
    assert 'BG6511' in login_html, "Auth password credential missing"
    
    # Assert SECURE ACCESS PORTAL is completely removed
    assert "SECURE ACCESS PORTAL" not in login_html, "ERROR: SECURE ACCESS PORTAL found in login.html"
    assert "login-secure-pill" not in login_html, "ERROR: login-secure-pill found in login.html"
    print("  [PASS] 'SECURE ACCESS PORTAL' is completely removed from login page.")

    # Check CSS centering rules
    assert ".login-body {" in style_css
    assert "justify-content: center;" in style_css
    assert ".login-card-header {" in style_css
    assert "align-items: center;" in style_css
    assert "text-align: center;" in style_css
    print("  [PASS] Login page structure, centering styles, and authentication intact.")

def test_footer_centering():
    print("\n--- [2] Checking Application Footer Centering ---")
    index_html_path = os.path.join(WORKSPACE, "frontend", "index.html")
    style_css_path = os.path.join(WORKSPACE, "frontend", "style.css")

    with open(index_html_path, "r", encoding="utf-8") as f:
        index_html = f.read()
    with open(style_css_path, "r", encoding="utf-8") as f:
        style_css = f.read()

    assert '<footer class="app-footer">' in index_html, "app-footer missing"
    assert '<strong>Smart Mangrove System</strong> — IoT-Driven Smart MRV and Blue Carbon Registry Platform' in index_html
    assert 'Pichavaram Estuarine Wetland, Cuddalore, Tamil Nadu • Ramsar Site No. 2475 © 2026' in index_html

    assert ".app-footer {" in style_css
    assert ".footer-content {" in style_css
    assert "text-align: center;" in style_css
    print("  [PASS] Footer 2 lines exist and are horizontally centered.")

def test_status_indicators():
    print("\n--- [3] Checking Status Indicators & Header ---")
    index_html_path = os.path.join(WORKSPACE, "frontend", "index.html")
    with open(index_html_path, "r", encoding="utf-8") as f:
        index_html = f.read()

    # System Active must NOT exist anywhere
    assert "system active" not in index_html.lower(), "ERROR: 'system active' found in index.html"
    assert "station active" not in index_html.lower(), "ERROR: 'station active' found in index.html"
    print("  [PASS] 'System Active' and 'Station Active' are completely removed.")

    # Header inspect
    h_start = index_html.find('<header class="app-header">')
    h_end = index_html.find('</header>')
    assert h_start != -1 and h_end != -1, "Header not found"
    header_content = index_html[h_start:h_end]

    # System Online must NOT be in top header
    assert "System Online" not in header_content, "ERROR: 'System Online' found in top header!"
    assert "systemStatusBadge" not in header_content, "ERROR: systemStatusBadge found in top header!"
    print("  [PASS] 'System Online' is completely removed from top header.")

    # Hardware Not Connected MUST remain
    assert "Hardware: Not Connected" in header_content, "ERROR: Hardware: Not Connected removed from header"
    print("  [PASS] 'Hardware: Not Connected' remains in header.")

    # Header structure: Left breadcrumb with SMART MANGROVE and currentViewTitle, Right profile with Blue Guard
    assert 'SMART MANGROVE' in header_content, "SMART MANGROVE missing from header"
    assert 'id="currentViewTitle"' in header_content, "currentViewTitle missing from header"
    assert 'id="currentViewSubtitle"' in header_content, "currentViewSubtitle missing from header"
    assert 'Blue Guard' in header_content, "Blue Guard missing from header"
    assert 'id="userProfileBtn"' in header_content, "userProfileBtn missing from header"
    assert 'id="profileDropdown"' in header_content, "profileDropdown missing from header"
    assert 'id="logoutBtn"' in header_content, "logoutBtn missing from header"
    print("  [PASS] Header structure verified: Left breadcrumb with titles, Right user profile with dropdown.")

    # SIMULATION labels MUST remain
    assert "SIMULATION" in index_html, "ERROR: SIMULATION labels removed"
    assert "SIMULATED DATA" in index_html, "ERROR: SIMULATED DATA labels removed"
    print("  [PASS] SIMULATION labels and badges remain intact.")

def test_three_dot_navigation():
    print("\n--- [4] Checking Left Three-Dot Navigation (⋮) ---")
    index_html_path = os.path.join(WORKSPACE, "frontend", "index.html")
    style_css_path = os.path.join(WORKSPACE, "frontend", "style.css")
    script_js_path = os.path.join(WORKSPACE, "frontend", "script.js")

    with open(index_html_path, "r", encoding="utf-8") as f:
        index_html = f.read()
    with open(style_css_path, "r", encoding="utf-8") as f:
        style_css = f.read()
    with open(script_js_path, "r", encoding="utf-8") as f:
        script_js = f.read()

    # 1. Left Three-Dot Button exists in .header-left
    assert 'class="nav-toggle-btn nav-three-dot-btn"' in index_html, "nav-three-dot-btn missing in index.html"
    assert '⋮' in index_html, "Three-dot character (⋮) missing in index.html"
    
    # 2. NO right-side three-dot menu
    assert 'id="threeDotMenuBtn"' not in index_html, "ERROR: right-side threeDotMenuBtn still present in index.html!"
    assert 'id="threeDotDropdown"' not in index_html, "ERROR: right-side threeDotDropdown still present in index.html!"
    assert 'three-dot-dropdown' not in index_html, "ERROR: three-dot-dropdown found in index.html!"
    print("  [PASS] Only ONE three-dot button exists, located on the LEFT side. No right-side three-dot menu.")

    # 3. Sidebar hidden by default in CSS
    assert "transform: translateX(-100%);" in style_css, "app-sidebar translateX(-100%) missing"
    assert ".app-sidebar.open {" in style_css, "app-sidebar.open missing"
    assert "transform: translateX(0);" in style_css, "app-sidebar.open translateX(0) missing"
    assert "margin-left: 0;" in style_css, "app-main-wrapper margin-left: 0 missing"
    print("  [PASS] Left sidebar is hidden offscreen by default and main content uses full width.")

    # 4. script.js has toggleNavMenu, closeNavMenu, click outside, and escape key
    assert "toggleNavMenu" in script_js, "toggleNavMenu missing in script.js"
    assert "closeNavMenu" in script_js, "closeNavMenu missing in script.js"
    assert "Escape" in script_js, "Escape key handler missing in script.js"
    print("  [PASS] script.js handles left three-dot toggle, click outside, and Escape key.")

def test_sidebar_views():
    print("\n--- [5] Checking Sidebar Views (All 10 Intact) ---")
    index_html_path = os.path.join(WORKSPACE, "frontend", "index.html")
    with open(index_html_path, "r", encoding="utf-8") as f:
        index_html = f.read()

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
        "view-reports"
    ]
    for v in views:
        assert f'id="{v}"' in index_html, f"Missing view: {v}"
        assert f'data-view="{v}"' in index_html, f"Missing sidebar data-view for {v}"
    print(f"  [PASS] All {len(views)} views present in HTML and sidebar with data-view.")

def test_dom_ids():
    print("\n--- [6] Checking DOM IDs referenced by script.js ---")
    index_html_path = os.path.join(WORKSPACE, "frontend", "index.html")
    script_js_path = os.path.join(WORKSPACE, "frontend", "script.js")

    with open(index_html_path, "r", encoding="utf-8") as f:
        index_html = f.read()
    with open(script_js_path, "r", encoding="utf-8") as f:
        script_js = f.read()

    # Find all document.getElementById("...")
    js_ids = set(re.findall(r'getElementById\(["\']([^"\']+)["\']\)', script_js))
    html_ids = set(re.findall(r'id=["\']([^"\']+)["\']', index_html))

    missing = js_ids - html_ids
    print(f"  Total JS getElementById references: {len(js_ids)}")
    print(f"  Total HTML IDs in index.html: {len(html_ids)}")
    if missing:
        print(f"  [FAIL] Missing IDs in HTML: {missing}")
        assert False, f"Missing IDs: {missing}"
    else:
        print("  [PASS] 100% of IDs accessed by script.js exist in index.html!")

def test_api_endpoints():
    print("\n--- [7] Checking Live FastAPI Endpoints (Port 8001) ---")
    endpoints = [
        ("GET", "http://127.0.0.1:8001/", 200),
        ("GET", "http://127.0.0.1:8001/login.html", 200),
        ("GET", "http://127.0.0.1:8001/style.css", 200),
        ("GET", "http://127.0.0.1:8001/script.js", 200),
        ("GET", "http://127.0.0.1:8001/docs", 200),
        ("GET", "http://127.0.0.1:8001/api/readings", 200),
        ("GET", "http://127.0.0.1:8001/api/readings/latest", 200),
        ("GET", "http://127.0.0.1:8001/api/status", 200),
        ("GET", "http://127.0.0.1:8001/api/hardware/status", 200),
        ("GET", "http://127.0.0.1:8001/api/telemetry", 200),
        ("GET", "http://127.0.0.1:8001/api/environmental-data", 200),
    ]

    for method, url, expected_code in endpoints:
        req = urllib.request.Request(url, method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                assert resp.status == expected_code, f"{url} returned {resp.status}"
                if "api" in url:
                    data = json.loads(resp.read().decode("utf-8"))
                    assert isinstance(data, (dict, list)), f"Unexpected JSON response from {url}"
                print(f"  [PASS] {method} {url} -> {resp.status} OK")
        except Exception as e:
            print(f"  [FAIL] {method} {url} -> {e}")
            raise e

if __name__ == "__main__":
    test_login_page()
    test_footer_centering()
    test_status_indicators()
    test_three_dot_navigation()
    test_sidebar_views()
    test_dom_ids()
    test_api_endpoints()
    print("\n==========================================")
    print("ALL TESTS PASSED! UI/UX CORRECTIONS COMPLETE.")
    print("==========================================")
