from fastapi import APIRouter, Depends, HTTPException, Response
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.auth import get_current_user
from app.services.analytics_service import AnalyticsService
from app.services.report_service import ReportService
from app.retrievers.sql_retriever import SQLRetriever
from typing import Dict, Any

router = APIRouter()

@router.get("/summary")
async def get_analytics_summary(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        user_id = current_user.get("id")
        role = current_user.get("role")
        
        summary = await AnalyticsService.get_analytics_summary(db, user_id, role)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/report")
async def get_fleet_report(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return Response(content="Report logic reach test", media_type="text/plain")
