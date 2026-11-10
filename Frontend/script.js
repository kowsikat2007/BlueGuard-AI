// ====================================================
// SMART MANGROVE SYSTEM — ENTERPRISE CLIENT SCRIPT
// IoT-Driven Smart MRV and Blue Carbon Registry Platform
// ====================================================

// Dynamic backend URL: connects to current host/port (e.g. http://127.0.0.1:8001) or defaults to port 8001 if opened via file://
const BACKEND_URL = (window.location.origin && window.location.origin.startsWith("http"))
  ? window.location.origin
  : "http://127.0.0.1:8001";

// Chart instances
let tiltChart = null;
let soilChart = null;
let tempChart = null;
let envSeasonalChartInstance = null;

// Polling and simulation timers
let sensorPollingInterval = null;
let simulationInterval = null;
let isSimulatorRunning = false;
let simulationStepCounter = 0;

// In-memory simulation values
let simState = {
  tilt_angle: 4.2,
  soil_moisture: 67.0,
  temperature: 29.5,
  humidity: 78.0,
  servo_position: 0,
  anchor_status: "Normal"
};

// History state
let storedHistoryReadings = [];


// ====================================================
// AUTHENTICATION & SESSION MANAGEMENT
// ====================================================

function checkAuth() {
  const session = localStorage.getItem("mangrove_session");
  if (session !== "true") {
    window.location.replace("login.html");
    return false;
  }
  return true;
}

function logout() {
  localStorage.removeItem("mangrove_session");
  localStorage.removeItem("mangrove_user");
  sessionStorage.removeItem("active_view");
  window.location.replace("login.html");
}


// ====================================================
// NAVIGATION & VIEW SWITCHING (INDEPENDENT PAGES)
// ====================================================

/**
 * Switches the active view so that ONLY the selected section is displayed.
 * No vertical stacking of sections.
 */
function switchView(viewId) {
  if (!viewId) return;

  const targetView = document.getElementById(viewId);
  if (!targetView) return;

  const allViews = document.querySelectorAll(".app-view");
  const allNavBtns = document.querySelectorAll(".sidebar-nav-list .nav-btn");

  // Deactivate all views and activate target
  allViews.forEach(v => v.classList.remove("active"));
  targetView.classList.add("active");

  // Highlight active nav item
  allNavBtns.forEach(btn => {
    if (btn.getAttribute("data-view") === viewId) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });

  // Update top breadcrumb and descriptive subtitle
  const currentTitle = document.getElementById("currentViewTitle");
  const currentSubtitle = document.getElementById("currentViewSubtitle");
  const activeBtn = document.querySelector(`.sidebar-nav-list .nav-btn[data-view="${viewId}"] .nav-text`);
  if (currentTitle && activeBtn) {
    currentTitle.innerText = activeBtn.innerText;
  }

  const viewSubtitles = {
    "view-dashboard": "Real-time coastal wetland MRV & automated root stabilization",
    "view-history": "Complete auditable historical telemetry log with multi-parameter filtering",
    "view-monitoring": "Rhizophora & Avicennia physiological indicators and estuarine health",
    "view-environmental": "Seasonal rainfall, salinity, tidal cycles & verified meteorological baselines",
    "view-sensors": "Active hardware sensor registry, operational telemetry & bus status",
    "view-blue-carbon": "Wetland carbon sequestration registry, biomass MRV & carbon crediting",
    "view-anchoring": "Dual-axis root stabilization mechanism with automated tilt intervention",
    "view-simulator": "Calibrated environmental sensor simulation console for validation & demo",
    "view-alerts": "Incident response log, safety envelope threshold rules & automated notifications",
    "view-reports": "Executive environmental compliance reports & automated audit exports"
  };

  if (currentSubtitle && viewSubtitles[viewId]) {
    currentSubtitle.innerText = viewSubtitles[viewId];
  }

  // Save selection
  sessionStorage.setItem("active_view", viewId);

  // Close mobile drawer if open
  closeMobileSidebar();

  // Scroll to top of content area smoothly
  window.scrollTo({ top: 0, behavior: "smooth" });

  // View-specific trigger
  if (viewId === "view-history") {
    fetchHistoryReadings();
  } else if (viewId === "view-environmental") {
    fetchEnvironmentalData();
  } else if (viewId === "view-simulator") {
    fetchTelemetryData();
  }
}

// ====================================================
// LEFT THREE-DOT NAVIGATION DRAWER CONTROLLER
// ====================================================

function toggleNavMenu(e) {
  if (e) {
    e.stopPropagation();
    e.preventDefault();
  }
  const sidebar = document.getElementById("appSidebar");
  if (!sidebar) return;

  const isOpen = sidebar.classList.contains("open");
  if (isOpen) {
    closeNavMenu();
  } else {
    openNavMenu();
  }
}

function openNavMenu() {
  const sidebar = document.getElementById("appSidebar");
  const backdrop = document.getElementById("sidebarBackdrop");
  const toggleBtn = document.getElementById("navToggleBtn");
  if (sidebar) sidebar.classList.add("open");
  if (backdrop) backdrop.classList.add("open");
  if (toggleBtn) {
    toggleBtn.classList.add("active");
    toggleBtn.setAttribute("aria-expanded", "true");
  }
}

function closeNavMenu() {
  const sidebar = document.getElementById("appSidebar");
  const backdrop = document.getElementById("sidebarBackdrop");
  const toggleBtn = document.getElementById("navToggleBtn");
  if (sidebar) sidebar.classList.remove("open");
  if (backdrop) backdrop.classList.remove("open");
  if (toggleBtn) {
    toggleBtn.classList.remove("active");
    toggleBtn.setAttribute("aria-expanded", "false");
  }
}

const toggleMobileSidebar = toggleNavMenu;
const closeMobileSidebar = closeNavMenu;

function initNavigation() {
  const navBtns = document.querySelectorAll(".sidebar-nav-list .nav-btn");
  navBtns.forEach(btn => {
    if (btn.id === "sideMenuLogoutBtn") return;
    btn.addEventListener("click", () => {
      const viewId = btn.getAttribute("data-view");
      if (viewId) switchView(viewId);
    });
  });

  // Sidebar navigation controls
  const toggleBtn = document.getElementById("navToggleBtn");
  const closeBtn = document.getElementById("sidebarCloseBtn");
  const backdrop = document.getElementById("sidebarBackdrop");
  const sideLogout = document.getElementById("sideMenuLogoutBtn");
  const headerLogout = document.getElementById("logoutBtn");

  if (toggleBtn) toggleBtn.addEventListener("click", toggleNavMenu);
  if (closeBtn) closeBtn.addEventListener("click", closeNavMenu);
  if (backdrop) backdrop.addEventListener("click", closeNavMenu);
  if (sideLogout) sideLogout.addEventListener("click", logout);
  if (headerLogout) headerLogout.addEventListener("click", logout);

  // Close navigation menu when clicking anywhere outside
  document.addEventListener("click", (e) => {
    const sidebar = document.getElementById("appSidebar");
    const toggleBtn = document.getElementById("navToggleBtn");
    if (sidebar && sidebar.classList.contains("open")) {
      if (!sidebar.contains(e.target) && (!toggleBtn || !toggleBtn.contains(e.target))) {
        closeNavMenu();
      }
    }
  });

  // Close navigation menu on Escape key
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closeNavMenu();
    }
  });

  // Initialize Right-Side User Profile Dropdown
  initUserProfileMenu();

  // Default to Dashboard or last active view
  const savedView = sessionStorage.getItem("active_view") || "view-dashboard";
  switchView(savedView);
}

// ====================================================
// RIGHT-SIDE USER PROFILE DROPDOWN MENU
// ====================================================

function initUserProfileMenu() {
  const profileWrapper = document.getElementById("profileMenuWrapper");
  const profileBtn = document.getElementById("userProfileBtn");
  const profileDropdown = document.getElementById("profileDropdown");

  if (!profileBtn || !profileDropdown) return;

  function toggleProfileMenu(e) {
    if (e) e.stopPropagation();
    const isOpen = profileDropdown.classList.contains("open");
    if (isOpen) {
      closeProfileMenu();
    } else {
      openProfileMenu();
    }
  }

  function openProfileMenu() {
    profileDropdown.classList.add("open");
    profileBtn.classList.add("active");
    profileBtn.setAttribute("aria-expanded", "true");
    profileDropdown.setAttribute("aria-hidden", "false");
  }

  function closeProfileMenu() {
    profileDropdown.classList.remove("open");
    profileBtn.classList.remove("active");
    profileBtn.setAttribute("aria-expanded", "false");
    profileDropdown.setAttribute("aria-hidden", "true");
  }

  profileBtn.addEventListener("click", toggleProfileMenu);

  // Close profile dropdown when clicking anywhere outside
  document.addEventListener("click", (e) => {
    if (profileWrapper && !profileWrapper.contains(e.target)) {
      closeProfileMenu();
    }
  });

  // Close profile dropdown on Escape key
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closeProfileMenu();
    }
  });
}


// ====================================================
// BACKEND STATUS & HARDWARE TELEMETRY PIPELINE
// ====================================================

/**
 * Checks backend health internally without exposing technical developer strings.
 */
async function checkBackendStatus() {
  try {
    const res = await fetch(BACKEND_URL + "/status");
    if (!res.ok) return false;
    const data = await res.json();
    return Boolean(data && data.status === "online");
  } catch (err) {
    return false;
  }
}

/**
 * Checks if physical hardware is actively connected.
 */
async function checkHardwareStatus() {
  try {
    const res = await fetch(BACKEND_URL + "/api/hardware/status");
    if (!res.ok) return { connected: false, source: "NONE" };
    return await res.json();
  } catch (err) {
    return { connected: false, source: "NONE" };
  }
}

/**
 * Main dashboard data refresh cycle (runs every 5 seconds).
 * - Never generates fake random values.
 * - If hardware is connected: displays actual hardware values.
 * - If hardware is disconnected: displays "Hardware Not Connected" and waits.
 * - Updates analytical trend charts and recent feed from stored database records.
 */
async function updateDashboardCycle() {
  const isOnline = await checkBackendStatus();
  if (!isOnline) {
    handleBackendUnavailableState();
    return;
  }

  // Check physical hardware connectivity
  const hwInfo = await checkHardwareStatus();
  const isHwConnected = Boolean(hwInfo && hwInfo.connected);
  const isRealHw = Boolean(hwInfo && hwInfo.is_real_hardware);
  const isTestMode = Boolean(hwInfo && hwInfo.is_test_mode);

  updateHardwareBadgeUI(isHwConnected, isRealHw, isTestMode);

  if (isHwConnected) {
    await updateDashboardWithHardwareData(hwInfo);
  } else {
    updateDashboardWithDisconnectedHardwareUI();
  }

  // Update historical trend charts and recent feed from SQLite
  await updateDashboardAnalyticsAndFeed();
}

/**
 * Updates top header hardware connection status badge.
 * Distinguishes REAL HARDWARE from TEST CONNECTION and DISCONNECTED.
 */
function updateHardwareBadgeUI(isConnected, isRealHw, isTestMode) {
  const hwBadge = document.getElementById("hwHeaderBadge");
  const hwDot = document.getElementById("hwHeaderDot");
  const hwText = document.getElementById("hwHeaderText");
  const sensorChip = document.getElementById("sensorHardwareStatusChip");

  if (hwBadge && hwDot && hwText) {
    if (isRealHw) {
      hwBadge.className = "hw-header-badge connected";
      hwDot.innerText = "🟢";
      hwText.innerText = "Hardware: Connected";
    } else if (isTestMode) {
      hwBadge.className = "hw-header-badge connected";
      hwDot.innerText = "🧪";
      hwText.innerText = "TEST CONNECTION";
    } else {
      hwBadge.className = "hw-header-badge disconnected";
      hwDot.innerText = "⚪";
      hwText.innerText = "Hardware: Not Connected";
    }
  }

  if (sensorChip) {
    if (isRealHw) {
      sensorChip.className = "status-chip success";
      sensorChip.innerText = "Hardware: Connected (ESP8266)";
    } else if (isTestMode) {
      sensorChip.className = "status-chip warning";
      sensorChip.innerText = "Hardware: Test Mode (Simulated)";
    } else {
      sensorChip.className = "status-chip neutral";
      sensorChip.innerText = "Hardware: Not Connected";
    }
  }
}

/**
 * When hardware is disconnected:
 * Never show random values or pretend simulation values are hardware data.
 */
function updateDashboardWithDisconnectedHardwareUI() {
  const banner = document.getElementById("dashSourceBanner");
  const dot = document.getElementById("dashSourceDot");
  const title = document.getElementById("dashSourceTitle");
  const subtitle = document.getElementById("dashSourceSubtitle");
  const lastUpdate = document.getElementById("dashLastUpdateTime");

  if (banner) banner.className = "dash-source-banner mode-simulation";
  if (dot) dot.innerText = "⚪";
  if (title) title.innerText = "Hardware: Not Connected";
  if (subtitle) {
    subtitle.innerText = "Data Source: SIMULATION — Waiting for real ESP8266 telemetry.";
  }
  if (lastUpdate) {
    lastUpdate.innerText = "Hardware Status: Waiting for ESP8266";
  }

  // Tags
  const tags = ["tagTilt", "tagSoil", "tagTemp", "tagHum", "tagServo", "tagAnchor"];
  tags.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.innerText = "NOT CONNECTED";
      el.className = "card-source-tag not-connected";
    }
  });

  // Telemetry cards display clean empty state
  const elTilt = document.getElementById("dashTiltAngle");
  const elSoil = document.getElementById("dashSoilMoisture");
  const elTemp = document.getElementById("dashTemperature");
  const elHum = document.getElementById("dashHumidity");
  const elServo = document.getElementById("dashServoPosition");
  const elAnchor = document.getElementById("dashAnchorStatus");

  if (elTilt) elTilt.innerText = "-- °";
  if (elSoil) elSoil.innerText = "-- %";
  if (elTemp) elTemp.innerText = "-- °C";
  if (elHum) elHum.innerText = "-- %";
  if (elServo) elServo.innerText = "-- °";
  if (elAnchor) {
    elAnchor.innerText = "--";
    elAnchor.className = "";
  }

  const alertMsg = document.getElementById("alertMessage");
  if (alertMsg) {
    alertMsg.innerText = "Monitoring system ready. Waiting for hardware telemetry stream.";
  }
}

/**
 * When hardware is connected:
 * Render authentic hardware readings from SQLite / telemetry.
 */
async function updateDashboardWithHardwareData(hwInfo) {
  try {
    const res = await fetch(BACKEND_URL + "/api/readings/latest?source=HARDWARE");
    if (!res.ok) {
      updateDashboardWithDisconnectedHardwareUI();
      return;
    }
    const latest = await res.json();
    renderDashboardLiveHardwareCards(latest, hwInfo);
  } catch (err) {
    console.warn("Failed to fetch latest hardware telemetry:", err);
  }
}

function renderDashboardLiveHardwareCards(reading, hwInfo) {
  if (!reading) return;

  const isReal = Boolean(hwInfo && hwInfo.is_real_hardware);
  const isTest = Boolean(hwInfo && hwInfo.is_test_mode);

  const banner = document.getElementById("dashSourceBanner");
  const dot = document.getElementById("dashSourceDot");
  const title = document.getElementById("dashSourceTitle");
  const subtitle = document.getElementById("dashSourceSubtitle");
  const lastUpdate = document.getElementById("dashLastUpdateTime");

  if (isReal) {
    if (banner) banner.className = "dash-source-banner mode-hardware";
    if (dot) dot.innerText = "🟢";
    if (title) title.innerText = "Hardware: Connected";
    const devId = reading.device_id || "ESP8266-001";
    if (subtitle) subtitle.innerText = `Data Source: REAL HARDWARE (${devId}) — Live Telemetry`;
  } else if (isTest) {
    if (banner) banner.className = "dash-source-banner mode-simulation";
    if (dot) dot.innerText = "🧪";
    if (title) title.innerText = "TEST CONNECTION (SOFTWARE ONLY)";
    if (subtitle) subtitle.innerText = "Data Source: TEST MOCK — For developer testing only, no real ESP8266 connected.";
  }

  if (lastUpdate && reading.timestamp) {
    lastUpdate.innerText = "Last reading: " + reading.timestamp;
  }

  // Tags
  const tagLabel = isReal ? "REAL HARDWARE" : "TEST MOCK";
  const tagClass = isReal ? "card-source-tag hardware" : "card-source-tag simulated";
  const tags = ["tagTilt", "tagSoil", "tagTemp", "tagHum", "tagServo", "tagAnchor"];
  tags.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.innerText = tagLabel;
      el.className = tagClass;
    }
  });

  const elTilt = document.getElementById("dashTiltAngle");
  const elSoil = document.getElementById("dashSoilMoisture");
  const elTemp = document.getElementById("dashTemperature");
  const elHum = document.getElementById("dashHumidity");
  const elServo = document.getElementById("dashServoPosition");
  const elAnchor = document.getElementById("dashAnchorStatus");

  // Tilt and Anchoring Evaluation
  const rawStatus = (reading.anchor_status || "").trim().toUpperCase();
  const isTiltDetected = Boolean(
    reading.tilt === 1 ||
    (reading.event && reading.event.includes("TILT")) ||
    Number(reading.tilt_angle) > 15.0
  );
  const isDeployed = (
    isTiltDetected ||
    rawStatus === "ACTIVE" ||
    rawStatus === "DEPLOYED" ||
    rawStatus.includes("ANCHOR") ||
    reading.servo_position > 0
  );

  if (elTilt) {
    if (isTiltDetected) {
      elTilt.innerHTML = `Tilt Detected <small style="font-size:0.85rem;color:#ef4444;font-weight:600;">(${Number(reading.tilt_angle).toFixed(1)}°)</small>`;
    } else {
      elTilt.innerText = `${Number(reading.tilt_angle).toFixed(1)}° (Normal)`;
    }
  }

  if (elSoil) elSoil.innerText = `${Number(reading.soil_moisture).toFixed(1)}%`;
  if (elTemp) elTemp.innerText = `${Number(reading.temperature).toFixed(1)}°C`;
  if (elHum) elHum.innerText = `${Number(reading.humidity).toFixed(1)}%`;
  if (elServo) elServo.innerText = `${reading.servo_position}°`;

  if (elAnchor) {
    if (isDeployed) {
      elAnchor.innerText = "Anchoring Activated";
      elAnchor.className = "status-active";
    } else {
      elAnchor.innerText = "NORMAL";
      elAnchor.className = "status-normal";
    }
  }

  // Secondary indicators
  const legRisk = document.getElementById("riskLevel");
  const legAnchor = document.getElementById("anchorStatus");
  const anchorRod = document.getElementById("anchorRod");
  const alertMsg = document.getElementById("alertMessage");

  if (legRisk) legRisk.innerText = isDeployed ? "HIGH RISK" : "NORMAL";
  if (legAnchor) legAnchor.innerText = isDeployed ? "Anchoring Activated" : "NORMAL";
  if (anchorRod) {
    if (isDeployed) anchorRod.classList.add("deployed");
    else anchorRod.classList.remove("deployed");
  }
  if (alertMsg) {
    alertMsg.innerText = isDeployed
      ? "Tilt Detected — Anchoring Activated. Mechanical anchor engaged by ESP8266."
      : "Normal Condition — Mangrove plant stable. Hardware monitoring active.";
  }
}

/**
 * Loads recent records from SQLite to plot trend graphs and populate the recent feed.
 */
async function updateDashboardAnalyticsAndFeed() {
  try {
    const res = await fetch(BACKEND_URL + "/api/readings?limit=20");
    if (!res.ok) return;
    const readings = await res.json();
    renderDashboardCharts(readings);
    renderRecentReadingsTable(readings);
  } catch (err) {
    console.warn("Analytics refresh warning:", err);
  }
}

/**
 * Renders analytical line charts with executive navy styling.
 */
function renderDashboardCharts(readings) {
  if (!Array.isArray(readings) || readings.length === 0) return;

  const chronData = [...readings].reverse();

  const labels = chronData.map(r => {
    if (!r.timestamp) return "";
    const parts = r.timestamp.split(" ");
    return parts.length > 1 ? parts[1] : r.timestamp;
  });

  const tiltValues = chronData.map(r => Number(r.tilt_angle));
  const soilValues = chronData.map(r => Number(r.soil_moisture));
  const tempValues = chronData.map(r => Number(r.temperature));

  const latest = readings[0];
  const badgeTilt = document.getElementById("chartTiltLatest");
  const badgeSoil = document.getElementById("chartSoilLatest");
  const badgeTemp = document.getElementById("chartTempLatest");

  if (badgeTilt) badgeTilt.innerText = `${Number(latest.tilt_angle).toFixed(1)}°`;
  if (badgeSoil) badgeSoil.innerText = `${Number(latest.soil_moisture).toFixed(1)}%`;
  if (badgeTemp) badgeTemp.innerText = `${Number(latest.temperature).toFixed(1)}°C`;

  if (tiltChart) { tiltChart.destroy(); tiltChart = null; }
  if (soilChart) { soilChart.destroy(); soilChart = null; }
  if (tempChart) { tempChart.destroy(); tempChart = null; }

  tiltChart = createStyledChart("tiltChart", labels, tiltValues, "Tilt Angle (°)", "#f59e0b", "rgba(245, 158, 11, 0.14)");
  soilChart = createStyledChart("soilChart", labels, soilValues, "Soil Moisture (%)", "#10b981", "rgba(16, 185, 129, 0.14)");
  tempChart = createStyledChart("tempChart", labels, tempValues, "Temperature (°C)", "#06b6d4", "rgba(6, 182, 212, 0.14)");
}

function createStyledChart(canvasId, labels, values, label, borderColor, backgroundColor) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || typeof Chart === "undefined") return null;

  return new Chart(canvas, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: label,
          data: values,
          borderColor: borderColor,
          backgroundColor: backgroundColor,
          borderWidth: 2.5,
          tension: 0.35,
          fill: true,
          pointRadius: 3,
          pointHoverRadius: 6,
          pointBackgroundColor: borderColor
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      plugins: {
        legend: {
          display: true,
          position: "top",
          labels: {
            boxWidth: 12,
            font: { family: "Inter", size: 12, weight: "600" },
            color: "#e2e8f0"
          }
        },
        tooltip: {
          mode: "index",
          intersect: false,
          backgroundColor: "rgba(15, 23, 42, 0.95)",
          titleColor: "#ffffff",
          bodyColor: "#cbd5e1",
          borderColor: "rgba(255, 255, 255, 0.15)",
          borderWidth: 1,
          padding: 10
        }
      },
      scales: {
        x: {
          grid: { color: "rgba(255, 255, 255, 0.06)" },
          ticks: {
            maxTicksLimit: 7,
            font: { family: "Inter", size: 11, weight: "500" },
            color: "#94a3b8"
          }
        },
        y: {
          grid: { color: "rgba(255, 255, 255, 0.06)" },
          ticks: {
            font: { family: "Inter", size: 11, weight: "500" },
            color: "#94a3b8"
          }
        }
      }
    }
  });
}

function renderRecentReadingsTable(readings) {
  const tbody = document.getElementById("recentReadingsBody");
  const countBadge = document.getElementById("recentReadingsCount");
  if (!tbody) return;

  if (!readings || readings.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="recent-state-cell empty">No stored sensor readings available in audit database.</td></tr>`;
    if (countBadge) countBadge.innerText = "0 records";
    return;
  }

  const slice = readings.slice(0, 10);
  if (countBadge) countBadge.innerText = `${readings.length} records`;

  tbody.innerHTML = slice.map(r => {
    const isHardware = (r.source || "").toUpperCase() === "HARDWARE";
    const srcBadge = isHardware
      ? `<span class="source-badge hw">REAL HARDWARE</span>`
      : `<span class="source-badge sim">SIMULATION</span>`;

    const rawStatus = (r.anchor_status || "").trim().toUpperCase();
    const isDeployed = (
      rawStatus === "ACTIVE" ||
      rawStatus === "DEPLOYED" ||
      rawStatus.includes("ANCHOR") ||
      (r.event && r.event.includes("TILT")) ||
      r.servo_position > 0 ||
      Number(r.tilt_angle) > 15.0
    );
    const anchorBadge = isDeployed
      ? `<span class="status-chip warning">ANCHORING ACTIVATED</span>`
      : `<span class="status-chip success">NORMAL</span>`;

    return `
      <tr>
        <td class="font-mono">${r.timestamp || "--"}</td>
        <td>${srcBadge}</td>
        <td><strong>${Number(r.tilt_angle).toFixed(1)}°</strong></td>
        <td>${Number(r.soil_moisture).toFixed(1)}%</td>
        <td>${Number(r.temperature).toFixed(1)}°C</td>
        <td>${anchorBadge}</td>
      </tr>
    `;
  }).join("");
}

function handleBackendUnavailableState() {
  updateHardwareBadgeUI(false, false, false);
  const stateMsg = document.getElementById("dashStateMessage");
  if (stateMsg) {
    stateMsg.style.display = "block";
    stateMsg.innerHTML = "ℹ️ <strong>System Notice:</strong> Unable to retrieve the latest monitoring data.";
  }
}


// ====================================================
// HISTORY AUDIT TABLE (SQLITE DATA PIPELINE)
// ====================================================

async function fetchHistoryReadings() {
  const tableBody = document.getElementById("historyTable");
  const countBadge = document.getElementById("historyRecordCount");
  const sourceFilter = document.getElementById("historySourceFilter");

  if (!tableBody) return;

  tableBody.innerHTML = `
    <tr>
      <td colspan="9" class="table-state-cell loading">
        <div class="table-state-content">
          <span class="spinner-dot">⏳</span>
          <span>Loading stored readings from database...</span>
        </div>
      </td>
    </tr>
  `;

  try {
    let url = BACKEND_URL + "/api/readings?limit=300";
    if (sourceFilter && sourceFilter.value !== "ALL") {
      url += `&source=${sourceFilter.value}`;
    }

    const res = await fetch(url);
    if (!res.ok) throw new Error("Status " + res.status);

    storedHistoryReadings = await res.json();
    renderHistoryTable();
  } catch (err) {
    console.error("Error fetching history:", err);
    tableBody.innerHTML = `
      <tr>
        <td colspan="9" class="table-state-cell error">
          <span>Unable to retrieve the latest monitoring data.</span>
        </td>
      </tr>
    `;
    if (countBadge) countBadge.innerText = "Offline";
  }
}

function renderHistoryTable() {
  const tableBody = document.getElementById("historyTable");
  const countBadge = document.getElementById("historyRecordCount");
  const searchInput = document.getElementById("historySearchInput");
  const query = (searchInput ? searchInput.value : "").trim().toLowerCase();

  if (!tableBody) return;

  let filtered = storedHistoryReadings;
  if (query) {
    filtered = storedHistoryReadings.filter(r => {
      const idMatch = String(r.id || "").toLowerCase().includes(query);
      const tsMatch = String(r.timestamp || "").toLowerCase().includes(query);
      const devMatch = String(r.device_id || "").toLowerCase().includes(query);
      const srcMatch = String(r.source || "").toLowerCase().includes(query);
      const eventMatch = String(r.event || "").toLowerCase().includes(query);
      const statusMatch = String(r.anchor_status || "").toLowerCase().includes(query);
      return idMatch || tsMatch || devMatch || srcMatch || eventMatch || statusMatch;
    });
  }

  if (countBadge) {
    countBadge.innerText = `${filtered.length} of ${storedHistoryReadings.length} records`;
  }

  if (filtered.length === 0) {
    tableBody.innerHTML = `
      <tr>
        <td colspan="9" class="table-state-cell empty">
          <span>No matching telemetry records found in SQLite database.</span>
        </td>
      </tr>
    `;
    return;
  }

  tableBody.innerHTML = filtered.map(r => {
    const isHardware = (r.source || "").toUpperCase() === "HARDWARE";
    const devTag = r.device_id ? `<br><small class="font-mono text-muted" style="font-size:0.75rem;color:#94a3b8;">${r.device_id}</small>` : "";
    const srcTag = isHardware
      ? `<span class="source-badge hw">REAL HARDWARE</span>${devTag}`
      : `<span class="source-badge sim">SIMULATION</span>`;

    const rawStatus = (r.anchor_status || "").trim().toUpperCase();
    const isDeployed = (
      rawStatus === "ACTIVE" ||
      rawStatus === "DEPLOYED" ||
      rawStatus.includes("ANCHOR") ||
      (r.event && r.event.includes("TILT")) ||
      r.servo_position > 0 ||
      Number(r.tilt_angle) > 15.0
    );
    const eventSnippet = (r.event && r.event !== "NORMAL") ? `<br><small style="color:#f59e0b;font-weight:600;font-size:0.75rem;">${r.event}</small>` : "";
    const anchorTag = isDeployed
      ? `<span class="status-chip warning">ANCHORING ACTIVATED</span>${eventSnippet}`
      : `<span class="status-chip success">NORMAL</span>`;

    return `
      <tr>
        <td class="font-mono">#${r.id}</td>
        <td class="font-mono">${r.timestamp || "--"}</td>
        <td>${srcTag}</td>
        <td><strong>${Number(r.tilt_angle).toFixed(1)}°</strong></td>
        <td>${Number(r.soil_moisture).toFixed(1)}%</td>
        <td>${Number(r.temperature).toFixed(1)}°C</td>
        <td>${Number(r.humidity).toFixed(1)}%</td>
        <td>${r.servo_position}°</td>
        <td>${anchorTag}</td>
      </tr>
    `;
  }).join("");
}

function initHistorySection() {
  const searchInput = document.getElementById("historySearchInput");
  const clearBtn = document.getElementById("historyClearSearchBtn");
  const filterSelect = document.getElementById("historySourceFilter");
  const refreshBtn = document.getElementById("refreshHistoryBtn");

  if (searchInput) searchInput.addEventListener("input", renderHistoryTable);
  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      if (searchInput) {
        searchInput.value = "";
        renderHistoryTable();
      }
    });
  }
  if (filterSelect) filterSelect.addEventListener("change", fetchHistoryReadings);
  if (refreshBtn) refreshBtn.addEventListener("click", fetchHistoryReadings);
}

function exportHistoryCsv() {
  if (!storedHistoryReadings || storedHistoryReadings.length === 0) {
    alert("No telemetry records available to export.");
    return;
  }

  const headers = ["ID", "Timestamp", "Device ID", "Source", "Event", "Tilt Angle (deg)", "Soil Moisture (%)", "Temperature (C)", "Humidity (%)", "Servo Position (deg)", "Anchor Status"];
  const rows = storedHistoryReadings.map(r => [
    r.id,
    `"${r.timestamp || ""}"`,
    `"${r.device_id || ""}"`,
    `"${r.source || ""}"`,
    `"${r.event || ""}"`,
    r.tilt_angle,
    r.soil_moisture,
    r.temperature,
    r.humidity,
    r.servo_position,
    `"${r.anchor_status || ""}"`
  ]);

  const csvContent = [headers.join(","), ...rows.map(e => e.join(","))].join("\n");
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.setAttribute("href", url);
  link.setAttribute("download", `smart_mangrove_telemetry_${new Date().toISOString().slice(0, 10)}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}


// ====================================================
// OFFICIAL ENVIRONMENTAL DATA (PICHAVARAM BASELINE)
// ====================================================

async function fetchEnvironmentalData() {
  try {
    const res = await fetch(BACKEND_URL + "/api/environmental-data");
    if (!res.ok) return;
    const data = await res.json();
    renderEnvironmentalUI(data);
  } catch (err) {
    console.warn("Failed to fetch official environmental data:", err);
  }
}

function renderEnvironmentalUI(data) {
  if (!data) return;

  const elArea = document.getElementById("envArea");
  const elLat = document.getElementById("envLatitude");
  const elLng = document.getElementById("envLongitude");
  const elRain = document.getElementById("envRainfall");
  const elSal = document.getElementById("envSalinity");
  const elPh = document.getElementById("envWaterPh");

  if (elArea && data.area_ha) elArea.innerText = Number(data.area_ha).toLocaleString() + " ha";
  if (elLat && data.latitude) elLat.innerText = data.latitude + "° N";
  if (elLng && data.longitude) elLng.innerText = data.longitude + "° E";
  if (elRain && data.rainfall_mm) elRain.innerText = Number(data.rainfall_mm).toLocaleString() + " mm";
  if (elSal && data.salinity_ppt) elSal.innerText = data.salinity_ppt + " ppt";
  if (elPh && data.water_ph) elPh.innerText = data.water_ph;

  if (data.seasonal_profiles) {
    renderEnvironmentalSeasonalChart(data.seasonal_profiles);
  }
}

function renderEnvironmentalSeasonalChart(profiles) {
  const canvas = document.getElementById("envSeasonalChart");
  if (!canvas || typeof Chart === "undefined") return;

  const labels = profiles.map(p => p.season);
  const rainfalls = profiles.map(p => p.rainfall_mm);
  const salinities = profiles.map(p => p.salinity_ppt);

  if (envSeasonalChartInstance) {
    envSeasonalChartInstance.destroy();
    envSeasonalChartInstance = null;
  }

  envSeasonalChartInstance = new Chart(canvas, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Rainfall (mm)",
          data: rainfalls,
          backgroundColor: "rgba(2, 132, 199, 0.75)",
          borderColor: "#0284c7",
          borderWidth: 1.5,
          yAxisID: "yRain",
          borderRadius: 4
        },
        {
          type: "line",
          label: "Salinity (ppt)",
          data: salinities,
          borderColor: "#059669",
          backgroundColor: "rgba(5, 150, 105, 0.15)",
          borderWidth: 2.5,
          fill: false,
          yAxisID: "ySal",
          tension: 0.35,
          pointRadius: 4,
          pointBackgroundColor: "#059669"
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: "top",
          labels: { font: { family: "Inter", size: 11, weight: "600" }, color: "#cbd5e1" }
        },
        tooltip: {
          mode: "index",
          intersect: false,
          backgroundColor: "rgba(15, 23, 42, 0.95)",
          titleColor: "#f8fafc",
          bodyColor: "#cbd5e1",
          borderColor: "rgba(255, 255, 255, 0.12)",
          borderWidth: 1
        }
      },
      scales: {
        x: { grid: { color: "rgba(255, 255, 255, 0.05)" }, ticks: { font: { family: "Inter", size: 11 }, color: "#94a3b8" } },
        yRain: {
          type: "linear",
          position: "left",
          title: { display: true, text: "Rainfall (mm)", font: { family: "Inter", size: 11, weight: "600" }, color: "#94a3b8" },
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: { color: "#94a3b8" }
        },
        ySal: {
          type: "linear",
          position: "right",
          title: { display: true, text: "Salinity (ppt)", font: { family: "Inter", size: 11, weight: "600" }, color: "#94a3b8" },
          grid: { drawOnChartArea: false },
          ticks: { color: "#94a3b8" }
        }
      }
    }
  });
}


// ====================================================
// SIMULATOR READING (DEMO ONLY — EXPLICIT START/STOP)
// ====================================================

function renderSimulatorReadings() {
  const elTilt = document.getElementById("simTiltAngle");
  const elSoil = document.getElementById("simSoilMoisture");
  const elTemp = document.getElementById("simTemperature");
  const elHum = document.getElementById("simHumidity");
  const elServo = document.getElementById("simServoPosition");
  const elAnchor = document.getElementById("simAnchorStatus");
  const elUpdate = document.getElementById("simLastUpdate");

  if (elTilt) elTilt.innerText = `${simState.tilt_angle.toFixed(1)}°`;
  if (elSoil) elSoil.innerText = `${Math.round(simState.soil_moisture)}%`;
  if (elTemp) elTemp.innerText = `${simState.temperature.toFixed(1)}°C`;
  if (elHum) elHum.innerText = `${Math.round(simState.humidity)}%`;
  if (elServo) elServo.innerText = `${simState.servo_position}°`;

  if (elAnchor) {
    elAnchor.innerText = simState.anchor_status;
    elAnchor.className = simState.anchor_status === "Deployed" ? "sim-value sim-status-deployed" : "sim-value sim-status-normal";
  }

  if (elUpdate) {
    elUpdate.innerText = isSimulatorRunning ? new Date().toLocaleTimeString() : "Stopped";
  }
}

async function stepSimulation() {
  simulationStepCounter++;

  // Realistic natural oscillation
  simState.tilt_angle = Math.max(0.5, Math.min(24.0, Number((simState.tilt_angle + (Math.random() * 1.6 - 0.78)).toFixed(1))));
  simState.soil_moisture = Math.max(35.0, Math.min(92.0, Number((simState.soil_moisture + (Math.random() * 2.0 - 1.0)).toFixed(1))));
  simState.temperature = Math.max(22.0, Math.min(38.0, Number((simState.temperature + (Math.random() * 0.4 - 0.2)).toFixed(1))));
  simState.humidity = Math.max(50.0, Math.min(95.0, Number((simState.humidity + (Math.random() * 1.6 - 0.8)).toFixed(1))));

  // Automated trigger logic: Tilt > 15° triggers Anchor
  if (simState.tilt_angle > 15.0) {
    simState.servo_position = 90;
    simState.anchor_status = "Deployed";
  } else {
    simState.servo_position = 0;
    simState.anchor_status = "Normal";
  }

  renderSimulatorReadings();

  // Persist each generated reading to SQLite via POST /api/readings
  const payload = {
    source: "SIMULATION",
    timestamp: new Date().toISOString().replace("T", " ").slice(0, 19),
    tilt_angle: simState.tilt_angle,
    soil_moisture: simState.soil_moisture,
    temperature: simState.temperature,
    humidity: simState.humidity,
    servo_position: simState.servo_position,
    anchor_status: simState.anchor_status
  };

  await persistSimulatorReading(payload);
}

async function persistSimulatorReading(payload) {
  const dbDot = document.getElementById("simDbDot");
  const dbText = document.getElementById("simDbStatusText");

  try {
    const res = await fetch(BACKEND_URL + "/api/readings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      if (dbDot) dbDot.innerText = "💾";
      if (dbText) dbText.innerText = "Simulated reading recorded in database";
    }
  } catch (err) {
    if (dbDot) dbDot.innerText = "⚠️";
    if (dbText) dbText.innerText = "Unable to record simulated reading";
  }
}

function startSimulation() {
  if (isSimulatorRunning) return;
  isSimulatorRunning = true;

  const startBtn = document.getElementById("startSimBtn");
  const stopBtn = document.getElementById("stopSimBtn");
  const pulseDot = document.getElementById("simPulseDot");
  const statusText = document.getElementById("simStatusText");

  if (startBtn) startBtn.classList.add("active");
  if (stopBtn) stopBtn.classList.remove("active");
  if (pulseDot) pulseDot.classList.add("active");
  if (statusText) statusText.innerText = "Simulation Running (Cadence: 2.5s)";

  stepSimulation();
  simulationInterval = setInterval(stepSimulation, 2500);
}

function stopSimulation() {
  if (!isSimulatorRunning) return;
  isSimulatorRunning = false;

  if (simulationInterval) {
    clearInterval(simulationInterval);
    simulationInterval = null;
  }

  const startBtn = document.getElementById("startSimBtn");
  const stopBtn = document.getElementById("stopSimBtn");
  const pulseDot = document.getElementById("simPulseDot");
  const statusText = document.getElementById("simStatusText");

  if (startBtn) startBtn.classList.remove("active");
  if (stopBtn) stopBtn.classList.add("active");
  if (pulseDot) pulseDot.classList.remove("active");
  if (statusText) statusText.innerText = "Simulation Stopped";

  renderSimulatorReadings();
}

async function fetchTelemetryData() {
  try {
    const res = await fetch(BACKEND_URL + "/api/telemetry");
    if (!res.ok) return;
    const data = await res.json();
    const jsonView = document.getElementById("telemetryJsonView");
    if (jsonView) jsonView.innerText = JSON.stringify(data, null, 2);

    const pipelineDot = document.getElementById("hwPipelineDot");
    const pipelineMode = document.getElementById("hwPipelineMode");
    if (pipelineDot && pipelineMode) {
      if (data.is_real_hardware) {
        pipelineDot.innerText = "🟢";
        pipelineMode.innerText = `REAL HARDWARE CONNECTED (${data.device_id || "ESP8266-001"})`;
      } else if (data.connected && data.source === "HARDWARE") {
        pipelineDot.innerText = "🧪";
        pipelineMode.innerText = "TEST CONNECTION (SOFTWARE MOCK)";
      } else {
        pipelineDot.innerText = "⚪";
        pipelineMode.innerText = "HARDWARE DISCONNECTED";
      }
    }
  } catch (err) {
    console.warn("Telemetry fetch error:", err);
  }
}

async function testConnectHardware() {
  try {
    const res = await fetch(BACKEND_URL + "/api/hardware/test-connect", { method: "POST" });
    if (res.ok) {
      await updateDashboardCycle();
      await fetchTelemetryData();
    }
  } catch (err) {
    console.error("Test connect error:", err);
  }
}

async function testDisconnectHardware() {
  try {
    const res = await fetch(BACKEND_URL + "/api/hardware/test-disconnect", { method: "POST" });
    if (res.ok) {
      await updateDashboardCycle();
      await fetchTelemetryData();
    }
  } catch (err) {
    console.error("Test disconnect error:", err);
  }
}

function initSimulatorPanel() {
  const startBtn = document.getElementById("startSimBtn");
  const stopBtn = document.getElementById("stopSimBtn");
  const testConnBtn = document.getElementById("testConnectHardwareBtn");
  const testDiscBtn = document.getElementById("testDisconnectHardwareBtn");

  if (startBtn) startBtn.addEventListener("click", startSimulation);
  if (stopBtn) stopBtn.addEventListener("click", stopSimulation);
  if (testConnBtn) testConnBtn.addEventListener("click", testConnectHardware);
  if (testDiscBtn) testDiscBtn.addEventListener("click", testDisconnectHardware);

  // Initial display without starting simulation
  renderSimulatorReadings();
  fetchTelemetryData();
}


// ====================================================
// INITIALIZATION ON DOM READY
// ====================================================

window.addEventListener("DOMContentLoaded", () => {
  if (!checkAuth()) return;

  // Set logged-in username in UI
  const user = localStorage.getItem("mangrove_user") || "Blue Guard";
  const userDisplay = document.getElementById("loggedInUser");
  const sideUserDisplay = document.getElementById("sideMenuUser");
  if (userDisplay) userDisplay.innerText = user;
  if (sideUserDisplay) sideUserDisplay.innerText = user;

  // Initialize navigation & independent view routing
  initNavigation();

  // Initialize history table listeners
  initHistorySection();

  // Initialize simulator panel (in stopped state)
  initSimulatorPanel();

  // Initial dashboard data load
  updateDashboardCycle();

  // Load environmental dataset
  fetchEnvironmentalData();

  // Auto-refresh dashboard every 5 seconds
  sensorPollingInterval = setInterval(updateDashboardCycle, 5000);
});