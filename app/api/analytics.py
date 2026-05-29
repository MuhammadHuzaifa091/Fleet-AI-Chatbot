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

@router.get("/fuel/{device_id}")
async def get_fuel_analytics(
    device_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    # Note: In production, verify user has permission to this device_id
    await AnalyticsService.detect_fuel_station_visits(db, device_id)
    analytics = await AnalyticsService.get_fuel_analytics(db, device_id)
    if "error" in analytics:
        raise HTTPException(status_code=404 if "not found" in analytics["error"] else 500, detail=analytics["error"])
    
    # Add station logs
    analytics["station_logs"] = await AnalyticsService.get_fuel_station_logs(db, device_id)
    return analytics

@router.get("/fuel-prices")
async def get_fuel_prices(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    from app.services.fuel_price_service import FuelPriceService
    return await FuelPriceService.get_latest_prices(db)
