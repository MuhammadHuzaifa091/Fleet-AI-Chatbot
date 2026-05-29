import asyncio
from app.db.session import SessionLocal
from sqlalchemy import text

async def test():
    db = SessionLocal()
    try:
        r1 = await db.execute(text('SELECT COUNT(*) FROM tc_positions'))
        print(f'Positions Count: {r1.scalar()}')
        
        r2 = await db.execute(text('SELECT COUNT(*) FROM tc_devices WHERE positionid IS NOT NULL'))
        print(f'Devices with PositionID: {r2.scalar()}')
        
        r3 = await db.execute(text('SELECT COUNT(*) FROM tc_devices'))
        print(f'Total Devices: {r3.scalar()}')
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(test())
