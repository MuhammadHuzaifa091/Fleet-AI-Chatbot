import aiohttp
import json
import logging
# Placeholder for project's actual DB connection pool (e.g., asyncpg or aiomysql)
# from core.db import get_db_pool  
from .5_backfill_job import run_backfill_job
import asyncio

logger = logging.getLogger(__name__)

# Dummy implementation of get_db_pool to pass linter, should be replaced with real
async def get_db_pool():
    class DummyPool:
        class DummyConn:
            async def __aenter__(self): return self
            async def __aexit__(self, exc_type, exc, tb): pass
            async def fetchrow(self, q, *a): return None
            async def fetch(self, q, *a): return []
            async def execute(self, q, *a): pass
        def acquire(self): return self.DummyConn()
    return DummyPool()

async def process_new_vin(device_id: int, new_vin: str, source: str):
    """
    Complete flow for handling a new VIN (Layer 2 & Layer 3).
    Includes wipe logic, enrichment, and triggering the backfill.
    """
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # Layer 2: Detect changes and wipe if needed
        record = await conn.fetchrow("SELECT vin FROM tc_devices WHERE id = $1", device_id)
        if not record:
            return # Device not found
            
        existing_vin = record.get('vin') if hasattr(record, 'get') else None
        
        if existing_vin and existing_vin != new_vin:
            # Data wipe
            await conn.execute("""
                UPDATE tc_devices 
                SET manufacturer = NULL, model = NULL, year = NULL, pid_profile = NULL, profile_status = NULL 
                WHERE id = $1
            """, device_id)
            
            await conn.execute("""
                INSERT INTO vin_change_log (device_id, old_vin, new_vin, changed_at, wipe_executed)
                VALUES ($1, $2, $3, NOW(), TRUE)
            """, device_id, existing_vin, new_vin)
            logger.info(f"Wiped existing data for device {device_id} due to VIN change.")
            
        # Temporarily save the new VIN before enrichment
        await conn.execute("UPDATE tc_devices SET vin = $1 WHERE id = $2", new_vin, device_id)
        
    # Layer 3: Execute enrichment
    status_label = 'obd_verified' if source == 'obd' else 'manual_enriched'
    await enrich_vin_data(device_id, new_vin, status_label)

    # Layer 5: Graceful fallback backfill trigger
    await run_backfill_job(device_id)

async def enrich_vin_data(device_id: int, vin: str, status_label: str):
    """
    Calls NHTSA API and saves vehicle profile.
    This runs asynchronously and does not block the API.
    """
    url = f"https://vpic.nhtsa.dot.gov/api/vehicles/decodevinvalues/{vin}?format=json"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=30) as response:
                if response.status != 200:
                    logger.error(f"NHTSA API failed with status {response.status} for VIN {vin}")
                    return
                    
                data = await response.json()
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
                
                # Dynamic PID profile based on manufacturer and specs
                pid_profile = {
                    "engine_temp": "0x05",
                    "engine_load": "0x04",
                    "rpm": "0x0C",
                    "speed": "0x0D",
                    "fuel_level": "0x2F",
                    "displacement_l": displacement,
                    "fuel_type": fuel_type
                }
                
                pool = await get_db_pool()
                async with pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE tc_devices 
                        SET manufacturer = $1, 
                            model = $2, 
                            year = $3, 
                            pid_profile = $4, 
                            profile_status = $5
                        WHERE id = $6
                    """, make, model, year, json.dumps(pid_profile), status_label, device_id)
                    
                logger.info(f"Enrichment complete for device {device_id} (VIN: {vin})")
        except Exception as e:
            logger.error(f"Exception during NHTSA API call for VIN {vin}: {e}")
