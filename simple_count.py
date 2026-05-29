import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os
from dotenv import load_dotenv

load_dotenv()

async def get_counts():
    db_url = f"mysql+aiomysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_SERVER')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    engine = create_async_engine(db_url)
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT COUNT(*) FROM tc_devices"))
        print(f"Total Devices: {res.scalar()}")
        res = await conn.execute(text("SELECT COUNT(*) FROM tc_users"))
        print(f"Total Users: {res.scalar()}")
        res = await conn.execute(text("SELECT COUNT(*) FROM tc_user_device"))
        print(f"Total Permissions: {res.scalar()}")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(get_counts())
