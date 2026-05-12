from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.retrievers.sql_retriever import SQLRetriever

router = APIRouter()

@router.get("/overspeeding")
async def get_overspeeding(days: int = Query(1, ge=1), db: AsyncSession = Depends(get_db)):
    retriever = SQLRetriever(db)
    return await retriever.get_overspeed_events(days)

@router.get("/maintenance")
async def get_maintenance(db: AsyncSession = Depends(get_db)):
    retriever = SQLRetriever(db)
    return await retriever.get_maintenance_status()
