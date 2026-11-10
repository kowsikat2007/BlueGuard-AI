from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from datetime import datetime
import random
import json
import os
from pathlib import Path

from .database import SessionLocal, SensorReading, Reading, init_db


app = FastAPI(
    title="Smart Mangrove System",
    description="IoT-Driven Smart MRV and Blue Carbon Registry System",
    version="1.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ====================================================
# PHASE 3E: HARDWARE / SIMULATION DATA ARCHITECTURE
# ====================================================

HARDWARE_TIMEOUT_SECONDS = 30  # Real ESP8266 heartbeat window

class TelemetryPayload(BaseModel):
    timestamp: Optional[str] = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    source: Literal["HARDWARE", "SIMULATION"] = "SIMULATION"
    tilt_angle: float
    soil_moisture: float
    temperature: float
    humidity: float
    servo_position: int = 0
    anchor_status: str = "Normal"


class HardwareTelemetryPayload(BaseModel):
    """
    Ingest payload for physical ESP8266 hardware.
    Supports both discrete tilt flags (0/1) and continuous angular readings (deg),
    as well as soil moisture, local servo states, and event notifications.
    """
    device_id: Optional[str] = "ESP8266-001"
    source: Optional[str] = "HARDWARE"
    tilt: Optional[float] = None          # 0 (normal), 1 (tilted), or degrees
    tilt_angle: Optional[float] = None    # degrees
    soil_moisture: float                  # 0 to 100 %
    servo_state: Optional[str] = None     # "NORMAL", "ANCHORING", "ACTIVE"
    servo_position: Optional[int] = None  # 0 to 180 degrees
    anchor_status: Optional[str] = None   # "Normal", "Anchoring", "Active"
    event: Optional[str] = None           # "TILT_DETECTED", "NORMAL", etc.
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    timestamp: Optional[str] = None

    @field_validator("soil_moisture")
    @classmethod
    def validate_moisture(cls, v):
        if v is None:
            raise ValueError("soil_moisture is required")
        if v < 0.0 or v > 100.0:
            raise ValueError("soil_moisture must be between 0.0 and 100.0 percent")
        return round(float(v), 1)

    @field_validator("tilt", "tilt_angle")
    @classmethod
    def validate_tilt_bounds(cls, v):
        if v is not None and (v < -180.0 or v > 180.0):
            raise ValueError("tilt value out of realistic angular bounds (-180 to 180)")
        return v


# Hardware connection state tracking
hardware_state = {
    "real_connected": False,
    "real_last_heartbeat": None,
    "real_latest_reading": None,
    "is_test_mode": False,
    "test_last_heartbeat": None,
    "test_latest_reading": None,
    "device_id": None
}


def check_and_update_hardware_timeout():
    """Evaluate heartbeat timeouts for real ESP8266 and test mock."""
    now = datetime.now()
    if hardware_state["real_connected"] and hardware_state["real_last_heartbeat"]:
        elapsed = (now - hardware_state["real_last_heartbeat"]).total_seconds()
        if elapsed > HARDWARE_TIMEOUT_SECONDS:
            hardware_state["real_connected"] = False

    if hardware_state["is_test_mode"] and hardware_state["test_last_heartbeat"]:
        elapsed = (now - hardware_state["test_last_heartbeat"]).total_seconds()
        if elapsed > 60:
            hardware_state["is_test_mode"] = False


@app.get("/api/telemetry")
def get_telemetry():
    """
    Unified Data Architecture endpoint returning telemetry fields.
    Prioritizes real ESP8266 telemetry when connected.
    """
    check_and_update_hardware_timeout()

    if hardware_state["real_connected"] and hardware_state["real_latest_reading"]:
        reading = dict(hardware_state["real_latest_reading"])
        reading["connected"] = True
        reading["is_real_hardware"] = True
        reading["source"] = "HARDWARE"
        reading["data_source_label"] = "REAL HARDWARE"
        return reading

    if hardware_state["is_test_mode"] and hardware_state["test_latest_reading"]:
        reading = dict(hardware_state["test_latest_reading"])
        reading["connected"] = True
        reading["is_real_hardware"] = False
        reading["source"] = "HARDWARE"
        reading["data_source_label"] = "TEST CONNECTION"
        return reading

    # When hardware is not connected, report disconnected state without fake data
    return {
        "connected": False,
        "is_real_hardware": False,
        "source": "NONE",
        "data_source_label": "SIMULATION",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "message": "Hardware Not Connected"
    }


@app.get("/api/hardware/status")
def get_hardware_status():
    """
    Check current hardware connection state and active telemetry source.
    Distinguishes REAL HARDWARE from TEST CONNECTION and SIMULATION.
    """
    check_and_update_hardware_timeout()
    is_real = bool(hardware_state["real_connected"])
    is_test = bool(hardware_state["is_test_mode"])
    is_connected = is_real or is_test

    connection_type = "REAL_HARDWARE" if is_real else ("TEST_MOCK" if is_test else "NONE")
    data_source_label = "REAL HARDWARE" if is_real else ("TEST CONNECTION" if is_test else "SIMULATION")
    device_id = hardware_state["device_id"] if is_real else ("TEST-DEVICE-01" if is_test else None)
    last_hb = hardware_state["real_last_heartbeat"] if is_real else (hardware_state["test_last_heartbeat"] if is_test else None)

    return {
        "connected": is_connected,
        "is_real_hardware": is_real,
        "is_test_mode": is_test,
        "connection_type": connection_type,
        "source": "HARDWARE" if is_connected else "NONE",
        "data_source_label": data_source_label,
        "device_id": device_id,
        "last_heartbeat": last_hb.strftime("%Y-%m-%d %H:%M:%S") if last_hb else None,
        "timeout_seconds": HARDWARE_TIMEOUT_SECONDS
    }


@app.post("/api/hardware/data")
def receive_hardware_data(payload: HardwareTelemetryPayload):
    """
    Ingest endpoint for real ESP8266 hardware telemetry over Wi-Fi.
    Enforces source='HARDWARE', performs validation,
    updates automatic hardware detection state, and stores readings in SQLite.
    """
    # 1. Validate tilt inputs: must have either tilt or tilt_angle
    if payload.tilt is None and payload.tilt_angle is None:
        raise HTTPException(
            status_code=422,
            detail="Hardware reading must specify either 'tilt' (0/1 or deg) or 'tilt_angle' (deg)."
        )

    # Determine tilt detection and angular representation
    if payload.tilt_angle is not None:
        tilt_angle_val = float(payload.tilt_angle)
        is_tilted = (tilt_angle_val > 15.0) or (payload.tilt is not None and bool(payload.tilt))
        tilt_flag = 1 if is_tilted else 0
    else:
        tilt_raw = float(payload.tilt)
        if tilt_raw > 1.0:
            tilt_angle_val = tilt_raw
            is_tilted = tilt_angle_val > 15.0
            tilt_flag = 1 if is_tilted else 0
        else:
            is_tilted = bool(tilt_raw == 1.0)
            tilt_angle_val = 20.0 if is_tilted else 0.0
            tilt_flag = 1 if is_tilted else 0

    # 2. Determine servo position & anchor status
    servo_state_raw = (payload.servo_state or payload.anchor_status or "").strip().upper()
    is_anchoring = (
        servo_state_raw in ("ANCHORING", "ACTIVE", "DEPLOYED", "ANCHORING ACTIVATED")
        or is_tilted
    )

    norm_anchor_status = "ANCHORING" if is_anchoring else "NORMAL"
    servo_pos = payload.servo_position
    if servo_pos is None:
        servo_pos = 90 if is_anchoring else 0

    # 3. Determine event label
    if payload.event and str(payload.event).strip():
        event_name = str(payload.event).strip().upper()
    elif is_tilted or is_anchoring:
        event_name = "TILT_DETECTED"
    else:
        event_name = "NORMAL"

    # 4. Device ID & Timestamp
    device_id = (payload.device_id or "ESP8266-001").strip()
    ts = payload.timestamp
    if not ts or not str(ts).strip():
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 5. Temperature and Humidity baseline
    temp_val = float(payload.temperature) if payload.temperature is not None else 28.5
    hum_val = float(payload.humidity) if payload.humidity is not None else 75.0
    moisture_val = round(float(payload.soil_moisture), 1)

    # 6. Update Real Hardware Detection State
    now = datetime.now()
    hardware_state["real_connected"] = True
    hardware_state["real_last_heartbeat"] = now
    hardware_state["device_id"] = device_id
    hardware_state["is_test_mode"] = False  # Real communication supersedes test mode

    telemetry_record = {
        "device_id": device_id,
        "source": "HARDWARE",
        "tilt": tilt_flag,
        "tilt_angle": tilt_angle_val,
        "soil_moisture": moisture_val,
        "temperature": temp_val,
        "humidity": hum_val,
        "servo_state": norm_anchor_status,
        "servo_position": servo_pos,
        "anchor_status": norm_anchor_status,
        "event": event_name,
        "timestamp": ts
    }
    hardware_state["real_latest_reading"] = telemetry_record

    # 7. Persist to SQLite Database
    db: Session = SessionLocal()
    try:
        new_record = Reading(
            timestamp=ts,
            device_id=device_id,
            source="HARDWARE",
            tilt_angle=tilt_angle_val,
            soil_moisture=moisture_val,
            temperature=temp_val,
            humidity=hum_val,
            servo_position=servo_pos,
            anchor_status=norm_anchor_status,
            event=event_name
        )
        db.add(new_record)
        db.commit()
        db.refresh(new_record)
        record_id = new_record.id
    finally:
        db.close()

    return {
        "status": "success",
        "message": f"Real hardware telemetry received from {device_id}",
        "source": "HARDWARE",
        "device_id": device_id,
        "record_id": record_id,
        "timestamp": ts,
        "event": event_name,
        "tilt": tilt_flag,
        "soil_moisture": moisture_val,
        "servo_state": norm_anchor_status
    }


@app.post("/api/hardware/test-connect")
def test_hardware_connect():
    """
    Developer route to test authentic HARDWARE mode transition without physical wires.
    Sets is_test_mode = True and provides valid test hardware telemetry.
    Strictly separated from real physical ESP8266 connection.
    """
    data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "device_id": "TEST-DEVICE-01",
        "source": "HARDWARE",
        "tilt": 0,
        "tilt_angle": 3.8,
        "soil_moisture": 64.0,
        "temperature": 28.9,
        "humidity": 76.0,
        "servo_position": 0,
        "anchor_status": "Normal",
        "event": "NORMAL"
    }
    hardware_state["is_test_mode"] = True
    hardware_state["test_last_heartbeat"] = datetime.now()
    hardware_state["test_latest_reading"] = data

    db: Session = SessionLocal()
    try:
        new_record = Reading(
            timestamp=data["timestamp"],
            device_id=data["device_id"],
            source="HARDWARE",
            tilt_angle=data["tilt_angle"],
            soil_moisture=data["soil_moisture"],
            temperature=data["temperature"],
            humidity=data["humidity"],
            servo_position=data["servo_position"],
            anchor_status=data["anchor_status"],
            event=data["event"]
        )
        db.add(new_record)
        db.commit()
    finally:
        db.close()

    return {
        "status": "ok",
        "source": "HARDWARE",
        "is_test_mode": True,
        "connection_type": "TEST_MOCK",
        "data": data
    }


@app.post("/api/hardware/test-disconnect")
def test_hardware_disconnect():
    """
    Developer route to test disconnection and automatic return to SIMULATION mode.
    """
    hardware_state["is_test_mode"] = False
    hardware_state["test_last_heartbeat"] = None
    hardware_state["test_latest_reading"] = None
    return {"status": "ok", "source": "SIMULATION", "is_test_mode": False}


# ====================================================
# PHASE 4A: DATABASE SETUP & SENSOR READINGS PIPELINE
# ====================================================

@app.on_event("startup")
def on_startup():
    """Ensure SQLite database tables are created on startup."""
    init_db()


class ReadingInput(BaseModel):
    timestamp: Optional[str] = None
    device_id: Optional[str] = None
    source: Optional[Literal["SIMULATION", "HARDWARE"]] = "SIMULATION"
    tilt_angle: float
    soil_moisture: float
    temperature: Optional[float] = 28.5
    humidity: Optional[float] = 75.0
    servo_position: Optional[int] = 0
    anchor_status: Optional[str] = "Normal"
    event: Optional[str] = None

    @field_validator("source", mode="before")
    @classmethod
    def validate_source(cls, v):
        if v is None or (isinstance(v, str) and not v.strip()):
            return "SIMULATION"
        upper_v = str(v).strip().upper()
        if upper_v not in ("SIMULATION", "HARDWARE"):
            raise ValueError("source must be either 'SIMULATION' or 'HARDWARE'")
        return upper_v


@app.get("/api/readings")
def get_readings(limit: Optional[int] = 200, source: Optional[str] = None):
    """
    Phase 4A/4C: Return stored readings from SQLite database.
    Ordered by latest ID descending.
    Supports optional source filtering ("SIMULATION" or "HARDWARE") and limit.
    """
    db: Session = SessionLocal()
    try:
        query = db.query(Reading).order_by(Reading.id.desc())
        if source and source.strip().upper() in ("SIMULATION", "HARDWARE"):
            query = query.filter(Reading.source == source.strip().upper())
        if limit and limit > 0:
            query = query.limit(limit)
        records = query.all()
        return [
            {
                "id": r.id,
                "timestamp": r.timestamp,
                "device_id": r.device_id or ("ESP8266-001" if r.source == "HARDWARE" else "SIMULATOR"),
                "source": r.source,
                "tilt_angle": r.tilt_angle,
                "soil_moisture": r.soil_moisture,
                "temperature": r.temperature,
                "humidity": r.humidity,
                "servo_position": r.servo_position,
                "anchor_status": r.anchor_status,
                "event": r.event or ("NORMAL" if (r.anchor_status or "").strip().upper() in ("NORMAL", "STANDBY") else "TILT_DETECTED"),
            }
            for r in records
        ]
    finally:
        db.close()


@app.post("/api/readings", status_code=201)
def create_reading(payload: ReadingInput):
    """
    Phase 4A: Accept a new reading and store it in SQLite.
    The source field must strictly represent 'SIMULATION' or 'HARDWARE'.
    """
    ts = payload.timestamp
    if not ts or not str(ts).strip():
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    source_val = payload.source or "SIMULATION"
    dev_id = payload.device_id or ("SIMULATOR" if source_val == "SIMULATION" else "ESP8266-001")
    event_val = payload.event or ("NORMAL" if (payload.anchor_status or "Normal").strip().upper() in ("NORMAL", "STANDBY") else "TILT_DETECTED")

    db: Session = SessionLocal()
    try:
        new_record = Reading(
            timestamp=ts,
            device_id=dev_id,
            source=source_val,
            tilt_angle=payload.tilt_angle,
            soil_moisture=payload.soil_moisture,
            temperature=payload.temperature if payload.temperature is not None else 28.5,
            humidity=payload.humidity if payload.humidity is not None else 75.0,
            servo_position=payload.servo_position if payload.servo_position is not None else 0,
            anchor_status=payload.anchor_status or "Normal",
            event=event_val,
        )
        db.add(new_record)
        db.commit()
        db.refresh(new_record)

        return {
            "id": new_record.id,
            "timestamp": new_record.timestamp,
            "device_id": new_record.device_id,
            "source": new_record.source,
            "tilt_angle": new_record.tilt_angle,
            "soil_moisture": new_record.soil_moisture,
            "temperature": new_record.temperature,
            "humidity": new_record.humidity,
            "servo_position": new_record.servo_position,
            "anchor_status": new_record.anchor_status,
            "event": new_record.event,
        }
    finally:
        db.close()


@app.get("/api/readings/latest")
def get_latest_reading(source: Optional[str] = None):
    """
    Phase 4A/Phase 5: Return the latest stored reading from SQLite database.
    Optionally filter by source ("HARDWARE" or "SIMULATION").
    """
    db: Session = SessionLocal()
    try:
        query = db.query(Reading)
        if source and source.strip().upper() in ("SIMULATION", "HARDWARE"):
            query = query.filter(Reading.source == source.strip().upper())
        record = query.order_by(Reading.id.desc()).first()
        if not record:
            raise HTTPException(status_code=404, detail="No readings found in database")
        return {
            "id": record.id,
            "timestamp": record.timestamp,
            "device_id": record.device_id or ("ESP8266-001" if record.source == "HARDWARE" else "SIMULATOR"),
            "source": record.source,
            "tilt_angle": record.tilt_angle,
            "soil_moisture": record.soil_moisture,
            "temperature": record.temperature,
            "humidity": record.humidity,
            "servo_position": record.servo_position,
            "anchor_status": record.anchor_status,
            "event": record.event or ("NORMAL" if (record.anchor_status or "").strip().upper() in ("NORMAL", "STANDBY") else "TILT_DETECTED"),
        }
    finally:
        db.close()


# ====================================================
# PHASE 6.2: OFFICIAL ENVIRONMENTAL DATA ENDPOINT
# ====================================================

ENV_DATA_FILE = Path(__file__).resolve().parent / "data" / "environmental_data.json"


@app.get("/api/environmental-data")
def get_environmental_data():
    """
    Phase 6.2: Return official reference environmental dataset for Pichavaram, Cuddalore.
    Strictly isolated from SIMULATION IoT data and future HARDWARE IoT data.
    """
    if ENV_DATA_FILE.exists():
        try:
            with open(ENV_DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error reading environmental dataset: {str(e)}")

    # Fallback to verified official baseline if file cannot be read
    return {
        "location": "Pichavaram, Cuddalore, Tamil Nadu",
        "data_source": "OFFICIAL_DATA",
        "data_source_label": "OFFICIAL ENVIRONMENTAL DATA",
        "data_type": "ENVIRONMENTAL",
        "wetland_type": "Estuarine Mangrove Wetland (Ramsar Site No. 2475)",
        "area_ha": 1478.6,
        "latitude": 11.428,
        "longitude": 79.782,
        "rainfall_mm": 1310.0,
        "salinity_ppt": 21.5,
        "water_ph": 7.9
    }


FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if not FRONTEND_DIR.exists():
    FRONTEND_DIR = Path(__file__).resolve().parent.parent / "Frontend"


@app.get("/")
def home(request: Request):
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        login_file = FRONTEND_DIR / "login.html"
        if login_file.exists():
            return FileResponse(str(login_file))
        index_file = FRONTEND_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))

    return {
        "message": "Smart Mangrove Backend is Running",
        "status": "connected"
    }


@app.get("/status")
def get_status():

    return {
        "system": "Smart Mangrove Monitoring System",
        "status": "online"
    }


@app.get("/api/status")
def system_status():

    return {
        "water_level": "Normal",
        "rainfall": "Monitoring",
        "mangrove_status": "Healthy",
        "anchor_status": "Standby"
    }


@app.get("/api/sensors")
def sensor_data():

    # Simulated sensor readings

    rainfall = round(
        random.uniform(5, 80), 1
    )

    water_level = round(
        random.uniform(0.8, 3.5), 2
    )

    soil_moisture = round(
        random.uniform(40, 90), 1
    )

    tilt_angle = round(
        random.uniform(0, 25), 1
    )


    # Risk calculation

    risk_score = 0

    if rainfall > 50:
        risk_score += 1

    if water_level > 2.5:
        risk_score += 1

    if soil_moisture > 80:
        risk_score += 1

    if tilt_angle > 15:
        risk_score += 2


    # Risk decision

    if risk_score >= 3:

        risk_level = "HIGH"
        anchor_status = "DEPLOYED"

        alert_message = (
            "High risk detected. "
            "Anchor mechanism activated."
        )

    elif risk_score >= 1:

        risk_level = "WARNING"
        anchor_status = "READY"

        alert_message = (
            "Environmental conditions "
            "require monitoring."
        )

    else:

        risk_level = "LOW"
        anchor_status = "STANDBY"

        alert_message = (
            "Environmental conditions "
            "are stable."
        )


    # Save reading to database

    db: Session = SessionLocal()

    reading = SensorReading(

        rainfall=rainfall,

        water_level=water_level,

        soil_moisture=soil_moisture,

        tilt_angle=tilt_angle,

        risk_level=risk_level,

        anchor_status=anchor_status
    )

    db.add(reading)

    db.commit()

    db.close()


    return {

        "rainfall": rainfall,

        "water_level": water_level,

        "soil_moisture": soil_moisture,

        "tilt_angle": tilt_angle,

        "risk_level": risk_level,

        "anchor_status": anchor_status,

        "alert": alert_message
    }


@app.get("/api/history")
def sensor_history():

    db: Session = SessionLocal()

    readings = (
        db.query(SensorReading)
        .order_by(SensorReading.id.desc())
        .limit(50)
        .all()
    )

    db.close()


    return [

        {
            "id": reading.id,

            "timestamp": reading.timestamp,

            "rainfall": reading.rainfall,

            "water_level": reading.water_level,

            "soil_moisture": reading.soil_moisture,

            "tilt_angle": reading.tilt_angle,

            "risk_level": reading.risk_level,

            "anchor_status": reading.anchor_status
        }

        for reading in readings
    ]


# ====================================================
# SERVE FRONTEND STATIC FILES DIRECTLY THROUGH FASTAPI
# ====================================================

if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")