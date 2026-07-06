import asyncio
from sqlalchemy import text
from app.db.session import SessionLocal

async def check():
    async with SessionLocal() as db:
        sql = """
            SELECT 
                f.vehicle_registration,
                f.uniqueid as fdb_imei,
                d.status as live_status
            FROM ke_fleet_database f
            LEFT JOIN tc_devices d ON f.uniqueid = d.uniqueid
            LIMIT 5
        """
        try:
            res = await db.execute(text(sql))
            print("JOIN TEST:", res.fetchall())
        except Exception as e:
            print("JOIN ERROR:", str(e))

if __name__ == "__main__":
    asyncio.run(check())
