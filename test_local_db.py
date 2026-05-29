import asyncio
from sqlalchemy.ext.asyncio import create_async_engine

async def test():
    # Attempt connecting to LOCAL database
    url = "mysql+aiomysql://traccar:traccar12344321@localhost/traccar"
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            print("LOCAL DB CONNECTION: SUCCESS")
    except Exception as e:
        print(f"LOCAL DB CONNECTION: FAILED - {e}")

if __name__ == "__main__":
    asyncio.run(test())
