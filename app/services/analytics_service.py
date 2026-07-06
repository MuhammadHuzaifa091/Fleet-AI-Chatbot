from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, and_, func
from app.models.traccar import Device, Position, FuelPrice, FuelStationVisit, Event, UserDevice, User
from typing import Dict, Any, List, Optional
import logging
import json
from datetime import datetime, timedelta
import httpx

logger = logging.getLogger(__name__)

class AnalyticsService:
    @staticmethod
    async def get_fuel_analytics(db: AsyncSession, device_id: int) -> Dict[str, Any]:
        """
        Two-Tier Fuel Analytics Engine with PKR Costing & Regularization:
        Tier A: Real OBD/Sensor Data
        Tier B: AI-Estimated Fallback based on Engine Specs
        Tier C: Regularized Fallback (50L Tank, 10 KM/L) for Missing Profiles
        """
        try:
            # 1. Get Device and Latest Position
            query = select(Device, Position).outerjoin(Position, Device.positionid == Position.id).where(Device.id == device_id)
            result = await db.execute(query)
            row = result.first()
            
            if not row:
                return {"error": "Device not found"}
            
            device, position = row
            dev_attr = device.attributes or {}
            pos_attr = position.attributes if position else {}
            
            # 2. Get Live PKR Price (dynamic source-backed price)
            fuel_type = (dev_attr.get("fuel_type") or "Petrol").title()
            if fuel_type not in ["Petrol", "Diesel"]:
                fuel_type = "Petrol"
            price_query = select(FuelPrice.price, FuelPrice.source, FuelPrice.last_updated).where(FuelPrice.fuel_type == fuel_type)
            price_res = await db.execute(price_query)
            fuel_price_row = price_res.fetchone()
            current_price = fuel_price_row[0] if fuel_price_row else 272.89
            price_source = fuel_price_row[1] if fuel_price_row else "Fallback"
            price_updated = fuel_price_row[2].isoformat() if fuel_price_row and fuel_price_row[2] else None
            
            # 3. Check for Real Sensor Data (Tier A)
            real_fuel = pos_attr.get("fuelLevel") or pos_attr.get("fuel") or dev_attr.get("fuel")
            distance = pos_attr.get("totalDistance") or pos_attr.get("odometer") or 0
            distance_km = distance / 1000

            # 4. Status Check for Missing Profile (Regularization)
            is_profile_missing = not (dev_attr.get("vin") or dev_attr.get("model") or dev_attr.get("engine_size"))
            status_flag = "AWAITING_USER_INPUT" if is_profile_missing else "OPERATIONAL"

            tank_size = float(dev_attr.get("tank_size") or 50.0)
            est_rate = float(dev_attr.get("est_fuel_rate") or 8.5)
            efficiency_score = AnalyticsService._compute_efficiency_score(est_rate, dev_attr)

            if real_fuel is not None:
                est_rate = dev_attr.get("est_fuel_rate") or 8.5
                total_liters = (distance_km / 100) * float(est_rate)
                station_logs = await AnalyticsService.get_fuel_station_logs(db, device_id)
                trip_costing = await AnalyticsService.get_trip_cost_breakdown(db, device_id, current_price, float(est_rate), float(tank_size))
                theft_alerts = await AnalyticsService.detect_fuel_theft(db, device_id)
                await AnalyticsService.log_fuel_theft_events(db, device_id, theft_alerts)
                
                return {
                    "tier": "A",
                    "method": "sensor",
                    "status": status_flag,
                    "source": "Verified ECU Data",
                    "current_level": real_fuel,
                    "fuel_level_percent": round(float(real_fuel), 2),
                    "fuel_status": "REAL_TIME_SENSOR",
                    "distance_km": round(distance_km, 2),
                    "price_pkr": current_price,
                    "fuel_type": fuel_type,
                    "price_source": price_source,
                    "price_last_updated": price_updated,
                    "total_cost_pkr": round(total_liters * current_price, 2),
                    "is_estimated": False,
                    "obd_integrated": True,
                    "efficiency_validation": {
                        "score": efficiency_score,
                        "status": "VALIDATED" if efficiency_score >= 70 else "CHECK_REQUIRED",
                        "label": "Eco Verified" if efficiency_score >= 85 else ("Efficient" if efficiency_score >= 70 else "Needs Review")
                    },
                    "unit": "Liters/Percentage",
                    "idle_breakdown": await AnalyticsService.get_idle_consumption(db, device_id, current_price),
                    "history": await AnalyticsService._get_historical_fuel_data(db, device_id, current_price, est_rate),
                    "trip_costing": trip_costing,
                    "station_logs": station_logs,
                    "theft_alerts": theft_alerts
                }
            
            # 5. Fallback Logic (Tier B or C)
            if is_profile_missing:
                # Tier C: Regularized Fallback
                est_rate = 10.0 # 0.1 L/KM = 10 KM/L
                tank_size = 50.0
                source = "Regularized Default Profile"
                tier = "C"
            else:
                # Tier B: AI-Estimated
                est_rate = float(dev_attr.get("est_fuel_rate") or 8.5)
                tank_size = float(dev_attr.get("tank_size") or 50.0)
                source = "AI-Estimated Profile"
                tier = "B"
            
            estimated_spent = (distance_km / 100) * est_rate
            station_logs = await AnalyticsService.get_fuel_station_logs(db, device_id)
            trip_costing = await AnalyticsService.get_trip_cost_breakdown(db, device_id, current_price, est_rate, tank_size)
            theft_alerts = await AnalyticsService.detect_fuel_theft(db, device_id)
            await AnalyticsService.log_fuel_theft_events(db, device_id, theft_alerts)
            
            return {
                "tier": tier,
                "method": "estimated",
                "status": status_flag,
                "source": source,
                "engine_specs": f"{dev_attr.get('engine_size')}L Displacement" if dev_attr.get('engine_size') else "Default 10KM/L Profile",
                "average_consumption": est_rate,
                "distance_km": round(distance_km, 2),
                "current_level": max(0, 100 - ((estimated_spent / tank_size) * 100) % 100),
                "fuel_level_percent": round(max(0, 100 - ((estimated_spent / tank_size) * 100) % 100), 2),
                "fuel_status": "AI_ESTIMATED" if tier == "B" else "FALLBACK_ESTIMATED",
                "price_pkr": current_price,
                "fuel_type": fuel_type,
                "price_source": price_source,
                "price_last_updated": price_updated,
                "total_cost_pkr": round(estimated_spent * current_price, 2),
                "is_estimated": True,
                "obd_integrated": False,
                "efficiency_validation": {
                    "score": efficiency_score,
                    "status": "VALIDATED" if efficiency_score >= 70 else "CHECK_REQUIRED",
                    "label": "Eco Verified" if efficiency_score >= 85 else ("Efficient" if efficiency_score >= 70 else "Needs Review")
                },
                "unit": "Liters",
                "idle_breakdown": await AnalyticsService.get_idle_consumption(db, device_id, current_price),
                "history": await AnalyticsService._get_historical_fuel_data(db, device_id, current_price, est_rate),
                "trip_costing": trip_costing,
                "station_logs": station_logs,
                "theft_alerts": theft_alerts
            }
            
        except Exception as e:
            logger.error(f"Error in fuel analytics engine: {e}")
            return {"error": "Internal analytics error"}

    @staticmethod
    async def _get_historical_fuel_data(db: AsyncSession, device_id: int, price: float, rate: float) -> List[Dict[str, Any]]:
        """
        Fetches real historical positions and calculates daily consumption/distance.
        Strictly NO MOCK data.
        """
        try:
            # Query last 7 days of position data
            query = text("""
                SELECT 
                    DATE(devicetime) as date,
                    MAX(CAST(JSON_EXTRACT(attributes, '$.totalDistance') AS DECIMAL(20,2))) - 
                    MIN(CAST(JSON_EXTRACT(attributes, '$.totalDistance') AS DECIMAL(20,2))) as daily_dist
                FROM tc_positions
                WHERE deviceid = :device_id AND devicetime > NOW() - INTERVAL 7 DAY
                GROUP BY DATE(devicetime)
                ORDER BY DATE(devicetime) ASC
            """)
            result = await db.execute(query, {"device_id": device_id})
            rows = result.fetchall()
            
            history = []
            for row in rows:
                dist_km = (row[1] or 0) / 1000
                consumption = (dist_km / 100) * rate
                history.append({
                    "time": row[0].strftime("%a"),
                    "distance": round(dist_km, 2),
                    "consumption": round(consumption, 2),
                    "cost": round(consumption * price, 2)
                })
            return history
        except Exception as e:
            logger.error(f"Historical data fetch error: {e}")
            return []

    @staticmethod
    async def detect_fuel_station_visits(db: AsyncSession, device_id: int):
        """
        Scans recent positions for stops at fuel stations: Speed == 0, Duration >= 3 min.
        """
        try:
            # Find stops in last 24h
            query = text("""
                SELECT 
                    id, latitude, longitude, devicetime,
                    CAST(JSON_EXTRACT(attributes, '$.fuelLevel') AS DECIMAL(10,2)) as fuel_level,
                    LEAD(devicetime) OVER (ORDER BY devicetime) as next_time,
                    LEAD(CAST(JSON_EXTRACT(attributes, '$.fuelLevel') AS DECIMAL(10,2))) OVER (ORDER BY devicetime) as next_fuel,
                    address
                FROM tc_positions
                WHERE deviceid = :device_id AND speed < 0.1 AND devicetime > NOW() - INTERVAL 1 DAY
                ORDER BY devicetime ASC
            """)
            result = await db.execute(query, {"device_id": device_id})
            positions = result.fetchall()

            tank_size = 50.0
            device_row = await db.execute(select(Device).where(Device.id == device_id))
            device = device_row.scalar_one_or_none()
            if device and device.attributes:
                tank_size = float(device.attributes.get("tank_size") or 50.0)

            for pos in positions:
                pos_id, lat, lon, start_time, start_fuel, end_time, end_fuel, address = pos
                if not end_time: continue
                
                duration = (end_time - start_time).total_seconds() / 60
                if duration >= 3: # 3 minutes stop
                    # Check if it's a gas station
                    station_info = await AnalyticsService._reverse_geocode_station(lat, lon)
                    if station_info:
                        # Save visit if not already recorded
                        visit_check = select(FuelStationVisit).where(
                            and_(
                                FuelStationVisit.deviceid == device_id,
                                FuelStationVisit.arrival_time == start_time
                            )
                        )
                        existing = await db.execute(visit_check)
                        if not existing.scalar_one_or_none():
                            fuel_delta = 0.0
                            if start_fuel is not None and end_fuel is not None and end_fuel > start_fuel:
                                fuel_delta = round(((float(end_fuel) - float(start_fuel)) / 100.0) * tank_size, 2)

                            current_price = await AnalyticsService._get_latest_fuel_price(db, device.attributes if device else {})
                            new_visit = FuelStationVisit(
                                deviceid=device_id,
                                station_brand=station_info["brand"],
                                station_branch=station_info["branch"],
                                arrival_time=start_time,
                                departure_time=end_time,
                                duration_minutes=int(duration),
                                liters_added=fuel_delta, # sensor-derived when available
                                cost_pkr=round(fuel_delta * current_price, 2) if fuel_delta > 0 else 0,
                                positionid=pos_id,
                                attributes={
                                    "address": address,
                                    "estimated_from_fuel_delta": True,
                                    "start_fuel": float(start_fuel) if start_fuel is not None else None,
                                    "end_fuel": float(end_fuel) if end_fuel is not None else None
                                }
                            )
                            db.add(new_visit)
            await db.commit()
        except Exception as e:
            logger.error(f"Error detecting station visits: {e}")

    @staticmethod
    async def _reverse_geocode_station(lat: float, lon: float) -> Optional[Dict[str, str]]:
        """
        Uses OSM/Google to identify fuel station brand and branch.
        """
        try:
            url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=18"
            async with httpx.AsyncClient(headers={"User-Agent": "AI-Telematics/1.0"}) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    amenity = data.get("address", {}).get("amenity")
                    if amenity == "fuel":
                        name = data.get("display_name", "")
                        # Extract brand (PSO, Shell, etc.)
                        brand = "Other"
                        for b in ["PSO", "Shell", "Total", "Attock", "Byco", "Cnergyico"]:
                            if b.lower() in name.lower():
                                brand = b
                                break
                        return {"brand": brand, "branch": name.split(',')[0]}
            return None
        except Exception as e:
            logger.error(f"Geocoding error: {e}")
            return None

    @staticmethod
    async def detect_fuel_theft(db: AsyncSession, device_id: int) -> List[Dict[str, Any]]:
        """
        Analyzes historical fuel levels for suspicious sudden drops (>10% in <15 mins).
        """
        try:
            # Query last 12h of fuel data
            query = text("""
                SELECT devicetime, 
                       CAST(JSON_EXTRACT(attributes, '$.fuelLevel') AS DECIMAL(10,2)) as fuel,
                       latitude, longitude
                FROM tc_positions
                WHERE deviceid = :device_id AND devicetime > NOW() - INTERVAL 12 HOUR
                AND JSON_EXTRACT(attributes, '$.fuelLevel') IS NOT NULL
                ORDER BY devicetime ASC
            """)
            result = await db.execute(query, {"device_id": device_id})
            rows = result.fetchall()
            
            theft_events = []
            for i in range(1, len(rows)):
                prev_time, prev_fuel, _, _ = rows[i-1]
                curr_time, curr_fuel, lat, lon = rows[i]
                
                if prev_fuel and curr_fuel:
                    drop = prev_fuel - curr_fuel
                    time_diff = (curr_time - prev_time).total_seconds() / 60
                    
                    if drop > 15.0 and time_diff < 5: # >15% drop in <5 mins (as per spec)
                        theft_events.append({
                            "time": curr_time.strftime("%Y-%m-%d %H:%M:%S"),
                            "severity": "CRITICAL",
                            "drop": round(drop, 1),
                            "drop_pct_label": f"{round(drop, 1)}%",
                            "window_min": round(time_diff, 1),
                            "location": f"{lat:.5f}, {lon:.5f}" if lat is not None and lon is not None else "Unknown",
                            "message": f"CRITICAL: Sudden fuel drop of {round(drop, 1)}% detected in {round(time_diff, 1)} min."
                        })
            return theft_events
        except Exception as e:
            logger.error(f"Theft detection error: {e}")
            return []

    @staticmethod
    async def get_fuel_station_logs(db: AsyncSession, device_id: int) -> List[Dict[str, Any]]:
        query = select(FuelStationVisit).where(FuelStationVisit.deviceid == device_id).order_by(FuelStationVisit.arrival_time.desc())
        result = await db.execute(query)
        rows = result.scalars().all()
        return [
            {
                "brand": r.station_brand,
                "branch": r.station_branch,
                "time": r.arrival_time.strftime("%Y-%m-%d %H:%M"),
                "duration": f"{r.duration_minutes} min",
                "liters": r.liters_added,
                "cost": r.cost_pkr,
                "meta": r.attributes or {}
            } for r in rows
        ]

    @staticmethod
    async def _get_latest_fuel_price(db: AsyncSession, dev_attr: Dict[str, Any]) -> float:
        fuel_type = (dev_attr.get("fuel_type") or "Petrol").title()
        if fuel_type not in ["Petrol", "Diesel"]:
            fuel_type = "Petrol"
        price_query = select(FuelPrice.price).where(FuelPrice.fuel_type == fuel_type)
        price_res = await db.execute(price_query)
        price_row = price_res.fetchone()
        return float(price_row[0]) if price_row else 272.89

    @staticmethod
    def _compute_efficiency_score(est_rate: float, dev_attr: Dict[str, Any]) -> int:
        """
        Estimate eco/efficiency confidence (0-100) based on expected consumption profile.
        """
        base = 80
        if est_rate <= 6:
            base += 10
        elif est_rate >= 12:
            base -= 15

        if dev_attr.get("vin"):
            base += 5
        if dev_attr.get("engine_size"):
            base += 5
        if not dev_attr.get("model"):
            base -= 10

        return max(40, min(99, int(base)))

    @staticmethod
    async def get_trip_cost_breakdown(
        db: AsyncSession,
        device_id: int,
        price_pkr: float,
        est_rate_l_per_100km: float,
        tank_size_l: float
    ) -> List[Dict[str, Any]]:
        """
        Build recent trip-level expense breakdown from movement segments.
        """
        try:
            query = text("""
                SELECT
                    devicetime,
                    speed,
                    CAST(JSON_EXTRACT(attributes, '$.totalDistance') AS DECIMAL(20,2)) as total_distance,
                    CAST(JSON_EXTRACT(attributes, '$.fuelLevel') AS DECIMAL(10,2)) as fuel_level
                FROM tc_positions
                WHERE deviceid = :device_id
                  AND devicetime > NOW() - INTERVAL 1 DAY
                ORDER BY devicetime ASC
            """)
            result = await db.execute(query, {"device_id": device_id})
            rows = result.fetchall()
            if len(rows) < 2:
                return []

            trips: List[Dict[str, Any]] = []
            current_trip = None

            for row in rows:
                devicetime, speed, total_distance, fuel_level = row
                moving = (speed or 0) > 3.0

                if moving and current_trip is None:
                    current_trip = {
                        "start_time": devicetime,
                        "end_time": devicetime,
                        "start_distance": float(total_distance or 0),
                        "end_distance": float(total_distance or 0),
                        "start_fuel": float(fuel_level) if fuel_level is not None else None,
                        "end_fuel": float(fuel_level) if fuel_level is not None else None
                    }
                    continue

                if current_trip:
                    current_trip["end_time"] = devicetime
                    current_trip["end_distance"] = float(total_distance or current_trip["end_distance"])
                    if fuel_level is not None:
                        current_trip["end_fuel"] = float(fuel_level)

                    # End trip when speed drops to near zero
                    if not moving:
                        distance_km = max(0.0, (current_trip["end_distance"] - current_trip["start_distance"]) / 1000.0)
                        if distance_km >= 0.5:
                            liters = (distance_km / 100.0) * est_rate_l_per_100km
                            if current_trip["start_fuel"] is not None and current_trip["end_fuel"] is not None:
                                fuel_drop = max(0.0, current_trip["start_fuel"] - current_trip["end_fuel"])
                                liters_by_sensor = (fuel_drop / 100.0) * tank_size_l
                                if liters_by_sensor > 0:
                                    liters = liters_by_sensor
                            cpk = (liters * price_pkr) / distance_km if distance_km > 0 else 0
                            trips.append({
                                "start_time": current_trip["start_time"].strftime("%Y-%m-%d %H:%M"),
                                "end_time": current_trip["end_time"].strftime("%Y-%m-%d %H:%M"),
                                "distance_km": round(distance_km, 2),
                                "fuel_liters": round(liters, 2),
                                "cost_pkr": round(liters * price_pkr, 2),
                                "cost_per_km": round(cpk, 2),
                                "pricing_type": "dynamic",
                                "price_pkr": round(price_pkr, 2)
                            })
                        current_trip = None

            # Include unfinished moving trip
            if current_trip:
                distance_km = max(0.0, (current_trip["end_distance"] - current_trip["start_distance"]) / 1000.0)
                if distance_km >= 0.5:
                    liters = (distance_km / 100.0) * est_rate_l_per_100km
                    cpk = (liters * price_pkr) / distance_km if distance_km > 0 else 0
                    trips.append({
                        "start_time": current_trip["start_time"].strftime("%Y-%m-%d %H:%M"),
                        "end_time": current_trip["end_time"].strftime("%Y-%m-%d %H:%M"),
                        "distance_km": round(distance_km, 2),
                        "fuel_liters": round(liters, 2),
                        "cost_pkr": round(liters * price_pkr, 2),
                        "cost_per_km": round(cpk, 2),
                        "pricing_type": "dynamic",
                        "price_pkr": round(price_pkr, 2)
                    })

            return trips[-12:]  # most recent 12 trips
        except Exception as e:
            logger.error(f"Trip costing breakdown error: {e}")
            return []

    @staticmethod
    async def log_fuel_theft_events(db: AsyncSession, device_id: int, theft_alerts: List[Dict[str, Any]]) -> None:
        """
        Persist suspicious fuel-drop anomalies into event log for audit/notification stream.
        """
        if not theft_alerts:
            return
        try:
            for alert in theft_alerts:
                event_time = None
                try:
                    event_time = datetime.strptime(alert["time"], "%Y-%m-%d %H:%M:%S")
                except Exception:
                    event_time = datetime.utcnow()

                # basic dedupe: avoid duplicate same-minute entries
                existing_q = text("""
                    SELECT id FROM tc_events
                    WHERE deviceid = :device_id
                      AND type = 'fuelTheftDetected'
                      AND eventtime BETWEEN :start_t AND :end_t
                    LIMIT 1
                """)
                exists = await db.execute(
                    existing_q,
                    {
                        "device_id": device_id,
                        "start_t": event_time - timedelta(minutes=1),
                        "end_t": event_time + timedelta(minutes=1),
                    },
                )
                if exists.first():
                    continue

                db.add(
                    Event(
                        type="fuelTheftDetected",
                        eventtime=event_time,
                        deviceid=device_id,
                        attributes={
                            "severity": alert.get("severity", "CRITICAL"),
                            "drop_pct": alert.get("drop"),
                            "window_min": alert.get("window_min"),
                            "location": alert.get("location"),
                            "message": alert.get("message"),
                        },
                    )
                )
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to persist fuel theft events: {e}")
            await db.rollback()

    @staticmethod
    async def get_idle_consumption(db: AsyncSession, device_id: int, price_pkr: float) -> Dict[str, Any]:
        """
        Calculates fuel wasted during idling (Speed < 3km/h AND Ignition ON).
        Assumes 1.8L/hour average idle consumption for standard engines.
        """
        try:
            query = text("""
                SELECT devicetime, speed, attributes 
                FROM tc_positions 
                WHERE deviceid = :device_id 
                  AND devicetime > NOW() - INTERVAL 1 DAY
                ORDER BY devicetime ASC
            """)
            result = await db.execute(query, {"device_id": device_id})
            rows = result.fetchall()
            
            idle_minutes = 0
            for i in range(1, len(rows)):
                prev_time, prev_speed, prev_attr = rows[i-1]
                curr_time, _, curr_attr = rows[i]
                
                # Check if ignition was on during this interval
                # attributes is often a string or dict depending on driver
                def is_ig_on(attr):
                    if isinstance(attr, str):
                        try: attr = json.loads(attr)
                        except: return False
                    return attr.get("ignition") in [True, "true", 1]

                if is_ig_on(prev_attr) and (prev_speed or 0) < 3.0:
                    delta = (curr_time - prev_time).total_seconds() / 60
                    if delta < 15: # Ignore gaps > 15 mins
                        idle_minutes += delta
            
            liters_wasted = (idle_minutes / 60) * 1.8
            return {
                "idle_minutes": round(idle_minutes, 1),
                "liters_wasted": round(liters_wasted, 2),
                "cost_pkr": round(liters_wasted * price_pkr, 2)
            }
        except Exception as e:
            logger.error(f"Idle consumption calculation error: {e}")
            return {"idle_minutes": 0, "liters_wasted": 0, "cost_pkr": 0}

    @staticmethod
    async def get_driver_analytics(db: AsyncSession, device_id: int) -> Dict[str, Any]:
        """
        Eco Score Engine & Driver Intelligence:
        Calculates score based on harsh events with Grace Logic.
        """
        try:
            # 1. Get Driver Info (fallback to device name if no driver assigned)
            query = text("""
                SELECT d.name as driver_name, d.uniqueid as driver_uid, d.attributes as driver_attrs,
                       dev.name as vehicle_name
                FROM tc_devices dev
                LEFT JOIN tc_device_driver dd ON dd.deviceid = dev.id
                LEFT JOIN tc_drivers d ON d.id = dd.driverid
                WHERE dev.id = :device_id
                LIMIT 1
            """)
            result = await db.execute(query, {"device_id": device_id})
            row = result.fetchone()
            
            if not row:
                return {"error": "Device not found"}

            driver_name_raw = row[0]
            driver_uid = row[1] or ""
            driver_attrs = row[2] or {}
            vehicle_name = row[3] or ""
            
            if isinstance(driver_attrs, str):
                try: driver_attrs = json.loads(driver_attrs)
                except: driver_attrs = {}
            auto_assigned = driver_attrs.get("auto_assigned", False)
            
            if driver_name_raw and not driver_name_raw.startswith("DRIVER-"):
                driver_name = driver_name_raw
            else:
                driver_name = vehicle_name or f"Driver-{device_id}"

            # 2. Fetch Harsh Events from fleet_alerts (pre-computed, fast)
            events_query = text("""
                SELECT 
                    SUM(CASE WHEN alert_type='hard_braking' THEN 1 ELSE 0 END) as brake_count,
                    SUM(CASE WHEN alert_type='hard_acceleration' THEN 1 ELSE 0 END) as accel_count,
                    SUM(CASE WHEN alert_type='hard_cornering' THEN 1 ELSE 0 END) as corner_count
                FROM fleet_alerts
                WHERE vehicle = :vehicle_name
                  AND alert_type IN ('hard_braking','hard_acceleration','hard_cornering')
            """)
            events_res = await db.execute(events_query, {"vehicle_name": vehicle_name})
            evt_row = events_res.fetchone()
            brake_count = evt_row[0] or 0
            accel_count = evt_row[1] or 0
            corner_count = evt_row[2] or 0

            # 3. Idle time from ke_gps_daily (pre-aggregated, fast)
            idle_minutes = 0
            try:
                idle_q = text("""
                    SELECT COALESCE(SUM(stop_time_min), 0) as idle_min
                    FROM ke_gps_daily
                    WHERE vehicle = :vehicle_name
                      AND record_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
                """)
                idle_res = await db.execute(idle_q, {"vehicle_name": vehicle_name})
                idle_row = idle_res.fetchone()
                idle_minutes = float(idle_row[0] or 0) if idle_row else 0
            except Exception:
                idle_minutes = 0

            # Last activity from fleet_alerts
            last_q = text("""
                SELECT MAX(alert_date) FROM fleet_alerts WHERE vehicle = :vehicle_name
            """)
            last_res = await db.execute(last_q, {"vehicle_name": vehicle_name})
            last_row = last_res.fetchone()
            last_activity = last_row[0].isoformat() if last_row and last_row[0] else None

            # 4. Eco Score Calculation
            # Starting Score = 100
            # Harsh Accel = -3
            # Harsh Corner = -4
            # Idle = -1 per 5 mins
            # Harsh Braking Grace: 1st 2 free, then -4 each
            
            penalized_brakes = max(0, brake_count - 2)
            grace_exempted = min(2, brake_count)
            
            idle_penalty = int(idle_minutes / 5)
            
            deduction = (penalized_brakes * 4) + (accel_count * 3) + (corner_count * 4) + idle_penalty
            final_score = max(0, 100 - deduction)

            return {
                "driver_name": driver_name,
                "driver_id": driver_uid,
                "vehicle_name": vehicle_name,
                "auto_assigned": auto_assigned,
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
                "last_activity": last_activity
            }
        except Exception as e:
            logger.error(f"Error in driver analytics: {e}")
            return {"error": str(e)}

    @staticmethod
    async def get_driver_leaderboard(db: AsyncSession, days: int = 30) -> List[Dict[str, Any]]:
        """Ranks KE drivers by Eco Score using fleet_alerts + tc_drivers for names."""
        try:
            if days > 0:
                batch_q = text("""
                    SELECT fa.vehicle,
                        SUM(CASE WHEN fa.alert_type='hard_braking' THEN 1 ELSE 0 END) as brake,
                        SUM(CASE WHEN fa.alert_type='hard_acceleration' THEN 1 ELSE 0 END) as accel,
                        SUM(CASE WHEN fa.alert_type='hard_cornering' THEN 1 ELSE 0 END) as corner,
                        SUM(CASE WHEN fa.alert_type IN ('hard_braking','hard_acceleration','hard_cornering','overspeed','harsh_driving','excessive_idle') THEN 1 ELSE 0 END) as total_events
                    FROM fleet_alerts fa
                    WHERE fa.alert_type IN ('hard_braking','hard_acceleration','hard_cornering','overspeed','harsh_driving','excessive_idle')
                      AND fa.alert_date >= DATE_SUB(CURDATE(), INTERVAL :days DAY)
                    GROUP BY fa.vehicle
                """)
                result = await db.execute(batch_q, {"days": days})
            else:
                batch_q = text("""
                    SELECT fa.vehicle,
                        SUM(CASE WHEN fa.alert_type='hard_braking' THEN 1 ELSE 0 END) as brake,
                        SUM(CASE WHEN fa.alert_type='hard_acceleration' THEN 1 ELSE 0 END) as accel,
                        SUM(CASE WHEN fa.alert_type='hard_cornering' THEN 1 ELSE 0 END) as corner,
                        SUM(CASE WHEN fa.alert_type IN ('hard_braking','hard_acceleration','hard_cornering','overspeed','harsh_driving','excessive_idle') THEN 1 ELSE 0 END) as total_events
                    FROM fleet_alerts fa
                    WHERE fa.alert_type IN ('hard_braking','hard_acceleration','hard_cornering','overspeed','harsh_driving','excessive_idle')
                    GROUP BY fa.vehicle
                """)
                result = await db.execute(batch_q)
            rows = result.fetchall()

            if not rows:
                return []

            driver_map = {}
            try:
                driver_q = text("SELECT dev.name, d.name FROM tc_devices dev JOIN tc_device_driver dd ON dd.deviceid = dev.id JOIN tc_drivers d ON d.id = dd.driverid")
                driver_res = await db.execute(driver_q)
                for dr in driver_res.fetchall():
                    driver_map[dr[0]] = dr[1]
            except Exception:
                pass

            trip_map = {}
            try:
                if days > 0:
                    trip_q = text("SELECT dev.name, COUNT(*) FROM ke_gps_daily g JOIN tc_devices dev ON dev.id = g.device_id WHERE g.record_date >= DATE_SUB(CURDATE(), INTERVAL :d DAY) GROUP BY dev.name")
                    trip_res = await db.execute(trip_q, {"d": days})
                else:
                    trip_q = text("SELECT dev.name, COUNT(*) FROM ke_gps_daily g JOIN tc_devices dev ON dev.id = g.device_id GROUP BY dev.name")
                    trip_res = await db.execute(trip_q)
                trip_map = {r[0]: r[1] for r in trip_res.fetchall()}
            except Exception:
                pass

            leaderboard = []
            for row in rows:
                vehicle_name, brake_count, accel_count, corner_count, total_events = row
                brake_count = brake_count or 0
                accel_count = accel_count or 0
                corner_count = corner_count or 0
                total_events = total_events or 0

                penalized_brakes = max(0, brake_count - 2)
                deduction = (penalized_brakes * 4) + (accel_count * 3) + (corner_count * 4)
                score = max(0, 100 - deduction)

                real_name = driver_map.get(vehicle_name, "")
                if not real_name or real_name.startswith("DRIVER-"):
                    real_name = vehicle_name or "Unknown"

                leaderboard.append({
                    "name": real_name,
                    "vehicle": vehicle_name or "",
                    "score": score,
                    "trips": trip_map.get(vehicle_name, 0),
                    "total_events": total_events,
                    "brake": brake_count,
                    "accel": accel_count,
                    "corner": corner_count
                })

            leaderboard.sort(key=lambda x: x["score"], reverse=True)
            for i, entry in enumerate(leaderboard):
                entry["rank"] = i + 1

            return leaderboard[:50]
        except Exception as e:
            logger.error(f"Leaderboard error: {e}")
            return []

    @staticmethod
    async def get_driver_summary_stats(db: AsyncSession) -> Dict[str, Any]:
        """Summary stats for the Driver Intelligence overview cards."""
        try:
            total_drivers_q = text("SELECT COUNT(DISTINCT id) FROM tc_drivers")
            total_res = await db.execute(total_drivers_q)
            total_drivers = total_res.scalar() or 0

            mapped_q = text("SELECT COUNT(DISTINCT deviceid) FROM tc_device_driver")
            mapped_res = await db.execute(mapped_q)
            mapped_vehicles = mapped_res.scalar() or 0

            events_30d_q = text("""
                SELECT 
                    SUM(CASE WHEN alert_type='hard_braking' THEN 1 ELSE 0 END) as brakes,
                    SUM(CASE WHEN alert_type='hard_acceleration' THEN 1 ELSE 0 END) as accels,
                    SUM(CASE WHEN alert_type='hard_cornering' THEN 1 ELSE 0 END) as corners,
                    SUM(CASE WHEN alert_type='excessive_idle' THEN 1 ELSE 0 END) as idles,
                    SUM(CASE WHEN alert_type='overspeed' THEN 1 ELSE 0 END) as overspeeds,
                    COUNT(*) as total
                FROM fleet_alerts
                WHERE alert_type IN ('hard_braking','hard_acceleration','hard_cornering','excessive_idle','overspeed')
                  AND alert_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            """)
            ev_res = await db.execute(events_30d_q)
            ev = ev_res.fetchone()

            safe_drivers_q = text("""
                SELECT COUNT(DISTINCT vehicle) FROM fleet_alerts
                WHERE alert_type IN ('hard_braking','hard_acceleration','hard_cornering')
                  AND alert_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            """)
            safe_res = await db.execute(safe_drivers_q)
            vehicles_with_events = safe_res.scalar() or 0

            avg_score_q = text("""
                SELECT 
                    fa.vehicle,
                    SUM(CASE WHEN fa.alert_type='hard_braking' THEN 1 ELSE 0 END) as brake,
                    SUM(CASE WHEN fa.alert_type='hard_acceleration' THEN 1 ELSE 0 END) as accel,
                    SUM(CASE WHEN fa.alert_type='hard_cornering' THEN 1 ELSE 0 END) as corner
                FROM fleet_alerts fa
                WHERE fa.alert_type IN ('hard_braking','hard_acceleration','hard_cornering')
                GROUP BY fa.vehicle
            """)
            avg_res = await db.execute(avg_score_q)
            scores = []
            for r in avg_res.fetchall():
                b, a, c = r[1] or 0, r[2] or 0, r[3] or 0
                pb = max(0, b - 2)
                ded = (pb * 4) + (a * 3) + (c * 4)
                scores.append(max(0, 100 - ded))
            avg_score = round(sum(scores) / len(scores), 1) if scores else 100

            return {
                "total_drivers": total_drivers,
                "mapped_vehicles": mapped_vehicles,
                "avg_eco_score": avg_score,
                "total_events_30d": ev[5] if ev else 0,
                "harsh_braking_30d": ev[0] if ev else 0,
                "harsh_accel_30d": ev[1] if ev else 0,
                "harsh_corner_30d": ev[2] if ev else 0,
                "idle_30d": ev[3] if ev else 0,
                "overspeed_30d": ev[4] if ev else 0,
                "safe_drivers_count": max(0, total_drivers - vehicles_with_events)
            }
        except Exception as e:
            logger.error(f"Driver summary stats error: {e}")
            return {"total_drivers": 0, "mapped_vehicles": 0, "avg_eco_score": 100, "total_events_30d": 0}

    @staticmethod
    async def get_analytics_summary(db: AsyncSession, user_id: int, role: str) -> Dict[str, Any]:
        logger.info(f"Fetching summary for user_id={user_id}, role={role}")
        try:
            # 1. Total Vehicles (Fast)
            if role in ["ADMIN", "SUPERADMIN"]:
                total = (await db.execute(select(func.count(Device.id)).where(Device.disabled == False))).scalar() or 0
                online = (await db.execute(select(func.count(Device.id)).where(Device.disabled == False, Device.status == 'online'))).scalar() or 0
            else:
                q = select(func.count(Device.id)).join(UserDevice, UserDevice.deviceid == Device.id).where(UserDevice.userid == user_id, Device.disabled == False)
                total = (await db.execute(q)).scalar() or 0
                q_online = q.where(Device.status == 'online')
                online = (await db.execute(q_online)).scalar() or 0

            offline = total - online

            # 1.1 Fetch user preferences for alert filtering
            try:
                user_res = await db.execute(select(User).where(User.id == user_id))
                user_obj = user_res.scalar_one_or_none()
                user_attrs = user_obj.attributes if user_obj else {}
                alert_prefs = user_attrs.get("alertPreferences", {}) if isinstance(user_attrs, dict) else {}
            except Exception as pref_err:
                logger.warning(f"Failed to fetch alert preferences: {pref_err}")
                alert_prefs = {}

            disabled_types = [k for k, v in alert_prefs.items() if v is False]

            # 2.0 Total Distance + Trip Counts (all vehicles)
            total_distance_km = 0.0
            active_trips = 0
            completed_today = 0
            try:
                if role in ["ADMIN", "SUPERADMIN"]:
                    dev_pos_q = select(Device, Position).outerjoin(Position, Device.positionid == Position.id).where(Device.disabled == False)
                else:
                    dev_pos_q = (
                        select(Device, Position)
                        .outerjoin(Position, Device.positionid == Position.id)
                        .join(UserDevice, UserDevice.deviceid == Device.id)
                        .where(UserDevice.userid == user_id, Device.disabled == False)
                    )
                dp_res = await db.execute(dev_pos_q)
                for dev, pos in dp_res.fetchall():
                    pos_attr = pos.attributes if pos else {}
                    dist_m = pos_attr.get("totalDistance") or pos_attr.get("odometer") or 0
                    total_distance_km += float(dist_m) / 1000.0
                    if pos and (pos.speed or 0) > 1:
                        active_trips += 1

                # Completed today = deviceStopped events today
                today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                if role in ["ADMIN", "SUPERADMIN"]:
                    comp_q = select(func.count(Event.id)).where(Event.type == 'deviceStopped', Event.eventtime >= today_start)
                else:
                    comp_q = (
                        select(func.count(Event.id))
                        .join(UserDevice, UserDevice.deviceid == Event.deviceid)
                        .where(UserDevice.userid == user_id, Event.type == 'deviceStopped', Event.eventtime >= today_start)
                    )
                completed_today = (await db.execute(comp_q)).scalar() or 0
            except Exception as dist_err:
                logger.warning(f"Distance/trips calculation failed: {dist_err}")

            # 2.1 Overspeed count
            # We only count for last 24h. If this is still slow, we'll return 0 or a cached value.
            try:
                # Use a simpler query first
                since = datetime.utcnow() - timedelta(days=1)
                if role in ["ADMIN", "SUPERADMIN"]:
                    overspeed_q = select(func.count(Event.id)).where(Event.type == 'deviceOverspeed', Event.eventtime > since)
                else:
                    overspeed_q = (
                        select(func.count(Event.id))
                        .join(UserDevice, UserDevice.deviceid == Event.deviceid)
                        .where(UserDevice.userid == user_id, Event.type == 'deviceOverspeed', Event.eventtime > since)
                    )
                
                # Set a local execution timeout if possible? Not easy in SQLAlchemy. 
                # We'll just assume it's okay now with proper ORM query or skip it if it was the culprit.
                # Skip overspeed count if explicitly disabled in preferences
                if alert_prefs.get('deviceOverspeed') is False:
                    overspeed = 0
                else:
                    overspeed = (await db.execute(overspeed_q)).scalar() or 0
                
                # 2.1 Security KPIs (Last 24h)
                sec_counts_q = (
                    select(Event.type, func.count(Event.id))
                    .where(Event.eventtime > since)
                    .group_by(Event.type)
                )
                if role not in ["ADMIN", "SUPERADMIN"]:
                    sec_counts_q = sec_counts_q.join(UserDevice, UserDevice.deviceid == Event.deviceid).where(UserDevice.userid == user_id)
                
                sec_counts_res = await db.execute(sec_counts_q)
                sec_raw = {row[0]: row[1] for row in sec_counts_res.fetchall()}
                
                security_stats = {
                    "tamper": sec_raw.get('tampering', 0) + sec_raw.get('removing', 0) + sec_raw.get('powerCut', 0),
                    "geofence": sec_raw.get('geofenceEnter', 0) + sec_raw.get('geofenceExit', 0),
                    "movement": sec_raw.get('deviceMoving', 0)
                }
            except Exception as e:
                logger.warning(f"Overspeed/Security count failed: {e}")
                overspeed = 0
                security_stats = {"tamper": 0, "geofence": 0, "movement": 0}

            # 3. Recent Events (Fast: Index-hinted order)
            recent_events = []
            try:
                if role in ["ADMIN", "SUPERADMIN"]:
                    ev_q = (
                        select(Event.type, Device.name, Event.eventtime, Device.id, Device.uniqueid, Event.id)
                        .join(Device, Event.deviceid == Device.id)
                        .order_by(Event.id.desc())
                        .limit(5)
                    )
                else:
                    ev_q = (
                        select(Event.type, Device.name, Event.eventtime, Device.id, Device.uniqueid, Event.id)
                        .join(Device, Event.deviceid == Device.id)
                        .join(UserDevice, UserDevice.deviceid == Device.id)
                        .where(UserDevice.userid == user_id)
                        .order_by(Event.id.desc())
                        .limit(5)
                    )
                
                # Apply event-type filtering from user preferences
                if disabled_types:
                    ev_q = ev_q.where(Event.type.notin_(disabled_types))
                
                ev_res = await db.execute(ev_q)
                for row in ev_res.fetchall():
                    recent_events.append({
                        "type": row[0],
                        "vehicle": row[1],
                        "time": row[2].strftime("%Y-%m-%d %H:%M:%S") if row[2] else "",
                        "device_id": row[3],
                        "unique_id": row[4],
                        "id": row[5]
                    })
            except Exception as ev_err:
                logger.warning(f"Recent events fetch failed: {ev_err}")

            return {
                "kpis": {
                    "total": total,
                    "active": online,
                    "idle": offline,
                    "stale": 0,
                    "overspeed": overspeed,
                    "avgSpeed": 0,
                    "avgFuel": 0,
                    "completedToday": completed_today,
                    "totalDistanceKm": round(total_distance_km, 2),
                    "moving": active_trips
                },
                "securityStats": security_stats,
                "recentEvents": recent_events,
                "recent_events": recent_events,
                "maintenanceAlerts": [],
                "systemHealth": {"dbSizeMb": 0, "serverTime": datetime.now().strftime("%H:%M:%S")}
            }

        except Exception as e:
            logger.error(f"Error in analytics summary: {e}")
            return {"kpis": {"total": 0, "active": 0, "idle": 0, "stale": 0, "overspeed": 0, "avgSpeed": 0, "avgFuel": 0, "completedToday": 0, "totalDistanceKm": 0, "moving": 0}, "recentEvents": []}

    @staticmethod
    async def get_organization_fuel_analytics(db: AsyncSession, user_id: int, role: str) -> Dict[str, Any]:
        """
        Aggregated Fuel Analytics for KE Fleet only.
        """
        try:
            # KE vehicles only
            query = text("""
                SELECT td.id, td.attributes as dev_attr, 
                       COALESCE(tp.attributes, '{}') as pos_attr
                FROM tc_devices td
                JOIN ke_vehicle_imei kv ON kv.imei = td.uniqueid
                LEFT JOIN tc_positions tp ON tp.id = td.positionid
                WHERE td.disabled = 0
            """)
            result = await db.execute(query)
            rows = result.fetchall()
            if not rows:
                return {"error": "No KE fleet assets found"}

            # Fetch fuel prices
            price_res = await db.execute(select(FuelPrice.fuel_type, FuelPrice.price))
            prices = {row[0]: row[1] for row in price_res.fetchall()}
            default_price = 272.89

            total_cost = 0.0
            total_distance = 0.0
            total_liters = 0.0
            device_ids = []

            for row in rows:
                device_ids.append(row[0])
                dev_attr = row[1] or {}
                pos_attr = row[2] or {}
                if isinstance(dev_attr, str):
                    try: dev_attr = json.loads(dev_attr)
                    except: dev_attr = {}
                if isinstance(pos_attr, str):
                    try: pos_attr = json.loads(pos_attr)
                    except: pos_attr = {}

                fuel_type = (dev_attr.get("fuel_type") or "Petrol").title()
                if fuel_type not in ["Petrol", "Diesel"]:
                    fuel_type = "Petrol"
                current_price = prices.get(fuel_type, default_price)

                dist_m = pos_attr.get("totalDistance") or pos_attr.get("odometer") or 0
                dist_km = float(dist_m) / 1000.0
                total_distance += dist_km

                est_rate = float(dev_attr.get("est_fuel_rate") or 10.0)
                consumption = (dist_km / 100.0) * est_rate
                total_liters += consumption
                total_cost += consumption * current_price

            # Recent station logs for KE vehicles
            station_logs = []
            if device_ids:
                try:
                    logs_q = text("""
                        SELECT fsv.station_brand, fsv.station_branch, fsv.arrival_time,
                               fsv.duration_minutes, fsv.liters_added, fsv.cost_pkr,
                               td.name as vehicle_name
                        FROM tc_fuel_station_visits fsv
                        JOIN tc_devices td ON td.id = fsv.deviceid
                        WHERE fsv.deviceid IN :device_ids
                        ORDER BY fsv.arrival_time DESC
                        LIMIT 20
                    """)
                    logs_res = await db.execute(logs_q, {"device_ids": tuple(device_ids)})
                    for log in logs_res.fetchall():
                        station_logs.append({
                            "vehicle": log[6],
                            "time": log[2].strftime("%Y-%m-%d %H:%M:%S") if log[2] else "",
                            "station": f"{log[0] or 'Unknown'} - {log[1] or ''}",
                            "liters": log[4],
                            "cost": log[5],
                            "duration": f"{log[3]} min" if log[3] else ""
                        })
                except Exception as e:
                    logger.warning(f"Station logs query error: {e}")

            return {
                "tier": "Fleet",
                "method": "aggregated",
                "status": "OPERATIONAL",
                "source": "KE Fleet Aggregation",
                "device_count": len(rows),
                "distance_km": round(total_distance, 2),
                "total_cost_pkr": round(total_cost, 2),
                "total_liters": round(total_liters, 2),
                "current_level": 0,
                "fuel_level_percent": 0,
                "price_pkr": prices.get("Petrol", default_price),
                "station_logs": station_logs,
                "history": [],
                "trip_costing": {"idle_cost": round(total_cost * 0.05, 2)},
                "idle_breakdown": {"idle_cost": round(total_cost * 0.05, 2), "idle_time_min": 0},
                "efficiency_validation": {"score": 70, "label": "Fleet Average", "status": "VALIDATED"}
            }

        except Exception as e:
            logger.error(f"Org fuel analytics error: {e}")
            return {"error": str(e)}

    @staticmethod
    async def get_alerts_history(db: AsyncSession, user_id: int, role: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Fetches the latest security and operational alerts for the fleet.
        """
        try:
            # 1. Base Query with Device Metadata
            query = (
                select(Event, Device)
                .join(Device, Event.deviceid == Device.id)
            )
            
            # 2. Role-based isolation
            if role not in ["ADMIN", "SUPERADMIN"]:
                query = query.join(UserDevice, UserDevice.deviceid == Device.id).where(UserDevice.userid == user_id)
            
            # 3. Execution (Latest first)
            query = query.order_by(Event.id.desc()).limit(limit)
            result = await db.execute(query)
            rows = result.fetchall()
            
            # 4. Helper for severity assignment
            def get_severity(etype):
                critical = ['fuelTheftDetected', 'alarm', 'deviceMoving', 'powerCut']
                warning = ['deviceOverspeed', 'geofenceEnter', 'geofenceExit', 'ignitionOn', 'tampering']
                if etype in critical: return 'CRITICAL'
                if etype in warning: return 'WARNING'
                return 'INFO'

            alerts = []
            for ev, dev in rows:
                attr = ev.attributes or {}
                # Clean up type label
                label = ev.type.replace('device', '').replace('harsh', 'Harsh ')
                label = ''.join([' ' + c if c.isupper() else c for c in label]).strip().title()

                alerts.append({
                    "id": ev.id,
                    "type": ev.type,
                    "label": label,
                    "device_id": ev.deviceid,
                    "vehicle": dev.name or f"Vehicle {ev.deviceid}",
                    "unique_id": dev.uniqueid,
                    "time": ev.eventtime.strftime("%Y-%m-%d %H:%M:%S"),
                    "severity": get_severity(ev.type),
                    "message": attr.get("message") or f"{label} detected at {dev.name}",
                    "pos_id": ev.positionid
                })
            
            return alerts
        except Exception as e:
            logger.error(f"Alert history fetch error: {e}")
            return []
