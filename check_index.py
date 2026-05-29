import asyncio
from sqlalchemy import text
from app.db.session import SessionLocal

async def check():
    async with SessionLocal() as db:
        res = await db.execute(text('SHOW INDEX FROM tc_user_device'))
        print(res.fetchall())

if __name__ == "__main__":
    asyncio.run(check())
