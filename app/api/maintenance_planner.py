from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.auth import get_current_user
from app.services.maintenance_planner_service import maintenance_planner_service
from typing import Dict, Any, Optional, List
from loguru import logger

router = APIRouter()


# ==================== MAINTENANCE TYPES ====================

@router.get("/types")
async def get_maintenance_types(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None),
    active_only: Optional[bool] = Query(None),
    deleted_only: Optional[bool] = Query(None),
    category: Optional[str] = Query(None),
    sort_by: str = Query("name"),
    sort_order: str = Query("asc"),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get maintenance types with pagination, search, category/status filtering, sorting"""
    return await maintenance_planner_service.get_maintenance_types(
        db, page, page_size, search, active_only, deleted_only, category, sort_by, sort_order
    )


@router.get("/types/summary")
async def get_maintenance_types_summary(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get summary counts for maintenance types"""
    return await maintenance_planner_service.get_maintenance_types_summary(db)


@router.get("/types/categories")
async def get_maintenance_categories(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get distinct maintenance type categories"""
    return await maintenance_planner_service.get_maintenance_categories(db)


@router.get("/types/{type_id}")
async def get_maintenance_type(
    type_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get a single maintenance type by ID"""
    mt = await maintenance_planner_service.get_maintenance_type_by_id(db, type_id)
    if not mt:
        raise HTTPException(status_code=404, detail="Maintenance type not found")
    return mt


@router.post("/types")
async def create_maintenance_type(
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Create a new maintenance type"""
    try:
        mt = await maintenance_planner_service.create_maintenance_type(db, data, current_user.get("id"))
        return {"id": mt.id, "name": mt.name, "message": "Maintenance type created", "item": mt.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/types/{type_id}")
async def update_maintenance_type(
    type_id: int,
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update a maintenance type"""
    mt = await maintenance_planner_service.update_maintenance_type(db, type_id, data, current_user.get("id"))
    if not mt:
        raise HTTPException(status_code=404, detail="Maintenance type not found or is system type")
    return {"id": mt.id, "name": mt.name, "message": "Maintenance type updated", "item": mt.to_dict()}


@router.delete("/types/{type_id}")
async def delete_maintenance_type(
    type_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Soft delete a maintenance type"""
    success = await maintenance_planner_service.delete_maintenance_type(db, type_id, current_user.get("id"))
    if not success:
        raise HTTPException(status_code=404, detail="Maintenance type not found or is system type")
    return {"message": "Maintenance type deleted"}


@router.patch("/types/{type_id}/restore")
async def restore_maintenance_type(
    type_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Restore a soft-deleted maintenance type"""
    mt = await maintenance_planner_service.restore_maintenance_type(db, type_id, current_user.get("id"))
    if not mt:
        raise HTTPException(status_code=404, detail="Maintenance type not found")
    return {"id": mt.id, "name": mt.name, "message": "Maintenance type restored", "item": mt.to_dict()}


@router.patch("/types/{type_id}/activate")
async def activate_maintenance_type(
    type_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Activate a maintenance type"""
    mt = await maintenance_planner_service.update_maintenance_type(db, type_id, {"is_active": True}, current_user.get("id"))
    if not mt:
        raise HTTPException(status_code=404, detail="Maintenance type not found or is system type")
    return {"id": mt.id, "name": mt.name, "message": "Maintenance type activated"}


@router.patch("/types/{type_id}/deactivate")
async def deactivate_maintenance_type(
    type_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Deactivate a maintenance type"""
    mt = await maintenance_planner_service.update_maintenance_type(db, type_id, {"is_active": False}, current_user.get("id"))
    if not mt:
        raise HTTPException(status_code=404, detail="Maintenance type not found or is system type")
    return {"id": mt.id, "name": mt.name, "message": "Maintenance type deactivated"}


@router.post("/types/seed")
async def seed_maintenance_types(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Seed default maintenance types (only if table is empty)"""
    count = await maintenance_planner_service.seed_default_types(db, current_user.get("id"))
    if count == 0:
        return {"message": "Types already seeded, no duplicates added", "count": 0}
    return {"message": f"{count} default maintenance types seeded", "count": count}


# ==================== MAINTENANCE RULES ====================

@router.get("/rules")
async def get_maintenance_rules(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    type_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    active_only: Optional[bool] = Query(None),
    sort_by: str = Query("rule_order"),
    sort_order: str = Query("asc"),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await maintenance_planner_service.get_maintenance_rules(
        db, page, page_size, type_id, search, active_only, sort_by, sort_order
    )


@router.post("/rules")
async def create_maintenance_rule(
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        rule = await maintenance_planner_service.create_maintenance_rule(db, data, current_user.get("id"))
        return {"id": rule.id, "name": rule.name, "message": "Maintenance rule created"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/rules/{rule_id}")
async def update_maintenance_rule(
    rule_id: int,
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    rule = await maintenance_planner_service.update_maintenance_rule(db, rule_id, data, current_user.get("id"))
    if not rule:
        raise HTTPException(status_code=404, detail="Maintenance rule not found")
    return {"id": rule.id, "name": rule.name, "message": "Maintenance rule updated"}


@router.delete("/rules/{rule_id}")
async def delete_maintenance_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    success = await maintenance_planner_service.delete_maintenance_rule(db, rule_id)
    if not success:
        raise HTTPException(status_code=404, detail="Maintenance rule not found")
    return {"message": "Maintenance rule deleted"}


# ==================== VALIDATION ====================

@router.post("/validate")
async def validate_rule(
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return maintenance_planner_service.validate_rule(data)


# ==================== TEMPLATES ====================

@router.get("/templates")
async def get_templates(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None),
    vehicle_type: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await maintenance_planner_service.get_templates(
        db, page, page_size, search, vehicle_type, category, status
    )


@router.get("/templates/{template_id}")
async def get_template_detail(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    detail = await maintenance_planner_service.get_template_detail(db, template_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Template not found")
    return detail


@router.post("/templates")
async def create_template(
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        template = await maintenance_planner_service.create_template(db, data, current_user.get("id"))
        return {"id": template.id, "name": template.name, "message": "Template created"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/templates/{template_id}")
async def update_template(
    template_id: int,
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    template = await maintenance_planner_service.update_template(db, template_id, data, current_user.get("id"))
    if not template:
        raise HTTPException(status_code=404, detail="Template not found or is system type")
    return {"id": template.id, "name": template.name, "message": "Template updated"}


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    success = await maintenance_planner_service.delete_template(db, template_id)
    if not success:
        raise HTTPException(status_code=404, detail="Template not found or is system type")
    return {"message": "Template deleted"}


@router.patch("/templates/{template_id}/restore")
async def restore_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    success = await maintenance_planner_service.restore_template(db, template_id)
    if not success:
        raise HTTPException(status_code=404, detail="Template not found or not deleted")
    return {"message": "Template restored"}


@router.patch("/templates/{template_id}/activate")
async def activate_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    success = await maintenance_planner_service.activate_template(db, template_id)
    if not success:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"message": "Template activated"}


@router.patch("/templates/{template_id}/deactivate")
async def deactivate_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    success = await maintenance_planner_service.deactivate_template(db, template_id)
    if not success:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"message": "Template deactivated"}


@router.post("/templates/{template_id}/duplicate")
async def duplicate_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    template = await maintenance_planner_service.duplicate_template(db, template_id, current_user.get("id"))
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"id": template.id, "name": template.name, "message": "Template duplicated"}


@router.post("/templates/seed")
async def seed_default_templates(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    count = await maintenance_planner_service.seed_default_templates(db, current_user.get("id"))
    return {"seeded": count, "message": f"{count} default templates created"}


@router.get("/validate")
async def validate_templates(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    fix = await maintenance_planner_service.ensure_all_templates_have_rules(db, current_user.get("id"))
    report = await maintenance_planner_service.validate_templates(db)
    report["auto_fix_result"] = fix
    return report


@router.get("/templates/{template_id}/rules")
async def get_template_rules(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await maintenance_planner_service.get_template_rules(db, template_id)


@router.post("/templates/{template_id}/rules")
async def add_rule_to_template(
    template_id: int,
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        link = await maintenance_planner_service.add_rule_to_template(
            db, template_id, data["rule_id"],
            data.get("override_km"), data.get("override_days"),
            data.get("override_hours"), data.get("override_priority"),
            data.get("execution_order"), data.get("is_enabled", True),
            current_user.get("id")
        )
        return {"id": link.id, "message": "Rule added to template"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/templates/{template_id}/rules/{rule_id}")
async def remove_rule_from_template(
    template_id: int,
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    success = await maintenance_planner_service.remove_rule_from_template(db, template_id, rule_id)
    if not success:
        raise HTTPException(status_code=404, detail="Rule not linked to template")
    return {"message": "Rule removed from template"}


@router.put("/templates/{template_id}/rules/reorder")
async def reorder_template_rules(
    template_id: int,
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    success = await maintenance_planner_service.reorder_template_rules(db, template_id, data.get("rule_ids", []))
    if not success:
        raise HTTPException(status_code=400, detail="Failed to reorder rules")
    return {"message": "Rules reordered"}


@router.get("/templates/{template_id}/vehicles")
async def get_template_vehicles(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    detail = await maintenance_planner_service.get_template_detail(db, template_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"items": detail.get("vehicles", []), "total": detail.get("vehicle_count", 0)}


# ==================== VEHICLE MAINTENANCE PLANS ====================

@router.get("/plans")
async def get_vehicle_plans(
    device_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    active_only: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await maintenance_planner_service.get_vehicle_plans(db, device_id, page, page_size, active_only)


@router.post("/plans")
async def create_vehicle_plan(
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        plan = await maintenance_planner_service.create_vehicle_plan(db, data["device_id"], data, current_user.get("id"))
        return {"id": plan.id, "name": plan.name, "message": "Vehicle plan created"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/plans/{plan_id}")
async def update_vehicle_plan(
    plan_id: int,
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    plan = await maintenance_planner_service.update_vehicle_plan(db, plan_id, data, current_user.get("id"))
    if not plan:
        raise HTTPException(status_code=404, detail="Vehicle plan not found")
    return {"id": plan.id, "name": plan.name, "message": "Vehicle plan updated"}


@router.delete("/plans/{plan_id}")
async def delete_vehicle_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    success = await maintenance_planner_service.delete_vehicle_plan(db, plan_id)
    if not success:
        raise HTTPException(status_code=404, detail="Vehicle plan not found")
    return {"message": "Vehicle plan deleted"}


@router.post("/plans/assign-template")
async def assign_template(
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        plan = await maintenance_planner_service.assign_template_to_vehicle(
            db, data["device_id"], data["template_id"], current_user.get("id")
        )
        return {"id": plan.id, "name": plan.name, "message": "Template assigned to vehicle"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/plans/replace-template")
async def replace_template(
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        plan = await maintenance_planner_service.replace_template_on_vehicle(
            db, data["device_id"], data["template_id"], current_user.get("id")
        )
        return {"id": plan.id, "name": plan.name, "message": "Template replaced on vehicle"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/plans/bulk-assign")
async def bulk_assign(
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        result = await maintenance_planner_service.bulk_assign_template(
            db, data["device_ids"], data["template_id"], current_user.get("id")
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/plans/{plan_id}/unassign")
async def unassign_template(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    success = await maintenance_planner_service.unassign_template(db, plan_id)
    if not success:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"message": "Template unassigned"}


@router.get("/plans/validate")
async def validate_plans(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await maintenance_planner_service.validate_vehicle_plans(db)


@router.get("/vehicles-plans")
async def get_vehicles_with_plans(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    health: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await maintenance_planner_service.get_vehicles_with_plans(
        db, search, status, health, category, page, page_size
    )


# ==================== RULE OVERRIDES ====================

@router.get("/plans/{plan_id}/overrides")
async def get_plan_overrides(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await maintenance_planner_service.get_plan_overrides(db, plan_id)


@router.post("/plans/{plan_id}/overrides")
async def create_plan_override(
    plan_id: int,
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        override = await maintenance_planner_service.create_plan_rule_override(
            db, plan_id, data["rule_id"], data["type_id"],
            data.get("override_km"), data.get("override_days"),
            data.get("override_hours"), data.get("override_priority"),
            data.get("is_enabled", True), data.get("reason"),
            current_user.get("id")
        )
        return {"id": override.id, "message": "Rule override created"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/overrides/{override_id}")
async def update_plan_override(
    override_id: int,
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    override = await maintenance_planner_service.update_plan_override(db, override_id, data, current_user.get("id"))
    if not override:
        raise HTTPException(status_code=404, detail="Rule override not found")
    return {"id": override.id, "message": "Rule override updated"}


@router.delete("/overrides/{override_id}")
async def delete_plan_override(
    override_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    success = await maintenance_planner_service.delete_plan_override(db, override_id)
    if not success:
        raise HTTPException(status_code=404, detail="Rule override not found")
    return {"message": "Rule override deleted"}


# ==================== DUE CALCULATION ENGINE ====================

@router.get("/due-calculation/{device_id}")
async def get_due_calculation(
    device_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await maintenance_planner_service.get_vehicle_due_calculation(db, device_id)


# ==================== PRIORITY ENGINE ====================

@router.post("/priority")
async def calculate_priority(
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return maintenance_planner_service.calculate_priority(
        km_remaining=data.get("km_remaining"),
        days_remaining=data.get("days_remaining"),
        km_grace=data.get("km_grace", 0),
        days_grace=data.get("days_grace", 0),
        interval_km=data.get("interval_km"),
        interval_days=data.get("interval_days")
    )


# ==================== RULE HISTORY ====================

@router.get("/history")
async def get_rule_history(
    rule_id: Optional[int] = Query(None),
    type_id: Optional[int] = Query(None),
    template_id: Optional[int] = Query(None),
    plan_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await maintenance_planner_service.get_rule_history(
        db, rule_id, type_id, template_id, plan_id, page, page_size
    )


@router.post("/history")
async def add_rule_history(
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    entry = await maintenance_planner_service.add_rule_history(
        db,
        rule_id=data.get("rule_id"),
        type_id=data.get("type_id"),
        template_id=data.get("template_id"),
        plan_id=data.get("plan_id"),
        field_name=data.get("field_name"),
        old_value=data.get("old_value"),
        new_value=data.get("new_value"),
        changed_by=current_user.get("id"),
        reason=data.get("reason")
    )
    return {"id": entry.id, "message": "History entry added"}


# ==================== SMART DUE ENGINE / SCHEDULER ====================

@router.get("/scheduler/summary")
async def get_scheduler_summary(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    fleet = await maintenance_planner_service.calculate_fleet_due_status(db)
    return {
        "health_score": fleet["health_score"],
        "summary": fleet["summary"],
        "calculated_at": fleet["calculated_at"],
        "total_rules_active": sum(len(v["items"]) for v in fleet["vehicles"]),
        "total_overdue_rules": sum(s["overdue"] for v in fleet["vehicles"] for s in [v["summary"]]),
        "total_due_soon_rules": sum(s["due_soon"] for v in fleet["vehicles"] for s in [v["summary"]]),
    }


@router.get("/scheduler/upcoming")
async def get_scheduler_upcoming(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    type_filter: Optional[str] = Query(None),
    sort_by: str = Query("days_remaining"),
    sort_order: str = Query("asc"),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await maintenance_planner_service.get_upcoming_items(
        db, page, page_size, search, type_filter, sort_by, sort_order
    )


@router.get("/scheduler/overdue")
async def get_scheduler_overdue(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    sort_by: str = Query("days_remaining"),
    sort_order: str = Query("asc"),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return await maintenance_planner_service.get_overdue_items(
        db, page, page_size, search, sort_by, sort_order
    )


@router.get("/scheduler/calendar")
async def get_scheduler_calendar(
    year: int = Query(..., ge=2020, le=2030),
    month: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    events = await maintenance_planner_service.get_calendar_events(db, year, month)
    return {"events": events, "year": year, "month": month}


@router.get("/scheduler/activity")
async def get_scheduler_activity(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    activities = await maintenance_planner_service.get_activity_feed(db, limit)
    return {"activities": activities}


@router.post("/scheduler/recalculate")
async def recalculate_fleet(
    device_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    if device_id:
        return await maintenance_planner_service.recalculate_vehicle(db, device_id)
    return await maintenance_planner_service.recalculate_fleet(db)