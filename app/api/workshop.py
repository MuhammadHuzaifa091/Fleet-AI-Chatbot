from fastapi import APIRouter, Depends, Query, HTTPException, Body, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.auth import get_current_user
from app.services.workshop_service import workshop_service
from typing import Dict, Any, Optional, List

router = APIRouter()


# ==================== WORKSHOP DASHBOARD ====================

@router.get("/dashboard")
async def get_workshop_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await workshop_service.get_workshop_dashboard(db)


# ==================== WORKSHOP JOBS ====================

@router.get("/jobs")
async def get_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    technician_id: Optional[int] = Query(None),
    device_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await workshop_service.get_jobs(db, page, page_size, search, status, priority, technician_id, device_id)


@router.post("/jobs")
async def create_job(
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        job = await workshop_service.create_job(db, data, current_user.get("id"))
        return {"id": job.id, "job_number": job.job_number, "status": job.status, "message": "Job created"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/jobs/{job_id}")
async def get_job_detail(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    detail = await workshop_service.get_job_detail(db, job_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Job not found")
    return detail


@router.put("/jobs/{job_id}")
async def update_job(
    job_id: int,
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        job = await workshop_service.update_job(db, job_id, data, current_user.get("id"))
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return {"id": job.id, "status": job.status, "total_cost": job.total_cost, "message": "Job updated"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/jobs/{job_id}/transition")
async def transition_status(
    job_id: int,
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        new_status = data.get("status")
        if not new_status:
            raise HTTPException(status_code=400, detail="Status is required")
        result = await workshop_service.transition_status(db, job_id, new_status, data, current_user.get("id"))
        if not result:
            raise HTTPException(status_code=404, detail="Job not found")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/jobs/{job_id}/quality-check")
async def quality_check(
    job_id: int,
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        job = await workshop_service.quality_check(db, job_id, data, current_user.get("id"))
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return {
            "id": job.id, "quality_check_passed": job.quality_check_passed,
            "status": job.status, "quality_checklist": job.quality_checklist,
            "message": "Quality check recorded"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/jobs/{job_id}/approve")
async def approve_job(
    job_id: int,
    data: Dict[str, Any] = Body({}),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        job = await workshop_service.approve_job(db, job_id, data, current_user.get("id"))
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return {"id": job.id, "approved": job.approved, "status": job.status, "message": "Job approved"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/jobs/{job_id}/complete")
async def complete_job(
    job_id: int,
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        result = await workshop_service.complete_job(db, job_id, data, current_user.get("id"))
        if not result:
            raise HTTPException(status_code=404, detail="Job not found")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: int,
    data: Dict[str, Any] = Body({}),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        job = await workshop_service.cancel_job(db, job_id, data.get("reason", ""), current_user.get("id"))
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return {"id": job.id, "status": job.status, "message": "Job cancelled"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/jobs/create-from-due")
async def create_job_from_due(
    device_id: int = Query(...),
    data: Dict[str, Any] = Body({}),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    job = await workshop_service.create_job_from_due(db, device_id, data, current_user.get("id"))
    if not job:
        raise HTTPException(status_code=400, detail="Could not create job from due data")
    return {"id": job.id, "job_number": job.job_number, "status": job.status, "message": "Job created from due vehicle"}


# ==================== TIMELINE ====================

@router.get("/jobs/{job_id}/timeline")
async def get_job_timeline(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await workshop_service.get_timeline(db, job_id)


# ==================== ATTACHMENTS ====================

@router.get("/jobs/{job_id}/attachments")
async def get_job_attachments(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await workshop_service.get_attachments(db, job_id)


@router.post("/jobs/{job_id}/attachments")
async def add_job_attachment(
    job_id: int,
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        att = await workshop_service.add_attachment(db, job_id, data, current_user.get("name", f"User {current_user.get('id')}"))
        if not att:
            raise HTTPException(status_code=404, detail="Job not found")
        return {"id": att.id, "filename": att.filename, "message": "Attachment added"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/attachments/{attachment_id}")
async def delete_attachment(
    attachment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    success = await workshop_service.delete_attachment(db, attachment_id)
    if not success:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return {"message": "Attachment deleted"}


# ==================== TECHNICIANS ====================

@router.get("/technicians")
async def get_technicians(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await workshop_service.get_technicians(db, page, page_size, search, status)


@router.post("/technicians")
async def create_technician(
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        tech = await workshop_service.create_technician(db, data, current_user.get("id"))
        return {"id": tech.id, "name": tech.name, "employee_id": tech.employee_id, "message": "Technician created"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/technicians/{tech_id}")
async def update_technician(
    tech_id: int,
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    tech = await workshop_service.update_technician(db, tech_id, data)
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")
    return {"id": tech.id, "name": tech.name, "message": "Technician updated"}


@router.delete("/technicians/{tech_id}")
async def delete_technician(
    tech_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    success = await workshop_service.delete_technician(db, tech_id)
    if not success:
        raise HTTPException(status_code=404, detail="Technician not found")
    return {"message": "Technician deleted"}


# ==================== STATUS FLOW ====================

@router.get("/status-flow")
async def get_status_flow(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return {
        "statuses": workshop_service.VALID_STATUSES,
        "transitions": workshop_service.VALID_TRANSITIONS,
        "default_checklist": workshop_service.DEFAULT_CHECKLIST,
    }
