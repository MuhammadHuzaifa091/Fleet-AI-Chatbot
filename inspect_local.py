import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os
from dotenv import load_dotenv

load_dotenv()

async def inspect_data():
    db_url = f"mysql+aiomysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_SERVER')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    engine = create_async_engine(db_url)
    async with engine.connect() as conn:
        print("--- LOCAL DEVICES (FIRST 10) ---")
        res = await conn.execute(text("SELECT id, name, uniqueid FROM tc_devices LIMIT 10"))
        for r in res:
            print(f"ID: {r[0]}, Name: {r[1]}, UniqueID: {r[2]}")
        
        print("\n--- LOCAL USERS (FIRST 5) ---")
        res = await conn.execute(text("SELECT id, name, email FROM tc_users LIMIT 5"))
        for r in res:
            print(f"ID: {r[0]}, Name: {r[1]}, Email: {r[2]}")
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(inspect_data())
