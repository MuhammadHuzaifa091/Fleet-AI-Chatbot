import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

PC12_DB_HOST = "202.141.246.12"
PC12_DB_USER = "traccar"
PC12_DB_PASS = "traccar12344321"

async def list_dbs():
    url = f"mysql+aiomysql://{PC12_DB_USER}:{PC12_DB_PASS}@{PC12_DB_HOST}/"
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            res = await conn.execute(text("SHOW DATABASES"))
            print("DATABASES ON PC12:")
            for r in res:
                print(f" - {r[0]}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(list_dbs())
