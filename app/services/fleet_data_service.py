from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.traccar import (
    Device, WorkshopJob, Technician, MaintenanceLog, Workshop,
    MaintenanceType, MaintenanceTemplate, SparePart, StockMovement,
    VehicleMaintenance, MaintenanceSchedule, Position, Event, Driver,
    DeviceDriver, FleetTrip, FuelStationVisit
)
from app.services.traccar_api_client import get_traccar_client
from app.services.workshop_service import WorkshopService
from typing import List, Dict, Any, Optional
from loguru import logger
from datetime import datetime, timedelta, timezone
import time
import asyncio

# ==================== CACHE ENGINE ====================

class FleetDataCache:
    """Intelligent cache with TTL and auto-invalidation"""

    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._ttl: Dict[str, float] = {}
        self.default_ttl = 60  # seconds

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            if time.time() - self._ttl.get(key, 0) < self.default_ttl:
                return self._cache[key]
            else:
                del self._cache[key]
                del self._ttl[key]
        return None

    def set(self, key: str, value: Any, ttl: int = None):
        self._cache[key] = value
        self._ttl[key] = time.time()
        if ttl:
            pass  # store custom ttl for this key

    def invalidate(self, pattern: str = None):
        if pattern is None:
            self._cache.clear()
            self._ttl.clear()
            logger.info("[FLEET_CACHE] Full cache invalidated")
            return
        keys_to_delete = [k for k in self._cache if pattern in k]
        for k in keys_to_delete:
            del self._cache[k]
            del self._ttl[k]
        logger.info(f"[FLEET_CACHE] Invalidated {len(keys_to_delete)} keys matching '{pattern}'")

    def invalidate_vehicle(self, device_id: int):
        self.invalidate(f"vehicle:{device_id}")
        self.invalidate("fleet_summary")
        self.invalidate("fleet_health")

    def invalidate_workshop(self):
        self.invalidate("workshop")
        self.invalidate("fleet_summary")
        self.invalidate("fleet_health")

    def invalidate_inventory(self):
        self.invalidate("inventory")
        self.invalidate("fleet_summary")

    def invalidate_maintenance(self):
        self.invalidate("maintenance")
        self.invalidate("vehicle_maintenance")
        self.invalidate("fleet_summary")
        self.invalidate("fleet_health")


_fleet_cache = FleetDataCache()


def get_fleet_cache() -> FleetDataCache:
    return _fleet_cache


# ==================== STANDARDIZED DATA OBJECTS ====================

def standardize_vehicle(device_row: Any, position_row: Any = None,
                        traccar_device: Dict = None, traccar_position: Dict = None) -> Dict[str, Any]:
    name = None
    unique_id = None
    status = None
    last_update = None
    phone = None
    model = None
    category = None

    if device_row:
        name = getattr(device_row, 'name', None)
        unique_id = getattr(device_row, 'uniqueid', None)
        status = getattr(device_row, 'status', None)
        last_update = getattr(device_row, 'lastupdate', None)
        phone = getattr(device_row, 'phone', None)
        model = getattr(device_row, 'model', None)
        category = getattr(device_row, 'category', None)

    if traccar_device:
        name = name or traccar_device.get('name')
        unique_id = unique_id or traccar_device.get('uniqueId')
        status = traccar_device.get('status') or status
        last_update = last_update or traccar_device.get('lastUpdate')
        phone = phone or traccar_device.get('phone')
        model = model or traccar_device.get('model')
        category = category or traccar_device.get('category')

    lat, lon, speed, course, altitude, address = None, None, None, None, None, None
    if position_row:
        lat = getattr(position_row, 'latitude', None)
        lon = getattr(position_row, 'longitude', None)
        speed = getattr(position_row, 'speed', None)
        course = getattr(position_row, 'course', None)
        altitude = getattr(position_row, 'altitude', None)
        address = getattr(position_row, 'address', None)
    if traccar_position:
        lat = lat or traccar_position.get('latitude')
        lon = lon or traccar_position.get('longitude')
        speed = speed or traccar_position.get('speed')
        course = course or traccar_position.get('course')
        altitude = altitude or traccar_position.get('altitude')
        address = address or traccar_position.get('address')

    odometer = None
    engine_hours = None
    if traccar_position:
        attrs = traccar_position.get('attributes', {}) or {}
        odometer = attrs.get('totalDistance') or attrs.get('odometer')
        engine_hours = attrs.get('engineHours')
    if position_row:
        attrs = getattr(position_row, 'attributes', None) or {}
        odometer = odometer or attrs.get('totalDistance') or attrs.get('odometer')
        engine_hours = engine_hours or attrs.get('engineHours')

    device_id = None
    if device_row:
        device_id = getattr(device_row, 'id', None)
    if traccar_device and not device_id:
        device_id = traccar_device.get('id')

    return {
        "id": device_id,
        "name": name or f"Vehicle {device_id}",
        "unique_id": unique_id,
        "status": status or "offline",
        "last_update": last_update.isoformat() if hasattr(last_update, 'isoformat') else last_update,
        "phone": phone,
        "model": model,
        "category": category,
        "latitude": lat,
        "longitude": lon,
        "speed": speed,
        "course": course,
        "altitude": altitude,
        "address": address,
        "odometer": round(float(odometer or 0), 2),
        "engine_hours": round(float(engine_hours or 0), 2),
        "position_time": traccar_position.get('deviceTime') if traccar_position else None,
    }


def standardize_maintenance(vm_row: Any, schedule_name: str = None,
                            device_name: str = None) -> Dict[str, Any]:
    return {
        "id": getattr(vm_row, 'id', None),
        "device_id": getattr(vm_row, 'device_id', None),
        "device_name": device_name,
        "schedule_id": getattr(vm_row, 'schedule_id', None),
        "schedule_name": schedule_name,
        "last_service_value": getattr(vm_row, 'last_service_value', None),
        "last_service_date": getattr(vm_row, 'last_service_date', None).isoformat() if getattr(vm_row, 'last_service_date', None) else None,
        "next_due_value": getattr(vm_row, 'next_due_value', None),
        "next_due_date": getattr(vm_row, 'next_due_date', None).isoformat() if getattr(vm_row, 'next_due_date', None) else None,
        "status": getattr(vm_row, 'status', 'unknown'),
        "km_overdue": getattr(vm_row, 'km_overdue', 0),
        "days_overdue": getattr(vm_row, 'days_overdue', 0),
        "assigned_workshop_id": getattr(vm_row, 'assigned_workshop_id', None),
    }


def standardize_workshop_job(job_row: Any, device_name: str = None,
                             tech_name: str = None) -> Dict[str, Any]:
    return {
        "id": getattr(job_row, 'id', None),
        "job_number": getattr(job_row, 'job_number', None),
        "device_id": getattr(job_row, 'device_id', None),
        "device_name": device_name,
        "title": getattr(job_row, 'title', None),
        "status": getattr(job_row, 'status', None),
        "priority": getattr(job_row, 'priority', 'medium'),
        "technician_id": getattr(job_row, 'technician_id', None),
        "technician_name": tech_name,
        "workshop_id": getattr(job_row, 'workshop_id', None),
        "total_cost": float(getattr(job_row, 'total_cost', 0) or 0),
        "labour_hours": float(getattr(job_row, 'labour_hours', 0) or 0),
        "created_date": getattr(job_row, 'created_date', None).isoformat() if getattr(job_row, 'created_date', None) else None,
        "completed_date": getattr(job_row, 'completed_date', None).isoformat() if getattr(job_row, 'completed_date', None) else None,
        "due_date": getattr(job_row, 'due_date', None).isoformat() if getattr(job_row, 'due_date', None) else None,
    }


def standardize_spare_part(part_row: Any) -> Dict[str, Any]:
    return {
        "id": getattr(part_row, 'id', None),
        "part_number": getattr(part_row, 'part_number', None),
        "name": getattr(part_row, 'name', None),
        "category": getattr(part_row, 'category', None),
        "brand": getattr(part_row, 'brand', None),
        "unit": getattr(part_row, 'unit', 'pcs'),
        "current_stock": float(getattr(part_row, 'current_quantity', 0) or 0),
        "minimum_stock": float(getattr(part_row, 'minimum_stock', 0) or 0),
        "maximum_stock": float(getattr(part_row, 'maximum_stock', 100) or 100),
        "unit_cost": float(getattr(part_row, 'unit_cost', 0) or 0),
        "supplier": getattr(part_row, 'supplier', None),
        "storage_location": getattr(part_row, 'storage_location', None),
        "is_active": getattr(part_row, 'is_active', True),
    }


def standardize_driver(driver_row: Any, device_id: int = None) -> Dict[str, Any]:
    return {
        "id": getattr(driver_row, 'id', None),
        "name": getattr(driver_row, 'name', None),
        "unique_id": getattr(driver_row, 'uniqueid', None),
        "device_id": device_id,
    }


def standardize_fleet_health(
    device_id: int, device_name: str,
    maint_status: str = "unknown",
    last_update: datetime = None,
    odometer: float = 0,
    engine_hours: float = 0,
    has_active_jobs: bool = False,
    has_overdue: bool = False,
    has_alerts: bool = False,
) -> Dict[str, Any]:
    score = 100
    reasons = []

    if has_overdue:
        score -= 25
        reasons.append("Overdue maintenance")
    if has_alerts:
        score -= 15
        reasons.append("Active alerts")
    if has_active_jobs:
        score -= 10
        reasons.append("Active workshop jobs")
    if maint_status == "critical":
        score -= 20
        reasons.append("Critical maintenance status")
    elif maint_status == "overdue":
        score -= 15
        reasons.append("Overdue maintenance")
    elif maint_status == "due":
        score -= 10
        reasons.append("Maintenance due soon")

    if last_update:
        hours_since = (datetime.now(timezone.utc) - last_update).total_seconds() / 3600
        if hours_since > 72:
            score -= 10
            reasons.append("No GPS update in 3+ days")
        elif hours_since > 24:
            score -= 5
            reasons.append("No GPS update in 24+ hours")

    score = max(0, min(100, score))

    return {
        "device_id": device_id,
        "device_name": device_name,
        "health_score": score,
        "status": "healthy" if score >= 70 else "warning" if score >= 40 else "critical",
        "reasons": reasons[:3],
        "maintenance_status": maint_status,
        "last_update": last_update.isoformat() if last_update else None,
        "odometer": round(float(odometer), 2),
        "engine_hours": round(float(engine_hours), 2),
    }


# ==================== FLEET DATA SERVICE ====================

class FleetDataService:
    """Enterprise Fleet Data Service — Single Source of Truth"""

    # ==================== CACHE MANAGEMENT ====================

    def invalidate_all(self):
        _fleet_cache.invalidate(None)

    def invalidate_vehicle_cache(self, device_id: int):
        _fleet_cache.invalidate_vehicle(device_id)

    def invalidate_workshop_cache(self):
        _fleet_cache.invalidate_workshop()

    def invalidate_inventory_cache(self):
        _fleet_cache.invalidate_inventory()

    def invalidate_maintenance_cache(self):
        _fleet_cache.invalidate_maintenance()

    # ==================== VEHICLE DATA ====================

    async def get_vehicle(self, db: AsyncSession, device_id: int) -> Optional[Dict[str, Any]]:
        cache_key = f"vehicle:{device_id}"
        cached = _fleet_cache.get(cache_key)
        if cached:
            return cached

        try:
            dev_result = await db.execute(select(Device).where(Device.id == device_id))
            device = dev_result.scalar_one_or_none()
        except Exception:
            device = None

        traccar_device = None
        traccar_position = None
        try:
            tc = await get_traccar_client()
            devices = await tc.get_devices()
            if devices:
                for d in devices:
                    if d.get("id") == device_id:
                        traccar_device = d
                        break
            positions = await tc.get_positions()
            if positions:
                for p in positions:
                    if p.get("deviceId") == device_id:
                        traccar_position = p
                        break
        except Exception as e:
            logger.debug(f"[FLEET] Traccar API unavailable for vehicle {device_id}: {e}")

        db_position = None
        if not traccar_position:
            try:
                pos_result = await db.execute(
                    select(Position).where(Position.deviceid == device_id)
                    .order_by(desc(Position.servertime)).limit(1)
                )
                db_position = pos_result.scalar_one_or_none()
            except Exception:
                pass

        vehicle = standardize_vehicle(device, db_position, traccar_device, traccar_position)

        if not vehicle.get("name") and traccar_device:
            vehicle["name"] = traccar_device.get("name", f"Vehicle {device_id}")

        _fleet_cache.set(cache_key, vehicle)
        return vehicle

    async def get_all_vehicles(self, db: AsyncSession) -> List[Dict[str, Any]]:
        cached = _fleet_cache.get("all_vehicles")
        if cached:
            return cached

        vehicles_map = {}
        try:
            devices_result = await db.execute(select(Device))
            for d in devices_result.scalars().all():
                vehicles_map[d.id] = {"device_row": d, "id": d.id}
        except Exception:
            pass

        traccar_devices = []
        try:
            tc = await get_traccar_client()
            traccar_devices = await tc.get_devices() or []
        except Exception:
            pass

        traccar_positions = []
        try:
            tc = await get_traccar_client()
            traccar_positions = await tc.get_positions() or []
        except Exception:
            pass

        pos_map = {p.get("deviceId"): p for p in traccar_positions}
        traccar_map = {d.get("id"): d for d in traccar_devices}

        all_ids = set(vehicles_map.keys()) | set(d.get("id") for d in traccar_devices if d.get("id"))

        results = []
        for vid in all_ids:
            v_info = vehicles_map.get(vid, {})
            device_row = v_info.get("device_row")
            tc_dev = traccar_map.get(vid)
            tc_pos = pos_map.get(vid)

            results.append(standardize_vehicle(device_row, None, tc_dev, tc_pos))

        _fleet_cache.set("all_vehicles", results, ttl=120)
        return results

    # ==================== VEHICLE STATUS ====================

    async def get_vehicle_status(self, db: AsyncSession, device_id: int = None) -> Dict[str, Any]:
        cached = _fleet_cache.get(f"vehicle_status:{device_id or 'all'}")
        if cached:
            return cached

        vehicles = await self.get_all_vehicles(db)
        if device_id:
            vehicles = [v for v in vehicles if v.get("id") == device_id]

        online = sum(1 for v in vehicles if v.get("status") == "online")
        offline = sum(1 for v in vehicles if v.get("status") == "offline")
        moving = sum(1 for v in vehicles if v.get("speed", 0) or 0 > 0)
        stopped = len(vehicles) - moving
        with_position = sum(1 for v in vehicles if v.get("latitude") is not None)

        result = {
            "total": len(vehicles),
            "online": online,
            "offline": offline,
            "moving": moving,
            "stopped": stopped,
            "with_position": with_position,
            "vehicles": vehicles[:50] if not device_id else vehicles,
        }
        _fleet_cache.set(f"vehicle_status:{device_id or 'all'}", result, ttl=30)
        return result

    # ==================== MAINTENANCE STATUS ====================

    async def get_maintenance_status(self, db: AsyncSession, device_id: int = None) -> List[Dict[str, Any]]:
        cache_key = f"vehicle_maintenance:{device_id or 'all'}"
        cached = _fleet_cache.get(cache_key)
        if cached:
            return cached

        query = select(VehicleMaintenance)
        if device_id:
            query = query.where(VehicleMaintenance.device_id == device_id)
        query = query.order_by(VehicleMaintenance.device_id)

        result = await db.execute(query)
        items = []
        for vm in result.scalars().all():
            sched_name = None
            try:
                sched = (await db.execute(select(MaintenanceSchedule).where(MaintenanceSchedule.id == vm.schedule_id))).scalar_one_or_none()
                sched_name = sched.name if sched else None
            except Exception:
                pass
            dev_name = None
            if device_id:
                vehicle = await self.get_vehicle(db, vm.device_id)
                dev_name = vehicle.get("name") if vehicle else None
            items.append(standardize_maintenance(vm, sched_name, dev_name))

        _fleet_cache.set(cache_key, items, ttl=60)
        return items

    async def get_vehicle_maintenance_summary(self, db: AsyncSession, device_id: int) -> Dict[str, Any]:
        cache_key = f"vehicle_maint_summary:{device_id}"
        cached = _fleet_cache.get(cache_key)
        if cached:
            return cached

        items = await self.get_maintenance_status(db, device_id)
        healthy = sum(1 for i in items if i["status"] == "healthy")
        due_soon = sum(1 for i in items if i["status"] == "due_soon")
        overdue = sum(1 for i in items if i["status"] in ("overdue", "critical", "due"))

        result = {
            "device_id": device_id,
            "total_schedules": len(items),
            "healthy": healthy,
            "due_soon": due_soon,
            "overdue": overdue,
            "items": items,
        }
        _fleet_cache.set(cache_key, result, ttl=60)
        return result

    # ==================== WORKSHOP STATUS ====================

    async def get_workshop_status(self, db: AsyncSession, device_id: int = None) -> Dict[str, Any]:
        cache_key = f"workshop:{device_id or 'all'}"
        cached = _fleet_cache.get(cache_key)
        if cached:
            return cached

        query = select(WorkshopJob)
        conditions = [WorkshopJob.is_active == True]
        if device_id:
            conditions.append(WorkshopJob.device_id == device_id)
        query = query.where(and_(*conditions)).order_by(desc(WorkshopJob.created_at)).limit(50)

        result = await db.execute(query)
        jobs = []
        for j in result.scalars().all():
            tech_name = None
            if j.technician_id:
                try:
                    tech_result = await db.execute(select(Technician).where(Technician.id == j.technician_id))
                    tech = tech_result.scalar_one_or_none()
                    tech_name = tech.name if tech else None
                except Exception:
                    pass
            jobs.append(standardize_workshop_job(j, device_name=None, tech_name=tech_name))

        active = sum(1 for j in jobs if j["status"] in
                     ("assigned", "vehicle_arrived", "inspection", "in_progress",
                      "waiting_parts", "paused", "quality_check"))
        completed = sum(1 for j in jobs if j["status"] == "completed")
        pending = sum(1 for j in jobs if j["status"] == "pending")
        cancelled = sum(1 for j in jobs if j["status"] == "cancelled")

        result = {
            "device_id": device_id,
            "total_jobs": len(jobs),
            "active_jobs": active,
            "completed_jobs": completed,
            "pending_jobs": pending,
            "cancelled_jobs": cancelled,
            "jobs": jobs,
        }
        _fleet_cache.set(cache_key, result, ttl=60)
        return result

    # ==================== INVENTORY STATUS ====================

    async def get_inventory_status(self, db: AsyncSession) -> Dict[str, Any]:
        cached = _fleet_cache.get("inventory:status")
        if cached:
            return cached

        try:
            total_parts = (await db.execute(
                select(func.count()).select_from(SparePart).where(SparePart.is_active == True)
            )).scalar() or 0

            total_stock = float((await db.execute(
                select(func.sum(SparePart.current_quantity)).where(SparePart.is_active == True)
            )).scalar() or 0)

            low_stock = (await db.execute(
                select(func.count()).select_from(SparePart).where(
                    and_(SparePart.is_active == True,
                         SparePart.current_quantity <= SparePart.minimum_stock,
                         SparePart.current_quantity > 0)
                )
            )).scalar() or 0

            out_of_stock = (await db.execute(
                select(func.count()).select_from(SparePart).where(
                    and_(SparePart.is_active == True, SparePart.current_quantity <= 0)
                )
            )).scalar() or 0

            total_value = float((await db.execute(
                select(func.sum(SparePart.current_quantity * SparePart.unit_cost)).where(SparePart.is_active == True)
            )).scalar() or 0)

            active_movements = (await db.execute(
                select(func.count()).select_from(StockMovement).where(
                    StockMovement.created_at >= datetime.utcnow() - timedelta(days=7)
                )
            )).scalar() or 0

            result = {
                "total_parts": total_parts,
                "total_stock": round(total_stock, 2),
                "low_stock_items": low_stock,
                "out_of_stock_items": out_of_stock,
                "total_value": round(total_value, 2),
                "active_movements_7d": active_movements,
            }
            _fleet_cache.set("inventory:status", result, ttl=120)
            return result
        except Exception as e:
            logger.warning(f"[FLEET] Inventory status error: {e}")
            return {}

    # ==================== DRIVER ASSIGNMENT ====================

    async def get_driver_assignment(self, db: AsyncSession, device_id: int = None) -> List[Dict[str, Any]]:
        cache_key = f"driver:{device_id or 'all'}"
        cached = _fleet_cache.get(cache_key)
        if cached:
            return cached

        try:
            query = select(DeviceDriver)
            if device_id:
                query = query.where(DeviceDriver.deviceid == device_id)
            result = await db.execute(query)
            items = []
            for dd in result.scalars().all():
                driver = (await db.execute(select(Driver).where(Driver.id == dd.driverid))).scalar_one_or_none()
                if driver:
                    items.append(standardize_driver(driver, dd.deviceid))
            _fleet_cache.set(cache_key, items, ttl=300)
            return items
        except Exception as e:
            logger.warning(f"[FLEET] Driver assignment error: {e}")
            return []

    # ==================== FLEET HEALTH ENGINE ====================

    async def get_fleet_health(self, db: AsyncSession, device_id: int = None) -> List[Dict[str, Any]]:
        cache_key = f"fleet_health:{device_id or 'all'}"
        cached = _fleet_cache.get(cache_key)
        if cached:
            return cached

        vehicles = await self.get_all_vehicles(db)
        maintenances = await self.get_maintenance_status(db, device_id)

        maint_by_device = {}
        for m in maintenances:
            did = m["device_id"]
            if did not in maint_by_device:
                maint_by_device[did] = {"status": "healthy", "has_overdue": False}
            if m["status"] in ("overdue", "critical"):
                maint_by_device[did]["status"] = m["status"]
                maint_by_device[did]["has_overdue"] = True
            elif m["status"] == "due" and maint_by_device[did]["status"] == "healthy":
                maint_by_device[did]["status"] = "due"

        workshop_by_device = {}
        ws = await self.get_workshop_status(db, device_id)
        for j in ws["jobs"]:
            did = j["device_id"]
            if did not in workshop_by_device:
                workshop_by_device[did] = False
            if j["status"] in ("assigned", "vehicle_arrived", "inspection", "in_progress",
                               "waiting_parts", "paused", "quality_check"):
                workshop_by_device[did] = True

        results = []
        for v in vehicles:
            vid = v["id"]
            if device_id and vid != device_id:
                continue

            m_info = maint_by_device.get(vid, {"status": "unknown", "has_overdue": False})
            ws_active = workshop_by_device.get(vid, False)

            last_update = None
            if v.get("last_update"):
                try:
                    last_update = datetime.fromisoformat(v["last_update"].replace("Z", "+00:00"))
                except Exception:
                    pass
            if v.get("position_time"):
                try:
                    last_update = datetime.fromisoformat(v["position_time"].replace("Z", "+00:00"))
                except Exception:
                    pass

            health = standardize_fleet_health(
                device_id=vid,
                device_name=v["name"],
                maint_status=m_info["status"],
                last_update=last_update or datetime.now(timezone.utc),
                odometer=v.get("odometer", 0),
                engine_hours=v.get("engine_hours", 0),
                has_active_jobs=ws_active,
                has_overdue=m_info["has_overdue"],
                has_alerts=m_info["has_overdue"],
            )
            results.append(health)

        results.sort(key=lambda x: x["health_score"])
        _fleet_cache.set(cache_key, results, ttl=60)
        return results

    # ==================== FLEET SUMMARY ====================

    async def get_fleet_summary(self, db: AsyncSession) -> Dict[str, Any]:
        cached = _fleet_cache.get("fleet_summary")
        if cached:
            return cached

        vehicles = await self.get_all_vehicles(db)
        health = await self.get_fleet_health(db)
        inventory = await self.get_inventory_status(db)

        total = len(vehicles)
        online = sum(1 for v in vehicles if v.get("status") == "online")
        moving = sum(1 for v in vehicles if (v.get("speed") or 0) > 0)

        avg_health = round(sum(h["health_score"] for h in health) / len(health), 1) if health else 0
        healthy_count = sum(1 for h in health if h["health_score"] >= 70)
        warning_count = sum(1 for h in health if 40 <= h["health_score"] < 70)
        critical_count = sum(1 for h in health if h["health_score"] < 40)

        total_maint_cost = 0
        try:
            cost_result = await db.execute(
                select(func.sum(MaintenanceLog.cost)).where(MaintenanceLog.cost > 0)
            )
            total_maint_cost = round(float(cost_result.scalar() or 0), 2)
        except Exception:
            pass

        total_ws_cost = 0
        try:
            ws_cost = await db.execute(
                select(func.sum(WorkshopJob.total_cost)).where(WorkshopJob.status == "completed")
            )
            total_ws_cost = round(float(ws_cost.scalar() or 0), 2)
        except Exception:
            pass

        result = {
            "total_vehicles": total,
            "online_vehicles": online,
            "offline_vehicles": total - online,
            "moving_vehicles": moving,
            "stopped_vehicles": total - moving,
            "fleet_health_avg": avg_health,
            "healthy_vehicles": healthy_count,
            "warning_vehicles": warning_count,
            "critical_vehicles": critical_count,
            "total_maintenance_cost": total_maint_cost,
            "total_workshop_cost": total_ws_cost,
            "total_combined_cost": round(total_maint_cost + total_ws_cost, 2),
            "inventory_value": inventory.get("total_value", 0),
            "total_parts": inventory.get("total_parts", 0),
            "low_stock_items": inventory.get("low_stock_items", 0),
            "out_of_stock_items": inventory.get("out_of_stock_items", 0),
        }
        _fleet_cache.set("fleet_summary", result, ttl=60)
        return result

    # ==================== DASHBOARD ====================

    async def get_dashboard(self, db: AsyncSession) -> Dict[str, Any]:
        cached = _fleet_cache.get("fleet_dashboard")
        if cached:
            return cached

        summary = await self.get_fleet_summary(db)
        health = await self.get_fleet_health(db)

        overdue_vms = (await db.execute(
            select(func.count()).select_from(VehicleMaintenance).where(
                VehicleMaintenance.status.in_(["overdue", "critical"])
            )
        )).scalar() or 0

        pending_jobs = (await db.execute(
            select(func.count()).select_from(WorkshopJob).where(WorkshopJob.status == "pending")
        )).scalar() or 0

        active_jobs = (await db.execute(
            select(func.count()).select_from(WorkshopJob).where(
                WorkshopJob.status.in_(["assigned", "vehicle_arrived", "inspection",
                                         "in_progress", "waiting_parts", "paused", "quality_check"])
            )
        )).scalar() or 0

        recent_logs = []
        try:
            logs_result = await db.execute(
                select(MaintenanceLog).order_by(desc(MaintenanceLog.service_date)).limit(10)
            )
            for log in logs_result.scalars().all():
                recent_logs.append({
                    "id": log.id, "device_id": log.device_id,
                    "service_date": log.service_date.isoformat() if log.service_date else None,
                    "service_type": log.service_type, "cost": log.cost,
                })
        except Exception:
            pass

        recent_jobs = []
        try:
            jobs_result = await db.execute(
                select(WorkshopJob).order_by(desc(WorkshopJob.created_at)).limit(10)
            )
            for j in jobs_result.scalars().all():
                recent_jobs.append({
                    "id": j.id, "job_number": j.job_number,
                    "device_id": j.device_id, "title": j.title,
                    "status": j.status, "total_cost": j.total_cost,
                    "created_date": j.created_date.isoformat() if j.created_date else None,
                })
        except Exception:
            pass

        result = {
            "summary": summary,
            "health": {
                "critical_vehicles": [h for h in health if h["health_score"] < 40][:5],
                "warning_vehicles": [h for h in health if 40 <= h["health_score"] < 70][:5],
                "overdue_maintenances": overdue_vms,
                "pending_jobs": pending_jobs,
                "active_jobs": active_jobs,
            },
            "recent_activity": {
                "maintenance_logs": recent_logs,
                "workshop_jobs": recent_jobs,
            },
        }
        _fleet_cache.set("fleet_dashboard", result, ttl=60)
        return result

    # ==================== VEHICLE HISTORY ====================

    async def get_vehicle_history(self, db: AsyncSession, device_id: int, days: int = 90) -> Dict[str, Any]:
        cache_key = f"vehicle_history:{device_id}:{days}"
        cached = _fleet_cache.get(cache_key)
        if cached:
            return cached

        vehicle = await self.get_vehicle(db, device_id)
        since = datetime.utcnow() - timedelta(days=days)

        logs = []
        try:
            result = await db.execute(
                select(MaintenanceLog).where(
                    and_(MaintenanceLog.device_id == device_id, MaintenanceLog.service_date >= since)
                ).order_by(desc(MaintenanceLog.service_date))
            )
            for log in result.scalars().all():
                logs.append({
                    "id": log.id, "service_date": log.service_date.isoformat() if log.service_date else None,
                    "service_value": log.service_value, "service_type": log.service_type,
                    "technician": log.technician, "cost": log.cost,
                    "notes": log.notes, "parts_replaced": log.parts_replaced or [],
                })
        except Exception as e:
            logger.warning(f"[FLEET] Vehicle history error: {e}")

        jobs = []
        try:
            result = await db.execute(
                select(WorkshopJob).where(
                    and_(WorkshopJob.device_id == device_id, WorkshopJob.created_date >= since)
                ).order_by(desc(WorkshopJob.created_date))
            )
            for j in result.scalars().all():
                jobs.append(standardize_workshop_job(j, vehicle.get("name") if vehicle else None))
        except Exception:
            pass

        total_maintenance = sum(l["cost"] or 0 for l in logs)
        total_workshop = sum(j["total_cost"] for j in jobs)

        result = {
            "vehicle": vehicle,
            "maintenance_history": logs,
            "workshop_jobs": jobs,
            "total_maintenance_cost": round(total_maintenance, 2),
            "total_workshop_cost": round(total_workshop, 2),
            "total_cost": round(total_maintenance + total_workshop, 2),
        }
        _fleet_cache.set(cache_key, result, ttl=120)
        return result

    # ==================== VEHICLE UTILIZATION ====================

    async def get_vehicle_utilization(self, db: AsyncSession, device_id: int, days: int = 30) -> Dict[str, Any]:
        vehicle = await self.get_vehicle(db, device_id)
        since = datetime.utcnow() - timedelta(days=days)

        trips = []
        total_distance = 0
        total_fuel = 0
        trip_count = 0
        try:
            result = await db.execute(
                select(FleetTrip).where(
                    and_(FleetTrip.device_id == device_id, FleetTrip.start_time >= since)
                ).order_by(FleetTrip.start_time)
            )
            for t in result.scalars().all():
                trips.append({
                    "start_time": t.start_time.isoformat() if t.start_time else None,
                    "end_time": t.end_time.isoformat() if t.end_time else None,
                    "distance_km": t.distance_km,
                    "fuel_consumed_l": t.fuel_consumed_l,
                    "mileage": t.mileage,
                })
                total_distance += t.distance_km or 0
                total_fuel += t.fuel_consumed_l or 0
                trip_count += 1
        except Exception:
            pass

        return {
            "vehicle": vehicle,
            "period_days": days,
            "trip_count": trip_count,
            "total_distance_km": round(total_distance, 2),
            "total_fuel_l": round(total_fuel, 2),
            "avg_distance_per_day": round(total_distance / days, 2) if days > 0 else 0,
            "avg_fuel_per_day": round(total_fuel / days, 2) if days > 0 else 0,
            "mileage": round(total_distance / total_fuel, 2) if total_fuel > 0 else None,
            "trips": trips,
        }

    # ==================== MAINTENANCE LOG (for reports) ====================

    async def get_maintenance_logs(self, db: AsyncSession, days: int = 90) -> List[Dict[str, Any]]:
        since = datetime.utcnow() - timedelta(days=days)
        try:
            result = await db.execute(
                select(MaintenanceLog).where(MaintenanceLog.service_date >= since)
                .order_by(desc(MaintenanceLog.service_date))
            )
            items = []
            for log in result.scalars().all():
                vehicle = await self.get_vehicle(db, log.device_id)
                items.append({
                    "id": log.id, "device_id": log.device_id,
                    "device_name": vehicle.get("name") if vehicle else f"Vehicle {log.device_id}",
                    "service_date": log.service_date.isoformat() if log.service_date else None,
                    "service_value": log.service_value, "service_type": log.service_type,
                    "technician": log.technician, "cost": log.cost,
                    "notes": log.notes, "parts_replaced": log.parts_replaced or [],
                })
            return items
        except Exception as e:
            logger.warning(f"[FLEET] Maintenance logs error: {e}")
            return []

    # ==================== WORKSHOP JOBS (for reports) ====================

    async def get_workshop_jobs(self, db: AsyncSession, days: int = 90) -> List[Dict[str, Any]]:
        since = datetime.utcnow() - timedelta(days=days)
        try:
            result = await db.execute(
                select(WorkshopJob).where(WorkshopJob.created_date >= since)
                .order_by(desc(WorkshopJob.created_date))
            )
            items = []
            for j in result.scalars().all():
                tech_name = None
                if j.technician_id:
                    try:
                        tech = (await db.execute(select(Technician).where(Technician.id == j.technician_id))).scalar_one_or_none()
                        tech_name = tech.name if tech else None
                    except Exception:
                        pass
                items.append(standardize_workshop_job(j, tech_name=tech_name))
            return items
        except Exception as e:
            logger.warning(f"[FLEET] Workshop jobs error: {e}")
            return []

    # ==================== ALL ALERTS ====================

    async def get_vehicle_alerts(self, db: AsyncSession, device_id: int = None, days: int = 7) -> List[Dict[str, Any]]:
        from app.models.traccar import Event as TraccarEvent
        since = datetime.utcnow() - timedelta(days=days)
        try:
            query = select(TraccarEvent).where(TraccarEvent.eventtime >= since)
            if device_id:
                query = query.where(TraccarEvent.deviceid == device_id)
            query = query.order_by(desc(TraccarEvent.eventtime)).limit(50)
            result = await db.execute(query)
            items = []
            for e in result.scalars().all():
                items.append({
                    "id": e.id, "type": e.type, "device_id": e.deviceid,
                    "event_time": e.eventtime.isoformat() if e.eventtime else None,
                    "attributes": e.attributes or {},
                })
            return items
        except Exception as ex:
            logger.warning(f"[FLEET] Alerts error: {ex}")
            return []

    async def get_cost_summary(self, db: AsyncSession, days: int = 365) -> Dict[str, Any]:
        since = datetime.utcnow() - timedelta(days=days)
        try:
            total_labour = float((await db.execute(
                select(func.sum(WorkshopJob.labour_cost)).where(
                    and_(WorkshopJob.status == "completed", WorkshopJob.created_date >= since)
                )
            )).scalar() or 0)

            total_parts = float((await db.execute(
                select(func.sum(WorkshopJob.parts_cost)).where(
                    and_(WorkshopJob.status == "completed", WorkshopJob.created_date >= since)
                )
            )).scalar() or 0)

            total_misc = float((await db.execute(
                select(func.sum(WorkshopJob.misc_cost)).where(
                    and_(WorkshopJob.status == "completed", WorkshopJob.created_date >= since)
                )
            )).scalar() or 0)

            total_maint = float((await db.execute(
                select(func.sum(MaintenanceLog.cost)).where(
                    and_(MaintenanceLog.service_date >= since, MaintenanceLog.cost > 0)
                )
            )).scalar() or 0)

            return {
                "labour_cost": round(total_labour, 2),
                "parts_cost": round(total_parts, 2),
                "misc_cost": round(total_misc, 2),
                "maintenance_cost": round(total_maint, 2),
                "total_cost": round(total_labour + total_parts + total_misc + total_maint, 2),
            }
        except Exception as e:
            logger.warning(f"[FLEET] Cost summary error: {e}")
            return {}


fleet_data_service = FleetDataService()
