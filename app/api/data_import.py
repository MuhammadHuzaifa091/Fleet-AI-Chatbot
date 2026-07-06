"""
Data Import API Router
======================
Prefix: /api/fleet/fdb/
Endpoints:
  POST /api/fleet/fdb/fdb-upload     — Upload FDB Excel (smart diff import)
  GET  /api/fleet/fdb/fdb-stats      — Get FDB table stats
  GET  /api/fleet/fdb/ke-vehicles    — Get KE vehicle registrations for filtering
  GET  /api/fleet/fdb/ke-live        — KE fleet live status (fast, no position join)
  GET  /api/fleet/fdb/data-explorer  — Paginated vehicle data with filters
  GET  /api/fleet/fdb/daily-ops      — Get daily operations
  POST /api/fleet/fdb/daily-ops      — Insert/update daily operations
  POST /api/fleet/fdb/fuel-upload    — Upload fuel transaction Excel
  GET  /api/fleet/fdb/fuel-stats     — Fuel transaction summary stats
  GET  /api/fleet/fdb/fuel-transactions — Paginated fuel transactions
  GET  /api/fleet/fdb/kemis-stats    — KEMIS MIS summary stats
  GET  /api/fleet/fdb/kemis-data     — Paginated KEMIS data
  GET  /api/fleet/fdb/kemis-vehicle/{vehicle} — Vehicle KEMIS breakdown
  GET  /api/fleet/fdb/kemis-efficiency — Top/bottom vehicles by benchmark
  GET  /api/fleet/fdb/kemis-vendor-trend — Vendor-filtered trend data
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import SessionLocal
from app.db.session import get_db
import json
import time
from app.api.auth import get_current_user
from app.services.data_import_service import parse_fdb_excel, import_fdb_to_db, parse_fuel_excel, import_fuel_to_db
from app.services.mis_service import MISService
from typing import Dict, Any
import traceback
from loguru import logger

router = APIRouter()


@router.post("/fdb-upload")
async def upload_fdb(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Upload FDB Excel file. Smart diff-based — only updates changed rows.
    Accepts .xlsx files with an 'FDB' sheet.
    """
    if current_user.get("role") not in ["SUPERADMIN", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Only administrators can upload fleet data.")

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx) are supported.")

    try:
        file_bytes = await file.read()
        if len(file_bytes) < 100:
            raise HTTPException(status_code=400, detail="File appears to be empty.")

        # Parse Excel
        rows, sheet_name = await parse_fdb_excel(file_bytes)

        if not rows:
            raise HTTPException(status_code=400, detail="No valid vehicle rows found in the Excel file.")

        # Import to DB with smart diff
        summary = await import_fdb_to_db(db, rows)
        summary["sheet_name"] = sheet_name
        summary["filename"] = file.filename

        return {
            "status": "success",
            "message": (
                f"FDB import complete: {summary['inserted']} new vehicles added, "
                f"{summary['updated']} updated, {summary['unchanged']} unchanged, "
                f"{summary['errors']} errors."
            ),
            "summary": summary,
        }

    except HTTPException:
        raise
    except Exception as exc:
        tb = traceback.format_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Import failed: {str(exc)}",
        )


@router.get("/fdb-stats")
async def get_fdb_stats(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get summary stats for ke_fleet_database table — optimized."""
    try:
        combined = await db.execute(text("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN benchmark_kmpl IS NOT NULL THEN 1 END) as with_benchmark,
                COUNT(CASE WHEN shift_hrs IS NOT NULL THEN 1 END) as with_shift
            FROM ke_fleet_database
        """))
        c = combined.fetchone()

        categories = await db.execute(text("SELECT vehicle_category, COUNT(*) FROM ke_fleet_database GROUP BY vehicle_category ORDER BY COUNT(*) DESC"))
        cat_stats = [{"category": r[0] or "Unknown", "count": r[1]} for r in categories.fetchall()]

        vendors = await db.execute(text("SELECT fleet_vendor, COUNT(*) FROM ke_fleet_database GROUP BY fleet_vendor ORDER BY COUNT(*) DESC LIMIT 8"))
        vendor_stats = [{"vendor": r[0] or "Unknown", "count": r[1]} for r in vendors.fetchall()]

        return {
            "total_vehicles": c[0], "with_benchmark": c[1], "with_shift_data": c[2],
            "categories": cat_stats, "top_vendors": vendor_stats,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(exc)}")


@router.get("/ke-vehicles")
async def get_ke_vehicle_names(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Return all KE vehicle registrations + IMEIs for filtering live Traccar data."""
    try:
        result = await db.execute(text("""
            SELECT DISTINCT f.vehicle_registration, COALESCE(m.imei, '') as imei
            FROM ke_fleet_database f
            LEFT JOIN ke_vehicle_imei m ON f.vehicle_registration = m.alias_name
        """))
        rows = result.fetchall()
        vehicles = []
        names_set = set()
        imeis_set = set()
        for r in rows:
            name = (r[0] or '').upper().strip()
            imei = (r[1] or '').strip()
            vehicles.append({"name": name, "imei": imei})
            if name: names_set.add(name)
            if imei: imeis_set.add(imei)
        return {"vehicles": vehicles, "names": list(names_set), "imeis": list(imeis_set), "count": len(names_set)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/ke-live")
async def get_ke_live_status(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get live status of KE fleet vehicles directly from DB (fast, no position join)."""
    try:
        result = await db.execute(text("""
            SELECT 
                m.alias_name as ke_registration,
                d.name as device_name,
                d.uniqueid,
                d.status,
                d.lastupdate,
                d.id as device_id
            FROM tc_devices d
            INNER JOIN ke_vehicle_imei m ON d.uniqueid = m.imei
            WHERE d.disabled = 0
            ORDER BY d.lastupdate DESC
        """))
        rows = result.fetchall()
        vehicles = []
        online_count = 0
        for r in rows:
            status = r[3] or 'unknown'
            if status == 'online':
                online_count += 1
            vehicles.append({
                "keName": r[0],
                "name": r[1],
                "uniqueId": r[2],
                "status": status,
                "lastUpdate": str(r[4]) if r[4] else None,
                "deviceId": r[5]
            })
        return {
            "vehicles": vehicles,
            "total": len(vehicles),
            "online": online_count,
            "offline": len(vehicles) - online_count
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


async def _run_mis_bg(dt, date_str):
    """Background execution of MIS sync to prevent frontend timeout"""
    try:
        async with SessionLocal() as db:
            await MISService.generate_daily_mis(db, dt)
    except Exception as exc:
        logger.error(f"[MIS-AUTO-BG] Sync failed for {date_str}: {exc}")

@router.post("/kemis-sync")
async def sync_fleet_mis(
    background_tasks: BackgroundTasks,
    target_date: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Trigger automated MIS generation for the entire fleet from live telemetry.
    If target_date is not provided, syncs for yesterday.
    Executes in the background due to potential long execution times.
    """
    if current_user.get("role") not in ["SUPERADMIN", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Only administrators can trigger fleet sync.")

    try:
        dt = None
        if target_date:
            from datetime import datetime
            dt = datetime.strptime(target_date, "%Y-%m-%d").date()
        else:
            from datetime import datetime, timedelta
            dt = (datetime.now() - timedelta(days=1)).date()
            
        date_str = dt.strftime("%Y-%m-%d")
        
        # Add the sync generator to the background tasks list
        background_tasks.add_task(_run_mis_bg, dt, date_str)
        
        return {
            "status": "success",
            "message": f"Sync started for {date_str}. Traccar telemetry is being processed in the background.",
            "summary": {"processed": "pending", "date": date_str}
        }
    except Exception as exc:
        logger.error(f"MIS Sync Failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/generate-mis/{vehicle}")
async def generate_mis_from_db(
    vehicle: str,
    start_date: str = None,
    end_date: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Generate MIS directly from Traccar raw data + KE fleet database. No file upload needed.
    Tries ke_gps_daily first (instant), falls back to tc_positions (slow)."""
    try:
        vehicle = vehicle.upper().strip()
        if not start_date:
            start_date = "2026-06-01"
        if not end_date:
            from datetime import datetime, timedelta
            end_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        vinfo = await db.execute(text("""
            SELECT f.vehicle_registration, f.benchmark_kmpl, f.shift_hrs,
                   f.vehicle_category, f.fleet_vendor, f.fleet_group, f.cluster,
                   m.imei
            FROM ke_fleet_database f
            LEFT JOIN ke_vehicle_imei m ON f.vehicle_registration = m.alias_name
            WHERE f.vehicle_registration = :v
        """), {"v": vehicle})
        vrow = vinfo.fetchone()
        if not vrow:
            raise HTTPException(status_code=404, detail=f"Vehicle {vehicle} not found in KE fleet database")

        benchmark = float(vrow[1]) if vrow[1] else 10.0
        shift_hrs = float(vrow[2]) if vrow[2] else 10.0
        category = vrow[3] or "Unknown"
        vendor = vrow[4] or "Unknown"
        fleet_group = vrow[5] or "Unknown"
        cluster = vrow[6] or "Unknown"
        imei = vrow[7]

        if not imei:
            raise HTTPException(status_code=404, detail=f"No IMEI mapping found for {vehicle}")

        dev = await db.execute(text("SELECT id FROM tc_devices WHERE uniqueid = :imei"), {"imei": imei})
        drow = dev.fetchone()
        if not drow:
            raise HTTPException(status_code=404, detail=f"No Traccar device found for IMEI {imei}")
        device_id = drow[0]

        # Try ke_gps_daily first (instant)
        gps_result = await db.execute(text("""
            SELECT record_date, total_positions, total_distance_km, on_peak_km, off_peak_km,
                   max_speed_kmh, avg_speed_kmh, speed_violations
            FROM ke_gps_daily
            WHERE device_id = :did AND record_date >= :sd AND record_date <= :ed
            ORDER BY record_date ASC
        """), {"did": device_id, "sd": start_date, "ed": end_date})
        gps_rows = gps_result.fetchall()

        source = "ke_gps_daily"
        if not gps_rows:
            # Fallback to tc_positions (slow)
            source = "tc_positions"
            positions = await db.execute(text("""
                SELECT DATE(devicetime) as pos_date, speed, devicetime
                FROM (
                    SELECT DATE(devicetime) as pos_date, speed, devicetime,
                        ROW_NUMBER() OVER (
                            PARTITION BY DATE(devicetime), FLOOR(UNIX_TIMESTAMP(devicetime)/600)
                            ORDER BY devicetime
                        ) as rn
                    FROM tc_positions
                    WHERE deviceid = :did
                      AND devicetime >= :sd
                      AND devicetime < DATE_ADD(:ed, INTERVAL 1 DAY)
                ) sub
                WHERE rn = 1
                ORDER BY devicetime ASC
            """), {"did": device_id, "sd": start_date, "ed": end_date})
            pos_rows = positions.fetchall()

            daily_data = {}
            prev_speed_kmh = None
            prev_devicetime = None
            prev_date = None

            for pr in pos_rows:
                pdate = str(pr[0])
                speed_knots = pr[1] or 0
                speed_kmh = speed_knots * 1.852
                devicetime = pr[2]

                if pdate not in daily_data:
                    daily_data[pdate] = {
                        "record_date": pdate,
                        "positions_count": 0,
                        "total_distance_km": 0,
                        "max_speed_kmh": 0,
                        "speed_sum": 0,
                        "on_peak_km": 0,
                        "off_peak_km": 0,
                        "idle_count": 0,
                        "speed_violations": 0,
                    }
                    prev_speed_kmh = None
                    prev_devicetime = None
                    prev_date = None

                d = daily_data[pdate]
                d["positions_count"] += 1
                d["speed_sum"] += speed_kmh

                if speed_kmh > d["max_speed_kmh"]:
                    d["max_speed_kmh"] = speed_kmh

                if speed_kmh == 0:
                    d["idle_count"] += 1

                if speed_kmh > 120:
                    d["speed_violations"] += 1

                dist_km = 0
                if prev_speed_kmh is not None and prev_devicetime is not None and prev_date == pdate:
                    time_delta_sec = (devicetime - prev_devicetime).total_seconds()
                    if 0 < time_delta_sec < 1800:
                        avg_spd = (prev_speed_kmh + speed_kmh) / 2.0
                        dist_km = avg_spd * (time_delta_sec / 3600.0)

                hour = devicetime.hour if devicetime else 12
                if dist_km > 0:
                    if 6 <= hour < 18:
                        d["on_peak_km"] += dist_km
                    else:
                        d["off_peak_km"] += dist_km
                    d["total_distance_km"] += dist_km

                prev_speed_kmh = speed_kmh
                prev_devicetime = devicetime
                prev_date = pdate

            gps_rows = []
            save_rows = []
            for pdate in sorted(daily_data.keys()):
                d = daily_data[pdate]
                avg_spd = d['speed_sum'] / d['positions_count'] if d['positions_count'] else 0
                gps_rows.append(type('Row', (), {
                    'record_date': d['record_date'],
                    'total_positions': d['positions_count'],
                    'total_distance_km': d['total_distance_km'],
                    'on_peak_km': d['on_peak_km'],
                    'off_peak_km': d['off_peak_km'],
                    'max_speed_kmh': d['max_speed_kmh'],
                    'avg_speed_kmh': avg_spd,
                    'speed_violations': d['speed_violations'],
                })())
                save_rows.append((device_id, pdate, d['positions_count'],
                    round(d['total_distance_km'], 2), round(d['on_peak_km'], 2),
                    round(d['off_peak_km'], 2), round(d['max_speed_kmh'], 1),
                    round(avg_spd, 1), d['speed_violations']))

            if save_rows:
                try:
                    for sr in save_rows:
                        await db.execute(text("""
                            INSERT IGNORE INTO ke_gps_daily
                            (device_id, record_date, total_positions, total_distance_km,
                             on_peak_km, off_peak_km, max_speed_kmh, avg_speed_kmh, speed_violations)
                            VALUES (:did, :rd, :tp, :tdk, :opk, :fpk, :msk, :ask, :sv)
                        """), {"did": sr[0], "rd": sr[1], "tp": sr[2], "tdk": sr[3],
                               "opk": sr[4], "fpk": sr[5], "msk": sr[6], "ask": sr[7], "sv": sr[8]})
                    await db.commit()
                except Exception:
                    pass

        records = []
        for gr in gps_rows:
            total_km = round(float(gr.total_distance_km), 2)
            fuel_consumed = round(total_km / benchmark, 2) if benchmark > 0 else 0
            records.append({
                "record_date": str(gr.record_date),
                "vehicle": vehicle,
                "vendor": vendor,
                "category": category,
                "fleet_group": fleet_group,
                "cluster": cluster,
                "benchmark": benchmark,
                "shift_hrs": shift_hrs,
                "total_km": total_km,
                "on_peak_km": round(float(gr.on_peak_km), 2),
                "off_peak_km": round(float(gr.off_peak_km), 2),
                "avg_speed_kmh": round(float(gr.avg_speed_kmh), 1),
                "max_speed_kmh": round(float(gr.max_speed_kmh), 1),
                "fuel_consumed": fuel_consumed,
                "speed_violations": gr.speed_violations,
                "idle_positions": 0,
                "total_positions": gr.total_positions,
                "efficiency_kmpl": round(total_km / fuel_consumed, 2) if fuel_consumed > 0 else 0,
            })

        total_km_all = sum(r["total_km"] for r in records)
        total_fuel_all = sum(r["fuel_consumed"] for r in records)
        on_peak_all = sum(r["on_peak_km"] for r in records)
        off_peak_all = sum(r["off_peak_km"] for r in records)
        violations_all = sum(r["speed_violations"] for r in records)

        return {
            "vehicle": vehicle,
            "benchmark": benchmark,
            "category": category,
            "vendor": vendor,
            "cluster": cluster,
            "source": source,
            "date_range": {"start": start_date, "end": end_date},
            "summary": {
                "total_days": len(records),
                "total_km": round(total_km_all, 2),
                "total_fuel_consumed": round(total_fuel_all, 2),
                "avg_efficiency": round(total_km_all / total_fuel_all, 2) if total_fuel_all > 0 else 0,
                "on_peak_km": round(on_peak_all, 2),
                "off_peak_km": round(off_peak_all, 2),
                "on_peak_pct": round(on_peak_all / total_km_all * 100, 1) if total_km_all > 0 else 0,
                "off_peak_pct": round(off_peak_all / total_km_all * 100, 1) if total_km_all > 0 else 0,
                "total_speed_violations": violations_all,
                "benchmark_diff": round((total_km_all / total_fuel_all) - benchmark, 2) if total_fuel_all > 0 and benchmark > 0 else 0,
            },
            "records": records,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate MIS: {str(exc)}")


def _batch_generate_mis_sync(start_date: str, end_date: str):
    """Synchronous batch: generate MIS for ALL KE vehicles one device at a time.
    Proven approach — same query that works for single vehicle generate-mis."""
    import pymysql
    from app.core.config import settings as _settings
    try:
        conn = pymysql.connect(
            host=_settings.DB_SERVER, port=_settings.DB_PORT,
            user=_settings.DB_USER, password=_settings.DB_PASSWORD,
            database=_settings.DB_NAME, charset='utf8mb4',
            connect_timeout=30
        )
        cursor = conn.cursor()
        cursor.execute("""
            SELECT f.vehicle_registration, f.benchmark_kmpl, f.shift_hrs,
                   f.vehicle_category, f.fleet_vendor, f.fleet_group, f.cluster,
                   d.id as device_id
            FROM ke_fleet_database f
            JOIN ke_vehicle_imei m ON f.vehicle_registration = m.alias_name
            JOIN tc_devices d ON d.uniqueid = m.imei
        """)
        vehicles = cursor.fetchall()
        total = len(vehicles)
        inserted = 0
        all_rows = []
        logger.info(f"[BATCH-MIS] Starting for {total} vehicles, {start_date} to {end_date}")

        for idx, v in enumerate(vehicles):
            vehicle_reg = v[0]
            benchmark = float(v[1]) if v[1] else 10.0
            shift_hrs = float(v[2]) if v[2] else 10.0
            category = v[3] or "Unknown"
            vendor = v[4] or "Unknown"
            fleet_group = v[5] or "Unknown"
            cluster = v[6] or "Unknown"
            device_id = v[7]

            cursor.execute("""
                SELECT record_date, total_distance_km, on_peak_km, off_peak_km, speed_violations
                FROM ke_gps_daily
                WHERE device_id = %s AND record_date >= %s AND record_date <= %s
            """, (device_id, start_date, end_date))
            gps_rows = cursor.fetchall()

            if not gps_rows:
                cursor.execute("""
                    SELECT DATE(devicetime) as pos_date, speed, devicetime FROM (
                        SELECT DATE(devicetime) as pos_date, speed, devicetime,
                            ROW_NUMBER() OVER (
                                PARTITION BY DATE(devicetime), FLOOR(UNIX_TIMESTAMP(devicetime)/600)
                                ORDER BY devicetime
                            ) as rn
                        FROM tc_positions
                        WHERE deviceid = %s AND devicetime >= %s AND devicetime < DATE_ADD(%s, INTERVAL 1 DAY)
                    ) sub WHERE rn = 1 ORDER BY devicetime ASC
                """, (device_id, start_date, end_date))
                pos_rows = cursor.fetchall()

                daily = {}
                prev_speed = None
                prev_time = None
                prev_date = None

                for pr in pos_rows:
                    pdate = str(pr[0])
                    speed_kmh = (pr[1] or 0) * 1.852
                    dt = pr[2]

                    if pdate not in daily:
                        daily[pdate] = {"km": 0, "on_peak": 0, "off_peak": 0, "violations": 0, "cnt": 0, "spd_sum": 0, "max_spd": 0}
                        prev_speed = None
                        prev_time = None
                        prev_date = None

                    d = daily[pdate]
                    d["cnt"] += 1
                    d["spd_sum"] += speed_kmh
                    if speed_kmh > d["max_spd"]: d["max_spd"] = speed_kmh
                    if speed_kmh > 120: d["violations"] += 1

                    dist = 0
                    if prev_speed is not None and prev_time is not None and prev_date == pdate:
                        td = (dt - prev_time).total_seconds()
                        if 0 < td < 1800:
                            dist = ((prev_speed + speed_kmh) / 2.0) * (td / 3600.0)

                    hour = dt.hour if dt else 12
                    if dist > 0:
                        d["km"] += dist
                        if 6 <= hour < 18: d["on_peak"] += dist
                        else: d["off_peak"] += dist

                    prev_speed = speed_kmh
                    prev_time = dt
                    prev_date = pdate

                for pdate in sorted(daily.keys()):
                    d = daily[pdate]
                    avg_spd = d["spd_sum"] / d["cnt"] if d["cnt"] else 0
                    try:
                        cursor.execute("""
                            INSERT IGNORE INTO ke_gps_daily
                            (device_id, record_date, total_positions, total_distance_km,
                             on_peak_km, off_peak_km, max_speed_kmh, avg_speed_kmh, speed_violations)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (device_id, pdate, d["cnt"], round(d["km"], 2),
                              round(d["on_peak"], 2), round(d["off_peak"], 2),
                              round(d["max_spd"], 1), round(avg_spd, 1), d["violations"]))
                    except Exception:
                        pass
                    gps_rows.append(type('Row', (), {
                        'record_date': pdate, 'total_distance_km': d['km'],
                        'on_peak_km': d['on_peak'], 'off_peak_km': d['off_peak'],
                        'speed_violations': d['violations']
                    })())
                conn.commit()

            for gr in gps_rows:
                pdate = str(gr.record_date)
                km = round(float(gr.total_distance_km), 2)
                if km < 0.1:
                    continue
                fc = round(km / benchmark, 2) if benchmark > 0 else 0
                all_rows.append((
                    pdate, vehicle_reg, vendor, category,
                    fleet_group, cluster, shift_hrs, benchmark,
                    round(float(gr.on_peak_km), 2), round(float(gr.off_peak_km), 2), km,
                    fc, gr.speed_violations
                ))
                inserted += 1

            if len(all_rows) >= 500:
                cursor.executemany("""
                    INSERT IGNORE INTO ke_mis_daily (record_date, vehicle, hired_own, vendor, tracker_company, category,
                        fleet_group, cluster, shift_hrs, benchmark,
                        on_off_road, peak_hour, peak_off, total_km,
                        fuel_drawn, fuel_consumed, fuel_difference,
                        speed_violation, remarks, is_reporting, travel_time_mins)
                    VALUES (%s, %s, 'Hired', %s, 'Traccar', %s,
                        %s, %s, %s, %s,
                        'On Road', %s, %s, %s,
                        0, %s, 0,
                        %s, 'Reporting', 1, 0)
                """, all_rows)
                conn.commit()
                all_rows = []
                logger.info(f"[BATCH-MIS] Progress: {idx+1}/{total} vehicles, {inserted} inserted")

        if all_rows:
            cursor.executemany("""
                INSERT IGNORE INTO ke_mis_daily (record_date, vehicle, hired_own, vendor, tracker_company, category,
                    fleet_group, cluster, shift_hrs, benchmark,
                    on_off_road, peak_hour, peak_off, total_km,
                    fuel_drawn, fuel_consumed, fuel_difference,
                    speed_violation, remarks, is_reporting, travel_time_mins)
                VALUES (%s, %s, 'Hired', %s, 'Traccar', %s,
                    %s, %s, %s, %s,
                    'On Road', %s, %s, %s,
                    0, %s, 0,
                    %s, 'Reporting', 1, 0)
            """, all_rows)
            conn.commit()

        logger.info(f"[BATCH-MIS] Done: {total} vehicles processed, {inserted} records inserted")
        cursor.close()
        conn.close()
    except Exception as exc:
        logger.error(f"[BATCH-MIS] Failed: {exc}")
        import traceback
        logger.error(traceback.format_exc())


@router.post("/kemis-generate-batch")
async def generate_batch_mis(
    start_date: str = "2026-06-01",
    end_date: str = "2026-06-22",
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Generate MIS for all KE vehicles from GPS and insert into ke_mis_daily. Runs in background thread."""
    if current_user.get("role") not in ["SUPERADMIN", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Only administrators can trigger batch generation.")
    import threading
    t = threading.Thread(target=_batch_generate_mis_sync, args=(start_date, end_date), daemon=True)
    t.start()
    return {"status": "started", "message": f"Generating MIS for {start_date} to {end_date} in background..."}


@router.get("/kemis-generate-batch")
async def generate_batch_mis_get(
    start_date: str = "2026-06-01",
    end_date: str = "2026-06-22",
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Generate MIS for all KE vehicles from GPS. GET version for easy triggering."""
    if current_user.get("role") not in ["SUPERADMIN", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Only administrators can trigger batch generation.")
    import threading
    t = threading.Thread(target=_batch_generate_mis_sync, args=(start_date, end_date), daemon=True)
    t.start()
    return {"status": "started", "message": f"Generating MIS for {start_date} to {end_date} in background..."}


@router.get("/kemis-generate-status")
async def get_generate_status(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Check how many records exist for recent dates."""
    try:
        async with SessionLocal() as db:
            result = await db.execute(text("""
                SELECT record_date, COUNT(*) as cnt 
                FROM ke_mis_daily 
                GROUP BY record_date 
                ORDER BY record_date DESC 
                LIMIT 60
            """))
            rows = result.fetchall()
            dates = [{"date": str(r[0]), "count": r[1]} for r in rows]
            return {"dates": dates}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/fdb-explorer")
async def get_fdb_explorer(
    group: str = None,
    search: str = None,
    status: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get master FDB records with real IMEI from ke_vehicle_imei mapping,
    and live status from tc_devices (via IMEI → uniqueid).
    status filter: 'online', 'offline', 'unmapped' (no Traccar device), or None (all).
    """
    try:
        sql = """
            SELECT 
                f.vehicle_registration,
                m.imei,
                f.fleet_group,
                f.vehicle_category,
                f.fleet_vendor,
                f.benchmark_kmpl,
                f.shift_hrs,
                f.time_in,
                f.time_out,
                f.current_status,
                f.cluster,
                f.sub_department,
                COALESCE(d.status, 'unmapped') as live_status,
                d.lastupdate as last_signal
            FROM ke_fleet_database f
            LEFT JOIN ke_vehicle_imei m ON f.vehicle_registration = m.alias_name
            LEFT JOIN (
                SELECT uniqueid, status, lastupdate FROM tc_devices
            ) d ON m.imei = d.uniqueid
            WHERE 1=1
        """
        params = {}
        if group:
            sql += " AND f.fleet_group LIKE :group"
            params["group"] = f"%{group}%"
        if search:
            sql += " AND (f.vehicle_registration LIKE :search OR m.imei LIKE :search OR f.fleet_group LIKE :search OR f.fleet_vendor LIKE :search OR f.cluster LIKE :search)"
            params["search"] = f"%{search}%"
        if status:
            if status == "online":
                sql += " AND d.status = 'online'"
            elif status == "offline":
                sql += " AND (d.status = 'offline' OR (m.imei IS NOT NULL AND d.status IS NULL))"
            elif status == "unmapped":
                sql += " AND m.imei IS NULL"
        
        sql += " ORDER BY f.vehicle_registration ASC LIMIT 1000"
        
        result = await db.execute(text(sql), params)
        rows = result.fetchall()
        
        data = []
        for r in rows:
            live = r[12] or "unmapped"
            status_class = "offline"
            if live == "online":
                status_class = "online"
            elif live == "unmapped":
                status_class = "warning"
            
            time_in = str(r[7])[:5] if r[7] else "--:--"
            time_out = str(r[8])[:5] if r[8] else "--:--"
            
            sig = "No Signal"
            if r[13]:
                try:
                    sig = r[13].strftime("%Y-%m-%d %H:%M")
                except:
                    sig = str(r[13])[:16]
            
            data.append({
                "registration": r[0],
                "imei": r[1] or "N/A",
                "group": r[2] or "N/A",
                "category": r[3] or "N/A",
                "vendor": r[4] or "N/A",
                "benchmark": r[5],
                "shift": r[6],
                "time_in": time_in,
                "time_out": time_out,
                "status": live,
                "status_class": status_class,
                "last_signal": sig,
                "cluster": r[10] or "",
                "sub_dept": r[11] or "",
            })
            
        return data
    except Exception as exc:
        logger.error(f"Explorer Database Error: {str(exc)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/daily-ops")
async def get_daily_operations(
    vehicle: str = None,
    date_from: str = None,
    date_to: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get daily operations records with optional filters."""
    try:
        conditions = []
        params = {}

        if vehicle:
            conditions.append("vehicle_registration = :vehicle")
            params["vehicle"] = vehicle
        if date_from:
            conditions.append("op_date >= :date_from")
            params["date_from"] = date_from
        if date_to:
            conditions.append("op_date <= :date_to")
            params["date_to"] = date_to

        where = " AND ".join(conditions) if conditions else "1=1"
        sql = f"SELECT * FROM ke_daily_operations WHERE {where} ORDER BY op_date DESC, vehicle_registration LIMIT 500"
        result = await db.execute(text(sql), params)
        rows = result.fetchall()
        col_names = list(result.keys())

        return {
            "total": len(rows),
            "records": [dict(zip(col_names, row)) for row in rows],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/daily-ops")
async def upsert_daily_operations(
    records: list,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Insert or update daily operations records.
    Expects list of dicts with: vehicle_registration, op_date, fuel_drawn, remarks, remarks_code
    """
    if current_user.get("role") not in ["SUPERADMIN", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Only administrators can modify daily operations.")

    inserted = 0
    updated = 0
    for rec in records:
        vreg = rec.get("vehicle_registration")
        op_date = rec.get("op_date")
        if not vreg or not op_date:
            continue

        # Check if exists
        existing = await db.execute(
            text("SELECT id FROM ke_daily_operations WHERE vehicle_registration = :v AND op_date = :d"),
            {"v": vreg, "d": op_date}
        )
        if existing.scalar():
            await db.execute(
                text("""UPDATE ke_daily_operations
                    SET fuel_drawn = :fuel_drawn, remarks = :remarks, remarks_code = :remarks_code
                    WHERE vehicle_registration = :v AND op_date = :d"""),
                {"v": vreg, "d": op_date,
                 "fuel_drawn": rec.get("fuel_drawn"),
                 "remarks": rec.get("remarks"),
                 "remarks_code": rec.get("remarks_code")}
            )
            updated += 1
        else:
            await db.execute(
                text("""INSERT INTO ke_daily_operations
                    (vehicle_registration, op_date, fuel_drawn, remarks, remarks_code)
                    VALUES (:v, :d, :fuel_drawn, :remarks, :remarks_code)"""),
                {"v": vreg, "d": op_date,
                 "fuel_drawn": rec.get("fuel_drawn"),
                 "remarks": rec.get("remarks"),
                 "remarks_code": rec.get("remarks_code")}
            )
            inserted += 1

    await db.commit()
    return {"inserted": inserted, "updated": updated, "total": len(records)}


# ============================================================
# FUEL TRANSACTION ENDPOINTS
# ============================================================

@router.post("/fuel-upload")
async def upload_fuel_transactions(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if current_user.get("role") not in ["SUPERADMIN", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Only administrators can upload fuel data.")
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx) are supported.")
    try:
        file_bytes = await file.read()
        if len(file_bytes) < 100:
            raise HTTPException(status_code=400, detail="File appears to be empty.")
        rows, sheet_name = parse_fuel_excel(file_bytes)
        if not rows:
            raise HTTPException(status_code=400, detail="No valid fuel transactions found in the file.")
        summary = await import_fuel_to_db(db, rows)
        summary["sheet_name"] = sheet_name
        summary["filename"] = file.filename
        return {"status": "success", "message": f"Fuel import: {summary['inserted']} records imported, {summary['skipped_void']} voids skipped, {summary['duplicates_skipped']} duplicates.", "summary": summary}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Fuel import failed: {str(exc)}")


@router.get("/fuel-stats")
async def get_fuel_stats(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    try:
        total = await db.execute(text("SELECT COUNT(*) FROM ke_fuel_transactions"))
        total_txns = total.scalar()
        veh = await db.execute(text("SELECT COUNT(DISTINCT vehicle_registration) FROM ke_fuel_transactions"))
        unique_vehicles = veh.scalar()
        fuel = await db.execute(text("SELECT COALESCE(SUM(quantity_liters),0), COALESCE(SUM(amount_pkr),0) FROM ke_fuel_transactions"))
        row = fuel.fetchone()
        total_fuel = row[0]
        total_amount = row[1]
        products = await db.execute(text("SELECT product, COUNT(*) as cnt, SUM(quantity_liters) as lit, SUM(amount_pkr) as amt FROM ke_fuel_transactions GROUP BY product ORDER BY cnt DESC"))
        product_stats = [{"product": r[0] or "Unknown", "count": r[1], "liters": round(r[2] or 0, 2), "amount": round(r[3] or 0, 2)} for r in products.fetchall()]
        outlets = await db.execute(text("SELECT retail_outlet, COUNT(*) as cnt, SUM(quantity_liters) as lit FROM ke_fuel_transactions GROUP BY retail_outlet ORDER BY cnt DESC LIMIT 10"))
        outlet_stats = [{"outlet": r[0] or "Unknown", "count": r[1], "liters": round(r[2] or 0, 2)} for r in outlets.fetchall()]
        dates = await db.execute(text("SELECT MIN(txn_date), MAX(txn_date) FROM ke_fuel_transactions"))
        d = dates.fetchone()
        date_range = {"min": str(d[0]) if d[0] else None, "max": str(d[1]) if d[1] else None}
        return {
            "total_transactions": total_txns,
            "unique_vehicles": unique_vehicles,
            "total_fuel_liters": round(total_fuel, 2),
            "total_amount_pkr": round(total_amount, 2),
            "product_stats": product_stats,
            "top_outlets": outlet_stats,
            "date_range": date_range,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to get fuel stats: {str(exc)}")


@router.get("/fuel-transactions")
async def get_fuel_transactions(
    search: str = None,
    product: str = None,
    page: int = 1,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    try:
        where_parts = ["1=1"]
        params = {}
        if search:
            where_parts.append("(vehicle_registration LIKE :search OR card_number LIKE :search OR retail_outlet LIKE :search OR rrn LIKE :search)")
            params["search"] = f"%{search}%"
        if product:
            where_parts.append("product = :product")
            params["product"] = product
        where = " AND ".join(where_parts)

        count_sql = f"SELECT COUNT(*) FROM ke_fuel_transactions WHERE {where}"
        total_result = await db.execute(text(count_sql), params)
        total = total_result.scalar()

        offset = (max(1, page) - 1) * limit
        params["limit"] = limit
        params["offset"] = offset
        data_sql = f"SELECT * FROM ke_fuel_transactions WHERE {where} ORDER BY txn_date DESC, txn_time DESC LIMIT :limit OFFSET :offset"
        result = await db.execute(text(data_sql), params)
        rows = result.fetchall()
        col_names = list(result.keys())

        records = [dict(zip(col_names, row)) for row in rows]
        for rec in records:
            if rec.get("txn_date"):
                rec["txn_date"] = str(rec["txn_date"])
            if rec.get("txn_time"):
                rec["txn_time"] = str(rec["txn_time"])
            if rec.get("created_at"):
                rec["created_at"] = str(rec["created_at"])

        return {
            "total": total,
            "page": page,
            "limit": limit,
            "pages": max(1, -(-total // limit)),
            "records": records,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================
# KEMIS MIS ENDPOINTS
# ============================================================

@router.get("/kemis-stats")
async def get_kemis_stats(
    date_from: str = None,
    date_to: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get KEMIS MIS summary stats from ke_mis_daily — optimized single query."""
    try:
        where_parts = ["1=1"]
        params = {}
        if date_from:
            where_parts.append("record_date >= :df")
            params["df"] = date_from
        if date_to:
            where_parts.append("record_date <= :dt")
            params["dt"] = date_to
        where = " AND ".join(where_parts)

        combined = await db.execute(text(f"""
            SELECT 
                COUNT(*) as total_rows,
                COUNT(DISTINCT vehicle) as unique_vehicles,
                MIN(record_date) as min_date, MAX(record_date) as max_date,
                COALESCE(SUM(CASE WHEN remarks = 'Reporting' THEN total_km ELSE 0 END), 0) as total_km,
                COALESCE(SUM(CASE WHEN remarks = 'Reporting' THEN fuel_consumed ELSE 0 END), 0) as total_fc,
                COALESCE(SUM(CASE WHEN remarks = 'Reporting' AND fuel_drawn > 0 THEN fuel_drawn ELSE 0 END), 0) as total_fd,
                COUNT(CASE WHEN remarks = 'Reporting' THEN 1 END) as reporting_count,
                COALESCE(AVG(CASE WHEN remarks = 'Reporting' AND benchmark > 0 THEN benchmark END), 0) as avg_benchmark
            FROM ke_mis_daily WHERE {where}
        """), params)
        c = combined.fetchone()

        categories = await db.execute(text(f"SELECT category, COUNT(*) as cnt FROM ke_mis_daily WHERE {where} GROUP BY category ORDER BY cnt DESC"), params)
        cat_stats = [{"category": r[0] or "Unknown", "count": r[1]} for r in categories.fetchall()]

        vendors = await db.execute(text(f"SELECT vendor, COUNT(CASE WHEN remarks = 'Reporting' THEN 1 END) as cnt, COALESCE(SUM(CASE WHEN remarks = 'Reporting' THEN total_km ELSE 0 END), 0), COALESCE(SUM(CASE WHEN remarks = 'Reporting' THEN fuel_consumed ELSE 0 END), 0) FROM ke_mis_daily WHERE {where} AND vendor IS NOT NULL AND vendor != '' GROUP BY vendor ORDER BY cnt DESC LIMIT 8"), params)
        vendor_stats = [{"vendor": r[0] or "Unknown", "count": r[1], "total_km": round(float(r[2]), 1), "total_fuel": round(float(r[3]), 1)} for r in vendors.fetchall()]

        groups = await db.execute(text(f"SELECT fleet_group, COUNT(*) as cnt FROM ke_mis_daily WHERE {where} AND fleet_group IS NOT NULL AND fleet_group != '' GROUP BY fleet_group ORDER BY cnt DESC LIMIT 8"), params)
        grp_stats = [{"group": r[0] or "Unknown", "count": r[1]} for r in groups.fetchall()]

        trend = await db.execute(text(f"""
            SELECT record_date, COALESCE(SUM(total_km), 0), COALESCE(SUM(fuel_consumed), 0), COUNT(*)
            FROM ke_mis_daily WHERE {where} AND remarks = 'Reporting'
            GROUP BY record_date ORDER BY record_date ASC
        """), params)
        trend_data = [{"date": str(r[0]), "total_km": round(float(r[1]), 1), "fuel_consumed": round(float(r[2]), 1), "records": r[3]} for r in trend.fetchall()]

        days = max(1, (c[3] - c[2]).days + 1) if c[2] and c[3] else 30

        return {
            "total_rows": c[0], "unique_vehicles": c[1],
            "date_range": {"min": str(c[2]) if c[2] else None, "max": str(c[3]) if c[3] else None},
            "total_km": round(float(c[4]), 2), "total_fuel_consumed": round(float(c[5]), 2),
            "total_fuel_drawn": round(float(c[6]), 2), "reporting_count": c[7],
            "avg_benchmark": round(float(c[8]), 2),
            "avg_km_per_vehicle_day": round(float(c[4]) / max(float(c[1]), 1) / days, 2) if c[1] else 0,
            "categories": cat_stats, "groups": grp_stats, "vendors": vendor_stats, "trend": trend_data,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to get KEMIS stats: {str(exc)}")


@router.get("/kemis-data")
async def get_kemis_data(
    search: str = None,
    vehicle: str = None,
    vendor: str = None,
    date_from: str = None,
    date_to: str = None,
    category: str = None,
    group: str = None,
    remarks: str = None,
    page: int = 1,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get KEMIS MIS data with filters and pagination.
    Auto-triggers GPS batch generation if no data exists for the date range."""
    try:
        where_parts = ["1=1"]
        params = {}

        if search:
            where_parts.append("(vehicle LIKE :search OR category LIKE :search OR fleet_group LIKE :search OR cluster LIKE :search OR vendor LIKE :search)")
            params["search"] = f"%{search}%"
        if vehicle:
            where_parts.append("vehicle = :vehicle")
            params["vehicle"] = vehicle
        if date_from:
            where_parts.append("record_date >= :date_from")
            params["date_from"] = date_from
        if date_to:
            where_parts.append("record_date <= :date_to")
            params["date_to"] = date_to
        if category:
            where_parts.append("category = :category")
            params["category"] = category
        if group:
            where_parts.append("fleet_group = :group")
            params["group"] = group
        if remarks:
            where_parts.append("remarks = :remarks")
            params["remarks"] = remarks
        if vendor:
            where_parts.append("vendor = :vendor")
            params["vendor"] = vendor

        where = " AND ".join(where_parts)

        count_result = await db.execute(text(f"SELECT COUNT(*) FROM ke_mis_daily WHERE {where}"), params)
        total = count_result.scalar()

        auto_generated = False

        offset = (max(1, page) - 1) * limit
        params["limit"] = limit
        params["offset"] = offset

        sql = f"""
            SELECT record_date, vehicle, hired_own, vendor, tracker_company, category,
                   fleet_group, bu_function, cluster, ibc_vibc, sub_department,
                   shift_hrs, shift_timing, on_off_road, benchmark,
                   peak_hour, peak_off, total_km, fuel_drawn, fuel_difference,
                   odometer, fuel_consumed, excess_idling_mins, harsh_braking,
                   speed_violation, travel_time_mins, stop_time_mins,
                   remarks_code, last_lat, last_lon, last_location, remarks,
                   no_of_polls, min_poll_duration_mins, max_poll_duration_mins
            FROM ke_mis_daily
            WHERE {where}
            ORDER BY record_date DESC, vehicle ASC
            LIMIT :limit OFFSET :offset
        """
        result = await db.execute(text(sql), params)
        rows = result.fetchall()
        col_names = list(result.keys())

        records = [dict(zip(col_names, row)) for row in rows]
        for rec in records:
            if rec.get("record_date"):
                rec["record_date"] = str(rec["record_date"])

        return {
            "total": total,
            "page": page,
            "limit": limit,
            "pages": max(1, -(-total // limit)),
            "records": records,
            "auto_generated": auto_generated,
            "message": f"MIS generation started for {date_from} to {date_to}. Refresh in 5-10 minutes." if auto_generated else None,
        }
    except Exception as exc:
        logger.error(f"KEMIS data error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/kemis-vehicle/{vehicle}")
async def get_kemis_vehicle(
    vehicle: str,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get daily KEMIS data for a specific vehicle."""
    try:
        sql = """
            SELECT record_date, vehicle, hired_own, vendor, tracker_company, category,
                   fleet_group, bu_function, cluster, ibc_vibc, sub_department,
                   shift_hrs, shift_timing, on_off_road, benchmark,
                   peak_hour, peak_off, total_km, fuel_drawn, fuel_difference,
                   odometer, fuel_consumed, excess_idling_mins, harsh_braking,
                   speed_violation, travel_time_mins, stop_time_mins,
                   remarks_code, last_lat, last_lon, last_location, remarks,
                   no_of_polls, min_poll_duration_mins, max_poll_duration_mins
            FROM ke_mis_daily
            WHERE vehicle = :vehicle
            ORDER BY record_date ASC
        """
        result = await db.execute(text(sql), {"vehicle": vehicle})
        rows = result.fetchall()
        col_names = list(result.keys())

        records = [dict(zip(col_names, row)) for row in rows]
        for rec in records:
            if rec.get("record_date"):
                rec["record_date"] = str(rec["record_date"])

        return {"vehicle": vehicle, "total": len(records), "records": records}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/kemis-vehicle-mis/{vehicle}")
async def get_kemis_vehicle_mis(
    vehicle: str,
    date_from: str = None,
    date_to: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get full MIS report for a single vehicle — on-peak/off-peak breakdown + summary."""
    try:
        where_parts = ["vehicle = :vehicle"]
        params = {"vehicle": vehicle}
        if date_from:
            where_parts.append("record_date >= :df")
            params["df"] = date_from
        if date_to:
            where_parts.append("record_date <= :dt")
            params["dt"] = date_to
        where = " AND ".join(where_parts)

        sql = f"""
            SELECT record_date, shift_hrs, shift_timing, peak_hour, peak_off, total_km,
                   fuel_drawn, fuel_consumed, fuel_difference, benchmark,
                   harsh_braking, speed_violation, excess_idling_mins,
                   travel_time_mins, stop_time_mins, remarks, on_off_road,
                   vendor, category, fleet_group, hired_own
            FROM ke_mis_daily
            WHERE {where}
            ORDER BY record_date ASC
        """
        result = await db.execute(text(sql), params)
        rows = result.fetchall()

        if not rows:
            return {"vehicle": vehicle, "summary": {}, "daily": []}

        records = []
        for r in rows:
            records.append({
                "date": str(r[0]),
                "shift_hrs": float(r[1]) if r[1] else 0,
                "shift_timing": str(r[2]) if r[2] else "",
                "on_peak_km": float(r[3]) if r[3] else 0,
                "off_peak_km": float(r[4]) if r[4] else 0,
                "total_km": float(r[5]) if r[5] else 0,
                "fuel_drawn": float(r[6]) if r[6] else 0,
                "fuel_consumed": float(r[7]) if r[7] else 0,
                "fuel_difference": float(r[8]) if r[8] else 0,
                "benchmark": float(r[9]) if r[9] else 0,
                "harsh_braking": int(r[10]) if r[10] else 0,
                "speed_violation": int(r[11]) if r[11] else 0,
                "excess_idling": int(r[12]) if r[12] else 0,
                "travel_time": float(r[13]) if r[13] else 0,
                "stop_time": float(r[14]) if r[14] else 0,
                "remarks": str(r[15]) if r[15] else "",
                "on_off_road": str(r[16]) if r[16] else "",
                "vendor": str(r[17]) if r[17] else "",
                "category": str(r[18]) if r[18] else "",
                "fleet_group": str(r[19]) if r[19] else "",
                "hired_own": str(r[20]) if r[20] else "",
            })

        reporting = [r for r in records if r["remarks"] == "Reporting"]
        total_days = len(records)
        reporting_days = len(reporting)
        total_km = sum(r["total_km"] for r in reporting)
        on_peak = sum(r["on_peak_km"] for r in reporting)
        off_peak = sum(r["off_peak_km"] for r in reporting)
        fuel_drawn = sum(r["fuel_drawn"] for r in reporting)
        fuel_consumed = sum(r["fuel_consumed"] for r in reporting)
        fuel_diff = sum(r["fuel_difference"] for r in reporting)
        benchmarks = [r["benchmark"] for r in reporting if r["benchmark"] > 0]
        avg_benchmark = sum(benchmarks) / len(benchmarks) if benchmarks else 0
        avg_daily_km = total_km / reporting_days if reporting_days > 0 else 0
        actual_kmpl = total_km / fuel_consumed if fuel_consumed > 0 else 0
        total_harsh = sum(r["harsh_braking"] for r in reporting)
        total_speed = sum(r["speed_violation"] for r in reporting)
        total_idling = sum(r["excess_idling"] for r in reporting)
        total_shift_hrs = sum(r["shift_hrs"] for r in reporting)
        avg_shift_hrs = total_shift_hrs / reporting_days if reporting_days > 0 else 0
        on_peak_pct = (on_peak / total_km * 100) if total_km > 0 else 0
        off_peak_pct = (off_peak / total_km * 100) if total_km > 0 else 0

        summary = {
            "vehicle": vehicle,
            "vendor": reporting[0]["vendor"] if reporting else "",
            "category": reporting[0]["category"] if reporting else "",
            "fleet_group": reporting[0]["fleet_group"] if reporting else "",
            "hired_own": reporting[0]["hired_own"] if reporting else "",
            "total_days": total_days,
            "reporting_days": reporting_days,
            "total_km": round(total_km, 1),
            "on_peak_km": round(on_peak, 1),
            "off_peak_km": round(off_peak, 1),
            "on_peak_pct": round(on_peak_pct, 1),
            "off_peak_pct": round(off_peak_pct, 1),
            "fuel_drawn": round(fuel_drawn, 1),
            "fuel_consumed": round(fuel_consumed, 1),
            "fuel_difference": round(fuel_diff, 1),
            "avg_benchmark": round(avg_benchmark, 2),
            "actual_kmpl": round(actual_kmpl, 2),
            "avg_daily_km": round(avg_daily_km, 1),
            "total_shift_hrs": round(total_shift_hrs, 1),
            "avg_shift_hrs": round(avg_shift_hrs, 1),
            "total_harsh_braking": total_harsh,
            "total_speed_violation": total_speed,
            "total_excess_idling": total_idling,
        }

        return {"vehicle": vehicle, "summary": summary, "daily": records}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/kemis-efficiency")
async def get_kemis_efficiency(
    sort_by: str = "benchmark",
    order: str = "desc",
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get fuel efficiency ranking — top/bottom vehicles by benchmark km/L."""
    try:
        order_dir = "DESC" if order == "desc" else "ASC"
        safe_sort = "benchmark" if sort_by not in ("benchmark", "total_km", "fuel_consumed", "avg_daily_km") else sort_by

        sql = f"""
            SELECT 
                vehicle,
                category,
                vendor,
                fleet_group,
                benchmark,
                SUM(total_km) as total_km,
                SUM(fuel_consumed) as total_fuel,
                COUNT(*) as days,
                AVG(total_km) as avg_daily_km,
                CASE WHEN SUM(fuel_consumed) > 0 THEN SUM(total_km) / SUM(fuel_consumed) ELSE 0 END as actual_kmpl
            FROM ke_mis_daily
            WHERE remarks = 'Reporting' AND benchmark > 0
            GROUP BY vehicle, category, vendor, fleet_group, benchmark
            HAVING days >= 5
            ORDER BY {safe_sort} {order_dir}
            LIMIT :limit
        """
        result = await db.execute(text(sql), {"limit": limit})
        rows = result.fetchall()

        records = []
        for r in rows:
            records.append({
                "vehicle": r[0],
                "category": r[1] or "--",
                "vendor": r[2] or "--",
                "group": r[3] or "--",
                "benchmark": round(float(r[4]), 2),
                "total_km": round(float(r[5]), 1),
                "total_fuel": round(float(r[6]), 1),
                "days": r[7],
                "avg_daily_km": round(float(r[8]), 1),
                "actual_kmpl": round(float(r[9]), 2),
            })

        return {"total": len(records), "sort_by": safe_sort, "order": order, "records": records}
    except Exception as exc:
        logger.error(f"KEMIS efficiency error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/kemis-vendor-trend")
async def get_kemis_vendor_trend(
    vendor: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get daily trend data, optionally filtered by vendor."""
    try:
        where = "AND vendor = :vendor" if vendor else ""
        params = {"vendor": vendor} if vendor else {}

        sql = f"""
            SELECT record_date, COALESCE(SUM(total_km), 0) as total_km, 
                   COALESCE(SUM(fuel_consumed), 0) as total_fuel,
                   COALESCE(AVG(benchmark), 0) as avg_benchmark,
                   COUNT(*) as records
            FROM ke_mis_daily
            WHERE remarks = 'Reporting' {where}
            GROUP BY record_date
            ORDER BY record_date ASC
        """
        result = await db.execute(text(sql), params)
        trend = [{"date": str(r[0]), "total_km": round(float(r[1]), 1), "fuel_consumed": round(float(r[2]), 1), "avg_benchmark": round(float(r[3]), 2), "records": r[4]} for r in result.fetchall()]

        return {"vendor": vendor, "trend": trend}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================================
# GPS MIS AUTO-GENERATION
# ============================================================================

_gps_gen_status = {}

def _run_gps_generation(date_from: str, date_to: str):
    """Background thread: generate GPS MIS for a month."""
    import math, pymysql as _pymysql
    key = f"{date_from}_{date_to}"
    _gps_gen_status[key] = {"status": "running", "inserted": 0, "started": time.time()}
    try:
        _DB = dict(host='202.141.246.12', port=3306, user='traccar', password='traccar12344321',
                    database='traccar', connect_timeout=30, read_timeout=600)
        _c = _pymysql.connect(**_DB)
        _cur = _c.cursor()
        def _hav(lat1, lon1, lat2, lon2):
            R = 6371
            dlat, dlon = math.radians(lat2-lat1), math.radians(lon2-lon1)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
            return R * 2 * math.asin(math.sqrt(a))
        _cur.execute("""
            SELECT kv.alias_name, kv.imei, td.id,
                   COALESCE(fd.benchmark_kmpl,10), COALESCE(fd.shift_hrs,12),
                   COALESCE(fd.fleet_group,''), COALESCE(fd.vehicle_category,''),
                   COALESCE(fd.cluster,''), COALESCE(fd.ibc_vibc,''),
                   COALESCE(fd.sub_department,''), COALESCE(fd.tracker_vendor,'Traccar'),
                   COALESCE(fd.time_in,''), COALESCE(fd.time_out,''), COALESCE(fd.fleet_vendor,'')
            FROM ke_vehicle_imei kv
            JOIN tc_devices td ON td.uniqueid = kv.imei
            LEFT JOIN ke_fleet_database fd ON fd.vehicle_registration = kv.alias_name
        """)
        vehicles = _cur.fetchall()
        inserted = 0
        sql = """INSERT INTO ke_gps_mis_daily (
            sno,record_date,vehicle,hired_own,vendor,tracker_company,category,fleet_group,bu_function,
            cluster,ibc_vibc,sub_department,shift_hrs,shift_timing,on_off_road,benchmark,
            peak_hour,peak_off,total_km,fuel_drawn,fuel_difference,odometer,
            fuel_consumed,excess_idling_mins,harsh_braking,speed_violation,
            travel_time_mins,stop_time_mins,remarks_code,last_lat,last_lon,last_location,remarks,
            is_reporting,no_of_polls,min_poll_duration_mins,max_poll_duration_mins,
            max_speed,avg_speed,device_id,imei
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE total_km=VALUES(total_km),peak_hour=VALUES(peak_hour),peak_off=VALUES(peak_off),
            fuel_consumed=VALUES(fuel_consumed),excess_idling_mins=VALUES(excess_idling_mins),
            harsh_braking=VALUES(harsh_braking),speed_violation=VALUES(speed_violation),
            travel_time_mins=VALUES(travel_time_mins),stop_time_mins=VALUES(stop_time_mins),
            no_of_polls=VALUES(no_of_polls),max_speed=VALUES(max_speed),avg_speed=VALUES(avg_speed),
            is_reporting=VALUES(is_reporting),last_lat=VALUES(last_lat),last_lon=VALUES(last_lon),remarks=VALUES(remarks)"""
        for v in vehicles:
            alias, imei, dev_id = v[0], v[1], v[2]
            bench = int(v[3]) if v[3] else 10
            shift_hrs = v[4] or 12
            fleet, cat, cluster = v[5] or '', v[6] or '', v[7] or ''
            ibc, sub_dept, tracker = v[8] or '', v[9] or '', v[10] or ''
            time_in, time_out, vendor_name = v[11] or '', v[12] or '', v[13] or ''
            sty = f"{time_in} To {time_out}" if time_in and time_out else f"{int(shift_hrs)}h"
            try:
                _cur.execute("""
                    SELECT DATE(fixtime), speed, latitude, longitude, HOUR(fixtime), UNIX_TIMESTAMP(fixtime)
                    FROM tc_positions WHERE deviceid = %s AND fixtime >= %s AND fixtime < %s ORDER BY fixtime
                """, (dev_id, date_from, date_to))
                rows = _cur.fetchall()
                if not rows: continue
                daily = {}
                for r in rows:
                    d = str(r[0])
                    if d not in daily: daily[d] = {'sp':[],'la':[],'lo':[],'hr':[],'ts':[]}
                    g = daily[d]
                    g['sp'].append(float(r[1]) if r[1] else 0)
                    g['la'].append(float(r[2]) if r[2] else 0)
                    g['lo'].append(float(r[3]) if r[3] else 0)
                    g['hr'].append(int(r[4]))
                    g['ts'].append(int(r[5]))
                batch = []
                for d, data in daily.items():
                    sp, la, lo, hr, ts = data['sp'], data['la'], data['lo'], data['hr'], data['ts']
                    n = len(la)
                    if n < 2: continue
                    tk = ok = ofk = 0
                    for i in range(1,n):
                        if la[i]==0 or lo[i]==0 or la[i-1]==0 or lo[i-1]==0: continue
                        dd = _hav(la[i-1],lo[i-1],la[i],lo[i])
                        if dd < 100:
                            tk += dd
                            if 6 <= hr[i] < 18: ok += dd
                            else: ofk += dd
                    tr = st = idle = 0
                    for i in range(1,n):
                        dt = (ts[i]-ts[i-1])/60.0
                        if dt > 60: dt = 0
                        tr += dt
                        if sp[i] < 1:
                            st += dt
                            if dt >= 15: idle += dt
                    ms = max(sp); asp = sum(sp)/len(sp)
                    sv = sum(1 for s in sp if s > 120)
                    hb = sum(1 for i in range(1,n) if 0<ts[i]-ts[i-1]<=5 and sp[i-1]-sp[i]>20)
                    fu = tk/bench if bench > 0 else 0
                    oo = "On Road" if tk > 1 else "Off Road"
                    batch.append((None,d,alias,'Hired',vendor_name,tracker,cat,fleet,'',cluster,ibc,sub_dept,
                        shift_hrs,sty,oo,bench,round(ok,2),round(ofk,2),round(tk,2),0,round(0-fu,2),0,
                        round(fu,2),round(idle,1),hb,sv,round(tr,1),round(st,1),1 if tk>0 else 0,
                        la[-1],lo[-1],'','Reporting' if tk>0 else 'No Data',1 if tk>0 else 0,n,0,0,round(ms,1),round(asp,1),dev_id,imei))
                if batch:
                    _cur.executemany(sql, batch)
                    _c.commit()
                    inserted += len(batch)
            except Exception:
                _c.rollback()
        _cur.close(); _c.close()
        _gps_gen_status[key] = {"status": "done", "inserted": inserted, "elapsed": time.time() - _gps_gen_status[key]["started"]}
    except Exception as e:
        _gps_gen_status[key] = {"status": "error", "error": str(e)}


@router.get("/gps-mis-status")
async def gps_mis_status(
    month: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Check GPS MIS data status for a month."""
    if not month:
        from datetime import date, timedelta
        today = date.today()
        first = today.replace(day=1)
        last_month = first - timedelta(days=1)
        month = last_month.strftime("%Y-%m")
    year, mon = month.split("-")
    date_from = f"{year}-{mon}-01"
    if mon == "12": date_to = f"{int(year)+1}-01-01"
    else: date_to = f"{year}-{int(mon)+1:02d}-01"

    result = await db.execute(text("""
        SELECT COUNT(*) as total_rows, COUNT(DISTINCT vehicle) as vehicles,
               MIN(record_date) as min_date, MAX(record_date) as max_date
        FROM ke_gps_mis_daily WHERE record_date >= :df AND record_date < :dt
    """), {"df": date_from, "dt": date_to})
    row = result.fetchone()

    gen_key = f"{date_from}_{date_to}"
    gen_status = _gps_gen_status.get(gen_key, {"status": "idle"})

    return {
        "month": month,
        "total_rows": row[0] if row else 0,
        "vehicles": row[1] if row else 0,
        "min_date": str(row[2]) if row and row[2] else None,
        "max_date": str(row[3]) if row and row[3] else None,
        "generation_status": gen_status["status"],
        "generation_inserted": gen_status.get("inserted", 0),
    }


@router.get("/gps-mis-generate")
async def gps_mis_generate(
    month: str = None,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Auto-generate GPS MIS for any month. Runs in background thread."""
    if current_user.get("role") not in ["SUPERADMIN", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Only administrators can generate MIS.")
    if not month:
        from datetime import date, timedelta
        today = date.today()
        first = today.replace(day=1)
        last_month = first - timedelta(days=1)
        month = last_month.strftime("%Y-%m")
    year, mon = month.split("-")
    date_from = f"{year}-{mon}-01"
    if mon == "12": date_to = f"{int(year)+1}-01-01"
    else: date_to = f"{year}-{int(mon)+1:02d}-01"

    gen_key = f"{date_from}_{date_to}"
    if gen_key in _gps_gen_status and _gps_gen_status[gen_key].get("status") == "running":
        return {"status": "already_running", "month": month}

    import threading
    t = threading.Thread(target=_run_gps_generation, args=(date_from, date_to), daemon=True)
    t.start()

    return {"status": "started", "month": month, "message": f"GPS MIS generation started for {month}. This may take 5-15 minutes."}


# ============================================================================
# MONTHLY MIS REPORT (ALL VEHICLES)
# ============================================================================

@router.get("/monthly-mis-days")
async def get_monthly_mis_days(
    month: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get available days with data for a month."""
    try:
        if not month:
            from datetime import date, timedelta
            today = date.today()
            first = today.replace(day=1)
            last_month = first - timedelta(days=1)
            month = last_month.strftime("%Y-%m")

        year, mon = month.split("-")
        date_from = f"{year}-{mon}-01"
        if mon == "12":
            date_to = f"{int(year)+1}-01-01"
        else:
            date_to = f"{year}-{int(mon)+1:02d}-01"

        result = await db.execute(text("""
            SELECT record_date, COUNT(DISTINCT vehicle) as vehicles,
                   SUM(total_km) as total_km, SUM(fuel_consumed) as fuel_consumed
            FROM ke_gps_mis_daily
            WHERE record_date >= :df AND record_date < :dt AND is_reporting = 1
            GROUP BY record_date ORDER BY record_date
        """), {"df": date_from, "dt": date_to})

        days = [{"date": str(r[0]), "vehicles": r[1],
                 "total_km": round(float(r[2]) if r[2] else 0, 1),
                 "total_fuel": round(float(r[3]) if r[3] else 0, 1)}
                for r in result.fetchall()]

        return {"month": month, "days": days}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Monthly MIS days error: {str(exc)}")


@router.get("/monthly-mis")
async def get_monthly_mis(
    month: str = None,
    day: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get Monthly MIS Report for ALL vehicles — optimized single query. Supports day filter."""
    try:
        if not month:
            from datetime import date, timedelta
            today = date.today()
            first = today.replace(day=1)
            last_month = first - timedelta(days=1)
            month = last_month.strftime("%Y-%m")

        if day:
            date_from = day
            date_to = day + " " + "23:59:59"
        else:
            year, mon = month.split("-")
            date_from = f"{year}-{mon}-01"
            if mon == "12":
                date_to = f"{int(year)+1}-01-01"
            else:
                date_to = f"{year}-{int(mon)+1:02d}-01"

        if day:
            date_filter = "WHERE record_date = :df AND is_reporting = 1"
            params = {"df": day}
        else:
            date_filter = "WHERE record_date >= :df AND record_date < :dt AND is_reporting = 1"
            params = {"df": date_from, "dt": date_to}

        # SINGLE QUERY — get all reporting data, compute everything in Python
        veh_result = await db.execute(text(f"""
            SELECT 
                vehicle, vendor, category, fleet_group, cluster, shift_hrs,
                MAX(benchmark) as benchmark,
                COUNT(*) as reporting_days,
                SUM(total_km) as total_km,
                SUM(peak_hour) as on_peak_km,
                SUM(peak_off) as off_peak_km,
                SUM(fuel_drawn) as fuel_drawn,
                SUM(fuel_consumed) as fuel_consumed,
                SUM(harsh_braking) as harsh_braking,
                SUM(speed_violation) as speed_violation,
                SUM(excess_idling_mins) as excess_idling,
                AVG(total_km) as avg_daily_km,
                SUM(travel_time_mins) as travel_time_mins
            FROM ke_gps_mis_daily
            {date_filter}
            GROUP BY vehicle, vendor, category, fleet_group, cluster, shift_hrs
            ORDER BY SUM(total_km) DESC
        """), params)
        raw = veh_result.fetchall()

        # Build vehicles + compute summary + vendor + category + trend in one pass
        vehicles = []
        vendor_map = {}
        cat_map = {}
        total_km = total_fuel = total_fd = 0
        total_on = total_off = 0
        total_braking = total_speed = total_idling = 0
        benchmarks = []

        for r in raw:
            vk = float(r[8]) if r[8] else 0
            vf = float(r[12]) if r[12] else 0
            vb = float(r[6]) if r[6] else 0
            fd = float(r[11]) if r[11] else 0
            on_pk = float(r[9]) if r[9] else 0
            off_pk = float(r[10]) if r[10] else 0
            brk = int(r[13] if r[13] else 0)
            spd = int(r[14] if r[14] else 0)
            idle = int(r[15] if r[15] else 0)

            vehicles.append({
                "vehicle": r[0], "vendor": r[1] or "", "category": r[2] or "",
                "fleet_group": r[3] or "", "cluster": r[4] or "",
                "shift_hrs": float(r[5]) if r[5] else 0,
                "benchmark": round(vb, 2), "reporting_days": r[7],
                "total_km": round(vk, 1), "on_peak_km": round(on_pk, 1),
                "off_peak_km": round(off_pk, 1), "fuel_drawn": round(fd, 1),
                "fuel_consumed": round(vf, 1), "fuel_difference": round(fd - vf, 1),
                "actual_kmpl": round(vk / vf, 2) if vf > 0 else 0,
                "avg_daily_km": round(float(r[16]) if r[16] else 0, 1),
                "harsh_braking": brk, "speed_violation": spd, "excess_idling": idle,
                "travel_time_hrs": round(float(r[17]) / 60, 1) if r[17] else 0,
            })

            total_km += vk; total_fuel += vf; total_fd += fd
            total_on += on_pk; total_off += off_pk
            total_braking += brk; total_speed += spd; total_idling += idle
            if vb > 0: benchmarks.append(vb)

            # Vendor aggregation
            vnd = r[1] or "Unknown"
            if vnd not in vendor_map:
                vendor_map[vnd] = {"vendor": vnd, "vehicles": 0, "total_km": 0, "total_fuel": 0, "benchmarks": [], "braking": 0, "speeding": 0}
            vendor_map[vnd]["vehicles"] += 1
            vendor_map[vnd]["total_km"] += vk
            vendor_map[vnd]["total_fuel"] += vf
            if vb > 0: vendor_map[vnd]["benchmarks"].append(vb)
            vendor_map[vnd]["braking"] += brk
            vendor_map[vnd]["speeding"] += spd

            # Category aggregation
            cat = r[2] or "Unknown"
            if cat not in cat_map:
                cat_map[cat] = {"category": cat, "vehicles": 0, "total_km": 0, "total_fuel": 0}
            cat_map[cat]["vehicles"] += 1
            cat_map[cat]["total_km"] += vk
            cat_map[cat]["total_fuel"] += vf

        avg_bench = round(sum(benchmarks) / len(benchmarks), 2) if benchmarks else 0
        actual_kmpl = round(total_km / total_fuel, 2) if total_fuel > 0 else 0

        summary = {
            "month": month,
            "total_vehicles": len(vehicles),
            "total_records": len(raw),
            "reporting_days_total": len(raw),
            "total_km": round(total_km, 1),
            "on_peak_km": round(total_on, 1),
            "off_peak_km": round(total_off, 1),
            "on_peak_pct": round(total_on / total_km * 100, 1) if total_km > 0 else 0,
            "off_peak_pct": round(total_off / total_km * 100, 1) if total_km > 0 else 0,
            "fuel_drawn": round(total_fd, 1),
            "fuel_consumed": round(total_fuel, 1),
            "fuel_difference": round(total_fd - total_fuel, 1),
            "avg_benchmark": avg_bench,
            "actual_kmpl": actual_kmpl,
            "avg_daily_km": round(total_km / max(len(vehicles), 1), 1),
            "total_harsh_braking": total_braking,
            "total_speed_violation": total_speed,
            "total_excess_idling": total_idling,
        }

        vendors = sorted([
            {"vendor": v["vendor"], "vehicles": v["vehicles"],
             "total_km": round(v["total_km"], 1), "total_fuel": round(v["total_fuel"], 1),
             "actual_kmpl": round(v["total_km"] / v["total_fuel"], 2) if v["total_fuel"] > 0 else 0,
             "avg_benchmark": round(sum(v["benchmarks"]) / len(v["benchmarks"]), 2) if v["benchmarks"] else 0,
             "harsh_braking": v["braking"], "speed_violation": v["speeding"]}
            for v in vendor_map.values()
        ], key=lambda x: x["total_km"], reverse=True)

        categories = sorted([
            {"category": v["category"], "vehicles": v["vehicles"],
             "total_km": round(v["total_km"], 1), "total_fuel": round(v["total_fuel"], 1),
             "actual_kmpl": round(v["total_km"] / v["total_fuel"], 2) if v["total_fuel"] > 0 else 0}
            for v in cat_map.values()
        ], key=lambda x: x["total_km"], reverse=True)

        # Daily trend — always shows full month (for context)
        if day:
            year_m, mon_m = month.split("-")
            trend_df = f"{year_m}-{mon_m}-01"
            if mon_m == "12":
                trend_dt = f"{int(year_m)+1}-01-01"
            else:
                trend_dt = f"{year_m}-{int(mon_m)+1:02d}-01"
            trend_params = {"df": trend_df, "dt": trend_dt}
        else:
            trend_params = params
        trend_result = await db.execute(text("""
            SELECT record_date, COUNT(DISTINCT vehicle) as vehicles,
                SUM(total_km) as total_km, SUM(fuel_consumed) as total_fuel,
                AVG(CASE WHEN benchmark > 0 THEN benchmark END) as avg_benchmark
            FROM ke_gps_mis_daily
            WHERE record_date >= :df AND record_date < :dt AND is_reporting = 1
            GROUP BY record_date ORDER BY record_date ASC
        """), trend_params)
        trend = [{"date": str(r[0]), "vehicles": r[1],
                  "total_km": round(float(r[2]) if r[2] else 0, 1),
                  "total_fuel": round(float(r[3]) if r[3] else 0, 1),
                  "avg_benchmark": round(float(r[4]) if r[4] else 0, 2)}
                 for r in trend_result.fetchall()]

        return {"summary": summary, "vehicles": vehicles, "vendors": vendors,
                "categories": categories, "trend": trend}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Monthly MIS error: {str(exc)}")


# ============================================================================
# MONTHLY MIS CSV EXPORT
# ============================================================================

@router.get("/monthly-mis-export")
async def export_monthly_mis(
    month: str = None,
    day: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Export Monthly MIS as CSV download. Supports day filter."""
    from fastapi.responses import StreamingResponse
    import csv, io

    if not month:
        from datetime import date, timedelta
        today = date.today()
        first = today.replace(day=1)
        last_month = first - timedelta(days=1)
        month = last_month.strftime("%Y-%m")

    if day:
        date_filter = "WHERE record_date = :df AND is_reporting = 1"
        params = {"df": day}
        csv_label = day
    else:
        year, mon = month.split("-")
        date_from = f"{year}-{mon}-01"
        if mon == "12":
            date_to = f"{int(year)+1}-01-01"
        else:
            date_to = f"{year}-{int(mon)+1:02d}-01"
        date_filter = "WHERE record_date >= :df AND record_date < :dt AND is_reporting = 1"
        params = {"df": date_from, "dt": date_to}
        csv_label = month

    veh_result = await db.execute(text(f"""
        SELECT 
            vehicle, vendor, category, fleet_group, cluster,
            MAX(benchmark) as benchmark,
            COUNT(*) as reporting_days,
            SUM(total_km) as total_km,
            SUM(peak_hour) as on_peak_km,
            SUM(peak_off) as off_peak_km,
            SUM(fuel_drawn) as fuel_drawn,
            SUM(fuel_consumed) as fuel_consumed,
            SUM(harsh_braking) as harsh_braking,
            SUM(speed_violation) as speed_violation,
            SUM(excess_idling_mins) as excess_idling,
            AVG(total_km) as avg_daily_km
        FROM ke_gps_mis_daily
        {date_filter}
        GROUP BY vehicle, vendor, category, fleet_group, cluster
        ORDER BY SUM(total_km) DESC
    """), params)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Vehicle", "Vendor", "Category", "Fleet Group", "Cluster",
        "Benchmark km/L", "Reporting Days", "Total KM", "On-Peak KM", "Off-Peak KM",
        "Fuel Drawn (L)", "Fuel Consumed (L)", "Actual km/L",
        "Avg Daily KM", "Harsh Braking", "Speed Violation", "Excess Idling (mins)"
    ])
    for r in veh_result.fetchall():
        vk = float(r[7]) if r[7] else 0
        vf = float(r[11]) if r[11] else 0
        writer.writerow([
            r[0], r[1] or "", r[2] or "", r[3] or "", r[4] or "",
            round(float(r[5]) if r[5] else 0, 2),
            r[6],
            round(vk, 1), round(float(r[8]) if r[8] else 0, 1), round(float(r[9]) if r[9] else 0, 1),
            round(float(r[10]) if r[10] else 0, 1), round(vf, 1),
            round(vk / vf, 2) if vf > 0 else 0,
            round(float(r[15]) if r[15] else 0, 1),
            int(r[12] if r[12] else 0), int(r[13] if r[13] else 0), int(r[14] if r[14] else 0),
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=Monthly_MIS_{csv_label}.csv"}
    )


# ============================================================================
# ALERTS ENDPOINTS
# ============================================================================

@router.get("/alerts")
async def get_alerts(
    alert_type: str = None,
    severity: str = None,
    vehicle: str = None,
    is_read: int = None,
    date_from: str = None,
    date_to: str = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get alerts with filters. All alerts are saved permanently."""
    try:
        conditions = []
        params = {}

        if alert_type:
            conditions.append("alert_type = :at")
            params["at"] = alert_type
        if severity:
            conditions.append("severity = :sev")
            params["sev"] = severity
        if vehicle:
            conditions.append("vehicle LIKE :veh")
            params["veh"] = f"%{vehicle}%"
        if is_read is not None:
            conditions.append("is_read = :ir")
            params["ir"] = is_read
        if date_from:
            conditions.append("alert_date >= :df")
            params["df"] = date_from
        if date_to:
            conditions.append("alert_date <= :dt")
            params["dt"] = date_to

        where = " AND ".join(conditions) if conditions else "1=1"
        params["lim"] = limit
        params["off"] = offset

        result = await db.execute(text(f"""
            SELECT id, vehicle, alert_type, severity, title, message, details, is_read, created_at,
                   is_acknowledged, acknowledged_by, acknowledged_at, action_taken
            FROM fleet_alerts
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT :lim OFFSET :off
        """), params)
        rows = result.fetchall()

        count_result = await db.execute(text(f"""
            SELECT COUNT(*) FROM fleet_alerts WHERE {where}
        """), params)
        total = count_result.fetchone()[0]

        unread_result = await db.execute(text("SELECT COUNT(*) FROM fleet_alerts WHERE is_read = 0"))
        unread_count = unread_result.fetchone()[0]

        alerts = []
        for r in rows:
            import json as _json
            details = None
            if r[6]:
                try:
                    details = _json.loads(r[6]) if isinstance(r[6], str) else r[6]
                except:
                    details = str(r[6])
            alerts.append({
                "id": r[0],
                "vehicle": r[1],
                "alert_type": r[2],
                "severity": r[3],
                "title": r[4],
                "message": r[5],
                "details": details,
                "is_read": bool(r[7]),
                "created_at": str(r[8]),
                "is_acknowledged": bool(r[9]),
                "acknowledged_by": r[10],
                "acknowledged_at": str(r[11]) if r[11] else None,
                "action_taken": r[12],
            })

        return {"alerts": alerts, "total": total, "unread": unread_count}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/alerts/unread-count")
async def get_unread_alert_count(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get count of unread alerts for the bell badge."""
    try:
        result = await db.execute(text("SELECT COUNT(*) FROM fleet_alerts WHERE is_read = 0"))
        count = result.fetchone()[0]
        return {"unread": count}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/alerts/stats")
async def get_alert_stats(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get alert statistics for dashboard."""
    try:
        result = await db.execute(text(f"""
            SELECT alert_type, severity, COUNT(*) as cnt
            FROM fleet_alerts
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL :days DAY)
            GROUP BY alert_type, severity
            ORDER BY cnt DESC
        """), {"days": days})
        rows = result.fetchall()

        by_type = {}
        by_severity = {"critical": 0, "warning": 0, "info": 0}
        for r in rows:
            t = r[0]
            s = r[1]
            c = r[2]
            by_type[t] = by_type.get(t, 0) + c
            if s in by_severity:
                by_severity[s] += c

        total_result = await db.execute(text(f"""
            SELECT COUNT(*) FROM fleet_alerts
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL :days DAY)
        """), {"days": days})
        total = total_result.fetchone()[0]

        return {"total": total, "by_type": by_type, "by_severity": by_severity}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/alerts/mark-read")
async def mark_alerts_read(
    body: dict = None,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Mark alerts as read. Pass {alert_ids: [1,2,3]} or {all: true}."""
    try:
        if body is None:
            body = {}
        all_flag = body.get("all", False)
        alert_ids = body.get("alert_ids", None)

        if all_flag:
            await db.execute(text("UPDATE fleet_alerts SET is_read = 1 WHERE is_read = 0"))
            await db.commit()
            return {"status": "ok", "message": "All alerts marked as read"}
        elif alert_ids:
            await db.execute(text("UPDATE fleet_alerts SET is_read = 1 WHERE id IN :ids"), {"ids": tuple(alert_ids)})
            await db.commit()
            return {"status": "ok", "message": f"{len(alert_ids)} alerts marked as read"}
        else:
            return {"status": "ok", "message": "No alerts to mark"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/alerts/create")
async def create_alert(
    body: dict = {},
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Create a new alert manually."""
    try:
        vehicle = body.get("vehicle", "")
        alert_type = body.get("alert_type", "custom_alert")
        severity = body.get("severity", "info")
        title = body.get("title", "")
        message = body.get("message", "")
        if not vehicle or not title:
            raise HTTPException(status_code=400, detail="vehicle and title are required")
        await db.execute(text("""
            INSERT INTO fleet_alerts (vehicle, alert_type, severity, title, message)
            VALUES (:v, :at, :sev, :t, :m)
        """), {"v": vehicle, "at": alert_type, "sev": severity, "t": title, "m": message})
        await db.commit()
        return {"status": "ok", "message": f"Alert created for {vehicle}"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/alerts/monthly-summary")
async def get_monthly_alert_summary(
    year: int = 2026,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get monthly alert summary for a year."""
    try:
        result = await db.execute(text("""
            SELECT MONTH(created_at) as mo, alert_type, severity, COUNT(*) as cnt
            FROM fleet_alerts
            WHERE YEAR(created_at) = :yr
            GROUP BY MONTH(created_at), alert_type, severity
            ORDER BY mo, cnt DESC
        """), {"yr": year})
        rows = result.fetchall()

        months = {}
        for r in rows:
            mo = int(r[0])
            if mo not in months:
                months[mo] = {"total": 0, "by_type": {}, "by_severity": {"critical": 0, "warning": 0, "info": 0}}
            months[mo]["total"] += r[3]
            months[mo]["by_type"][r[1]] = months[mo]["by_type"].get(r[1], 0) + r[3]
            if r[2] in months[mo]["by_severity"]:
                months[mo]["by_severity"][r[2]] += r[3]

        return {"year": year, "months": months}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================================
# ALERT PREFERENCES ENDPOINTS
# ============================================================================

@router.get("/alerts/preferences")
async def get_alert_preferences(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get user's alert type preferences."""
    try:
        user_id = current_user.get("sub", current_user.get("email", "admin"))
        result = await db.execute(text("""
            SELECT alert_type, enabled FROM alert_preferences
            WHERE user_id = :uid
        """), {"uid": user_id})
        rows = result.fetchall()
        
        if not rows:
            # First time - create defaults for all types
            all_types = [
                'hard_acceleration', 'hard_braking', 'hard_cornering',
                'overspeed', 'device_moving', 'device_stopped', 'device_online', 'device_offline',
                'ignition_on', 'ignition_off', 'driver_changed',
                'jamming', 'fatigue_driving', 'accident', 'low_battery',
                'power_off', 'fault', 'excessive_idle',
                'speed_alert', 'maintenance', 'imei_missing'
            ]
            for t in all_types:
                await db.execute(text("""
                    INSERT IGNORE INTO alert_preferences (user_id, alert_type, enabled)
                    VALUES (:uid, :at, 1)
                """), {"uid": user_id, "at": t})
            await db.commit()
            return {t: True for t in all_types}
        
        return {r[0]: bool(r[1]) for r in rows}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/alerts/preferences")
async def update_alert_preferences(
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Update user's alert type preferences. Body: {alert_type: true/false}"""
    try:
        user_id = current_user.get("sub", current_user.get("email", "admin"))
        for alert_type, enabled in body.items():
            await db.execute(text("""
                INSERT INTO alert_preferences (user_id, alert_type, enabled)
                VALUES (:uid, :at, :en)
                ON DUPLICATE KEY UPDATE enabled = :en
            """), {"uid": user_id, "at": alert_type, "en": 1 if enabled else 0})
        await db.commit()
        return {"status": "ok", "message": "Preferences updated"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/alerts/all-types")
async def get_all_alert_types(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get all available alert types with their categories."""
    try:
        result = await db.execute(text("""
            SELECT alert_type, severity, COUNT(*) as cnt
            FROM fleet_alerts
            GROUP BY alert_type, severity
            ORDER BY cnt DESC
        """))
        rows = result.fetchall()
        
        types_info = {
            'hard_acceleration': {'label': 'Hard Acceleration', 'category': 'Driving Behavior', 'icon': 'zap'},
            'hard_braking': {'label': 'Hard Braking', 'category': 'Driving Behavior', 'icon': 'shield-alert'},
            'hard_cornering': {'label': 'Hard Cornering', 'category': 'Driving Behavior', 'icon': 'rotate-cw'},
            'overspeed': {'label': 'Overspeed', 'category': 'Speed', 'icon': 'gauge'},
            'speed_alert': {'label': 'Speed Alert', 'category': 'Speed', 'icon': 'alert-triangle'},
            'device_moving': {'label': 'Vehicle Moving', 'category': 'Vehicle Status', 'icon': 'move'},
            'device_stopped': {'label': 'Vehicle Stopped', 'category': 'Vehicle Status', 'icon': 'square'},
            'device_online': {'label': 'Device Online', 'category': 'Device', 'icon': 'wifi'},
            'device_offline': {'label': 'Device Offline', 'category': 'Device', 'icon': 'wifi-off'},
            'ignition_on': {'label': 'Ignition On', 'category': 'Vehicle Status', 'icon': 'power'},
            'ignition_off': {'label': 'Ignition Off', 'category': 'Vehicle Status', 'icon': 'power'},
            'driver_changed': {'label': 'Driver Changed', 'category': 'Driver', 'icon': 'user'},
            'jamming': {'label': 'GPS Jamming', 'category': 'Security', 'icon': 'radio'},
            'fatigue_driving': {'label': 'Fatigue Driving', 'category': 'Safety', 'icon': 'bed'},
            'accident': {'label': 'Accident', 'category': 'Safety', 'icon': 'alert-octagon'},
            'low_battery': {'label': 'Low Battery', 'category': 'Device', 'icon': 'battery-low'},
            'power_off': {'label': 'Power Off', 'category': 'Device', 'icon': 'power'},
            'fault': {'label': 'Device Fault', 'category': 'Device', 'icon': 'alert-circle'},
            'excessive_idle': {'label': 'Excessive Idle', 'category': 'Driving Behavior', 'icon': 'clock'},
            'idle_alert': {'label': 'Idle Alert', 'category': 'Driving Behavior', 'icon': 'clock'},
            'maintenance': {'label': 'Maintenance', 'category': 'Maintenance', 'icon': 'wrench'},
            'imei_missing': {'label': 'IMEI Missing', 'category': 'Fleet', 'icon': 'hash'},
            'geofence_enter': {'label': 'Geofence Enter', 'category': 'Geofence', 'icon': 'log-in'},
            'geofence_exit': {'label': 'Geofence Exit', 'category': 'Geofence', 'icon': 'log-out'},
            'custom_alert': {'label': 'Custom Alert', 'category': 'Custom', 'icon': 'message-square'},
        }
        
        result_list = []
        for r in rows:
            at = r[0]
            info = types_info.get(at, {'label': at.replace('_', ' ').title(), 'category': 'Other', 'icon': 'bell'})
            result_list.append({
                'type': at,
                'label': info['label'],
                'category': info['category'],
                'icon': info['icon'],
                'severity': r[1],
                'count': r[2]
            })
        
        return {"types": result_list}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

# ── PUT /alerts/{alert_id}/acknowledge ───────────────────────────────────────
@router.put("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Acknowledge an alert so it can be sent forward."""
    try:
        user_name = current_user.get("name") or current_user.get("email") or "Unknown"
        await db.execute(text("""
            UPDATE fleet_alerts
            SET is_acknowledged = 1, acknowledged_by = :user_name, acknowledged_at = NOW()
            WHERE id = :alert_id
        """), {"alert_id": alert_id, "user_name": user_name})
        await db.commit()
        return {"success": True, "message": "Alert acknowledged"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

# ── PUT /alerts/{alert_id}/action ────────────────────────────────────────────
@router.put("/alerts/{alert_id}/action")
async def set_alert_action(
    alert_id: int,
    body: dict = {},
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Set action taken on an alert (escalated, dismissed, assigned, etc.)."""
    try:
        action = body.get("action", "")
        user_name = current_user.get("name") or current_user.get("email") or "Unknown"
        await db.execute(text("""
            UPDATE fleet_alerts
            SET action_taken = :action, is_acknowledged = 1, acknowledged_by = :user_name, acknowledged_at = NOW()
            WHERE id = :alert_id
        """), {"alert_id": alert_id, "action": action, "user_name": user_name})
        await db.commit()
        return {"success": True, "message": f"Action '{action}' recorded"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

# ── POST /alerts/mark-all-read ───────────────────────────────────────────────
@router.post("/alerts/mark-all-read")
async def mark_all_alerts_read(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Mark all alerts as read."""
    try:
        await db.execute(text("UPDATE fleet_alerts SET is_read = 1 WHERE is_read = 0"))
        await db.commit()
        return {"success": True, "message": "All alerts marked as read"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

# ── GET /alerts/summary ─────────────────────────────────────────────────────
@router.get("/alerts/summary")
async def get_alerts_summary(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get dashboard summary for alerts — eco driving, top offenders, severity breakdown."""
    try:
        # Combined query: eco driving counts + 30-day trend + severity + totals
        cursor = await db.execute(text("""
            SELECT
                SUM(CASE WHEN alert_type = 'hard_braking' THEN 1 ELSE 0 END) as brk_total,
                SUM(CASE WHEN alert_type = 'hard_acceleration' THEN 1 ELSE 0 END) as acc_total,
                SUM(CASE WHEN alert_type = 'hard_cornering' THEN 1 ELSE 0 END) as crn_total,
                SUM(CASE WHEN alert_type IN ('idle_alert','excessive_idle') THEN 1 ELSE 0 END) as idle_total,
                SUM(CASE WHEN alert_type IN ('overspeed','speed_alert') THEN 1 ELSE 0 END) as spd_total,
                SUM(CASE WHEN alert_type IN ('hard_braking','hard_acceleration','hard_cornering','idle_alert','excessive_idle','overspeed','speed_alert') THEN 1 ELSE 0 END) as harsh_total,
                SUM(CASE WHEN alert_type = 'hard_braking' AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY) THEN 1 ELSE 0 END) as brk_tw,
                SUM(CASE WHEN alert_type = 'hard_braking' AND created_at >= DATE_SUB(NOW(), INTERVAL 60 DAY) AND created_at < DATE_SUB(NOW(), INTERVAL 30 DAY) THEN 1 ELSE 0 END) as brk_lw,
                SUM(CASE WHEN alert_type = 'hard_acceleration' AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY) THEN 1 ELSE 0 END) as acc_tw,
                SUM(CASE WHEN alert_type = 'hard_acceleration' AND created_at >= DATE_SUB(NOW(), INTERVAL 60 DAY) AND created_at < DATE_SUB(NOW(), INTERVAL 30 DAY) THEN 1 ELSE 0 END) as acc_lw,
                SUM(CASE WHEN alert_type = 'hard_cornering' AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY) THEN 1 ELSE 0 END) as crn_tw,
                SUM(CASE WHEN alert_type = 'hard_cornering' AND created_at >= DATE_SUB(NOW(), INTERVAL 60 DAY) AND created_at < DATE_SUB(NOW(), INTERVAL 30 DAY) THEN 1 ELSE 0 END) as crn_lw,
                SUM(CASE WHEN alert_type IN ('idle_alert','excessive_idle') AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY) THEN 1 ELSE 0 END) as idle_tw,
                SUM(CASE WHEN alert_type IN ('idle_alert','excessive_idle') AND created_at >= DATE_SUB(NOW(), INTERVAL 60 DAY) AND created_at < DATE_SUB(NOW(), INTERVAL 30 DAY) THEN 1 ELSE 0 END) as idle_lw,
                SUM(CASE WHEN alert_type IN ('overspeed','speed_alert') AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY) THEN 1 ELSE 0 END) as spd_tw,
                SUM(CASE WHEN alert_type IN ('overspeed','speed_alert') AND created_at >= DATE_SUB(NOW(), INTERVAL 60 DAY) AND created_at < DATE_SUB(NOW(), INTERVAL 30 DAY) THEN 1 ELSE 0 END) as spd_lw,
                SUM(CASE WHEN alert_type IN ('hard_braking','hard_acceleration','hard_cornering','idle_alert','excessive_idle','overspeed','speed_alert') AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY) THEN 1 ELSE 0 END) as harsh_tw,
                SUM(CASE WHEN alert_type IN ('hard_braking','hard_acceleration','hard_cornering','idle_alert','excessive_idle','overspeed','speed_alert') AND created_at >= DATE_SUB(NOW(), INTERVAL 60 DAY) AND created_at < DATE_SUB(NOW(), INTERVAL 30 DAY) THEN 1 ELSE 0 END) as harsh_lw,
                SUM(CASE WHEN severity = 'critical' THEN 1 ELSE 0 END) as sev_crit,
                SUM(CASE WHEN severity = 'warning' THEN 1 ELSE 0 END) as sev_warn,
                SUM(CASE WHEN severity = 'info' THEN 1 ELSE 0 END) as sev_info,
                COUNT(*) as total_all,
                SUM(CASE WHEN is_read = 0 THEN 1 ELSE 0 END) as total_unread,
                SUM(CASE WHEN is_acknowledged = 1 THEN 1 ELSE 0 END) as total_ack
            FROM fleet_alerts
        """))
        result = cursor.fetchone()

        def _trend(tw, lw):
            tw, lw = tw or 0, lw or 0
            pct = round(((tw - lw) / lw * 100), 1) if lw > 0 else (100 if tw > 0 else 0)
            return {"this_week": tw, "last_week": lw, "change_pct": pct}

        behavior = {
            "hard_braking": result[0] or 0, "hard_acceleration": result[1] or 0, "hard_cornering": result[2] or 0,
            "idle": result[3] or 0, "overspeed": result[4] or 0, "harsh_driving": result[5] or 0
        }
        behavior_trend = {
            "hard_braking": _trend(result[6], result[7]), "hard_acceleration": _trend(result[8], result[9]),
            "hard_cornering": _trend(result[10], result[11]), "idle": _trend(result[12], result[13]),
            "overspeed": _trend(result[14], result[15]), "harsh_driving": _trend(result[16], result[17])
        }
        severity = {"critical": result[18] or 0, "warning": result[19] or 0, "info": result[20] or 0}

        # Top 10 vehicles (single query)
        top_result = await db.execute(text("""
            SELECT vehicle, COUNT(*) as cnt,
                SUM(CASE WHEN alert_type = 'hard_braking' THEN 1 ELSE 0 END) as brk,
                SUM(CASE WHEN alert_type = 'hard_acceleration' THEN 1 ELSE 0 END) as acc,
                SUM(CASE WHEN alert_type = 'hard_cornering' THEN 1 ELSE 0 END) as crn,
                SUM(CASE WHEN alert_type IN ('overspeed','speed_alert') THEN 1 ELSE 0 END) as spd,
                SUM(CASE WHEN alert_type IN ('idle_alert','excessive_idle') THEN 1 ELSE 0 END) as idle
            FROM fleet_alerts GROUP BY vehicle ORDER BY cnt DESC LIMIT 10
        """))
        top_vehicles = [{"vehicle": r[0], "total": r[1], "braking": r[2], "accel": r[3], "cornering": r[4], "speeding": r[5], "idle": r[6]} for r in top_result.fetchall()]

        # Daily trend last 14 days (for better visual)
        daily_result = await db.execute(text("""
            SELECT DATE(created_at) as dt, COUNT(*) as cnt
            FROM fleet_alerts
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 14 DAY)
            GROUP BY DATE(created_at) ORDER BY dt ASC
        """))
        daily_trend = [{"date": str(r[0]), "count": r[1]} for r in daily_result.fetchall()]

        return {
            "total": result[12] or 0, "unread": result[13] or 0, "acknowledged": result[14] or 0,
            "behavior": behavior, "behavior_trend": behavior_trend, "severity": severity,
            "top_vehicles": top_vehicles, "daily_trend": daily_trend,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

# ── DELETE /alerts/{alert_id}/dismiss ───────────────────────────────────────
@router.delete("/alerts/{alert_id}/dismiss")
async def dismiss_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Dismiss/close an alert (permanently remove)."""
    try:
        await db.execute(text("DELETE FROM fleet_alerts WHERE id = :aid"), {"aid": alert_id})
        await db.commit()
        return {"success": True, "message": "Alert dismissed"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

# ── GET /alerts/severity-context ────────────────────────────────────────────
@router.get("/alerts/severity-context")
async def get_severity_context(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get detailed context for severity breakdown (non-eco items only)."""
    try:
        result = await db.execute(text("""
            SELECT 
                severity,
                COUNT(*) as cnt,
                SUM(CASE WHEN alert_type = 'device_offline' THEN 1 ELSE 0 END) as offline,
                SUM(CASE WHEN alert_type = 'device_offline' AND created_at < NOW() - INTERVAL 5 DAY THEN 1 ELSE 0 END) as offline_5d,
                SUM(CASE WHEN alert_type IN ('accident','fatigue_driving','jamming') THEN 1 ELSE 0 END) as safety,
                SUM(CASE WHEN alert_type IN ('geofence_enter','geofence_exit') THEN 1 ELSE 0 END) as geofence,
                SUM(CASE WHEN alert_type IN ('ignition_on','ignition_off','device_moving','device_stopped','device_online') THEN 1 ELSE 0 END) as routine,
                SUM(CASE WHEN alert_type IN ('maintenance') THEN 1 ELSE 0 END) as maintenance,
                SUM(CASE WHEN alert_type IN ('custom_alert') THEN 1 ELSE 0 END) as custom,
                SUM(CASE WHEN alert_type IN ('low_battery','power_off','fault') THEN 1 ELSE 0 END) as device_issues
            FROM fleet_alerts
            GROUP BY severity
        """))
        
        context_map = {}
        for r in result.fetchall():
            severity = r[0]
            cnt = r[1]
            offline = r[2] or 0
            offline_5d = r[3] or 0
            safety = r[4] or 0
            geofence = r[5] or 0
            routine = r[6] or 0
            maintenance = r[7] or 0
            custom = r[8] or 0
            device_issues = r[9] or 0
            
            if severity == 'critical':
                parts = []
                if offline_5d > 0: parts.append(f"{offline_5d} offline >5 days")
                if safety > 0: parts.append(f"{safety} safety critical (accident/fatigue)")
                if offline > offline_5d and offline_5d > 0: parts.append(f"{offline - offline_5d} recent offline")
                context = ", ".join(parts) if parts else "Critical events"
            elif severity == 'warning':
                parts = []
                if geofence > 0: parts.append(f"{geofence} geofence alerts")
                if device_issues > 0: parts.append(f"{device_issues} device issues (battery/power/fault)")
                context = ", ".join(parts) if parts else "Warning events"
            else:
                parts = []
                if routine > 0: parts.append(f"{routine} routine")
                if maintenance > 0: parts.append(f"{maintenance} maintenance")
                if custom > 0: parts.append(f"{custom} custom")
                context = ", ".join(parts) if parts else "Info events"
            
            context_map[severity] = {
                "count": cnt,
                "context": context,
                "breakdown": {
                    "offline_5d": offline_5d,
                    "harsh_recent": harsh_recent,
                    "overspeed": overspeed,
                    "idle": idle,
                    "safety": safety,
                    "routine": routine,
                    "maintenance": maintenance,
                    "custom": custom
                }
            }
        
        return context_map
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
