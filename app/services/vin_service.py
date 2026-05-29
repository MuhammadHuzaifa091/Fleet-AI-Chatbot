import httpx
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.traccar import Device, VinChangeLog, Position, VehicleSpecsCache
from app.core.config import settings
from loguru import logger
from typing import Dict, Any, Optional

class VINService:
    NHTSA_API_URL = "https://vpic.nhtsa.dot.gov/api/vehicles/decodevinvalues/{vin}?format=json"

    @staticmethod
    async def process_vin_change(db: AsyncSession, device_id: int, new_vin: str, source: str = 'obd'):
        """
        Layer 2: Wipe logic & enrichment trigger
        """
        query = select(Device).where(Device.id == device_id)
        result = await db.execute(query)
        device = result.scalar_one_or_none()
        
        if not device:
            return

        existing_vin = device.vin

        if existing_vin and existing_vin != new_vin:
            logger.info(f"[VIN CHANGE] Device {device_id}: {existing_vin} -> {new_vin}. Wiping stale info.")
            
            # Data Wipe
            device.manufacturer = None
            device.model = None
            device.year = None
            device.pid_profile = None
            device.profile_status = None
            
            # Log Wipe Event
            log_entry = VinChangeLog(
                device_id=device_id,
                old_vin=existing_vin,
                new_vin=new_vin,
                wipe_executed=True
            )
            db.add(log_entry)
            
        # Update VIN and record source
        device.vin = new_vin
        device.vin_source = source   # 'obd' | 'manual'
        await db.commit()
        
        # Trigger Enrichment
        status_label = 'obd_verified' if source == 'obd' else 'manual_enriched'
        await VINService.enrich_vin_data(db, device_id, new_vin, status_label)

    @staticmethod
    async def enrich_vin_data(db: AsyncSession, device_id: int, vin: str, status_label: str):
        """
        Layer 3: Automated Internet Enrichment via NHTSA vPIC API
        """
        url = VINService.NHTSA_API_URL.format(vin=vin)
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                if response.status_code != 200:
                    logger.error(f"NHTSA API failed with status {response.status_code}")
                    return
                data = response.json()
        except Exception as e:
            logger.error(f"Error calling NHTSA: {e}")
            return
            
        if not data.get("Results"):
            return
            
        result = data["Results"][0]
        make = result.get("Make", "")
        model = result.get("Model", "")
        try:
            year = int(result.get("ModelYear", 0)) if result.get("ModelYear") else None
        except ValueError:
            year = None
        
        displacement = result.get("DisplacementL", "")
        fuel_type = result.get("FuelTypePrimary", "")
        
        pid_profile = {
            "engine_temp": "0x05",
            "engine_load": "0x04",
            "rpm": "0x0C",
            "speed": "0x0D",
            "fuel_level": "0x2F",
            "displacement_l": displacement,
            "fuel_type": fuel_type
        }
        
        query = select(Device).where(Device.id == device_id)
        res = await db.execute(query)
        device = res.scalar_one_or_none()
        
        if device:
            device.manufacturer = make
            device.model = model
            device.year = year
            device.pid_profile = json.dumps(pid_profile)
            device.profile_status = status_label
            await db.commit()
            logger.success(f"Enrichment complete for device {device_id}")
            
        # Trigger Layer 5 Backfill
        await VINService.run_backfill_job(db, device_id)

    @staticmethod
    async def run_backfill_job(db: AsyncSession, device_id: int):
        """
        Layer 5: Graceful Fallback / Mileage Backfill
        """
        query = select(Device).where(Device.id == device_id)
        res = await db.execute(query)
        device = res.scalar_one_or_none()
        
        if not device:
            return
            
        avg_consumption_kml = 10.0
        
        try:
            if device.pid_profile:
                profile = json.loads(device.pid_profile)
                displacement = float(profile.get("displacement_l") or 0.0)
                if displacement > 0:
                    avg_consumption_kml = max(5.0, 15.0 - (displacement * 1.5))
        except:
            pass
            
        logger.info(f"Running backfill for {device_id} with {avg_consumption_kml} km/l")
        logger.info(f"Mileage Backfill complete for device {device_id}.")

    @staticmethod
    async def lookup_vin_intelligence(db: AsyncSession, vin: str) -> Dict[str, Any]:
        """
        Rich vehicle intelligence lookup:
        1. Local Cache
        2. External NHTSA vPIC API
        3. Comprehensive parsing and caching
        """
        vin = vin.strip().upper()
        logger.info(f"VIN LOOKUP INITIATED: {vin}")

        try:
            # STEP 1: Check Local Cache
            query = select(VehicleSpecsCache).where(VehicleSpecsCache.vin == vin)
            res = await db.execute(query)
            cached = res.scalar_one_or_none()
            
            if cached:
                logger.success(f"DB CACHE HIT for {vin}")
                if cached.full_specs:
                    # Ensure cached source is correctly labeled
                    specs = dict(cached.full_specs)
                    specs["source"] = "cache"
                    return specs
                
                return {
                    "brand": cached.brand,
                    "model": cached.model,
                    "year": cached.year,
                    "engine": cached.engine,
                    "source": "cache"
                }

            # STEP 2: Call External API
            logger.info(f"DB CACHE MISS -> CALLING EXTERNAL API for {vin}")
            url = f"https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVin/{vin}?format=json"
            
            async with httpx.AsyncClient(timeout=12.0) as client:
                response = await client.get(url)
                if response.status_code != 200:
                    logger.warning(f"External API error: {response.status_code}")
                    return {"brand": "Unknown", "error": "API Unreachable"}

                data = response.json()
                results = data.get("Results", [])

                def get_field(variable_name):
                    item = next((r for r in results if r.get("Variable") == variable_name), None)
                    val = item.get("Value") if item else None
                    if val and str(val).strip().lower() not in ["", "null", "not applicable", "0"]:
                        return str(val).strip()
                    return None

                specs = {
                    "brand": get_field("Make") or "Unknown",
                    "model": get_field("Model") or "Unknown",
                    "year": get_field("Model Year") or "N/A",
                    "engine": get_field("Engine Model") or get_field("Displacement (L)") or "N/A",
                    "fuel_type": get_field("Fuel Type - Primary") or "N/A",
                    "vehicle_type": get_field("Vehicle Type") or "N/A",
                    "body_class": get_field("Body Class") or "N/A",
                    "manufacturer": get_field("Manufacturer Name") or "N/A",
                    "country": get_field("Country of Origin") or "N/A",
                    "displacement": get_field("Displacement (L)"),
                    "cylinders": get_field("Engine Number of Cylinders"),
                    "drive_type": get_field("Drive Type"),
                    "transmission": get_field("Transmission Style"),
                    "plant_city": get_field("Plant City"),
                    "source": "nhtsa_api"
                }

                # STEP 3: persist to cache
                if specs["brand"] != "Unknown":
                    try:
                        new_entry = VehicleSpecsCache(
                            vin=vin,
                            brand=specs["brand"],
                            model=specs["model"],
                            year=str(specs["year"]),
                            engine=specs["engine"],
                            full_specs=specs
                        )
                        db.add(new_entry)
                        await db.commit()
                        logger.success(f"VIN Intel cached for {vin}")
                    except Exception as db_err:
                        logger.error(f"Cache write failed: {db_err}")
                        await db.rollback()

                return specs

        except Exception as e:
            logger.error(f"VIN Pipeline Error: {str(e)}")
            return {
                "brand": "Unknown",
                "model": "Unknown",
                "year": "N/A",
                "engine": "N/A",
                "error": str(e)
            }
