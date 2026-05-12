from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.auth import get_current_user
from app.retrievers.sql_retriever import SQLRetriever
from typing import List, Dict, Any

router = APIRouter()

@router.get("/live")
async def get_live_vehicles(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    retriever = SQLRetriever(db, current_user)
    return await retriever.get_live_vehicles()

@router.get("/{name}")
async def get_vehicle_by_name(
    name: str, 
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    retriever = SQLRetriever(db, current_user)
    vehicle = await retriever.get_vehicle_by_name(name)
    if not vehicle:
        return {"error": "Vehicle not found"}
    return vehicle
