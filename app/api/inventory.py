from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.auth import get_current_user
from app.services.inventory_service import inventory_service
from typing import Dict, Any, Optional, List

router = APIRouter()


# ==================== DASHBOARD ====================

@router.get("/dashboard")
async def get_inventory_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await inventory_service.get_dashboard(db)


# ==================== SPARE PARTS ====================

@router.get("/parts")
async def get_parts(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    supplier: Optional[str] = Query(None),
    stock_status: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    sort_by: str = Query("name"),
    sort_dir: str = Query("asc"),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await inventory_service.get_parts(db, page, page_size, search, category, supplier, stock_status, location, sort_by, sort_dir)


@router.get("/parts/{part_id}")
async def get_part_detail(
    part_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    detail = await inventory_service.get_part_detail(db, part_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Part not found")
    return detail


@router.post("/parts")
async def create_part(
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        part = await inventory_service.create_part(db, data, current_user.get("id"))
        return {"id": part.id, "part_number": part.part_number, "name": part.name, "message": "Part created"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/parts/{part_id}")
async def update_part(
    part_id: int,
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        part = await inventory_service.update_part(db, part_id, data)
        if not part:
            raise HTTPException(status_code=404, detail="Part not found")
        return {"id": part.id, "name": part.name, "message": "Part updated"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/parts/{part_id}")
async def delete_part(
    part_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    success = await inventory_service.delete_part(db, part_id)
    if not success:
        raise HTTPException(status_code=404, detail="Part not found")
    return {"message": "Part deactivated"}


# ==================== STOCK MOVEMENTS ====================

@router.post("/parts/{part_id}/stock-in")
async def stock_in(
    part_id: int,
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        return await inventory_service.stock_in(db, part_id, data, f"User {current_user.get('id')}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/parts/{part_id}/stock-out")
async def stock_out(
    part_id: int,
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        return await inventory_service.stock_out(db, part_id, data, f"User {current_user.get('id')}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/parts/{part_id}/adjust")
async def adjust_stock(
    part_id: int,
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        return await inventory_service.adjust_stock(db, part_id, data, f"User {current_user.get('id')}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/parts/{part_id}/transfer")
async def transfer_stock(
    part_id: int,
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        return await inventory_service.transfer_stock(db, part_id, data, f"User {current_user.get('id')}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/parts/{part_id}/return")
async def return_stock(
    part_id: int,
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        return await inventory_service.return_stock(db, part_id, data, f"User {current_user.get('id')}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/parts/{part_id}/scrap")
async def scrap_stock(
    part_id: int,
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        return await inventory_service.scrap_stock(db, part_id, data, f"User {current_user.get('id')}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== WORKSHOP INTEGRATION ====================

@router.post("/jobs/{job_id}/issue-parts")
async def issue_parts_to_job(
    job_id: int,
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Issue parts to a workshop job. Body: { parts: [{part_id, quantity}] }"""
    try:
        parts = data.get("parts", [])
        return await inventory_service.issue_parts_to_job(db, job_id, parts, f"User {current_user.get('id')}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/jobs/{job_id}/return-parts")
async def return_parts_from_job(
    job_id: int,
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Return parts from a workshop job. Body: { parts: [{part_id, quantity}] }"""
    try:
        parts = data.get("parts", [])
        return await inventory_service.return_parts_from_job(db, job_id, parts, f"User {current_user.get('id')}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/jobs/{job_id}/parts")
async def get_job_parts(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await inventory_service.get_job_parts(db, job_id)


# ==================== MOVEMENTS ====================

@router.get("/movements")
async def get_movements(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    spare_part_id: Optional[int] = Query(None),
    movement_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await inventory_service.get_movements(db, page, page_size, spare_part_id, movement_type, search)


# ==================== REPORTS ====================

@router.get("/reports/stock-ledger")
async def get_stock_ledger(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await inventory_service.get_stock_ledger(db)


@router.get("/reports/consumption")
async def get_consumption_report(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await inventory_service.get_consumption_report(db, days)


@router.get("/reports/low-stock")
async def get_low_stock_report(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await inventory_service.get_low_stock_report(db)


@router.get("/reports/workshop-usage")
async def get_workshop_parts_usage(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await inventory_service.get_workshop_parts_usage(db, days)


# ==================== META ====================

@router.get("/meta")
async def get_inventory_meta(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return {
        "categories": inventory_service.CATEGORIES,
        "units": inventory_service.UNITS,
        "movement_types": inventory_service.MOVEMENT_TYPES,
        "statuses": inventory_service.STATUSES,
    }
