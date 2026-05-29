from fastapi import APIRouter, Depends, Body, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.api.auth import get_current_user
from app.retrievers.sql_retriever import SQLRetriever
from app.models.traccar import Device, Position, VehicleSpecsCache
from app.services.vin_service import VINService
from typing import Dict, Any
import re
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

# ── GET /{device_id}/intel ────────────────────────────────────────────────────
# Full enriched profile: VIN badge, specs (from DB cache), depreciation data
@router.get("/{device_id}/intel")
async def get_vehicle_intel(
    device_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
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

    # --- VIN resolution: native DB column first, then attributes ---
    vin        = device.vin or pos_attr.get("obdVin") or pos_attr.get("io256") or dev_attr.get("vin")
    vin_source = device.vin_source  # 'obd' | 'manual' | None

    # --- Determine badge ---
    if vin_source == "obd":
        badge = {"label": "⚡ ECU Verified", "class": "success"}
    elif vin_source == "manual":
        badge = {"label": "🤖 Profile Synced", "class": "primary"}
    else:
        badge = {"label": "⚠️ Profile Incomplete", "class": "warning"}

    # --- Specs (from cached DB columns) ---
    pid_profile_data = {}
    if device.pid_profile:
        try:
            pid_profile_data = json.loads(device.pid_profile)
        except Exception:
            pass

    displacement = pid_profile_data.get("displacement_l") or "N/A"
    fuel_type    = pid_profile_data.get("fuel_type")      or "N/A"

    specs = {
        "make":       device.manufacturer or "N/A",
        "model":      device.model        or dev_attr.get("model") or "N/A",
        "year":       device.year         or dev_attr.get("year")  or None,
        "engine":     f"{displacement}L" if displacement != "N/A" else "N/A",
        "fuel_type":  fuel_type,
        "category":   device.category     or "N/A",
    }

    # --- Odometer / usage for depreciation graph ---
    total_dist_m  = pos_attr.get("totalDistance") or 0       # metres
    total_dist_km = round(total_dist_m / 1000, 1)

    # Simple depreciation model (can be improved):
    # Linear: vehicle is worth 100% at 0 km, depreciates ~1% per 2 000 km, floor 10%
    current_year = 2026
    vehicle_age  = (current_year - device.year) if device.year else 0
    km_depr      = min(90, total_dist_km / 2000)          # max 90% from km
    age_depr     = min(50, vehicle_age * 5)                # max 50% from age (5%/yr)
    current_value_pct = max(10, 100 - km_depr - age_depr)

    # Build a 5-point depreciation curve (years 0..4 from baseline)
    depr_curve = []
    for i in range(5):
        yr_val = max(10, 100 - (age_depr + i * 5) - km_depr)
        depr_curve.append(round(yr_val, 1))

    depr_labels = [str(current_year - vehicle_age + i) for i in range(5)] if device.year else [f"Y{i+1}" for i in range(5)]

    # --- Is profile complete? ---
    is_incomplete = not vin or not device.manufacturer or not device.model

    return {
        "device_id":        device_id,
        "name":             device.name,
        "unique_id":        device.uniqueid,
        "vin":              vin,
        "vin_source":       vin_source,
        "badge":            badge,
        "specs":            specs,
        "is_incomplete":    is_incomplete,
        "odometer_km":      total_dist_km,
        "profile_status":   device.profile_status,
        "depreciation": {
            "labels":          depr_labels,
            "projected":       [round(100 - i*7, 1) for i in range(5)],  # expected norm
            "actual":          depr_curve,
            "current_pct":     round(current_value_pct, 1),
        }
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
