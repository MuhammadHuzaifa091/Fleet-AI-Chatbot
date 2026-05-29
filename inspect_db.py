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
    local_url = f"mysql+aiomysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_SERVER')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    remote_url = f"mysql+aiomysql://{PC12_DB_USER}:{PC12_DB_PASS}@{PC12_DB_HOST}/{PC12_DB_NAME}"
    
    local_engine = create_async_engine(local_url)
    remote_engine = create_async_engine(remote_url)
    
    try:
        async with remote_engine.connect() as conn:
            print("--- REMOTE PC12 DEVICES (FIRST 10) ---")
            res = await conn.execute(text("SELECT id, name, uniqueid FROM tc_devices LIMIT 10"))
            for r in res:
                print(f"ID: {r[0]}, Name: {r[1]}, UniqueID: {r[2]}")
    except Exception as e:
        print(f"Remote Error: {e}")
            
    await local_engine.dispose()
    await remote_engine.dispose()

if __name__ == "__main__":
    asyncio.run(inspect_data())
