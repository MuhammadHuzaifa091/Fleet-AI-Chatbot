from fastapi import APIRouter, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.vector.qdrant import qdrant_service
from app.retrievers.sql_retriever import SQLRetriever
from typing import List, Dict, Any

router = APIRouter()

@router.post("/reindex")
async def reindex_fleet_data(db: AsyncSession = Depends(get_db)):
    """
    Summarizes fleet status and indexes it for semantic search.
    """
    system_user = {"id": 0, "role": "SUPERADMIN"}
    retriever = SQLRetriever(db, system_user)
    vehicles = await retriever.get_live_vehicles()
    
    points = []
    for v in vehicles:
        summary = f"Vehicle {v['name']} ({v['uniqueId']}) is currently {v['status']}. Location: {v['address']}. Last update: {v['lastUpdate']}."
        points.append({
            "id": v['id'],
            "text": summary,
            "metadata": {"type": "vehicle_summary", "vehicle_id": v['id']}
        })
    
    await qdrant_service.upsert_points(points)
    return {"message": f"Successfully indexed {len(points)} vehicle summaries."}
