import asyncio
import logging
from app.db.session import SessionLocal
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def apply_migrations():
    async with SessionLocal() as db:
        cols = [
            "vin VARCHAR(17)",
            "vin_source VARCHAR(20)",
            "manufacturer VARCHAR(100)",
            "model VARCHAR(100)",
            "year INT",
            "pid_profile TEXT",
            "profile_status VARCHAR(30)"
        ]
        
        for col in cols:
            try:
                await db.execute(text(f"ALTER TABLE tc_devices ADD COLUMN {col};"))
                logger.info(f"Added column {col}")
            except (OperationalError, ProgrammingError) as e:
                # 1060 is Duplicate column name in MySQL
                if "1060" in str(e) or "Duplicate column" in str(e):
                    logger.info(f"Column already exists: {col}, skipping.")
                else:
                    logger.error(f"Error adding {col}: {e}")
        
        try:
            await db.execute(text("""
            CREATE TABLE IF NOT EXISTS vin_change_log (
              id SERIAL PRIMARY KEY,
              device_id INT,
              old_vin VARCHAR(17),
              new_vin VARCHAR(17),
              changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              wipe_executed BOOLEAN DEFAULT TRUE
            );
            """))
            logger.info("Checked vin_change_log table")
        except Exception as e:
            logger.error(f"Error creating vin_change_log: {e}")

        try:
            await db.execute(text("""
            CREATE TABLE IF NOT EXISTS fleet_trips (
                id SERIAL PRIMARY KEY,
                device_id INT,
                distance_km FLOAT,
                fuel_consumed_l FLOAT,
                cost_estimate FLOAT,
                efficiency_score FLOAT,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                mileage FLOAT,
                is_historic BOOLEAN DEFAULT FALSE
            );
            """))
            logger.info("Checked fleet_trips table")
        except Exception as e:
            logger.error(f"Error creating fleet_trips: {e}")

        await db.commit()
        logger.info("Migrations applied successfully!")

if __name__ == "__main__":
    asyncio.run(apply_migrations())
