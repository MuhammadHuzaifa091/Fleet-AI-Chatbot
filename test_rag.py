import asyncio
from app.rag.pipeline import RAGPipeline
from app.db.session import SessionLocal

async def main():
    async with SessionLocal() as db:
        user = {"id": 1, "email": "ali.w.farhan@gmail.com", "role": "SUPERADMIN"}
        try:
            rag = RAGPipeline(db, user)
            res = await rag.process_query("show my vehicles")
            print("SUCCESS:", res)
        except Exception as e:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
