import asyncio
from sqlalchemy import text
from app.db.session import engine

async def check():
    try:
        async with engine.connect() as conn:
            res = await conn.execute(text('SELECT id, name, email FROM tc_users'))
            users = res.all()
            for u in users:
                print(u)
    except Exception as e:
        print(f'Error: {e}')

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(check())
    finally:
        loop.close()
