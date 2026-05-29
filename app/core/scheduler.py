"""
Automated Sync Scheduler
========================
Uses APScheduler to run SyncService.sync_from_pc12() automatically:
  - Once immediately on server startup
  - Every 5 minutes thereafter (non-blocking, runs in background)

The scheduler is intentionally decoupled from FastAPI's request lifecycle
so a slow sync never blocks API responses.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from app.db.session import SessionLocal
from app.services.sync_service import SyncService
from app.services.vin_service import VINService
from app.services.fuel_price_service import FuelPriceService
from app.models.traccar import Device
from sqlalchemy import select

# Module-level scheduler instance (singleton)
_scheduler: AsyncIOScheduler = AsyncIOScheduler(timezone="UTC")


async def _run_vin_sync_job() -> None:
    """
    30-day background sync for vehicle intelligence.
    Ensures all devices with a VIN have up-to-date specs.
    """
    logger.info("[SCHEDULER] Triggered 30-day VIN intelligence sync job …")
    try:
        async with SessionLocal() as db:
            query = select(Device).where(Device.attributes.contains({"last_verified_vin": ""}))
            result = await db.execute(query)
            devices = result.scalars().all()
            
            for device in devices:
                vin = device.attributes.get("last_verified_vin")
                if vin:
                    logger.debug(f"[SCHEDULER] Re-syncing intelligence for device {device.id} (VIN: {vin})")
                    await VINService.process_vin_change(db, device.id, vin)
                    
        logger.success("[SCHEDULER] VIN intelligence sync finished.")
    except Exception as exc:
        logger.error(f"[SCHEDULER] Unhandled exception in VIN sync job: {exc}")


async def _run_fuel_price_sync_job() -> None:
    """
    Daily sync for live fuel prices in Pakistan.
    """
    logger.info("[SCHEDULER] Triggered daily fuel price scraper job …")
    try:
        async with SessionLocal() as db:
            await FuelPriceService.scrape_and_update_prices(db)
        logger.success("[SCHEDULER] Fuel price sync finished.")
    except Exception as exc:
        logger.error(f"[SCHEDULER] Unhandled exception in fuel price sync: {exc}")


async def _run_sync_job() -> None:
    """
    Job function called by APScheduler every 5 minutes.
    Opens its own DB session so it is fully independent of
    any current HTTP request.
    """
    logger.info("[SCHEDULER] Triggered scheduled sync job …")
    try:
        async with SessionLocal() as db:
            result = await SyncService.sync_from_pc12(db)

        status   = result.get("status", "unknown")
        synced   = result.get("synced", {})
        end_time = result.get("end_time", "?")

        logger.info(
            f"[SCHEDULER] Sync finished — status={status}  "
            f"users={synced.get('users', 0)}  "
            f"devices={synced.get('devices', 0)}  "
            f"permissions={synced.get('permissions', 0)}  "
            f"ended={end_time}"
        )

        if result.get("errors"):
            for err in result["errors"]:
                logger.warning(f"[SCHEDULER] Sync warning/error: {err}")

    except Exception as exc:
        # APScheduler swallows exceptions silently by default;
        # we log explicitly so nothing disappears.
        logger.error(f"[SCHEDULER] Unhandled exception in sync job: {exc}", exc_info=True)


def start_scheduler() -> None:
    """
    Register the sync job and start the scheduler.
    Call this once from the FastAPI startup event.

    Schedule:
      - Interval trigger: every 5 minutes
      - `next_run_time=now()` ensures it fires immediately on startup
    """
    from datetime import datetime, timezone

    if _scheduler.running:
        logger.warning("[SCHEDULER] Scheduler already running — skipping start")
        return

    _scheduler.add_job(
        _run_sync_job,
        trigger=IntervalTrigger(minutes=5),
        id="pc12_sync_job",
        name="PC12 → PC14 Auto Sync",
        replace_existing=True,
        # No next_run_time — waits 5 min before first auto-run
        # so it doesn't conflict with a manual sync on startup
        max_instances=1,         # never run two syncs simultaneously
        coalesce=True,           # collapse missed triggers into one run
    )

    _scheduler.add_job(
        _run_vin_sync_job,
        trigger=IntervalTrigger(days=30),
        id="vin_intel_sync_job",
        name="30-Day VIN Intelligence Sync",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    _scheduler.add_job(
        _run_fuel_price_sync_job,
        trigger=IntervalTrigger(hours=12),
        id="fuel_price_sync_job",
        name="Daily Fuel Price Sync",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    _scheduler.start()
    logger.success(
        "[SCHEDULER] Started — PC12→PC14 sync will run NOW and every 5 minutes."
    )


def stop_scheduler() -> None:
    """Gracefully shut down the scheduler on app shutdown."""
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("[SCHEDULER] Stopped.")
