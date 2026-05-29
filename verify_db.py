import asyncio
import logging
from app.db.session import SessionLocal
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def verify_columns():
    async with SessionLocal() as db:
        try:
            result = await db.execute(text("SHOW COLUMNS FROM tc_devices;"))
            columns = [row[0] for row in result.fetchall()]
            logger.info(f"Current columns in tc_devices: {columns}")
            
            required = ['vin', 'vin_source', 'manufacturer', 'model', 'year', 'pid_profile', 'profile_status']
            missing = [c for c in required if c not in columns]
            
            if not missing:
                logger.info("All required columns are present.")
            else:
                logger.warning(f"Missing columns: {missing}")
        except Exception as e:
            logger.error(f"Error verifying columns: {e}")

if __name__ == "__main__":
    asyncio.run(verify_columns())
