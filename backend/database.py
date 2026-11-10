import os
from sqlalchemy import create_engine, Column, Integer, Float, String
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

# Absolute path ensures smart_mangrove.db is created inside backend/ folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "smart_mangrove.db")
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, index=True)

    timestamp = Column(
        String,
        default=lambda: datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    rainfall = Column(Float)
    water_level = Column(Float)
    soil_moisture = Column(Float)
    tilt_angle = Column(Float)

    risk_level = Column(String)
    anchor_status = Column(String)


class Reading(Base):
    """
    Phase 4A: SQLite readings table for multi-source telemetry storage.
    Fields:
    - id: Primary Key autoincrement integer
    - timestamp: Datetime string (YYYY-MM-DD HH:MM:SS)
    - source: "SIMULATION" or "HARDWARE"
    - device_id: string (e.g. "ESP8266-001" or "SIMULATOR")
    - event: string (e.g. "NORMAL", "TILT_DETECTED", "ANCHORING_ACTIVATED")
    - tilt_angle: float
    - soil_moisture: float
    - temperature: float
    - humidity: float
    - servo_position: int
    - anchor_status: string
    """
    __tablename__ = "readings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    timestamp = Column(
        String,
        nullable=False,
        default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    source = Column(String, nullable=False, default="SIMULATION")
    device_id = Column(String, nullable=True, default=None)
    event = Column(String, nullable=True, default=None)
    tilt_angle = Column(Float, nullable=False)
    soil_moisture = Column(Float, nullable=False)
    temperature = Column(Float, nullable=False, default=28.5)
    humidity = Column(Float, nullable=False, default=75.0)
    servo_position = Column(Integer, nullable=False, default=0)
    anchor_status = Column(String, nullable=False, default="Normal")


def init_db():
    Base.metadata.create_all(bind=engine)
    # Safe SQLite column migration for device_id and event
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            res = conn.execute(text("PRAGMA table_info(readings)")).fetchall()
            cols = [r[1] for r in res]
            if "device_id" not in cols:
                conn.execute(text("ALTER TABLE readings ADD COLUMN device_id VARCHAR"))
            if "event" not in cols:
                conn.execute(text("ALTER TABLE readings ADD COLUMN event VARCHAR"))
            conn.commit()
    except Exception as e:
        print(f"Database schema initialization notice: {e}")


init_db()