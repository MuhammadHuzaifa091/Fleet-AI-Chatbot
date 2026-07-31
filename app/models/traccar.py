from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, JSON, Boolean, Text, BigInteger
from sqlalchemy.orm import relationship
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


# ============================================================
# MAINTENANCE MODULE MODELS
# ============================================================

class MaintenanceSchedule(Base):
    """Maintenance schedule definitions - linked to Traccar's tc_maintenances"""
    __tablename__ = "maintenance_schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    traccar_maintenance_id = Column(Integer, unique=True, index=True)  # Links to tc_maintenances.id
    name = Column(String(128), nullable=False)
    type = Column(String(50), nullable=False)  # 'totalDistance', 'engineHours', 'time'
    start_value = Column(Float, default=0)
    period = Column(Float, nullable=False)  # km, hours, or days
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class VehicleMaintenance(Base):
    """Tracks maintenance status per vehicle per schedule"""
    __tablename__ = "vehicle_maintenance"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("tc_devices.id"), index=True, nullable=False)
    schedule_id = Column(Integer, ForeignKey("maintenance_schedules.id"), index=True, nullable=False)
    
    # Current status
    last_service_value = Column(Float, default=0)  # odometer/hours at last service
    last_service_date = Column(DateTime, nullable=True)
    next_due_value = Column(Float, nullable=False)  # odometer/hours when next due
    next_due_date = Column(DateTime, nullable=True)  # estimated date based on usage
    
    # Status
    status = Column(String(20), default="healthy")  # healthy, due_soon, due, overdue, critical
    km_overdue = Column(Float, default=0)
    days_overdue = Column(Integer, default=0)
    
    # Workshop assignment
    assigned_workshop_id = Column(Integer, ForeignKey("workshops.id"), nullable=True)
    assigned_technician = Column(String(128), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    device = relationship("Device", backref="maintenance_records")
    schedule = relationship("MaintenanceSchedule", backref="vehicle_records")
    workshop = relationship("Workshop", backref="assigned_maintenance")


class MaintenanceLog(Base):
    """History of completed maintenance"""
    __tablename__ = "maintenance_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("tc_devices.id"), index=True, nullable=False)
    schedule_id = Column(Integer, ForeignKey("maintenance_schedules.id"), index=True, nullable=False)
    vehicle_maintenance_id = Column(Integer, ForeignKey("vehicle_maintenance.id"), index=True, nullable=True)
    
    # Service details
    service_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    service_value = Column(Float, nullable=False)  # odometer/hours at service
    service_type = Column(String(50), nullable=False)  # scheduled, unscheduled, repair
    
    # Workshop details
    workshop_id = Column(Integer, ForeignKey("workshops.id"), nullable=True)
    technician = Column(String(128), nullable=True)
    cost = Column(Float, default=0)
    currency = Column(String(3), default="PKR")
    
    # Notes and parts
    notes = Column(Text, nullable=True)
    parts_replaced = Column(JSON, nullable=True)  # [{"part": "Oil Filter", "qty": 1, "cost": 500}]
    
    # Odometer validation
    previous_odometer = Column(Float, nullable=True)
    odometer_difference = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("tc_users.id"), nullable=True)
    
    # Relationships
    device = relationship("Device", backref="maintenance_logs")
    schedule = relationship("MaintenanceSchedule", backref="logs")
    workshop = relationship("Workshop", backref="maintenance_logs")


class Workshop(Base):
    """Workshop/Service center management"""
    __tablename__ = "workshops"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    code = Column(String(20), unique=True, index=True, nullable=False)
    address = Column(String(256), nullable=True)
    city = Column(String(64), nullable=True)
    phone = Column(String(32), nullable=True)
    email = Column(String(128), nullable=True)
    contact_person = Column(String(128), nullable=True)
    is_active = Column(Boolean, default=True)
    capabilities = Column(JSON, nullable=True)  # ["oil_change", "brake_service", "tire_rotation", ...]
    rating = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MaintenanceAlert(Base):
    """Alerts for upcoming/overdue maintenance"""
    __tablename__ = "maintenance_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("tc_devices.id"), index=True, nullable=False)
    schedule_id = Column(Integer, ForeignKey("maintenance_schedules.id"), index=True, nullable=False)
    vehicle_maintenance_id = Column(Integer, ForeignKey("vehicle_maintenance.id"), index=True, nullable=True)
    
    alert_type = Column(String(20), nullable=False)  # due_soon, due, overdue, critical
    message = Column(Text, nullable=False)
    priority = Column(Integer, default=1)  # 1=low, 2=medium, 3=high, 4=critical
    
    is_read = Column(Boolean, default=False)
    is_dismissed = Column(Boolean, default=False)
    acknowledged_by = Column(Integer, ForeignKey("tc_users.id"), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    device = relationship("Device", backref="maintenance_alerts")
    schedule = relationship("MaintenanceSchedule", backref="alerts")


# ============================================================
# MAINTENANCE PLANNER & RULE ENGINE MODELS
# ============================================================

class MaintenanceType(Base):
    """Master maintenance type definitions"""
    __tablename__ = "maintenance_types"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False, unique=True, index=True)
    slug = Column(String(128), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(64), nullable=True)
    color = Column(String(7), default="#3b82f6")
    category = Column(String(50), nullable=True)
    default_interval_km = Column(Float, nullable=False, default=5000)
    default_interval_days = Column(Integer, nullable=False, default=180)
    default_interval_hours = Column(Float, nullable=True)
    default_engine_hours = Column(Float, nullable=True)
    priority = Column(String(20), default='medium')
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)
    is_system = Column(Boolean, default=False)
    created_by = Column(Integer, ForeignKey("tc_users.id"), nullable=True)
    updated_by = Column(Integer, ForeignKey("tc_users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "icon": self.icon,
            "color": self.color,
            "category": self.category,
            "default_interval_km": self.default_interval_km,
            "default_interval_days": self.default_interval_days,
            "default_interval_hours": self.default_interval_hours,
            "default_engine_hours": self.default_engine_hours,
            "priority": self.priority,
            "is_active": self.is_active,
            "is_deleted": self.is_deleted,
            "is_system": self.is_system,
            "created_by": self.created_by,
            "updated_by": self.updated_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class MaintenanceRule(Base):
    """Configurable maintenance rules per type"""
    __tablename__ = "maintenance_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    type_id = Column(Integer, ForeignKey("maintenance_types.id"), index=True, nullable=False)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    
    # Trigger methods
    trigger_km = Column(Float, nullable=True)  # distance-based trigger
    trigger_days = Column(Integer, nullable=True)  # time-based trigger
    trigger_hours = Column(Float, nullable=True)  # engine hours-based trigger
    trigger_manual = Column(Boolean, default=False)  # manual trigger only
    
    # Grace periods
    grace_km = Column(Float, default=0)
    grace_days = Column(Integer, default=0)
    
    # Priority and order
    priority = Column(String(20), default="medium")  # low, medium, high, critical
    rule_order = Column(Integer, default=0)
    
    # Validation
    min_interval_km = Column(Float, nullable=True)
    max_interval_km = Column(Float, nullable=True)
    min_interval_days = Column(Integer, nullable=True)
    max_interval_days = Column(Integer, nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("tc_users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    type = relationship("MaintenanceType", foreign_keys=[type_id], lazy="selectin")


class MaintenanceTemplate(Base):
    """Reusable maintenance templates"""
    __tablename__ = "maintenance_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    slug = Column(String(128), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    vehicle_type = Column(String(50), nullable=True)  # truck, bus, car, generator, etc.
    vehicle_category = Column(String(50), nullable=True)
    manufacturer = Column(String(128), nullable=True)
    model = Column(String(128), nullable=True)
    year_from = Column(Integer, nullable=True)
    year_to = Column(Integer, nullable=True)
    estimated_service_cost = Column(Float, nullable=True)
    estimated_annual_maint = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)
    is_archived = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    is_system = Column(Boolean, default=False)
    created_by = Column(Integer, ForeignKey("tc_users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships for selectinload
    template_rules = relationship("TemplateRuleLink", back_populates="template", lazy="selectin")
    plans = relationship("VehicleMaintenancePlan", back_populates="template", lazy="selectin")


class TemplateRuleLink(Base):
    """Links rules to templates with optional overrides"""
    __tablename__ = "template_rule_links"
    
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("maintenance_templates.id"), index=True, nullable=False)
    rule_id = Column(Integer, ForeignKey("maintenance_rules.id"), index=True, nullable=False)
    
    # Override values for this template
    override_km = Column(Float, nullable=True)
    override_days = Column(Integer, nullable=True)
    override_hours = Column(Float, nullable=True)
    override_priority = Column(String(20), nullable=True)
    
    execution_order = Column(Integer, default=0)
    is_enabled = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("tc_users.id"), nullable=True)

    # Relationships
    template = relationship("MaintenanceTemplate", back_populates="template_rules")
    rule = relationship("MaintenanceRule", lazy="selectin")


class VehicleMaintenancePlan(Base):
    """Per-vehicle maintenance plan"""
    __tablename__ = "vehicle_maintenance_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("tc_devices.id"), index=True, nullable=False)
    template_id = Column(Integer, ForeignKey("maintenance_templates.id"), index=True, nullable=True)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    assigned_by = Column(Integer, ForeignKey("tc_users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    template = relationship("MaintenanceTemplate", back_populates="plans", lazy="selectin")


class VehiclePlanRuleOverride(Base):
    """Individual rule overrides for a vehicle plan"""
    __tablename__ = "vehicle_plan_rule_overrides"
    
    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("vehicle_maintenance_plans.id"), index=True, nullable=False)
    rule_id = Column(Integer, ForeignKey("maintenance_rules.id"), index=True, nullable=False)
    type_id = Column(Integer, ForeignKey("maintenance_types.id"), index=True, nullable=False)
    
    # Override values (null means use rule default)
    override_km = Column(Float, nullable=True)
    override_days = Column(Integer, nullable=True)
    override_hours = Column(Float, nullable=True)
    override_priority = Column(String(20), nullable=True)
    
    is_enabled = Column(Boolean, default=True)
    reason = Column(Text, nullable=True)  # why this override exists
    created_by = Column(Integer, ForeignKey("tc_users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    rule = relationship("MaintenanceRule", lazy="selectin")
    type = relationship("MaintenanceType", lazy="selectin")


class RuleHistory(Base):
    """Audit trail for rule changes"""
    __tablename__ = "rule_history"
    
    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("maintenance_rules.id"), index=True, nullable=True)
    type_id = Column(Integer, ForeignKey("maintenance_types.id"), index=True, nullable=True)
    template_id = Column(Integer, ForeignKey("maintenance_templates.id"), index=True, nullable=True)
    plan_id = Column(Integer, ForeignKey("vehicle_maintenance_plans.id"), index=True, nullable=True)
    
    field_name = Column(String(128), nullable=False)
    old_value = Column(String(500), nullable=True)
    new_value = Column(String(500), nullable=True)
    
    changed_by = Column(Integer, ForeignKey("tc_users.id"), nullable=True)
    reason = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# WORKSHOP MANAGEMENT MODELS
# ============================================================

class Technician(Base):
    """Workshop technician management"""
    __tablename__ = "technicians"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    employee_id = Column(String(50), unique=True, index=True, nullable=False)
    phone = Column(String(32), nullable=True)
    email = Column(String(128), nullable=True)
    skills = Column(JSON, nullable=True)  # ["oil_change", "brake_service", "electrical", ...]
    status = Column(String(20), default="available")  # available, busy, off_duty
    max_workload = Column(Integer, default=3)  # max concurrent active jobs
    workshop_id = Column(Integer, ForeignKey("workshops.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    workshop = relationship("Workshop", backref="technicians")


class WorkshopJob(Base):
    """Workshop maintenance job tracking"""
    __tablename__ = "workshop_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_number = Column(String(30), unique=True, index=True, nullable=False)
    
    # Vehicle and maintenance reference
    device_id = Column(Integer, ForeignKey("tc_devices.id"), index=True, nullable=False)
    template_id = Column(Integer, ForeignKey("maintenance_templates.id"), nullable=True)
    type_id = Column(Integer, ForeignKey("maintenance_types.id"), nullable=True)
    plan_id = Column(Integer, ForeignKey("vehicle_maintenance_plans.id"), nullable=True)
    
    # Job details
    title = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String(20), default="medium")  # low, medium, high, critical
    status = Column(String(20), default="pending")  # pending, assigned, vehicle_arrived, inspection, in_progress, waiting_parts, paused, quality_check, approved, completed, cancelled
    
    # Assignment
    technician_id = Column(Integer, ForeignKey("technicians.id"), nullable=True)
    workshop_id = Column(Integer, ForeignKey("workshops.id"), nullable=True)
    
    # Odometer and timing
    current_odometer = Column(Float, nullable=True)
    due_reason = Column(Text, nullable=True)  # why this job was created
    created_date = Column(DateTime, default=datetime.utcnow)
    started_date = Column(DateTime, nullable=True)
    completed_date = Column(DateTime, nullable=True)
    due_date = Column(DateTime, nullable=True)
    
    # Cost tracking
    estimated_cost = Column(Float, nullable=True)
    actual_cost = Column(Float, default=0)
    labour_hours = Column(Float, default=0)
    labour_cost = Column(Float, default=0)
    parts_cost = Column(Float, default=0)
    misc_cost = Column(Float, default=0)
    total_cost = Column(Float, default=0)
    
    # Parts and notes
    parts_used = Column(JSON, nullable=True)  # [{"part": "Oil Filter", "qty": 1, "cost": 500}]
    notes = Column(Text, nullable=True)
    internal_notes = Column(Text, nullable=True)
    
    # Quality check
    quality_check_passed = Column(Boolean, nullable=True)
    quality_check_notes = Column(Text, nullable=True)
    quality_checked_by = Column(String(128), nullable=True)
    quality_check_date = Column(DateTime, nullable=True)
    quality_checklist = Column(JSON, nullable=True)  # [{item, passed, remarks}]
    
    # Approval
    approved = Column(Boolean, default=False)
    approved_by = Column(String(128), nullable=True)
    approved_date = Column(DateTime, nullable=True)
    
    # Additional dates
    vehicle_arrived_date = Column(DateTime, nullable=True)
    inspection_date = Column(DateTime, nullable=True)
    paused_date = Column(DateTime, nullable=True)
    resumed_date = Column(DateTime, nullable=True)
    
    # Completion
    maintenance_log_id = Column(Integer, ForeignKey("maintenance_logs.id"), nullable=True)
    next_due_km = Column(Float, nullable=True)
    next_due_date = Column(DateTime, nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("tc_users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    device = relationship("Device", backref="workshop_jobs")
    template = relationship("MaintenanceTemplate", lazy="selectin")
    type = relationship("MaintenanceType", lazy="selectin")
    technician = relationship("Technician", backref="jobs", lazy="selectin")
    workshop_rel = relationship("Workshop", backref="workshop_jobs", foreign_keys=[workshop_id])
    plan = relationship("VehicleMaintenancePlan", lazy="selectin")
    maintenance_log = relationship("MaintenanceLog", backref="workshop_job", uselist=False)


class JobNote(Base):
    """Job notes and timeline events"""
    __tablename__ = "job_notes"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("workshop_jobs.id"), index=True, nullable=False)
    note_type = Column(String(20), default="note")  # note, status_change, assignment, quality_check, timeline
    content = Column(Text, nullable=False)
    author = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("WorkshopJob", backref="job_notes")


class WorkshopAttachment(Base):
    """File attachments for workshop jobs"""
    __tablename__ = "workshop_attachments"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("workshop_jobs.id"), index=True, nullable=False)
    filename = Column(String(256), nullable=False)
    original_name = Column(String(256), nullable=False)
    file_type = Column(String(50), nullable=True)  # before_photo, after_photo, invoice, receipt, document
    file_size = Column(BigInteger, nullable=True)
    mime_type = Column(String(100), nullable=True)
    uploaded_by = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    job = relationship("WorkshopJob", backref="attachments")


# ============================================================
# INVENTORY & SPARE PARTS MODELS
# ============================================================

class SparePart(Base):
    """Spare parts inventory master"""
    __tablename__ = "spare_parts"
    
    id = Column(Integer, primary_key=True, index=True)
    part_number = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)  # engine, brakes, electrical, filters, fluids, body, tyres, tools, other
    brand = Column(String(100), nullable=True)
    compatible_vehicle_category = Column(String(100), nullable=True)  # truck, bus, car, generator, all
    unit = Column(String(30), default="pcs")  # pcs, litres, kg, metres, sets
    
    # Stock levels
    current_quantity = Column(Float, default=0)
    minimum_stock = Column(Float, default=0)
    maximum_stock = Column(Float, default=100)
    
    # Costing (PKR)
    unit_cost = Column(Float, default=0)
    
    # Storage
    storage_location = Column(String(256), nullable=True)  # Warehouse A, Shelf B3, etc.
    supplier = Column(String(256), nullable=True)
    supplier_contact = Column(String(128), nullable=True)
    
    # Status
    status = Column(String(20), default="active")  # active, discontinued, expired
    expiry_date = Column(DateTime, nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class StockMovement(Base):
    """Inventory stock movement history"""
    __tablename__ = "stock_movements"
    
    id = Column(Integer, primary_key=True, index=True)
    spare_part_id = Column(Integer, ForeignKey("spare_parts.id"), index=True, nullable=False)
    
    # Movement details
    movement_type = Column(String(20), nullable=False)  # stock_in, stock_out, adjustment, transfer, return, scrap
    quantity = Column(Float, nullable=False)  # positive for in, negative for out
    reference_type = Column(String(30), nullable=True)  # workshop_job, purchase, manual, transfer
    reference_id = Column(Integer, nullable=True)  # job_id, purchase_order_id, etc.
    reference_number = Column(String(50), nullable=True)  # job_number, PO number, etc.
    
    # Cost at time of movement
    unit_cost = Column(Float, default=0)
    total_cost = Column(Float, default=0)
    
    # Stock after movement
    stock_before = Column(Float, default=0)
    stock_after = Column(Float, default=0)
    
    # Reason and user
    reason = Column(Text, nullable=True)
    performed_by = Column(String(128), nullable=True)
    
    # Location (for transfers)
    from_location = Column(String(256), nullable=True)
    to_location = Column(String(256), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    spare_part = relationship("SparePart", backref="movements")
