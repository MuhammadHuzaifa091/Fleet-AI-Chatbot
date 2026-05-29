import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os
from dotenv import load_dotenv

load_dotenv()

PC12_DB_HOST = "202.141.246.12"
PC12_DB_USER = "traccar"
PC12_DB_PASS = "traccar12344321"
PC12_DB_NAME = "traccar"

async def inspect_data():
    remote_url = f"mysql+aiomysql://{PC12_DB_USER}:{PC12_DB_PASS}@{PC12_DB_HOST}/{PC12_DB_NAME}"
    remote_engine = create_async_engine(remote_url)
    
    try:
        async with remote_engine.connect() as conn:
            res = await conn.execute(text("SELECT COUNT(*) FROM tc_devices"))
            print(f"REMOTE TOTAL DEVICES: {res.scalar()}")
            res = await conn.execute(text("SELECT COUNT(*) FROM tc_positions"))
            print(f"REMOTE TOTAL POSITIONS: {res.scalar()}")
    except Exception as e:
        print(f"Remote Error: {e}")
            
    await remote_engine.dispose()

if __name__ == "__main__":
    asyncio.run(inspect_data())
