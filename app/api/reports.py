from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.auth import get_current_user
from app.services.reports_service import reports_service
from typing import Dict, Any, Optional

router = APIRouter()


@router.get("/dashboard")
async def get_report_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await reports_service.get_dashboard_kpis(db)


@router.get("/fleet-maintenance")
async def get_fleet_maintenance(
    days: int = Query(90, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await reports_service.get_fleet_maintenance_report(db, days)


@router.get("/vehicle-history/{device_id}")
async def get_vehicle_history(
    device_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await reports_service.get_vehicle_history(db, device_id)


@router.get("/workshop-performance")
async def get_workshop_performance(
    days: int = Query(90, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await reports_service.get_workshop_performance(db, days)


@router.get("/technician-performance")
async def get_technician_performance(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await reports_service.get_technician_performance(db)


@router.get("/inventory-analytics")
async def get_inventory_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await reports_service.get_inventory_analytics(db)


@router.get("/cost-analytics")
async def get_cost_analytics(
    days: int = Query(365, ge=1, le=1095),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await reports_service.get_cost_analytics(db, days)


@router.get("/monthly")
async def get_monthly_report(
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await reports_service.get_monthly_report(db, year, month)


@router.get("/yearly")
async def get_yearly_report(
    year: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await reports_service.get_yearly_report(db, year)


@router.get("/vehicle-downtime")
async def get_vehicle_downtime(
    days: int = Query(90, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await reports_service.get_vehicle_downtime(db, days)


@router.get("/low-stock")
async def get_low_stock(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await reports_service.get_low_stock_report(db)


@router.get("/parts-usage")
async def get_parts_usage(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await reports_service.get_parts_usage_by_job(db, days)


# ==================== CHART DATA ====================

@router.get("/charts/cost-trend")
async def get_cost_trend(
    months: int = Query(12, ge=1, le=24),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await reports_service.get_maintenance_cost_trend(db, months)


@router.get("/charts/status-distribution")
async def get_status_distribution(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await reports_service.get_job_status_distribution(db)


@router.get("/charts/inventory-by-category")
async def get_inventory_by_category(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await reports_service.get_inventory_value_by_category(db)
