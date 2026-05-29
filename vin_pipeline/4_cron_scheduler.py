import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
# from core.db import get_db_pool
from .3_enrichment_service import enrich_vin_data

logger = logging.getLogger(__name__)

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

async def monthly_enrichment_task():
    """
    Cron job function that: 
    - Re-runs NHTSA API enrichment for every device every 30 days.
    - Catches any registry updates for the manufacturer.
    """
    logger.info("Starting automated monthly VIN enrichment refresh...")
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # Get all devices that have a VIN assigned
        devices = await conn.fetch("SELECT id, vin, profile_status FROM tc_devices WHERE vin IS NOT NULL")
        
    for device in devices:
        vin = device.get('vin') if hasattr(device, 'get') else device[1]
        device_id = device.get('id') if hasattr(device, 'get') else device[0]
        current_status = device.get('profile_status') if hasattr(device, 'get') else device[2]
        
        # Keep the existing status label unless it's missing
        status_label = current_status or 'system_enriched'
        
        # Run non-blocking async call and catch exceptions to prevent cascading failure
        try:
            await enrich_vin_data(device_id, vin, status_label)
        except Exception as e:
            logger.error(f"Failed to refresh manufacturer registry for device {device_id}: {str(e)}")
            
    logger.info("Monthly VIN enrichment refresh complete.")

def start_vin_cron_scheduler():
    """
    Spins up the APScheduler. Should be called during FastAPI startup events.
    """
    scheduler = AsyncIOScheduler()
    # Runs the job every 30 days
    scheduler.add_job(monthly_enrichment_task, 'interval', days=30)
    scheduler.start()
    logger.info("VIN Enrichment Cron scheduler started. Next run in 30 days.")

# Example usage in FastAPI main.py:
# @app.on_event("startup")
# async def startup_event():
#     start_vin_cron_scheduler()
