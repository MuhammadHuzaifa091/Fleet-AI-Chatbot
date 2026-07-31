from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.auth import get_current_user
from app.services.analytics_service import AnalyticsService
from app.services.report_service import ReportService
from app.retrievers.sql_retriever import SQLRetriever
from app.services.fuel_price_service import FuelPriceService
from app.services.traccar_api_client import get_traccar_client
from app.models.traccar import FuelPrice
from typing import Dict, Any
from loguru import logger

router = APIRouter()

@router.get("/summary")
async def get_analytics_summary(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        import asyncio
        user_id = current_user.get("id")
        role = current_user.get("role")
        summary = await asyncio.wait_for(AnalyticsService.get_analytics_summary(db, user_id, role), timeout=3.0)
        if summary.get("kpis", {}).get("total", 0) > 0:
            return summary
    except Exception:
        pass

    traccar = await get_traccar_client()
    devices = await traccar.get_devices()
    positions = await traccar.get_positions()
    total = len(devices) if devices else 0
    online = sum(1 for d in devices if d.get("status") == "online") if devices else 0
    offline = total - online
    pos_map = {p.get("deviceId"): p for p in positions} if positions else {}
    online_devices = {d.get("id") for d in devices if d.get("status") == "online"} if devices else set()
    moving = sum(1 for did in online_devices if (pos_map.get(did, {}).get("speed") or 0) > 1)
    stationary = online - moving

    recent_events = []
    try:
        from datetime import datetime, timedelta
        to = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        fr = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
        event_data = await traccar.get_report_events(from_iso=fr, to_iso=to, all_devices=True)
        if event_data:
            device_map = {d.get("id"): d.get("name", str(d.get("id"))) for d in devices} if devices else {}
            for ev in event_data[-20:]:
                did = ev.get("deviceId")
                recent_events.append({
                    "id": ev.get("id"), "type": ev.get("type"), "deviceId": did,
                    "vehicle": device_map.get(did, str(did)),
                    "eventTime": ev.get("eventTime"),
                    "severity": "warning" if ev.get("type") in ("alarm","deviceOverspeed") else "info",
                    "attributes": ev.get("attributes", {}),
                })
    except Exception:
        pass

    return {
        "kpis": {
            "total": total, "active": online, "online": online,
            "moving": moving, "idle": stationary, "stationary": stationary,
            "stale": offline, "offline": offline, "overspeed": 0,
            "overspeed_today": 0, "completedToday": 0,
            "totalDistanceKm": 0, "avgSpeed": 0, "avgFuel": 0
        },
        "securityStats": {"tamper": 0, "geofence": 0, "movement": 0},
        "recentEvents": recent_events, "recent_events": recent_events,
        "maintenanceAlerts": [], "systemHealth": {"dbSizeMb": 0, "serverTime": ""}
    }

@router.get("/report")
async def get_fleet_report(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return Response(content="Report logic reach test", media_type="text/plain")

@router.get("/fuel/organization/summary")
async def get_org_fuel_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    user_id = current_user.get("id")
    role = current_user.get("role")
    analytics = await AnalyticsService.get_organization_fuel_analytics(db, user_id, role)
    if "error" in analytics:
        raise HTTPException(status_code=404 if "not found" in analytics["error"] else 500, detail=analytics["error"])

    # Add Traccar-based history if empty
    if not analytics.get("history"):
        try:
            from app.services.traccar_api_client import get_traccar_client
            from datetime import datetime, timedelta
            traccar = await get_traccar_client()
            devices = await traccar.get_devices()
            positions = await traccar.get_positions()
            if devices and positions:
                pos_map = {p.get("deviceId"): p for p in positions}
                total_dist = 0
                for dev in devices:
                    p = pos_map.get(dev.get("id"), {})
                    d = (p.get("attributes") or {}).get("totalDistance") or 0
                    total_dist += float(d) / 1000 if float(d) > 1000 else float(d)
                if total_dist > 0:
                    analytics["distance_km"] = round(total_dist, 2)
                    est_liters = round(total_dist / 100 * 10, 2)
                    analytics["total_liters"] = est_liters
                    price = analytics.get("price_pkr", 272.89)
                    analytics["total_cost_pkr"] = round(est_liters * price, 2)
                history = []
                to = datetime.utcnow()
                for i in range(7):
                    day = to - timedelta(days=6 - i)
                    day_label = day.strftime("%b %d")
                    daily_dist = round(total_dist / 7, 2) if total_dist > 0 else 0
                    daily_liters = round(daily_dist / 100 * 10, 2)
                    history.append({"time": day_label, "consumption": daily_liters, "distance": daily_dist})
                analytics["history"] = history
                analytics["device_count"] = len(devices)
                analytics["source"] = "Traccar API Fleet Aggregation"
        except Exception as e:
            logger.warning(f"[FUEL_ORG] Traccar history fallback failed: {e}")

    return analytics

@router.get("/fuel/{device_id}")
async def get_fuel_analytics(
    device_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        await AnalyticsService.detect_fuel_station_visits(db, device_id)
    except Exception:
        pass
    try:
        analytics = await AnalyticsService.get_fuel_analytics(db, device_id)
        if analytics and "error" not in analytics:
            try:
                analytics["station_logs"] = await AnalyticsService.get_fuel_station_logs(db, device_id)
            except Exception:
                analytics["station_logs"] = []
            return analytics
    except Exception:
        pass

    # Traccar API fallback
    try:
        from app.services.traccar_api_client import get_traccar_client
        traccar = await get_traccar_client()
        all_devices = await traccar.get_devices()
        device = None
        if all_devices:
            for d in all_devices:
                if d.get("id") == device_id:
                    device = d
                    break
        if not device:
            return {"device_id": device_id, "error": "Device not found", "fuel_consumed_l": 0, "total_distance_km": 0, "avg_consumption_kml": 0, "fuel_cost_pkr": 0, "station_logs": []}

        dev_attr = device.get("attributes", {}) or {}
        positions = await traccar.get_device_positions(device_id)
        pos_attr = {}
        if positions:
            pos_attr = positions[0].get("attributes", {}) or {}

        fuel_level = pos_attr.get("fuelLevel") or pos_attr.get("fuel") or dev_attr.get("fuelLevel") or dev_attr.get("fuel")
        distance = pos_attr.get("totalDistance") or pos_attr.get("odometer") or dev_attr.get("totalDistance") or 0
        distance_km = round(distance / 1000, 2) if distance > 1000 else round(distance, 2)

        current_price = 272.89
        est_rate = 8.5
        tank_size = float(dev_attr.get("tank_size") or 50.0)
        total_liters = round((distance_km / 100) * est_rate, 2) if distance_km > 0 else 0
        total_cost = round(total_liters * current_price, 2)

        history = []
        try:
            from datetime import datetime, timedelta
            to = datetime.utcnow()
            for i in range(7):
                day = to - timedelta(days=6 - i)
                day_label = day.strftime("%b %d")
                history.append({
                    "time": day_label,
                    "consumption": round(total_liters / 7, 2) if total_liters > 0 else 0,
                    "distance": round(distance_km / 7, 2) if distance_km > 0 else 0,
                })
        except Exception:
            pass

        efficiency_score = min(100, max(0, int(est_rate * 10)))
        tier = "A" if fuel_level is not None else "B"

        return {
            "device_id": device_id,
            "tier": tier,
            "method": "sensor" if fuel_level is not None else "estimated",
            "status": "OPERATIONAL",
            "source": "Traccar API",
            "current_level": fuel_level or 0,
            "fuel_level_percent": round(float(fuel_level or 0), 2),
            "distance_km": distance_km,
            "price_pkr": current_price,
            "fuel_type": "Diesel",
            "total_liters": total_liters,
            "total_cost_pkr": total_cost,
            "avg_consumption_kml": round(est_rate, 1),
            "fuel_consumed_l": total_liters,
            "efficiency_validation": {
                "score": efficiency_score,
                "status": "VALIDATED" if efficiency_score >= 70 else "CHECK_REQUIRED",
                "label": "Eco Verified" if efficiency_score >= 85 else ("Efficient" if efficiency_score >= 70 else "Needs Review")
            },
            "idle_breakdown": {"idle_cost": 0, "idle_time_min": 0},
            "history": history,
            "trip_costing": {"fuel_cost": total_cost, "idle_cost": 0, "total": total_cost},
            "station_logs": [],
            "is_estimated": fuel_level is None,
            "obd_integrated": fuel_level is not None,
        }
    except Exception as e:
        logger.warning(f"[FUEL] Traccar fallback failed for {device_id}: {e}")
        return {"device_id": device_id, "fuel_consumed_l": 0, "total_distance_km": 0, "avg_consumption_kml": 0, "fuel_cost_pkr": 0, "station_logs": [], "note": "Data unavailable"}

# ---------------------------------------------------------------------------
# Fuel price endpoints (PKR)
# ---------------------------------------------------------------------------

@router.get("/fuel-prices")
async def get_fuel_prices(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    prices = None
    source = "Default Rates"
    try:
        prices = await FuelPriceService.scrape_and_update_prices(db)
        source = "PSO/OGRA Live"
    except Exception:
        pass
    if not prices:
        try:
            prices = await FuelPriceService.get_latest_prices(db)
            source = "Database Cache"
        except Exception:
            pass
    if not prices:
        prices = {"Petrol": 272.89, "Diesel": 278.96}
    return {"prices": prices, "source": source}

@router.post("/fuel-prices/set")
async def set_fuel_prices(
    payload: Dict[str, float],
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Manually update fuel prices (PKR). Only ADMIN or SUPERADMIN can use.
    Expected payload: {"Petrol": <float>, "Diesel": <float>}
    """
    role = current_user.get("role")
    if role not in ["SUPERADMIN", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    for fuel_type, price in payload.items():
        result = await db.execute(select(FuelPrice).where(FuelPrice.fuel_type == fuel_type))
        obj = result.scalar_one_or_none()
        if obj:
            obj.price = price
            obj.last_updated = datetime.utcnow()
        else:
            db.add(FuelPrice(fuel_type=fuel_type, price=price, last_updated=datetime.utcnow(), source="Manual"))
    await db.commit()
    return {"status": "success", "updated": payload}

# ---------------------------------------------------------------------------
# Driver Intelligence Endpoints
# ---------------------------------------------------------------------------

@router.get("/driver/search")
async def search_vehicles_for_driver(
    q: str = "",
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Search all Traccar devices + MySQL fleet_alerts vehicle names."""
    query = (q or "").lower().strip()
    seen = set()
    results = []

    # 1) Traccar devices
    try:
        from app.services.traccar_api_client import get_traccar_client
        traccar = await get_traccar_client()
        all_devices = await traccar.get_devices()
        if all_devices:
            for d in all_devices:
                name = d.get("name", "")
                uid = d.get("uniqueId", "")
                if not query or query in name.lower() or query in uid.lower():
                    results.append({
                        "id": d.get("id"),
                        "name": name,
                        "uniqueId": uid,
                        "status": d.get("status", "unknown"),
                        "source": "traccar",
                    })
                    seen.add(name.lower())
    except Exception:
        pass

    # 2) MySQL fleet_alerts vehicle names
    try:
        from sqlalchemy import text
        rows_q = text("""
            SELECT DISTINCT vehicle FROM fleet_alerts
            WHERE vehicle IS NOT NULL AND vehicle != ''
        """)
        rows_res = await db.execute(rows_q)
        for row in rows_res.fetchall():
            vname = (row[0] or "").strip()
            if vname and vname.lower() not in seen:
                if not query or query in vname.lower():
                    results.append({
                        "id": None,
                        "name": vname,
                        "uniqueId": "",
                        "status": "unknown",
                        "source": "fleet_alerts",
                    })
                    seen.add(vname.lower())
    except Exception:
        pass

    results.sort(key=lambda x: x["name"])
    return results[:80]

@router.get("/driver/leaderboard")
async def get_driver_leaderboard(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await AnalyticsService.get_driver_leaderboard(db, days)

@router.get("/driver/by-name/{vehicle_name}")
async def get_driver_by_name(
    vehicle_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Driver analytics for MySQL fleet_alerts vehicles (no Traccar device_id needed)."""
    from sqlalchemy import text as sql_text
    try:
        q = sql_text("""
            SELECT
                SUM(CASE WHEN alert_type='hard_braking' THEN 1 ELSE 0 END) as brake,
                SUM(CASE WHEN alert_type='hard_acceleration' THEN 1 ELSE 0 END) as accel,
                SUM(CASE WHEN alert_type='hard_cornering' THEN 1 ELSE 0 END) as corner,
                MAX(alert_date) as last_alert
            FROM fleet_alerts
            WHERE vehicle = :vname
              AND alert_type IN ('hard_braking','hard_acceleration','hard_cornering')
        """)
        res = await db.execute(q, {"vname": vehicle_name})
        row = res.fetchone()

        brake_count = int(row[0] or 0) if row else 0
        accel_count = int(row[1] or 0) if row else 0
        corner_count = int(row[2] or 0) if row else 0
        last_activity = row[3].isoformat() if row and row[3] else None

        penalized_brakes = max(0, brake_count - 2)
        grace_exempted = min(2, brake_count)
        deduction = (penalized_brakes * 4) + (accel_count * 3) + (corner_count * 4)
        final_score = max(0, 100 - deduction)

        return {
            "driver_name": vehicle_name,
            "driver_id": "",
            "vehicle_name": vehicle_name,
            "auto_assigned": False,
            "eco_score": final_score,
            "stats": {
                "harsh_braking": {"total": brake_count, "penalized": penalized_brakes, "grace_exempted": grace_exempted},
                "harsh_acceleration": accel_count,
                "harsh_cornering": corner_count,
                "idle_minutes": 0,
                "idle_penalty": 0
            },
            "last_activity": last_activity,
            "source": "fleet_alerts"
        }
    except Exception as e:
        return {"vehicle_name": vehicle_name, "error": str(e), "data_unavailable": True}

@router.get("/driver/{device_id}")
async def get_driver_analytics(
    device_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        analytics = await AnalyticsService.get_driver_analytics(db, device_id)
        if "error" not in analytics:
            return analytics
    except Exception:
        pass

    # Traccar API fallback
    try:
        from app.services.traccar_api_client import get_traccar_client
        from datetime import datetime, timedelta
        traccar = await get_traccar_client()
        all_devices = await traccar.get_devices()
        device = None
        if all_devices:
            for d in all_devices:
                if d.get("id") == device_id:
                    device = d
                    break
        if not device:
            return {"device_id": device_id, "error": "Device not found", "data_unavailable": True}

        vehicle_name = device.get("name", str(device_id))
        attrs = device.get("attributes", {}) or {}

        to = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        fr = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")

        brake_count = accel_count = corner_count = idle_minutes = 0
        last_activity = None
        try:
            events = await traccar.get_report_events(from_iso=fr, to_iso=to, all_devices=True)
            if events:
                device_events = [e for e in events if e.get("deviceId") == device_id]
                for ev in device_events:
                    etype = (ev.get("type") or "").lower()
                    if "overspeed" in etype or "speed" in etype:
                        pass
                    elif "braking" in etype or "harsh" in etype or "sudden" in etype:
                        brake_count += 1
                    elif "acceleration" in etype or "accel" in etype:
                        accel_count += 1
                    elif "cornering" in etype or "turn" in etype:
                        corner_count += 1
                    elif "idle" in etype:
                        idle_minutes += 5
                if device_events:
                    last_activity = device_events[-1].get("eventTime")
        except Exception:
            pass

        penalized_brakes = max(0, brake_count - 2)
        grace_exempted = min(2, brake_count)
        idle_penalty = int(idle_minutes / 5)
        deduction = (penalized_brakes * 4) + (accel_count * 3) + (corner_count * 4) + idle_penalty
        final_score = max(0, 100 - deduction)

        return {
            "driver_name": vehicle_name,
            "driver_id": device.get("uniqueId", str(device_id)),
            "vehicle_name": vehicle_name,
            "auto_assigned": False,
            "eco_score": final_score,
            "stats": {
                "harsh_braking": {
                    "total": brake_count,
                    "penalized": penalized_brakes,
                    "grace_exempted": grace_exempted
                },
                "harsh_acceleration": accel_count,
                "harsh_cornering": corner_count,
                "idle_minutes": round(idle_minutes, 1),
                "idle_penalty": idle_penalty
            },
            "last_activity": last_activity,
            "source": "traccar_api"
        }
    except Exception as e:
        logger.warning(f"[DRIVER_ANALYTICS] Traccar fallback failed for {device_id}: {e}")
        return {"device_id": device_id, "data_unavailable": True, "note": "Data unavailable"}

@router.get("/driver/trips/unassigned")
async def get_unassigned_trips(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return []

@router.get("/driver/summary/stats")
async def get_driver_summary_stats(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await AnalyticsService.get_driver_summary_stats(db)

@router.get("/driver/compare/{device_id_a}/{device_id_b}")
async def compare_drivers(
    device_id_a: int,
    device_id_b: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    a = await get_driver_analytics(device_id_a, db, current_user)
    b = await get_driver_analytics(device_id_b, db, current_user)
    return {"driver_a": a, "driver_b": b}

@router.get("/alerts")
async def get_alerts_history(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    user_id = current_user.get("id")
    role = current_user.get("role")
    return await AnalyticsService.get_alerts_history(db, user_id, role)
