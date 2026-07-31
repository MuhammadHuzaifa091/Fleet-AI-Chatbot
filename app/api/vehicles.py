from fastapi import APIRouter, Depends, Body, BackgroundTasks, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.api.auth import get_current_user
from app.retrievers.sql_retriever import SQLRetriever
from app.models.traccar import Device, Position, VehicleSpecsCache
from app.services.vin_service import VINService
from app.services.traccar_api_client import get_traccar_client
from typing import Dict, Any, List
import re
from datetime import datetime
from loguru import logger
import json
from pydantic import BaseModel

# ─── Pydantic Schemas ────────────────────────────────────────────────────────
class VinUpdatePayload(BaseModel):
    vin: str

# ─── VIN Validation ──────────────────────────────────────────────────────────
def is_valid_vin(vin: str) -> bool:
    if not vin:
        return False
    vin = vin.upper()
    if len(vin) != 17:
        return False
    if not re.match(r'^[A-HJ-NPR-Z0-9]{17}$', vin):
        return False
    return True

# ─── Router ──────────────────────────────────────────────────────────────────
router = APIRouter()

# ── GET /live ─────────────────────────────────────────────────────────────────
@router.get("/live")
async def get_live_vehicles(
    limit: int = 5000,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    traccar = await get_traccar_client()
    devices = await traccar.get_devices()
    if devices:
        positions = await traccar.get_positions()
        pos_map = {p.get("deviceId"): p for p in positions} if positions else {}
        result = []
        for d in devices:
            pos = pos_map.get(d.get("id"))
            result.append({
                "id": d.get("id"),
                "name": d.get("name"),
                "uniqueId": d.get("uniqueId"),
                "status": d.get("status"),
                "lastUpdate": d.get("lastUpdate"),
                "groupId": d.get("groupId"),
                "category": d.get("category"),
                "model": d.get("model"),
                "contact": d.get("contact"),
                "phone": d.get("phone"),
                "latitude": pos.get("latitude") if pos else None,
                "longitude": pos.get("longitude") if pos else None,
                "altitude": pos.get("altitude") if pos else None,
                "speed": pos.get("speed") if pos else 0,
                "course": pos.get("course") if pos else 0,
                "address": pos.get("address") if pos else None,
                "attributes": pos.get("attributes", {}) if pos else {},
            })
        return result

    retriever = SQLRetriever(db, current_user)
    return await retriever.get_live_vehicles(limit=limit)


# ── GET /positions ─────────────────────────────────────────────────────────────
# Historical GPS positions for a device in a time range (for Route Playback)
# Queries local tc_positions table directly — no Traccar session required.
@router.get("/positions")
async def get_positions(
    deviceId: int,
    from_: str = Query(default=None, alias="from"),
    to_: str = Query(default=None, alias="to"),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        q = select(Position).where(Position.deviceid == deviceId)
        if from_:
            try:
                from_dt = datetime.fromisoformat(from_.replace("Z", "+00:00")).replace(tzinfo=None)
                q = q.where(Position.fixtime >= from_dt)
            except Exception:
                pass
        if to_:
            try:
                to_dt = datetime.fromisoformat(to_.replace("Z", "+00:00")).replace(tzinfo=None)
                q = q.where(Position.fixtime <= to_dt)
            except Exception:
                pass
        q = q.order_by(Position.fixtime.asc()).limit(5000)
        result = await db.execute(q)
        positions = result.scalars().all()
        return [
            {
                "id": p.id, "deviceId": p.deviceid,
                "fixTime": p.fixtime.isoformat() if p.fixtime else None,
                "latitude": p.latitude, "longitude": p.longitude,
                "altitude": p.altitude,
                "speed": round((p.speed or 0) * 1.852, 2),
                "course": p.course, "valid": p.valid, "attributes": p.attributes or {},
            }
            for p in positions if p.latitude and p.longitude
        ]
    except Exception:
        pass
    try:
        from app.services.traccar_api_client import get_traccar_client
        traccar = await get_traccar_client()
        pos_list = await traccar.get_device_positions(deviceId)
        if pos_list:
            return [
                {
                    "id": p.get("id"), "deviceId": p.get("deviceId"),
                    "fixTime": p.get("fixTime"),
                    "latitude": p.get("latitude"), "longitude": p.get("longitude"),
                    "altitude": p.get("altitude"),
                    "speed": p.get("speed"), "course": p.get("course"),
                    "valid": p.get("valid"), "attributes": p.get("attributes", {}),
                }
                for p in pos_list if p.get("latitude") and p.get("longitude")
            ]
    except Exception as e:
        logger.error(f"[POSITIONS] Traccar API fallback failed for device {deviceId}: {e}")
    return []


# ── GET /{device_id}/intel ────────────────────────────────────────────────────
# Full enriched profile: VIN badge, specs (from DB cache), depreciation data
@router.get("/{device_id}/intel")
async def get_vehicle_intel(
    device_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    import asyncio as _asyncio
    pos_attr = {}
    dev_attr = {}
    _device_sql = None
    pid_profile_data = {}
    lookup_name = None
    overspeed_count = 0
    gps_summary = {}
    fdb_data = {}
    recent_alerts = []
    device_name = str(device_id)
    device_uniqueid = str(device_id)
    traccar_dev = None

    try:
        traccar = await get_traccar_client()
        all_devices = await traccar.get_devices()
        if all_devices:
            for d in all_devices:
                if d.get("id") == device_id:
                    traccar_dev = d
                    break
        if traccar_dev:
            device_name = traccar_dev.get("name", str(device_id))
            device_uniqueid = traccar_dev.get("uniqueId", str(device_id))
            dev_attr = traccar_dev.get("attributes", {}) or {}
            pos_attr = {}
            try:
                dev_positions = await traccar.get_device_positions(device_id)
                for p in dev_positions:
                    if p.get("deviceId") == device_id:
                        pos_attr = p.get("attributes", {}) or {}
                        dev_attr.update(pos_attr)
                        break
            except Exception:
                pass
        try:
            from app.models.traccar import Device as TDev, Position as TPos
            q = select(TDev, TPos).outerjoin(TPos, TDev.positionid == TPos.id).where(TDev.id == device_id, TDev.disabled == False)
            res = await db.execute(q)
            row = res.first()
            if row:
                _device_sql, _pos_sql = row
                if not traccar_dev:
                    device_name = _device_sql.name
                    device_uniqueid = _device_sql.uniqueid
                    dev_attr = _device_sql.attributes or {}
        except Exception:
            pass
        try:
            from sqlalchemy import text as _text
            alias_task = db.execute(_text("SELECT alias_name FROM ke_vehicle_imei WHERE imei = :imei LIMIT 1"), {"imei": device_uniqueid})
            overspeed_task = db.execute(_text("SELECT COUNT(*) FROM tc_events WHERE deviceid = :did AND type = 'alarm' AND eventtime >= DATE_SUB(NOW(), INTERVAL 30 DAY) AND (attributes LIKE '%overspeed%' OR attributes LIKE '%speed%')"), {"did": device_id})
            gps_task = db.execute(_text("SELECT AVG(total_distance_km), MAX(max_speed_kmh), AVG(avg_speed_kmh), SUM(speed_violations), COUNT(*) FROM ke_gps_daily WHERE device_id = :did AND record_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)"), {"did": device_id})
            alias_res, os_res, gs_res = await _asyncio.gather(alias_task, overspeed_task, gps_task, return_exceptions=True)
            if not isinstance(alias_res, Exception):
                alias_row = alias_res.fetchone()
                lookup_name = alias_row[0] if alias_row else None
            if not isinstance(os_res, Exception):
                overspeed_count = (os_res.fetchone()[0] or 0) if os_res else 0
            if not isinstance(gs_res, Exception):
                gs_row = gs_res.fetchone() if gs_res else None
                if gs_row and gs_row[0] is not None:
                    gps_summary = {"avg_daily_km": round(float(gs_row[0]), 1), "max_speed_7d": round(float(gs_row[1]), 1), "avg_speed_7d": round(float(gs_row[2]), 1), "speed_violations_7d": int(gs_row[3] or 0), "days_active_7d": int(gs_row[4])}
            if lookup_name:
                fdb_result = await db.execute(_text("SELECT vehicle_registration, benchmark_kmpl, allocated_km, shift_type, shift_hrs, fuel_type, tonnage, vehicle_category, vehicle_type, make, model_year, fleet_group, region, cluster, tracker_vendor FROM ke_fleet_database WHERE vehicle_registration = :vname LIMIT 1"), {"vname": lookup_name})
                fdb_row = fdb_result.fetchone()
                if fdb_row:
                    fdb_data = {"vehicle_registration": fdb_row[0], "benchmark_kmpl": fdb_row[1], "allocated_km": fdb_row[2], "shift_type": fdb_row[3], "shift_hrs": fdb_row[4], "fuel_type": fdb_row[5], "tonnage": fdb_row[6], "category": fdb_row[7], "vehicle_type": fdb_row[8], "make": fdb_row[9], "model_year": fdb_row[10], "fleet_group": fdb_row[11], "region": fdb_row[12], "cluster": fdb_row[13], "tracker_vendor": fdb_row[14]}
                ra_result = await db.execute(_text("SELECT alert_type, severity, title, created_at FROM fleet_alerts WHERE vehicle = :vname ORDER BY created_at DESC LIMIT 10"), {"vname": lookup_name})
                for r in ra_result.fetchall():
                    recent_alerts.append({"type": r[0], "severity": r[1], "title": r[2], "time": str(r[3]) if r[3] else None})
        except Exception:
            pass
    except Exception as _e:
        logger.warning(f"[INTEL_EXCEPTION] device={device_id}: {_e}")

    # --- VIN ---
    vin = (traccar_dev.get("attributes", {}).get("vin") if traccar_dev else None) or pos_attr.get("obdVin") or pos_attr.get("io256") or dev_attr.get("vin") or None
    vin_source = None
    if _device_sql:
        vin = vin or getattr(_device_sql, 'vin', None)
        vin_source = getattr(_device_sql, 'vin_source', None)
    vin_source = vin_source or ("obd" if vin else None)

    if vin_source == "obd":
        badge = {"label": "ECU Verified", "class": "success"}
    elif vin_source == "manual":
        badge = {"label": "Profile Synced", "class": "primary"}
    else:
        badge = {"label": "Profile Incomplete", "class": "warning"}

    pid_profile_data = {}
    if _device_sql and getattr(_device_sql, 'pid_profile', None):
        try: pid_profile_data = json.loads(_device_sql.pid_profile)
        except: pass

    displacement = pid_profile_data.get("displacement_l") or "N/A"
    fuel_type = pid_profile_data.get("fuel_type") or fdb_data.get("fuel_type") or "N/A"

    specs = {
        "make": (traccar_dev.get("attributes", {}).get("make") if traccar_dev else None) or (getattr(_device_sql, 'manufacturer', None) if _device_sql else None) or fdb_data.get("make") or dev_attr.get("make") or "N/A",
        "model": (traccar_dev.get("model") if traccar_dev else None) or (getattr(_device_sql, 'model', None) if _device_sql else None) or dev_attr.get("model") or fdb_data.get("vehicle_type") or "N/A",
        "year": (traccar_dev.get("attributes", {}).get("year") if traccar_dev else None) or (getattr(_device_sql, 'year', None) if _device_sql else None) or dev_attr.get("year") or fdb_data.get("model_year") or "N/A",
        "engine": f"{displacement}L" if displacement != "N/A" else "N/A",
        "fuel_type": fuel_type,
        "category": (traccar_dev.get("category") if traccar_dev else None) or (getattr(_device_sql, 'category', None) if _device_sql else None) or fdb_data.get("category") or dev_attr.get("category") or "N/A",
    }

    total_dist_m = pos_attr.get("totalDistance") or 0
    total_dist_km = round(float(total_dist_m) / 1000, 1) if total_dist_m else 0
    if total_dist_km <= 0 and fdb_data.get("allocated_km"):
        total_dist_km = float(fdb_data.get("allocated_km") or 120000)

    current_year = datetime.now().year
    try: vy = int(specs["year"])
    except: vy = current_year - 5
    vehicle_age = max(1, current_year - vy)
    km_per_year = total_dist_km / vehicle_age if vehicle_age > 0 else total_dist_km
    avg_annual_km = 30000
    km_factor = min(1.0, km_per_year / avg_annual_km)
    base_rate = 15 + (km_factor * 15)
    if vehicle_age <= 2:
        annual_rate = base_rate * 1.3
    elif vehicle_age <= 5:
        annual_rate = base_rate
    else:
        annual_rate = base_rate * 0.7
    annual_rate = min(35, max(8, annual_rate))
    depr_curve = []
    val = 100.0
    for yr in range(5):
        val = val * (1 - annual_rate / 100)
        depr_curve.append(max(5, round(val, 1)))
    depr_labels = [str(current_year + i) for i in range(5)]
    current_value_pct = max(5, round(100 - (vehicle_age * annual_rate) - (km_factor * 10), 1))

    is_incomplete = not vin or specs.get("make") == "N/A" or specs.get("model") == "N/A"

    return {
        "device_id": device_id, "name": device_name, "unique_id": device_uniqueid,
        "vin": vin, "vin_source": vin_source, "badge": badge, "specs": specs,
        "is_incomplete": is_incomplete, "odometer_km": total_dist_km,
        "profile_status": "obd_verified" if vin else "incomplete",
        "depreciation": {
            "labels": depr_labels,
            "projected": [round(100 * (1 - (12 + km_factor * 5) / 100) ** i, 1) for i in range(5)],
            "actual": [round(v, 1) for v in depr_curve],
            "current_pct": round(current_value_pct, 1),
        },
        "overspeed_count": overspeed_count, "fdb_data": fdb_data,
        "gps_summary": gps_summary, "recent_alerts": recent_alerts,
    }

# ── PATCH /{device_id}/vin ────────────────────────────────────────────────────
@router.patch("/{device_id}/vin")
async def update_vehicle_vin(
    device_id: int,
    payload: VinUpdatePayload,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    vin = payload.vin.strip().upper()
    if not is_valid_vin(vin):
        raise HTTPException(
            status_code=400,
            detail="Invalid VIN. Must be exactly 17 alphanumeric characters (no I, O, Q)."
        )

    q = select(Device).where(Device.id == device_id)
    res = await db.execute(q)
    record = res.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Device not found.")

    background_tasks.add_task(VINService.process_vin_change, db, device_id, vin, 'manual')
    return {"status": "success", "message": "VIN accepted. Enrichment pipeline started."}

# ── GET /vin/saved (Pinned Dashboard) ────────────────────────────────────────
@router.get("/vin/saved")
async def get_saved_vins(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        q = select(VehicleSpecsCache).where(VehicleSpecsCache.is_pinned == True).order_by(VehicleSpecsCache.created_at.desc())
        res = await db.execute(q)
        rows = res.scalars().all()
        return [{
            "vin": r.vin,
            "brand": r.brand or "Unknown",
            "model": r.model or "Unknown",
            "year": r.year or "N/A",
            "engine": r.engine or "N/A",
            "full_specs": r.full_specs or {},
            "created_at": r.created_at.isoformat() if r.created_at else None
        } for r in rows]
    except Exception as e:
        logger.error(f"Failed to fetch saved VINs: {str(e)}")
        return []

# ── GET /vin/{vin} ──────────────────────────────────────────────────────────
@router.get("/vin/{vin}")
async def get_vin_intelligence(
    vin: str,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    if not is_valid_vin(vin):
        return await VINService.lookup_vin_intelligence(db, vin) # Graceful fallback
    
    return await VINService.lookup_vin_intelligence(db, vin)

# ── POST /vin/{vin}/pin ──────────────────────────────────────────────────────
@router.post("/vin/{vin}/pin")
async def pin_vin(
    vin: str,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    q = select(VehicleSpecsCache).where(VehicleSpecsCache.vin == vin)
    res = await db.execute(q)
    record = res.scalar_one_or_none()

    if not record:
        logger.info(f"Pinning requested for unassigned VIN: {vin}. Fetching intelligence first.")
        # This function commits internally, so we must re-query or merge
        await VINService.lookup_vin_intelligence(db, vin)
        res = await db.execute(q)
        record = res.scalar_one_or_none()

    if not record:
        logger.error(f"Critical failure: VIN {vin} could not be pinned because intelligence lookup failed.")
        raise HTTPException(status_code=404, detail="Vehicle intelligence could not be decoded. Pinning aborted.")

    # Explicitly ensure the record is tracked and updated
    record.is_pinned = True
    db.add(record)
    await db.commit()
    logger.success(f"VIN {vin} successfully pinned to Managed Dashboard.")
    return {"status": "success", "message": "Reconnaissance data pinned to dashboard."}

# ── DELETE /vin/{vin} ────────────────────────────────────────────────────────
@router.delete("/vin/{vin}")
async def unpin_vin(
    vin: str,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    q = select(VehicleSpecsCache).where(VehicleSpecsCache.vin == vin)
    res = await db.execute(q)
    record = res.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="VIN record not found.")
    
    record.is_pinned = False
    await db.commit()
    return {"status": "success", "message": "VIN removed from dashboard."}

# ── GET /{device_id}/profile ──────────────────────────────────────────────────
@router.get("/{device_id}/profile")
async def get_device_profile(
    device_id: int,
    db: AsyncSession = Depends(get_db)
):
    record = None
    try:
        q = select(Device).where(Device.id == device_id)
        res = await db.execute(q)
        record = res.scalar_one_or_none()
    except Exception:
        pass

    if record:
        is_incomplete = not record.vin or not record.manufacturer or not record.model
        parsed_pids = None
        if record.pid_profile:
            try:
                parsed_pids = json.loads(record.pid_profile)
            except Exception:
                pass
        return {
            "device_id": device_id, "vin": record.vin, "vin_source": record.vin_source,
            "manufacturer": record.manufacturer, "model": record.model, "year": record.year,
            "profile_status": record.profile_status, "is_incomplete": is_incomplete,
            "assumptions": {"tank_size_liters": 50.0, "avg_consumption_kml": 10.0},
            "obd_pids": parsed_pids
        }

    try:
        from app.services.traccar_api_client import get_traccar_client
        traccar = await get_traccar_client()
        all_devices = await traccar.get_devices()
        dev = None
        for d in all_devices:
            if d.get("id") == device_id:
                dev = d
                break
        if dev:
            attrs = dev.get("attributes", {}) or {}
            return {
                "device_id": device_id, "vin": attrs.get("vin"), "vin_source": "obd" if attrs.get("vin") else None,
                "manufacturer": attrs.get("make") or dev.get("model") or "N/A",
                "model": dev.get("model") or "N/A", "year": attrs.get("year") or "N/A",
                "profile_status": "incomplete", "is_incomplete": not bool(attrs.get("vin")),
                "assumptions": {"tank_size_liters": 50.0, "avg_consumption_kml": 10.0},
                "obd_pids": None
            }
    except Exception:
        pass

    return {"device_id": device_id, "error": "Device not found", "is_incomplete": True}

# ── PATCH /{device_id} (general update) ──────────────────────────────────────
@router.patch("/{device_id}")
async def update_vehicle(
    device_id: int,
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    retriever = SQLRetriever(db, current_user)
    success = await retriever.update_vehicle(device_id, data)
    if not success:
        return {"error": "Vehicle not found or access denied"}
    return {"message": "Vehicle updated successfully"}

# ── GET /{name} (by name — keep last to avoid routing conflicts) ───────────────
@router.get("/{name}")
async def get_vehicle_by_name(
    name: str,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    retriever = SQLRetriever(db, current_user)
    vehicle = await retriever.get_vehicle_by_name(name)
    if not vehicle:
        return {"error": "Vehicle not found"}
    return vehicle
