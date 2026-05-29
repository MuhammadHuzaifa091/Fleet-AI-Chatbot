import asyncio
import traceback
import sys

async def main():
    log_lines = []
    try:
        from app.db.session import SessionLocal
        from app.rag.pipeline import RAGPipeline
        log_lines.append("Imports OK")

        async with SessionLocal() as db:
            user = {"id": 1, "email": "ali.w.farhan@gmail.com", "role": "SUPERADMIN"}
            log_lines.append("DB session OK")
            
            rag = RAGPipeline(db, user)
            log_lines.append("RAG Pipeline created OK")
            
            res = await rag.process_query("show my vehicles")
            log_lines.append(f"SUCCESS: {res}")
    except Exception as e:
        log_lines.append(f"ERROR: {type(e).__name__}: {e}")
        log_lines.append(traceback.format_exc())
    
    # Write to file with utf-8
    with open("test_rag_output.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))
    print("Output written to test_rag_output.txt")

asyncio.run(main())
