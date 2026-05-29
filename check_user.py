import asyncio
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.traccar import User

async def check_user():
    async with SessionLocal() as db:
        query = select(User).where(User.email == "farhan@gmail.com")
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        if user:
            print(f"User found: ID={user.id}, Email={user.email}, Name={user.name}, Admin={user.administrator}")
        else:
            print("User not found in local DB")

if __name__ == "__main__":
    asyncio.run(check_user())
