import asyncio
import logging
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from app.core.database import SessionLocal, engine
from app.models.traccar import FleetTrip, Device

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backfill-job")

async def optimize_historic_mileage(device_id: int):
    """
    Backfills missing historic mileage for a given device.
    Uses optimization_engine concepts.
    """
    logger.info(f"Starting async milestone backfill for device ID {device_id}")
    
    with SessionLocal() as session:
        device = session.query(Device).filter(Device.id == device_id).first()
        if not device:
            logger.error(f"Device {device_id} not found.")
            return
        
        # In a real app we would use optimization_engine, but here we estimate
        historic_trips = session.query(FleetTrip).filter(
            FleetTrip.device_id == device_id,
            FleetTrip.mileage == None
        ).all()
        
        if not historic_trips:
            logger.info(f"No pending trips found for device {device_id}")
            return
        
        logger.info(f"Found {len(historic_trips)} historic trips pending optimization.")
        for trip in historic_trips:
            # Rehydrate missing mileage fields based on some deterministic logic
            # e.g., if we know the device is a 50L capacity car that runs approx 10km/L
            if trip.distance_km and trip.fuel_consumed_l and trip.fuel_consumed_l > 0:
                trip.mileage = trip.distance_km / trip.fuel_consumed_l
            else:
                trip.mileage = 10.0 # Default fallback as per specs

            trip.is_historic = True

        session.commit()
        logger.info(f"Successfully optimized and backfilled {len(historic_trips)} trips for Device {device_id}")

async def run_full_fleet_backfill():
    """
    Scans for all devices that recently had their VINs enriched, and updates their trip history.
    """
    logger.info("Starting Full Fleet Mileage Backfill.")
    with SessionLocal() as session:
        devices = session.query(Device).filter(Device.vin != None).all()
        logger.info(f"Found {len(devices)} enriched VIN devices. Firing backfill...")
        
    for d in devices:
        await optimize_historic_mileage(d.id)
    
    logger.info("Fleet Backfill job completely finished.")

if __name__ == "__main__":
    logger.info("Booting historical optimization pipeline...")
    asyncio.run(run_full_fleet_backfill())
