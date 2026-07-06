from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, JSON, Boolean
from app.db.base_class import Base
from datetime import datetime

class Device(Base):
    __tablename__ = "tc_devices"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128))
    uniqueid = Column(String(128), unique=True, index=True)
    status = Column(String(128))
    lastupdate = Column(DateTime)
    positionid = Column(Integer)
    groupid = Column(Integer)
    phone = Column(String(128))
    model = Column(String(128))       # traccar native model field
    contact = Column(String(128))
    category = Column(String(128))
    disabled = Column(Boolean, default=False)
    attributes = Column(JSON)
    # --- VIN Intelligence Columns ---
    vin = Column(String(17), nullable=True)
    vin_source = Column(String(20), nullable=True)  # 'obd' | 'manual'
    manufacturer = Column(String(100), nullable=True)
    year = Column(Integer, nullable=True)
    pid_profile = Column(String(2000), nullable=True)
    profile_status = Column(String(30), nullable=True)

class VinChangeLog(Base):
    __tablename__ = "vin_change_log"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("tc_devices.id"), index=True)
    old_vin = Column(String(17))
    new_vin = Column(String(17))
    changed_at = Column(DateTime, default=datetime.utcnow)
    wipe_executed = Column(Boolean, default=True)

class Position(Base):
    __tablename__ = "tc_positions"
    id = Column(Integer, primary_key=True, index=True)
    protocol = Column(String(128))
    deviceid = Column(Integer, ForeignKey("tc_devices.id"), index=True)
    servertime = Column(DateTime, default=datetime.utcnow)
    devicetime = Column(DateTime)
    fixtime = Column(DateTime)
    valid = Column(Boolean)
    latitude = Column(Float)
    longitude = Column(Float)
    altitude = Column(Float)
    speed = Column(Float) # in knots in Traccar
    course = Column(Float)
    address = Column(String(512))
    attributes = Column(JSON)
    accuracy = Column(Float)
    network = Column(JSON)

class Event(Base):
    __tablename__ = "tc_events"
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(128))
    eventtime = Column(DateTime, default=datetime.utcnow)
    deviceid = Column(Integer, ForeignKey("tc_devices.id"), index=True)
    positionid = Column(Integer, ForeignKey("tc_positions.id"))
    geofenceid = Column(Integer)
    attributes = Column(JSON)
    maintenanceid = Column(Integer)

class Maintenance(Base):
    __tablename__ = "tc_maintenances"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128))
    type = Column(String(128))
    start = Column(Float)
    period = Column(Float)
    attributes = Column(JSON)

class User(Base):
    __tablename__ = "tc_users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128))
    email = Column(String(128), unique=True, index=True)
    hashedpassword = Column(String(128))
    administrator = Column(Boolean, default=False)
    attributes = Column(JSON)

class UserDevice(Base):
    __tablename__ = "tc_user_device"
    userid = Column(Integer, ForeignKey("tc_users.id"), primary_key=True)
    deviceid = Column(Integer, ForeignKey("tc_devices.id"), primary_key=True)

class FuelPrice(Base):
    __tablename__ = "tc_fuel_prices"
    id = Column(Integer, primary_key=True, index=True)
    fuel_type = Column(String(50)) # Petrol, Diesel
    price = Column(Float)
    last_updated = Column(DateTime, default=datetime.utcnow)
    source = Column(String(100)) # OGRA, PSO

class FuelStationVisit(Base):
    __tablename__ = "tc_fuel_station_visits"
    id = Column(Integer, primary_key=True, index=True)
    deviceid = Column(Integer, ForeignKey("tc_devices.id"), index=True)
    station_brand = Column(String(100)) # PSO, Shell, etc.
    station_branch = Column(String(200))
    arrival_time = Column(DateTime)
    departure_time = Column(DateTime)
    duration_minutes = Column(Integer)
    liters_added = Column(Float)
    cost_pkr = Column(Float)
    positionid = Column(Integer, ForeignKey("tc_positions.id"))
    attributes = Column(JSON)

class FleetTrip(Base):
    """
    Placeholder/mock table structure for the trips table expected in production.
    """
    __tablename__ = "fleet_trips"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("tc_devices.id"), index=True)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    distance_km = Column(Float)
    fuel_consumed_l = Column(Float)
    mileage = Column(Float, nullable=True) # km/L

class VehicleSpecsCache(Base):
    __tablename__ = "vehicle_specs_cache"
    id = Column(Integer, primary_key=True, index=True)
    vin = Column(String(17), unique=True, index=True)
    brand = Column(String(100))
    model = Column(String(100))
    year = Column(String(10))
    engine = Column(String(100))
    full_specs = Column(JSON, nullable=True)
    is_pinned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Driver(Base):
    __tablename__ = "tc_drivers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128))
    uniqueid = Column(String(128), unique=True, index=True)
    attributes = Column(JSON)

class DeviceDriver(Base):
    __tablename__ = "tc_device_driver"
    deviceid = Column(Integer, ForeignKey("tc_devices.id"), primary_key=True)
    driverid = Column(Integer, ForeignKey("tc_drivers.id"), primary_key=True)
