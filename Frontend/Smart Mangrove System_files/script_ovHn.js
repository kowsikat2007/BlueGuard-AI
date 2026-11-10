// =========================================
// SMART MANGROVE SYSTEM
// COMPLETE FRONTEND SCRIPT
// =========================================

const BACKEND_URL = "http://127.0.0.1:8000";

let rainfallChart = null;
let waterChart = null;
let soilChart = null;
let tiltChart = null;


// =========================================
// GET LIVE SENSOR DATA
// =========================================

async function getSensorData() {

  const connection =
    document.getElementById("connectionStatus");

  try {

    connection.innerText =
      "Connecting to sensor simulator...";


    const response =
      await fetch(
        BACKEND_URL + "/api/sensors"
      );


    if (!response.ok) {

      throw new Error(
        "Sensor API error: " +
        response.status
      );

    }


    const data =
      await response.json();


    console.log(
      "Live sensor data:",
      data
    );


    // =====================================
    // LIVE SENSOR VALUES
    // =====================================

    document.getElementById(
      "rainfall"
    ).innerText =
      data.rainfall + " mm";


    document.getElementById(
      "waterLevel"
    ).innerText =
      data.water_level + " m";


    document.getElementById(
      "soilMoisture"
    ).innerText =
      data.soil_moisture + " %";


    document.getElementById(
      "tiltAngle"
    ).innerText =
      data.tilt_angle + " °";


    // =====================================
    // RISK STATUS
    // =====================================

    document.getElementById(
      "riskLevel"
    ).innerText =
      data.risk_level;


    // =====================================
    // ANCHOR STATUS
    // =====================================

    document.getElementById(
      "anchorStatus"
    ).innerText =
      data.anchor_status;


    // =====================================
    // ALERT MESSAGE
    // =====================================

    document.getElementById(
      "alertMessage"
    ).innerText =
      data.alert;


    // =====================================
    // CONNECTION STATUS
    // =====================================

    connection.innerText =
      "✅ Backend and sensor simulator connected";


    // =====================================
    // UPDATE ANCHOR SIMULATION
    // =====================================

    updateAnchorSimulation(
      data.anchor_status
    );


    // =====================================
    // LOAD DATABASE HISTORY
    // =====================================

    await loadHistory();


  } catch (error) {

    console.error(
      "Sensor error:",
      error
    );


    connection.innerText =
      "❌ Backend connection failed";

  }

}



// =========================================
// LOAD STORED SENSOR HISTORY
// =========================================

async function loadHistory() {

  try {

    const response =
      await fetch(
        BACKEND_URL + "/api/history"
      );


    if (!response.ok) {

      throw new Error(
        "History API error: " +
        response.status
      );

    }


    const history =
      await response.json();


    console.log(
      "Stored history:",
      history
    );


    // =====================================
    // CHECK DATA
    // =====================================

    if (!Array.isArray(history)) {

      console.error(
        "History is not an array:",
        history
      );

      return;
    }


    if (history.length === 0) {

      console.log(
        "No sensor history available."
      );

      return;
    }


    // =====================================
    // REVERSE FOR GRAPH
    // OLDEST → NEWEST
    // =====================================

    const graphData =
      [...history].reverse();


    // =====================================
    // UPDATE CHARTS
    // =====================================

    updateCharts(
      graphData
    );


    // =====================================
    // UPDATE TABLE
    // =====================================

    updateHistoryTable(
      history
    );


  } catch (error) {

    console.error(
      "History loading error:",
      error
    );

  }

}



// =========================================
// UPDATE ALL CHARTS
// =========================================

function updateCharts(data) {


  // =====================================
  // LABELS
  // =====================================

  const labels =
    data.map(
      item => item.timestamp
    );


  // =====================================
  // RAINFALL
  // =====================================

  const rainfall =
    data.map(
      item => Number(
        item.rainfall
      )
    );


  // =====================================
  // WATER LEVEL
  // =====================================

  const water =
    data.map(
      item => Number(
        item.water_level
      )
    );


  // =====================================
  // SOIL MOISTURE
  // =====================================

  const soil =
    data.map(
      item => Number(
        item.soil_moisture
      )
    );


  // =====================================
  // TILT
  // =====================================

  const tilt =
    data.map(
      item => Number(
        item.tilt_angle
      )
    );


  // =====================================
  // DESTROY OLD CHARTS
  // =====================================

  if (rainfallChart) {

    rainfallChart.destroy();

    rainfallChart = null;

  }


  if (waterChart) {

    waterChart.destroy();

    waterChart = null;

  }


  if (soilChart) {

    soilChart.destroy();

    soilChart = null;

  }


  if (tiltChart) {

    tiltChart.destroy();

    tiltChart = null;

  }


  // =====================================
  // CREATE NEW CHARTS
  // =====================================

  rainfallChart =
    createChart(
      "rainfallChart",
      labels,
      rainfall,
      "Rainfall (mm)"
    );


  waterChart =
    createChart(
      "waterChart",
      labels,
      water,
      "Water Level (m)"
    );


  soilChart =
    createChart(
      "soilChart",
      labels,
      soil,
      "Soil Moisture (%)"
    );


  tiltChart =
    createChart(
      "tiltChart",
      labels,
      tilt,
      "Tilt Angle (°)"
    );

}



// =========================================
// CREATE CHART
// =========================================

function createChart(
  canvasId,
  labels,
  values,
  label
) {


  const canvas =
    document.getElementById(
      canvasId
    );


  if (!canvas) {

    console.error(
      "Canvas not found:",
      canvasId
    );

    return null;

  }


  // Check Chart.js

  if (
    typeof Chart ===
    "undefined"
  ) {

    console.error(
      "Chart.js is not loaded."
    );

    return null;

  }


  return new Chart(
    canvas,
    {

      type: "line",


      data: {

        labels: labels,


        datasets: [

          {

            label: label,

            data: values,

            borderWidth: 3,

            tension: 0.3,

            fill: false,

            pointRadius: 3,

            pointHoverRadius: 6

          }

        ]

      },


      options: {

        responsive: true,

        maintainAspectRatio: false,

        animation: false,


        plugins: {

          legend: {

            display: true

          }

        },


        scales: {

          x: {

            ticks: {

              maxTicksLimit: 10

            }

          },


          y: {

            beginAtZero: true

          }

        }

      }

    }
  );

}



// =========================================
// UPDATE HISTORY TABLE
// =========================================

function updateHistoryTable(data) {


  const table =
    document.getElementById(
      "historyTable"
    );


  if (!table) {

    console.error(
      "History table not found."
    );

    return;

  }


  table.innerHTML = "";


  data.forEach(
    item => {


      const row =
        document.createElement(
          "tr"
        );


      row.innerHTML = `

                <td>
                    ${item.id}
                </td>

                <td>
                    ${item.timestamp}
                </td>

                <td>
                    ${item.rainfall} mm
                </td>

                <td>
                    ${item.water_level} m
                </td>

                <td>
                    ${item.soil_moisture} %
                </td>

                <td>
                    ${item.tilt_angle} °
                </td>

                <td>
                    ${item.risk_level}
                </td>

                <td>
                    ${item.anchor_status}
                </td>

            `;


      table.appendChild(
        row
      );

    }
  );

}



// =========================================
// AUTOMATED ANCHOR SIMULATION
// =========================================

function updateAnchorSimulation(
  status
) {


  const anchorRod =
    document.getElementById(
      "anchorRod"
    );


  const simulationStatus =
    document.getElementById(
      "anchorSimulationStatus"
    );


  // If anchor simulation
  // doesn't exist, stop safely.

  if (
    !anchorRod ||
    !simulationStatus
  ) {

    return;

  }


  // =====================================
  // HIGH RISK / DEPLOYED
  // =====================================

  if (
    status === "DEPLOYED"
  ) {


    anchorRod.classList.add(
      "deployed"
    );


    simulationStatus.innerText =
      "DEPLOYED";


    simulationStatus.style.color =
      "#b42318";


  }


  // =====================================
  // NORMAL / READY / STANDBY
  // =====================================

  else {


    anchorRod.classList.remove(
      "deployed"
    );


    simulationStatus.innerText =
      status || "STANDBY";


    simulationStatus.style.color =
      "#176b3a";

  }

}



// =========================================
// START DASHBOARD
// =========================================

window.addEventListener(
  "DOMContentLoaded",
  function () {


    console.log(
      "================================="
    );


    console.log(
      "Smart Mangrove Dashboard started"
    );


    console.log(
      "================================="
    );


    // Get first sensor reading

    getSensorData();


    // Get new sensor data
    // every 5 seconds

    setInterval(
      getSensorData,
      5000
    );

  }
);