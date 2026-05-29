import asyncio
from sqlalchemy import text
from app.db.session import engine

async def check_table():
    async with engine.connect() as conn:
        result = await conn.execute(text("SHOW TABLES LIKE 'vehicle_specs_cache'"))
        row = result.fetchone()
        if row:
            print("TABLE EXISTS")
        else:
            print("TABLE MISSING")
            # Attempt to create if missing
            from app.models.traccar import Base
            async with engine.begin() as conn_create:
                await conn_create.run_sync(Base.metadata.create_all)
            print("TABLE CREATED")

if __name__ == "__main__":
    asyncio.run(check_table())
