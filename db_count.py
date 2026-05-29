import asyncio
from app.db.session import SessionLocal
from sqlalchemy import text

async def t():
    async with SessionLocal() as db:
        res = await db.execute(text("SELECT COUNT(*) FROM tc_devices"))
        print("TOTAL:", res.scalar())
        res2 = await db.execute(text("SELECT COUNT(*) FROM tc_devices WHERE disabled=0"))
        print("DISABLED=0:", res2.scalar())
        res3 = await db.execute(text("SELECT COUNT(*) FROM tc_devices WHERE disabled=False"))
        print("DISABLED=False:", res3.scalar())
asyncio.run(t())
