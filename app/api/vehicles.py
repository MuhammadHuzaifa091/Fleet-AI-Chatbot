from fastapi import APIRouter, Depends, Body, BackgroundTasks, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.api.auth import get_current_user
from app.retrievers.sql_retriever import SQLRetriever
from app.models.traccar import Device, Position, VehicleSpecsCache
from app.services.vin_service import VINService
from typing import Dict, Any
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
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
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
                "id": p.id,
                "deviceId": p.deviceid,
                "fixTime": p.fixtime.isoformat() if p.fixtime else None,
                "latitude": p.latitude,
                "longitude": p.longitude,
                "altitude": p.altitude,
                "speed": round((p.speed or 0) * 1.852, 2),  # knots → km/h
                "course": p.course,
                "valid": p.valid,
                "attributes": p.attributes or {},
            }
            for p in positions
            if p.latitude and p.longitude
        ]
    except Exception as e:
        logger.error(f"[POSITIONS] Error fetching positions for device {deviceId}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /{device_id}/intel ────────────────────────────────────────────────────
# Full enriched profile: VIN badge, specs (from DB cache), depreciation data
@router.get("/{device_id}/intel")
async def get_vehicle_intel(
    device_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    import asyncio

    # Join device + latest position in one query
    q = (
        select(Device, Position)
        .outerjoin(Position, Device.positionid == Position.id)
        .where(Device.id == device_id, Device.disabled == False)
    )
    res = await db.execute(q)
    row = res.first()
    if not row:
        raise HTTPException(status_code=404, detail="Device not found.")

    device, position = row
    pos_attr  = position.attributes  if position else {}
    dev_attr  = device.attributes    or {}

    # --- Parallel fetch: IMEI mapping, overspeed count, GPS summary, alerts ---
    from sqlalchemy import text

    alias_task = db.execute(text("SELECT alias_name FROM ke_vehicle_imei WHERE imei = :imei LIMIT 1"), {"imei": device.uniqueid})
    overspeed_task = db.execute(text("""
        SELECT COUNT(*) FROM tc_events
        WHERE deviceid = :did AND type = 'alarm' AND eventtime >= DATE_SUB(NOW(), INTERVAL 30 DAY)
          AND (attributes LIKE '%overspeed%' OR attributes LIKE '%speed%')
    """), {"did": device_id})
    gps_task = db.execute(text("""
        SELECT AVG(total_distance_km), MAX(max_speed_kmh), AVG(avg_speed_kmh),
               SUM(speed_violations), COUNT(*)
        FROM ke_gps_daily WHERE device_id = :did AND record_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
    """), {"did": device_id})

    alias_res, os_res, gs_res = await asyncio.gather(alias_task, overspeed_task, gps_task)

    alias_row = alias_res.fetchone()
    lookup_name = alias_row[0] if alias_row else None
    overspeed_count = (os_res.fetchone()[0] or 0) if os_res else 0

    gs_row = gs_res.fetchone() if gs_res else None
    gps_summary = {}
    if gs_row and gs_row[0] is not None:
        gps_summary = {
            "avg_daily_km": round(float(gs_row[0]), 1),
            "max_speed_7d": round(float(gs_row[1]), 1),
            "avg_speed_7d": round(float(gs_row[2]), 1),
            "speed_violations_7d": int(gs_row[3] or 0),
            "days_active_7d": int(gs_row[4]),
        }

    # --- FDB data (only if alias found) ---
    fdb_data = {}
    if lookup_name:
        try:
            fdb_result = await db.execute(text("""
                SELECT vehicle_registration, benchmark_kmpl, allocated_km,
                       shift_type, shift_hrs, fuel_type, tonnage,
                       vehicle_category, vehicle_type, make, model_year,
                       fleet_group, region, cluster, tracker_vendor
                FROM ke_fleet_database
                WHERE vehicle_registration = :vname LIMIT 1
            """), {"vname": lookup_name})
            fdb_row = fdb_result.fetchone()
            if fdb_row:
                fdb_data = {
                    "vehicle_registration": fdb_row[0], "benchmark_kmpl": fdb_row[1],
                    "allocated_km": fdb_row[2], "shift_type": fdb_row[3], "shift_hrs": fdb_row[4],
                    "fuel_type": fdb_row[5], "tonnage": fdb_row[6], "category": fdb_row[7],
                    "vehicle_type": fdb_row[8], "make": fdb_row[9], "model_year": fdb_row[10],
                    "fleet_group": fdb_row[11], "region": fdb_row[12], "cluster": fdb_row[13],
                    "tracker_vendor": fdb_row[14],
                }
        except Exception as e:
            logger.error(f"[INTEL] FDB lookup error: {e}")

    # --- Recent alerts ---
    recent_alerts = []
    if lookup_name:
        try:
            ra_result = await db.execute(text("""
                SELECT alert_type, severity, title, created_at
                FROM fleet_alerts WHERE vehicle = :vname ORDER BY created_at DESC LIMIT 10
            """), {"vname": lookup_name})
            for r in ra_result.fetchall():
                recent_alerts.append({
                    "type": r[0], "severity": r[1], "title": r[2],
                    "time": str(r[3]) if r[3] else None
                })
        except Exception:
            pass

    # --- VIN ---
    vin = device.vin or pos_attr.get("obdVin") or pos_attr.get("io256") or dev_attr.get("vin")
    vin_source = device.vin_source or ("obd" if vin else None)

    if vin_source == "obd":
        badge = {"label": "ECU Verified", "class": "success"}
    elif vin_source == "manual":
        badge = {"label": "Profile Synced", "class": "primary"}
    else:
        badge = {"label": "Profile Incomplete", "class": "warning"}

    # --- Specs ---
    pid_profile_data = {}
    if device.pid_profile:
        try: pid_profile_data = json.loads(device.pid_profile)
        except: pass

    displacement = pid_profile_data.get("displacement_l") or "N/A"
    fuel_type = pid_profile_data.get("fuel_type") or fdb_data.get("fuel_type") or "N/A"

    specs = {
        "make": device.manufacturer or fdb_data.get("make") or "N/A",
        "model": device.model or dev_attr.get("model") or fdb_data.get("vehicle_type") or "N/A",
        "year": device.year or dev_attr.get("year") or fdb_data.get("model_year") or "N/A",
        "engine": f"{displacement}L" if displacement != "N/A" else "N/A",
        "fuel_type": fuel_type,
        "category": device.category or fdb_data.get("category") or "N/A",
    }

    # --- Odometer ---
    total_dist_m = pos_attr.get("totalDistance") or 0
    total_dist_km = round(total_dist_m / 1000, 1)
    if total_dist_km <= 0 and fdb_data.get("allocated_km"):
        total_dist_km = float(fdb_data.get("allocated_km") or 120000)

    # --- Depreciation ---
    current_year = datetime.now().year
    try: vy = int(specs["year"])
    except: vy = current_year
    vehicle_age = max(0, current_year - vy)
    km_depr = min(90, total_dist_km / 2000) if total_dist_km > 0 else 15
    age_depr = min(50, vehicle_age * 5)
    current_value_pct = max(10, 100 - km_depr - age_depr)
    depr_curve = [max(10, 100 - (age_depr + i * 5) - km_depr) for i in range(5)]
    depr_labels = [str(vy + i) for i in range(5)]

    is_incomplete = not vin or specs.get("make") == "N/A" or specs.get("model") == "N/A"

    return {
        "device_id": device_id, "name": device.name, "unique_id": device.uniqueid,
        "vin": vin, "vin_source": vin_source, "badge": badge, "specs": specs,
        "is_incomplete": is_incomplete, "odometer_km": total_dist_km,
        "profile_status": device.profile_status or "obd_verified",
        "depreciation": {
            "labels": depr_labels,
            "projected": [round(100 - i*7, 1) for i in range(5)],
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
    q = select(Device).where(Device.id == device_id)
    res = await db.execute(q)
    record = res.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Device not found.")

    is_incomplete = not record.vin or not record.manufacturer or not record.model

    parsed_pids = None
    if record.pid_profile:
        try:
            parsed_pids = json.loads(record.pid_profile)
        except Exception:
            pass

    return {
        "device_id":      device_id,
        "vin":            record.vin,
        "vin_source":     record.vin_source,
        "manufacturer":   record.manufacturer,
        "model":          record.model,
        "year":           record.year,
        "profile_status": record.profile_status,
        "is_incomplete":  is_incomplete,
        "assumptions": {
            "tank_size_liters":    50.0,
            "avg_consumption_kml": 10.0
        },
        "obd_pids": parsed_pids
    }

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
