from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.auth import get_current_user
from app.services.analytics_service import AnalyticsService
from app.services.report_service import ReportService
from app.retrievers.sql_retriever import SQLRetriever
from app.services.fuel_price_service import FuelPriceService
from app.models.traccar import FuelPrice
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

@router.get("/fuel/organization/summary")
async def get_org_fuel_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    user_id = current_user.get("id")
    role = current_user.get("role")
    analytics = await AnalyticsService.get_organization_fuel_analytics(db, user_id, role)
    if "error" in analytics:
        raise HTTPException(status_code=404 if "not found" in analytics["error"] else 500, detail=analytics["error"])
    return analytics

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

# ---------------------------------------------------------------------------
# Fuel price endpoints (PKR)
# ---------------------------------------------------------------------------

@router.get("/fuel-prices")
async def get_fuel_prices(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    # Attempt to scrape fresh PKR prices each request
    prices = await FuelPriceService.scrape_and_update_prices(db)
    source = "PSO/OGRA Live"
    if not prices:
        prices = await FuelPriceService.get_latest_prices(db)
        source = "Database Cache"
    if not prices:
        prices = {"Petrol": 272.89, "Diesel": 278.96}
        source = "Default Rates"
    return {"prices": prices, "source": source}

@router.post("/fuel-prices/set")
async def set_fuel_prices(
    payload: Dict[str, float],
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Manually update fuel prices (PKR). Only ADMIN or SUPERADMIN can use.
    Expected payload: {"Petrol": <float>, "Diesel": <float>}
    """
    role = current_user.get("role")
    if role not in ["SUPERADMIN", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    for fuel_type, price in payload.items():
        result = await db.execute(select(FuelPrice).where(FuelPrice.fuel_type == fuel_type))
        obj = result.scalar_one_or_none()
        if obj:
            obj.price = price
            obj.last_updated = datetime.utcnow()
        else:
            db.add(FuelPrice(fuel_type=fuel_type, price=price, last_updated=datetime.utcnow(), source="Manual"))
    await db.commit()
    return {"status": "success", "updated": payload}

# ---------------------------------------------------------------------------
# Driver Intelligence Endpoints
# ---------------------------------------------------------------------------

@router.get("/driver/leaderboard")
async def get_driver_leaderboard(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await AnalyticsService.get_driver_leaderboard(db, days)

@router.get("/driver/{device_id}")
async def get_driver_analytics(
    device_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    analytics = await AnalyticsService.get_driver_analytics(db, device_id)
    if "error" in analytics:
        raise HTTPException(status_code=404, detail=analytics["error"])
    return analytics

@router.get("/driver/trips/unassigned")
async def get_unassigned_trips(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return []

@router.get("/driver/summary/stats")
async def get_driver_summary_stats(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await AnalyticsService.get_driver_summary_stats(db)

@router.get("/driver/compare/{device_id_a}/{device_id_b}")
async def compare_drivers(
    device_id_a: int,
    device_id_b: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    a = await AnalyticsService.get_driver_analytics(db, device_id_a)
    b = await AnalyticsService.get_driver_analytics(db, device_id_b)
    return {"driver_a": a, "driver_b": b}

@router.get("/alerts")
async def get_alerts_history(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    user_id = current_user.get("id")
    role = current_user.get("role")
    return await AnalyticsService.get_alerts_history(db, user_id, role)
