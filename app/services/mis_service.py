import datetime
from typing import Dict, List, Any, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from loguru import logger
import asyncio

class MISService:
    @staticmethod
    async def generate_daily_mis(db: AsyncSession, target_date: Optional[datetime.date] = None):
        """
        Automated MIS Generator:
        Calculates daily stats for all vehicles in ke_fleet_database
        using optimized, concurrent indexed queries against the live Traccar database (PC12).
        """
        if not target_date:
            target_date = (datetime.datetime.now() - datetime.timedelta(days=1)).date()
        
        date_str = target_date.strftime("%Y-%m-%d")
        logger.info(f"[MIS-AUTO] Starting High-Speed Index-Optimized MIS Sync for {date_str}")

        # 1. Fetch metadata mapping locally
        vehicles_result = await db.execute(text("""
            SELECT f.vehicle_registration, f.benchmark_kmpl, f.shift_hrs,
                   f.vehicle_category, f.fleet_vendor, f.fleet_group, f.cluster,
                   f.bu_function, f.ibc_vibc, f.sub_department,
                   m.imei
            FROM ke_fleet_database f
            LEFT JOIN ke_vehicle_imei m ON f.vehicle_registration = m.alias_name
            WHERE m.imei IS NOT NULL
        """))
        v_rows = vehicles_result.fetchall()
        
        v_map = {}
        imeis_to_fetch = []
        for r in v_rows:
            imei = str(r[10]).strip()
            imeis_to_fetch.append(imei)
            v_map[imei] = {
                "reg": r[0],
                "bench": float(r[1]) if r[1] else 10.0,
                "shift": float(r[2]) if r[2] else 10.0,
                "cat": r[3], "vendor": r[4], "grp": r[5], "cluster": r[6],
                "func": r[7], "ibc": r[8], "sub": r[9]
            }

        logger.info(f"[MIS-AUTO] Loaded {len(v_map)} vehicles for sync.")
        
        # 2. Setup Async Engine for PC12
        PC12_DB_URL = "mysql+aiomysql://traccar:traccar12344321@202.141.246.12/traccar"
        remote_engine = create_async_engine(PC12_DB_URL, pool_size=20, max_overflow=50, connect_args={"connect_timeout": 5})
        
        # We need to map IMEI -> deviceid first
        device_mapping = {}
        try:
            async with remote_engine.connect() as remote_conn:
                d_query = text("SELECT id, uniqueid FROM tc_devices")
                d_res = await remote_conn.execute(d_query)
                for did, dstr in d_res.fetchall():
                    if str(dstr) in v_map:
                        device_mapping[did] = str(dstr)
        except Exception as e:
            logger.error(f"[MIS-AUTO] Failed fetching device metadata: {e}")
            await remote_engine.dispose()
            return {"date": date_str, "processed": 0, "errors": 1, "detail": "PC12 Timeout"}
        
        logger.info(f"[MIS-AUTO] Mapped {len(device_mapping)} remote device IDs.")
        
        # 3. Concurrently fetch aggregated stats for each device
        # Leveraging Traccar's index: `deviceid, fixtime`
        agg_rows = []
        semaphore = asyncio.Semaphore(15) # Concurrent DB queries 

        async def fetch_device_stats(device_id):
            async with semaphore:
                try:
                    async with remote_engine.connect() as conn:
                        q = text("""
                            SELECT 
                                :did as device_id,
                                COUNT(*) as total_pos,
                                SUM(CASE WHEN speed = 0 THEN 1 ELSE 0 END) as idle_pos,
                                SUM(CASE WHEN (speed * 1.852) > 120 THEN 1 ELSE 0 END) as violations,
                                MAX(speed * 1.852) as max_speed,
                                SUM(speed * 1.852) as sum_speed,
                                SUM(CASE WHEN speed > 0 THEN (speed * 1.852)/3600 ELSE 0 END) as total_km,
                                SUM(CASE WHEN speed > 0 AND HOUR(fixtime) BETWEEN 6 AND 17 THEN (speed * 1.852)/3600 ELSE 0 END) as peak_km,
                                SUM(CASE WHEN speed > 0 AND (HOUR(fixtime) < 6 OR HOUR(fixtime) >= 18) THEN (speed * 1.852)/3600 ELSE 0 END) as off_peak_km
                            FROM tc_positions p
                            WHERE deviceid = :did AND fixtime >= :sd AND fixtime < DATE_ADD(:sd, INTERVAL 1 DAY)
                        """)
                        res = await conn.execute(q, {"did": device_id, "sd": date_str})
                        row = res.fetchone()
                        if row and row[1] > 0: # If has positions
                            return row
                except Exception as e:
                    logger.warning(f"Error fetching device {device_id}: {e}")
                return None

        # Gather tasks
        tasks = [fetch_device_stats(did) for did in device_mapping.keys()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for r in results:
            if r and not isinstance(r, Exception):
                agg_rows.append(r)
                
        await remote_engine.dispose()
        logger.info(f"[MIS-AUTO] Aggregation complete. Received data for {len(agg_rows)} vehicles.")

        # 4. Process and match with KE mapping, then UPSERT locally
        bulk_data = []
        processed = 0
        
        for r in agg_rows:
            did = r[0]
            imei = device_mapping.get(did)
            if not imei or imei not in v_map:
                continue
                
            v = v_map[imei]
            total_km = round(float(r[6] or 0), 2)
            if total_km < 0.1:
                continue # Ignore vehicles that didn't move
            
            benchmark = v["bench"]
            fuel_consumed = round(total_km / benchmark, 2) if benchmark > 0 else 0
            avg_speed = round(float(r[5] or 0) / float(r[1] or 1), 1)
            
            bulk_data.append({
                "rd": date_str, "v": v["reg"], "vn": v["vendor"], "cat": v["cat"], 
                "fg": v["grp"], "cl": v["cluster"], "bf": v["func"], "iv": v["ibc"], "sd": v["sub"],
                "bm": benchmark, "sh": v["shift"], "tkm": total_km, 
                "ph": round(float(r[7] or 0), 2), "po": round(float(r[8] or 0), 2),
                "avg": avg_speed, "max": round(float(r[4] or 0), 1), 
                "fc": fuel_consumed, "sv": int(r[3] or 0),
                "rem": "System Generated (Live Sync)"
            })
            processed += 1

        if bulk_data:
            logger.info(f"[MIS-AUTO] Writing {len(bulk_data)} records to local database...")
            upsert_sql = text("""
                INSERT INTO ke_mis_daily 
                (record_date, vehicle, vendor, category, fleet_group, cluster, bu_function, ibc_vibc, sub_department,
                 benchmark, shift_hrs, total_km, peak_hour, peak_off, avg_speed_kmh, max_speed_kmh, 
                 fuel_consumed, speed_violation, remarks)
                VALUES (:rd, :v, :vn, :cat, :fg, :cl, :bf, :iv, :sd, :bm, :sh, :tkm, :ph, :po, :avg, :max, :fc, :sv, :rem)
                ON DUPLICATE KEY UPDATE 
                    total_km = VALUES(total_km), peak_hour = VALUES(peak_hour), peak_off = VALUES(peak_off),
                    avg_speed_kmh = VALUES(avg_speed_kmh), max_speed_kmh = VALUES(max_speed_kmh),
                    fuel_consumed = VALUES(fuel_consumed), speed_violation = VALUES(speed_violation),
                    remarks = VALUES(remarks)
            """)
            
            for i in range(0, len(bulk_data), 500):
                await db.execute(upsert_sql, bulk_data[i:i+500])
                
            await db.commit()

        logger.info(f"[MIS-AUTO] High-Speed MIS Generation complete. Inserted/Updated: {processed}.")
        return {"date": date_str, "processed": processed, "errors": 0}
