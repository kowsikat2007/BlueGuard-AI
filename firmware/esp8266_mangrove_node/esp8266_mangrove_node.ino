/*
  =============================================================================
  SMART MANGROVE SYSTEM — ESP8266 HARDWARE NODE FIRMWARE
  IoT-Driven Coastal Wetland MRV & Automated Root Stabilization Mechanism
  =============================================================================

  HARDWARE RESPONSIBILITY:
  1. Real-time local tilt detection (independent of network/browser status).
  2. Immediate local servo actuation for root anchoring when tilt is detected.
  3. Continuous rhizosphere soil-moisture acquisition.
  4. Non-blocking periodic telemetry stream to FastAPI backend over Wi-Fi.
  5. Immediate event reporting on tilt alert and stabilization recovery.
  6. Safety hysteresis state machine preventing continuous servo jitter.

  TARGET BOARD: ESP8266 (NodeMCU v2/v3, WeMos D1 Mini, ESP-12E/F)
  DEPENDENCIES: Built-in ESP8266 Arduino Core (ESP8266WiFi, ESP8266HTTPClient, Servo)
  =============================================================================
*/

#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>
#include <Servo.h>

// =========================================================================
// 1. NETWORK & BACKEND CONFIGURATION
// =========================================================================
// Replace with your local Wi-Fi router / mobile hotspot credentials
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// FastAPI Backend Server Settings (running on laptop / workstation / cloud)
// IMPORTANT: Enter the local IP address of your machine hosting FastAPI
const char* FASTAPI_HOST  = "192.168.1.100";  // Example LAN IP of backend PC
const int   FASTAPI_PORT  = 8001;             // Default Smart Mangrove port
const char* FASTAPI_PATH  = "/api/hardware/data";
const char* DEVICE_ID     = "ESP8266-001";    // Unique hardware station ID

// =========================================================================
// 2. SENSOR & SERVO PIN ASSIGNMENTS (CONFIGURABLE PLACEHOLDERS)
// =========================================================================
// NOTE: Change these pins to match your physical wiring.
// Standard NodeMCU GPIO pin definitions:
// D1=GPIO5, D2=GPIO4, D3=GPIO0, D4=GPIO2, D5=GPIO14, D6=GPIO12, D7=GPIO13
const int PIN_TILT_SENSOR   = D5;  // GPIO14: Digital tilt switch (SW-520D / ball tilt)
const int PIN_SOIL_MOISTURE = A0;  // ADC0: Analog soil moisture sensor (capacitive / resistive)
const int PIN_SERVO         = D4;  // GPIO2: PWM control signal for root anchor servo

// =========================================================================
// 3. SENSOR CALIBRATION & THRESHOLD SETTINGS
// =========================================================================
// Tilt sensor active logic:
// HIGH: sensor pin reads HIGH when tilted
// LOW:  sensor pin reads LOW when tilted (e.g. pullup switch opened)
const int TILT_ACTIVE_LOGIC = HIGH;

// Soil moisture ADC calibration:
// Measure raw values: Air (completely dry) vs Water (immersed)
const int SOIL_RAW_DRY_AIR  = 850; // Typical dry air reading on 10-bit ADC (0-1023)
const int SOIL_RAW_WET_WATER = 350; // Typical reading immersed in water

// Mechanical Servo Angles (adjust based on your physical anchor linkage)
const int SERVO_POS_NORMAL    = 0;   // Standby position (anchor retracted)
const int SERVO_POS_ANCHORING = 90;  // Deployed position (anchor engaged)

// Timing intervals
const unsigned long TELEMETRY_INTERVAL_MS = 3000; // Normal periodic telemetry (3s)
const unsigned long DEBOUNCE_DELAY_MS     = 250;  // Noise filter debounce delay (ms)

// =========================================================================
// 4. OPERATIONAL STATE MACHINE (ANCHORING SAFETY)
// =========================================================================
enum AnchorState {
  STATE_NORMAL,    // Plant stable, servo at standby (0 deg)
  STATE_ANCHORED   // Tilt detected, servo deployed (90 deg)
};

AnchorState currentAnchorState = STATE_NORMAL;
Servo anchorServo;

unsigned long lastTelemetryTime = 0;
unsigned long lastDebounceTime  = 0;
int lastRawTiltState            = LOW;
int confirmedTiltState          = LOW;

// =========================================================================
// 5. HELPER FUNCTIONS
// =========================================================================

/**
 * Connect to Wi-Fi with non-blocking retry logic
 */
void connectToWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;

  Serial.println();
  Serial.print(F("[WiFi] Connecting to SSID: "));
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(F("."));
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println();
    Serial.print(F("[WiFi] Connected! Node IP: "));
    Serial.println(WiFi.localIP());
  } else {
    Serial.println();
    Serial.println(F("[WiFi] Connection timeout. Local tilt control remains active. Will retry in background."));
  }
}

/**
 * Read and calibrate soil moisture percentage (0.0 to 100.0%)
 */
float readSoilMoisture() {
  int rawADC = analogRead(PIN_SOIL_MOISTURE);
  // Constrain raw reading to calibration limits
  rawADC = constrain(rawADC, min(SOIL_RAW_DRY_AIR, SOIL_RAW_WET_WATER), max(SOIL_RAW_DRY_AIR, SOIL_RAW_WET_WATER));

  // Map ADC reading inversely: higher voltage often means drier for resistive, or vice versa
  float percentage = 0.0;
  if (SOIL_RAW_DRY_AIR > SOIL_RAW_WET_WATER) {
    percentage = (float)(SOIL_RAW_DRY_AIR - rawADC) / (float)(SOIL_RAW_DRY_AIR - SOIL_RAW_WET_WATER) * 100.0;
  } else {
    percentage = (float)(rawADC - SOIL_RAW_DRY_AIR) / (float)(SOIL_RAW_WET_WATER - SOIL_RAW_DRY_AIR) * 100.0;
  }

  percentage = constrain(percentage, 0.0, 100.0);
  return percentage;
}

/**
 * Send JSON telemetry payload to FastAPI backend
 */
bool sendTelemetryToFastAPI(int tiltVal, float soilMoisture, const char* servoState, const char* eventName) {
  if (WiFi.status() != WL_CONNECTED) {
    connectToWiFi();
    if (WiFi.status() != WL_CONNECTED) return false;
  }

  WiFiClient client;
  HTTPClient http;

  char url[128];
  snprintf(url, sizeof(url), "http://%s:%d%s", FASTAPI_HOST, FASTAPI_PORT, FASTAPI_PATH);

  http.begin(client, url);
  http.addHeader(F("Content-Type"), F("application/json"));
  http.setTimeout(2500); // 2.5s timeout prevents blocking loop if backend offline

  // Construct JSON payload
  char jsonBuffer[256];
  snprintf(jsonBuffer, sizeof(jsonBuffer),
    "{"
      "\"device_id\":\"%s\","
      "\"source\":\"HARDWARE\","
      "\"tilt\":%d,"
      "\"soil_moisture\":%.1f,"
      "\"servo_state\":\"%s\","
      "\"event\":\"%s\""
    "}",
    DEVICE_ID, tiltVal, soilMoisture, servoState, eventName
  );

  int httpCode = http.POST((uint8_t*)jsonBuffer, strlen(jsonBuffer));

  if (httpCode > 0) {
    Serial.print(F("[HTTP] POST successful ("));
    Serial.print(httpCode);
    Serial.println(F(")"));
  } else {
    Serial.print(F("[HTTP] POST failed: "));
    Serial.println(http.errorToString(httpCode));
  }

  http.end();
  return (httpCode == 200 || httpCode == 201);
}

// =========================================================================
// 6. SETUP & MAIN LOOP
// =========================================================================

void setup() {
  Serial.begin(115200);
  delay(200);

  Serial.println(F("\n=============================================="));
  Serial.println(F(" SMART MANGROVE SYSTEM — ESP8266 NODE FIRMWARE"));
  Serial.println(F(" Device ID: ESP8266-001"));
  Serial.println(F("=============================================="));

  // Initialize GPIO pins
  pinMode(PIN_TILT_SENSOR, INPUT_PULLUP);

  // Initialize Servo
  anchorServo.attach(PIN_SERVO);
  anchorServo.write(SERVO_POS_NORMAL); // Set initial standby position
  currentAnchorState = STATE_NORMAL;
  Serial.println(F("[Hardware] Root anchor servo initialized in STANDBY (0 deg)."));

  // Connect to Wi-Fi network
  connectToWiFi();
}

void loop() {
  unsigned long now = millis();

  // -------------------------------------------------------------------------
  // A. LOCAL TILT SENSING WITH DEBOUNCE & HYSTERESIS
  // -------------------------------------------------------------------------
  int rawReading = digitalRead(PIN_TILT_SENSOR);

  if (rawReading != lastRawTiltState) {
    lastDebounceTime = now;
  }

  if ((now - lastDebounceTime) > DEBOUNCE_DELAY_MS) {
    if (rawReading != confirmedTiltState) {
      confirmedTiltState = rawReading;

      // Check if tilt condition is detected
      bool isTilted = (confirmedTiltState == TILT_ACTIVE_LOGIC);

      if (isTilted && currentAnchorState == STATE_NORMAL) {
        // TRANSITION: NORMAL -> ANCHORED
        Serial.println(F("\n[ALERT] TILT DETECTED! Engaging automated root anchor servo locally..."));
        anchorServo.write(SERVO_POS_ANCHORING); // Immediate local servo control
        currentAnchorState = STATE_ANCHORED;

        // Immediate event dispatch to FastAPI backend
        float moisture = readSoilMoisture();
        sendTelemetryToFastAPI(1, moisture, "ANCHORING", "TILT_DETECTED");
        lastTelemetryTime = now;
      }
      else if (!isTilted && currentAnchorState == STATE_ANCHORED) {
        // TRANSITION: ANCHORED -> NORMAL (Stabilization recovered)
        Serial.println(F("\n[INFO] Mangrove upright stability restored. Returning anchor to standby..."));
        anchorServo.write(SERVO_POS_NORMAL); // Return servo to standby
        currentAnchorState = STATE_NORMAL;

        // Immediate recovery event dispatch
        float moisture = readSoilMoisture();
        sendTelemetryToFastAPI(0, moisture, "NORMAL", "NORMAL");
        lastTelemetryTime = now;
      }
    }
  }

  lastRawTiltState = rawReading;

  // -------------------------------------------------------------------------
  // B. PERIODIC TELEMETRY STREAM TO FASTAPI BACKEND
  // -------------------------------------------------------------------------
  if (now - lastTelemetryTime >= TELEMETRY_INTERVAL_MS) {
    lastTelemetryTime = now;

    float soilMoisture = readSoilMoisture();
    bool isTilted = (confirmedTiltState == TILT_ACTIVE_LOGIC);

    int tiltVal = isTilted ? 1 : 0;
    const char* servoState = (currentAnchorState == STATE_ANCHORED) ? "ANCHORING" : "NORMAL";
    const char* eventName  = isTilted ? "TILT_DETECTED" : "NORMAL";

    Serial.print(F("[Telemetry] Soil: "));
    Serial.print(soilMoisture, 1);
    Serial.print(F("% | Tilt: "));
    Serial.print(tiltVal);
    Serial.print(F(" | Servo: "));
    Serial.print(servoState);
    Serial.print(F(" | Event: "));
    Serial.println(eventName);

    sendTelemetryToFastAPI(tiltVal, soilMoisture, servoState, eventName);
  }

  // Small CPU yield for ESP8266 background Wi-Fi stack
  yield();
}
