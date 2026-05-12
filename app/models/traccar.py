from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, JSON, Boolean
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

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
    model = Column(String(128))
    contact = Column(String(128))
    category = Column(String(128))
    disabled = Column(Boolean, default=False)
    attributes = Column(JSON)

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
    servertime = Column(DateTime, default=datetime.utcnow)
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
