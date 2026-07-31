from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.traccar import SparePart, StockMovement, WorkshopJob, JobNote
from typing import List, Dict, Any, Optional
from loguru import logger
from datetime import datetime, timedelta
import uuid


class InventoryService:
    """Enterprise Spare Parts & Inventory Management"""

    CATEGORIES = ["engine", "brakes", "electrical", "filters", "fluids", "body", "tyres", "tools", "other"]
    UNITS = ["pcs", "litres", "kg", "metres", "sets", "bottles", "cans", "boxes"]
    MOVEMENT_TYPES = ["stock_in", "stock_out", "adjustment", "transfer", "return", "scrap"]
    STATUSES = ["active", "discontinued", "expired"]

    # ==================== DASHBOARD ====================

    @staticmethod
    async def get_dashboard(db: AsyncSession) -> Dict[str, Any]:
        try:
            total_parts = (await db.execute(
                select(func.count()).select_from(SparePart).where(SparePart.is_active == True)
            )).scalar() or 0

            available_stock = (await db.execute(
                select(func.sum(SparePart.current_quantity)).where(
                    and_(SparePart.is_active == True, SparePart.current_quantity > 0)
                )
            )).scalar() or 0

            low_stock_items = (await db.execute(
                select(func.count()).select_from(SparePart).where(
                    and_(SparePart.is_active == True,
                         SparePart.current_quantity <= SparePart.minimum_stock,
                         SparePart.current_quantity > 0)
                )
            )).scalar() or 0

            out_of_stock = (await db.execute(
                select(func.count()).select_from(SparePart).where(
                    and_(SparePart.is_active == True, SparePart.current_quantity <= 0)
                )
            )).scalar() or 0

            total_value_result = await db.execute(
                select(func.sum(SparePart.current_quantity * SparePart.unit_cost)).where(
                    SparePart.is_active == True
                )
            )
            total_value = round(float(total_value_result.scalar() or 0), 2)

            today = datetime.utcnow().date()
            today_start = datetime.combine(today, datetime.min.time())
            today_end = datetime.combine(today, datetime.max.time())

            parts_issued_today = (await db.execute(
                select(func.count()).select_from(StockMovement).where(
                    and_(StockMovement.movement_type == "stock_out",
                         StockMovement.created_at >= today_start,
                         StockMovement.created_at <= today_end)
                )
            )).scalar() or 0

            parts_returned_today = (await db.execute(
                select(func.count()).select_from(StockMovement).where(
                    and_(StockMovement.movement_type == "return",
                         StockMovement.created_at >= today_start,
                         StockMovement.created_at <= today_end)
                )
            )).scalar() or 0

            pending_purchase = (await db.execute(
                select(func.count()).select_from(SparePart).where(
                    and_(SparePart.is_active == True,
                         SparePart.current_quantity <= SparePart.minimum_stock)
                )
            )).scalar() or 0

            # Alerts
            alerts = []
            low_parts = await db.execute(
                select(SparePart).where(
                    and_(SparePart.is_active == True,
                         SparePart.current_quantity <= SparePart.minimum_stock,
                         SparePart.current_quantity > 0)
                )
            )
            for p in low_parts.scalars().all():
                alerts.append({
                    "type": "low_stock", "severity": "warning",
                    "part": p.name, "part_number": p.part_number,
                    "current": p.current_quantity, "minimum": p.minimum_stock,
                    "message": f"{p.name} ({p.part_number}) is low on stock: {p.current_quantity} {p.unit} remaining"
                })

            oos_parts = await db.execute(
                select(SparePart).where(
                    and_(SparePart.is_active == True, SparePart.current_quantity <= 0)
                )
            )
            for p in oos_parts.scalars().all():
                alerts.append({
                    "type": "out_of_stock", "severity": "critical",
                    "part": p.name, "part_number": p.part_number,
                    "current": p.current_quantity, "minimum": p.minimum_stock,
                    "message": f"{p.name} ({p.part_number}) is OUT OF STOCK"
                })

            expired_parts = await db.execute(
                select(SparePart).where(
                    and_(SparePart.is_active == True,
                         SparePart.expiry_date != None,
                         SparePart.expiry_date < datetime.utcnow())
                )
            )
            for p in expired_parts.scalars().all():
                alerts.append({
                    "type": "expired", "severity": "critical",
                    "part": p.name, "part_number": p.part_number,
                    "message": f"{p.name} ({p.part_number}) has expired on {p.expiry_date.strftime('%Y-%m-%d')}"
                })

            return {
                "kpis": {
                    "total_parts": total_parts,
                    "available_stock": round(float(available_stock), 2),
                    "low_stock_items": low_stock_items,
                    "out_of_stock": out_of_stock,
                    "total_inventory_value": total_value,
                    "parts_issued_today": parts_issued_today,
                    "parts_returned_today": parts_returned_today,
                    "pending_purchase_items": pending_purchase,
                },
                "alerts": alerts,
            }
        except Exception as e:
            logger.warning(f"Error in inventory dashboard: {e}")
            return {"kpis": {}, "alerts": []}

    # ==================== SPARE PARTS CRUD ====================

    @staticmethod
    async def get_parts(db: AsyncSession, page: int = 1, page_size: int = 50,
                        search: str = None, category: str = None, supplier: str = None,
                        stock_status: str = None, location: str = None,
                        sort_by: str = "name", sort_dir: str = "asc") -> Dict[str, Any]:
        try:
            query = select(SparePart).where(SparePart.is_active == True)
            conditions = []
            if search:
                conditions.append(or_(
                    SparePart.part_number.ilike(f"%{search}%"),
                    SparePart.name.ilike(f"%{search}%"),
                    SparePart.brand.ilike(f"%{search}%"),
                    SparePart.supplier.ilike(f"%{search}%")
                ))
            if category:
                conditions.append(SparePart.category == category)
            if supplier:
                conditions.append(SparePart.supplier.ilike(f"%{supplier}%"))
            if location:
                conditions.append(SparePart.storage_location.ilike(f"%{location}%"))
            if stock_status == "in_stock":
                conditions.append(SparePart.current_quantity > SparePart.minimum_stock)
            elif stock_status == "low_stock":
                conditions.append(and_(
                    SparePart.current_quantity <= SparePart.minimum_stock,
                    SparePart.current_quantity > 0
                ))
            elif stock_status == "out_of_stock":
                conditions.append(SparePart.current_quantity <= 0)
            elif stock_status == "overstocked":
                conditions.append(SparePart.current_quantity > SparePart.maximum_stock)
            if conditions:
                query = query.where(and_(*conditions))

            # Sorting
            sort_col = getattr(SparePart, sort_by, SparePart.name)
            if sort_dir == "desc":
                query = query.order_by(desc(sort_col))
            else:
                query = query.order_by(sort_col)

            total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
            query = query.limit(page_size).offset((page - 1) * page_size)
            result = await db.execute(query)
            parts = result.scalars().all()

            items = []
            for p in parts:
                stock_status_val = "in_stock"
                if p.current_quantity <= 0:
                    stock_status_val = "out_of_stock"
                elif p.current_quantity <= p.minimum_stock:
                    stock_status_val = "low_stock"
                elif p.current_quantity > p.maximum_stock:
                    stock_status_val = "overstocked"

                items.append({
                    "id": p.id, "part_number": p.part_number, "name": p.name,
                    "description": p.description, "category": p.category,
                    "brand": p.brand, "compatible_vehicle_category": p.compatible_vehicle_category,
                    "unit": p.unit,
                    "current_quantity": p.current_quantity,
                    "minimum_stock": p.minimum_stock, "maximum_stock": p.maximum_stock,
                    "unit_cost": p.unit_cost,
                    "total_value": round(p.current_quantity * p.unit_cost, 2),
                    "storage_location": p.storage_location,
                    "supplier": p.supplier, "supplier_contact": p.supplier_contact,
                    "status": p.status, "stock_status": stock_status_val,
                    "expiry_date": p.expiry_date.isoformat() if p.expiry_date else None,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                    "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                })

            return {
                "items": items, "total": total, "page": page, "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
            }
        except Exception as e:
            logger.warning(f"Error in get_parts: {e}")
            return {"items": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 0}

    @staticmethod
    async def get_part_detail(db: AsyncSession, part_id: int) -> Optional[Dict[str, Any]]:
        try:
            result = await db.execute(select(SparePart).where(SparePart.id == part_id))
            p = result.scalar_one_or_none()
            if not p:
                return None

            # Recent movements
            mov_result = await db.execute(
                select(StockMovement).where(StockMovement.spare_part_id == part_id)
                .order_by(desc(StockMovement.created_at)).limit(20)
            )
            movements = []
            for m in mov_result.scalars().all():
                movements.append({
                    "id": m.id, "movement_type": m.movement_type,
                    "quantity": m.quantity, "reference_type": m.reference_type,
                    "reference_id": m.reference_id, "reference_number": m.reference_number,
                    "unit_cost": m.unit_cost, "total_cost": m.total_cost,
                    "stock_before": m.stock_before, "stock_after": m.stock_after,
                    "reason": m.reason, "performed_by": m.performed_by,
                    "from_location": m.from_location, "to_location": m.to_location,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                })

            stock_status_val = "in_stock"
            if p.current_quantity <= 0:
                stock_status_val = "out_of_stock"
            elif p.current_quantity <= p.minimum_stock:
                stock_status_val = "low_stock"
            elif p.current_quantity > p.maximum_stock:
                stock_status_val = "overstocked"

            return {
                "id": p.id, "part_number": p.part_number, "name": p.name,
                "description": p.description, "category": p.category,
                "brand": p.brand, "compatible_vehicle_category": p.compatible_vehicle_category,
                "unit": p.unit,
                "current_quantity": p.current_quantity,
                "minimum_stock": p.minimum_stock, "maximum_stock": p.maximum_stock,
                "unit_cost": p.unit_cost,
                "total_value": round(p.current_quantity * p.unit_cost, 2),
                "storage_location": p.storage_location,
                "supplier": p.supplier, "supplier_contact": p.supplier_contact,
                "status": p.status, "stock_status": stock_status_val,
                "expiry_date": p.expiry_date.isoformat() if p.expiry_date else None,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                "recent_movements": movements,
            }
        except Exception as e:
            logger.warning(f"Error in get_part_detail: {e}")
            return None

    @staticmethod
    async def create_part(db: AsyncSession, data: Dict[str, Any], created_by: int = None) -> SparePart:
        try:
            existing = await db.execute(
                select(SparePart).where(SparePart.part_number == data.get("part_number"))
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"Part number {data.get('part_number')} already exists")

            part = SparePart(
                part_number=data["part_number"],
                name=data["name"],
                description=data.get("description", ""),
                category=data.get("category", "other"),
                brand=data.get("brand", ""),
                compatible_vehicle_category=data.get("compatible_vehicle_category", "all"),
                unit=data.get("unit", "pcs"),
                current_quantity=data.get("current_quantity", 0),
                minimum_stock=data.get("minimum_stock", 0),
                maximum_stock=data.get("maximum_stock", 100),
                unit_cost=data.get("unit_cost", 0),
                storage_location=data.get("storage_location", ""),
                supplier=data.get("supplier", ""),
                supplier_contact=data.get("supplier_contact", ""),
                status=data.get("status", "active"),
                expiry_date=datetime.fromisoformat(data["expiry_date"]) if data.get("expiry_date") else None,
            )
            db.add(part)
            await db.commit()
            await db.refresh(part)

            # Create initial stock movement if quantity > 0
            if part.current_quantity > 0:
                await InventoryService._add_movement(db, part.id, "stock_in", part.current_quantity,
                    reference_type="initial", reason="Initial stock entry",
                    unit_cost=part.unit_cost, stock_before=0, stock_after=part.current_quantity,
                    performed_by=f"User {created_by}")

            return part
        except Exception as e:
            logger.warning(f"Error creating part: {e}")
            raise

    @staticmethod
    async def update_part(db: AsyncSession, part_id: int, data: Dict[str, Any]) -> Optional[SparePart]:
        try:
            result = await db.execute(select(SparePart).where(SparePart.id == part_id))
            part = result.scalar_one_or_none()
            if not part:
                return None
            for field in ["name", "description", "category", "brand", "compatible_vehicle_category",
                          "unit", "minimum_stock", "maximum_stock", "unit_cost",
                          "storage_location", "supplier", "supplier_contact", "status"]:
                if field in data:
                    setattr(part, field, data[field])
            if "expiry_date" in data:
                part.expiry_date = datetime.fromisoformat(data["expiry_date"]) if data["expiry_date"] else None
            part.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(part)
            return part
        except Exception as e:
            logger.warning(f"Error updating part: {e}")
            raise

    @staticmethod
    async def delete_part(db: AsyncSession, part_id: int) -> bool:
        try:
            result = await db.execute(select(SparePart).where(SparePart.id == part_id))
            part = result.scalar_one_or_none()
            if not part:
                return False
            part.is_active = False
            part.status = "discontinued"
            await db.commit()
            return True
        except Exception as e:
            logger.warning(f"Error deleting part: {e}")
            raise

    # ==================== STOCK MOVEMENTS ====================

    @staticmethod
    async def stock_in(db: AsyncSession, part_id: int, data: Dict[str, Any], performed_by: str = None) -> Dict[str, Any]:
        try:
            result = await db.execute(select(SparePart).where(SparePart.id == part_id))
            part = result.scalar_one_or_none()
            if not part:
                raise ValueError("Part not found")

            quantity = data.get("quantity", 0)
            if quantity <= 0:
                raise ValueError("Quantity must be positive")

            unit_cost = data.get("unit_cost", part.unit_cost)
            stock_before = part.current_quantity
            part.current_quantity += quantity
            part.unit_cost = unit_cost
            part.updated_at = datetime.utcnow()

            await InventoryService._add_movement(
                db, part_id, "stock_in", quantity,
                reference_type=data.get("reference_type", "purchase"),
                reference_number=data.get("reference_number"),
                unit_cost=unit_cost, total_cost=round(quantity * unit_cost, 2),
                stock_before=stock_before, stock_after=part.current_quantity,
                reason=data.get("reason", "Stock in"),
                to_location=part.storage_location,
                performed_by=performed_by
            )

            await db.commit()
            return {"part_id": part_id, "quantity_added": quantity, "new_stock": part.current_quantity}
        except Exception as e:
            logger.warning(f"Error in stock_in: {e}")
            raise

    @staticmethod
    async def stock_out(db: AsyncSession, part_id: int, data: Dict[str, Any], performed_by: str = None) -> Dict[str, Any]:
        try:
            result = await db.execute(select(SparePart).where(SparePart.id == part_id))
            part = result.scalar_one_or_none()
            if not part:
                raise ValueError("Part not found")

            quantity = data.get("quantity", 0)
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
            if part.current_quantity < quantity:
                raise ValueError(f"Insufficient stock. Available: {part.current_quantity} {part.unit}, Requested: {quantity}")

            stock_before = part.current_quantity
            part.current_quantity -= quantity
            part.updated_at = datetime.utcnow()

            await InventoryService._add_movement(
                db, part_id, "stock_out", -quantity,
                reference_type=data.get("reference_type", "manual"),
                reference_id=data.get("reference_id"),
                reference_number=data.get("reference_number"),
                unit_cost=part.unit_cost, total_cost=round(quantity * part.unit_cost, 2),
                stock_before=stock_before, stock_after=part.current_quantity,
                reason=data.get("reason", "Stock out"),
                from_location=part.storage_location,
                performed_by=performed_by
            )

            await db.commit()
            return {"part_id": part_id, "quantity_removed": quantity, "new_stock": part.current_quantity}
        except Exception as e:
            logger.warning(f"Error in stock_out: {e}")
            raise

    @staticmethod
    async def adjust_stock(db: AsyncSession, part_id: int, data: Dict[str, Any], performed_by: str = None) -> Dict[str, Any]:
        try:
            result = await db.execute(select(SparePart).where(SparePart.id == part_id))
            part = result.scalar_one_or_none()
            if not part:
                raise ValueError("Part not found")

            new_quantity = data.get("new_quantity")
            if new_quantity is None:
                raise ValueError("new_quantity is required")
            if new_quantity < 0:
                raise ValueError("Stock cannot be negative")

            stock_before = part.current_quantity
            diff = new_quantity - stock_before
            part.current_quantity = new_quantity
            part.updated_at = datetime.utcnow()

            await InventoryService._add_movement(
                db, part_id, "adjustment", diff,
                reference_type="manual",
                unit_cost=part.unit_cost, total_cost=round(abs(diff) * part.unit_cost, 2),
                stock_before=stock_before, stock_after=new_quantity,
                reason=data.get("reason", "Stock adjustment"),
                performed_by=performed_by
            )

            await db.commit()
            return {"part_id": part_id, "adjusted": diff, "new_stock": part.current_quantity}
        except Exception as e:
            logger.warning(f"Error in adjust_stock: {e}")
            raise

    @staticmethod
    async def transfer_stock(db: AsyncSession, part_id: int, data: Dict[str, Any], performed_by: str = None) -> Dict[str, Any]:
        try:
            result = await db.execute(select(SparePart).where(SparePart.id == part_id))
            part = result.scalar_one_or_none()
            if not part:
                raise ValueError("Part not found")

            quantity = data.get("quantity", 0)
            to_location = data.get("to_location", "")
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
            if part.current_quantity < quantity:
                raise ValueError(f"Insufficient stock. Available: {part.current_quantity}")

            stock_before = part.current_quantity
            part.current_quantity -= quantity
            part.storage_location = to_location
            part.updated_at = datetime.utcnow()

            await InventoryService._add_movement(
                db, part_id, "transfer", -quantity,
                reference_type="transfer",
                unit_cost=part.unit_cost, total_cost=round(quantity * part.unit_cost, 2),
                stock_before=stock_before, stock_after=part.current_quantity,
                from_location=stock_before if False else data.get("from_location", part.storage_location),
                to_location=to_location,
                reason=data.get("reason", "Transfer"),
                performed_by=performed_by
            )

            # Create stock_in at destination (creates new movement for receiving)
            part.current_quantity += quantity
            await InventoryService._add_movement(
                db, part_id, "stock_in", quantity,
                reference_type="transfer",
                unit_cost=part.unit_cost, total_cost=round(quantity * part.unit_cost, 2),
                stock_before=part.current_quantity - quantity, stock_after=part.current_quantity,
                to_location=to_location,
                reason=f"Received from transfer",
                performed_by=performed_by
            )

            await db.commit()
            return {"part_id": part_id, "transferred": quantity, "to_location": to_location, "new_stock": part.current_quantity}
        except Exception as e:
            logger.warning(f"Error in transfer_stock: {e}")
            raise

    @staticmethod
    async def return_stock(db: AsyncSession, part_id: int, data: Dict[str, Any], performed_by: str = None) -> Dict[str, Any]:
        try:
            result = await db.execute(select(SparePart).where(SparePart.id == part_id))
            part = result.scalar_one_or_none()
            if not part:
                raise ValueError("Part not found")

            quantity = data.get("quantity", 0)
            if quantity <= 0:
                raise ValueError("Quantity must be positive")

            stock_before = part.current_quantity
            part.current_quantity += quantity
            part.updated_at = datetime.utcnow()

            await InventoryService._add_movement(
                db, part_id, "return", quantity,
                reference_type=data.get("reference_type", "workshop_return"),
                reference_id=data.get("reference_id"),
                reference_number=data.get("reference_number"),
                unit_cost=part.unit_cost, total_cost=round(quantity * part.unit_cost, 2),
                stock_before=stock_before, stock_after=part.current_quantity,
                reason=data.get("reason", "Parts returned from workshop"),
                to_location=part.storage_location,
                performed_by=performed_by
            )

            await db.commit()
            return {"part_id": part_id, "quantity_returned": quantity, "new_stock": part.current_quantity}
        except Exception as e:
            logger.warning(f"Error in return_stock: {e}")
            raise

    @staticmethod
    async def scrap_stock(db: AsyncSession, part_id: int, data: Dict[str, Any], performed_by: str = None) -> Dict[str, Any]:
        try:
            result = await db.execute(select(SparePart).where(SparePart.id == part_id))
            part = result.scalar_one_or_none()
            if not part:
                raise ValueError("Part not found")

            quantity = data.get("quantity", 0)
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
            if part.current_quantity < quantity:
                raise ValueError(f"Insufficient stock. Available: {part.current_quantity}")

            stock_before = part.current_quantity
            part.current_quantity -= quantity
            part.updated_at = datetime.utcnow()

            await InventoryService._add_movement(
                db, part_id, "scrap", -quantity,
                reference_type="scrap",
                unit_cost=part.unit_cost, total_cost=round(quantity * part.unit_cost, 2),
                stock_before=stock_before, stock_after=part.current_quantity,
                reason=data.get("reason", "Scrapped"),
                performed_by=performed_by
            )

            await db.commit()
            return {"part_id": part_id, "quantity_scrapped": quantity, "new_stock": part.current_quantity}
        except Exception as e:
            logger.warning(f"Error in scrap_stock: {e}")
            raise

    # ==================== WORKSHOP INTEGRATION ====================

    @staticmethod
    async def issue_parts_to_job(db: AsyncSession, job_id: int, parts: List[Dict[str, Any]], issued_by: str = None) -> Dict[str, Any]:
        """Issue spare parts to a workshop job — deducts inventory, updates job cost"""
        try:
            result = await db.execute(select(WorkshopJob).where(WorkshopJob.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                raise ValueError("Job not found")

            issued = []
            errors = []
            total_parts_cost = 0

            for item in parts:
                part_id = item.get("part_id")
                quantity = item.get("quantity", 0)
                if not part_id or quantity <= 0:
                    errors.append(f"Invalid part data: {item}")
                    continue

                part_result = await db.execute(select(SparePart).where(SparePart.id == part_id))
                part = part_result.scalar_one_or_none()
                if not part:
                    errors.append(f"Part {part_id} not found")
                    continue

                if part.current_quantity < quantity:
                    errors.append(f"Insufficient stock for {part.name}: available {part.current_quantity}, requested {quantity}")
                    continue

                stock_before = part.current_quantity
                part.current_quantity -= quantity
                part.updated_at = datetime.utcnow()

                part_cost = round(quantity * part.unit_cost, 2)
                total_parts_cost += part_cost

                await InventoryService._add_movement(
                    db, part_id, "stock_out", -quantity,
                    reference_type="workshop_job",
                    reference_id=job_id,
                    reference_number=job.job_number,
                    unit_cost=part.unit_cost, total_cost=part_cost,
                    stock_before=stock_before, stock_after=part.current_quantity,
                    reason=f"Issued for job {job.job_number}",
                    from_location=part.storage_location,
                    performed_by=issued_by
                )

                issued.append({
                    "part_id": part_id, "part_number": part.part_number,
                    "name": part.name, "quantity": quantity,
                    "unit_cost": part.unit_cost, "total_cost": part_cost
                })

            # Update job parts_cost and total_cost
            existing_parts = job.parts_used or []
            existing_parts.extend(issued)
            job.parts_used = existing_parts
            job.parts_cost = (job.parts_cost or 0) + total_parts_cost
            job.total_cost = (job.labour_cost or 0) + job.parts_cost + (job.misc_cost or 0)
            job.updated_at = datetime.utcnow()

            # Add timeline event
            if issued:
                note = JobNote(
                    job_id=job_id, note_type="parts_issued",
                    content=f"Parts issued: {len(issued)} items, total cost Rs. {total_parts_cost:,.2f}",
                    author=issued_by
                )
                db.add(note)

            await db.commit()

            return {
                "issued": issued, "errors": errors,
                "total_parts_cost": total_parts_cost,
                "new_job_parts_cost": job.parts_cost,
                "new_job_total_cost": job.total_cost,
            }
        except Exception as e:
            logger.warning(f"Error issuing parts to job: {e}")
            raise

    @staticmethod
    async def return_parts_from_job(db: AsyncSession, job_id: int, parts: List[Dict[str, Any]], returned_by: str = None) -> Dict[str, Any]:
        """Return unused parts from a workshop job back to inventory"""
        try:
            result = await db.execute(select(WorkshopJob).where(WorkshopJob.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                raise ValueError("Job not found")

            returned = []
            errors = []
            total_returned_cost = 0

            for item in parts:
                part_id = item.get("part_id")
                quantity = item.get("quantity", 0)
                if not part_id or quantity <= 0:
                    errors.append(f"Invalid part data: {item}")
                    continue

                part_result = await db.execute(select(SparePart).where(SparePart.id == part_id))
                part = part_result.scalar_one_or_none()
                if not part:
                    errors.append(f"Part {part_id} not found")
                    continue

                stock_before = part.current_quantity
                part.current_quantity += quantity
                part.updated_at = datetime.utcnow()

                part_cost = round(quantity * part.unit_cost, 2)
                total_returned_cost += part_cost

                await InventoryService._add_movement(
                    db, part_id, "return", quantity,
                    reference_type="workshop_return",
                    reference_id=job_id,
                    reference_number=job.job_number,
                    unit_cost=part.unit_cost, total_cost=part_cost,
                    stock_before=stock_before, stock_after=part.current_quantity,
                    reason=f"Returned from job {job.job_number}",
                    to_location=part.storage_location,
                    performed_by=returned_by
                )

                returned.append({
                    "part_id": part_id, "part_number": part.part_number,
                    "name": part.name, "quantity": quantity,
                    "unit_cost": part.unit_cost, "total_cost": part_cost
                })

            # Update job cost
            job.parts_cost = max(0, (job.parts_cost or 0) - total_returned_cost)
            job.total_cost = (job.labour_cost or 0) + job.parts_cost + (job.misc_cost or 0)
            job.updated_at = datetime.utcnow()

            if returned:
                note = JobNote(
                    job_id=job_id, note_type="parts_returned",
                    content=f"Parts returned: {len(returned)} items, credit Rs. {total_returned_cost:,.2f}",
                    author=returned_by
                )
                db.add(note)

            await db.commit()

            return {
                "returned": returned, "errors": errors,
                "total_returned_cost": total_returned_cost,
                "new_job_parts_cost": job.parts_cost,
                "new_job_total_cost": job.total_cost,
            }
        except Exception as e:
            logger.warning(f"Error returning parts from job: {e}")
            raise

    @staticmethod
    async def get_job_parts(db: AsyncSession, job_id: int) -> List[Dict[str, Any]]:
        """Get parts issued to a specific job"""
        try:
            result = await db.execute(
                select(StockMovement).where(
                    and_(StockMovement.reference_type == "workshop_job",
                         StockMovement.reference_id == job_id)
                ).order_by(desc(StockMovement.created_at))
            )
            parts = []
            for m in result.scalars().all():
                parts.append({
                    "id": m.id, "spare_part_id": m.spare_part_id,
                    "quantity": abs(m.quantity), "unit_cost": m.unit_cost,
                    "total_cost": m.total_cost,
                    "performed_by": m.performed_by,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                })
            return parts
        except Exception as e:
            logger.warning(f"Error getting job parts: {e}")
            return []

    # ==================== MOVEMENTS ====================

    @staticmethod
    async def get_movements(db: AsyncSession, page: int = 1, page_size: int = 50,
                            spare_part_id: int = None, movement_type: str = None,
                            search: str = None) -> Dict[str, Any]:
        try:
            query = select(StockMovement)
            conditions = []
            if spare_part_id:
                conditions.append(StockMovement.spare_part_id == spare_part_id)
            if movement_type:
                conditions.append(StockMovement.movement_type == movement_type)
            if search:
                conditions.append(or_(
                    StockMovement.reference_number.ilike(f"%{search}%"),
                    StockMovement.reason.ilike(f"%{search}%"),
                    StockMovement.performed_by.ilike(f"%{search}%")
                ))
            if conditions:
                query = query.where(and_(*conditions))

            total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
            query = query.order_by(desc(StockMovement.created_at)).limit(page_size).offset((page - 1) * page_size)
            result = await db.execute(query)
            movements = result.scalars().all()

            items = []
            for m in movements:
                part_name = None
                part_number = None
                try:
                    p_result = await db.execute(select(SparePart).where(SparePart.id == m.spare_part_id))
                    part = p_result.scalar_one_or_none()
                    if part:
                        part_name = part.name
                        part_number = part.part_number
                except Exception:
                    pass

                items.append({
                    "id": m.id, "spare_part_id": m.spare_part_id,
                    "part_name": part_name, "part_number": part_number,
                    "movement_type": m.movement_type, "quantity": m.quantity,
                    "reference_type": m.reference_type,
                    "reference_id": m.reference_id,
                    "reference_number": m.reference_number,
                    "unit_cost": m.unit_cost, "total_cost": m.total_cost,
                    "stock_before": m.stock_before, "stock_after": m.stock_after,
                    "reason": m.reason, "performed_by": m.performed_by,
                    "from_location": m.from_location, "to_location": m.to_location,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                })

            return {
                "items": items, "total": total, "page": page, "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
            }
        except Exception as e:
            logger.warning(f"Error in get_movements: {e}")
            return {"items": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 0}

    # ==================== REPORTS ====================

    @staticmethod
    async def get_stock_ledger(db: AsyncSession) -> List[Dict[str, Any]]:
        try:
            result = await db.execute(
                select(SparePart).where(SparePart.is_active == True).order_by(SparePart.part_number)
            )
            ledger = []
            for p in result.scalars().all():
                ledger.append({
                    "part_id": p.id, "part_number": p.part_number, "name": p.name,
                    "category": p.category, "unit": p.unit,
                    "opening_stock": p.maximum_stock,
                    "current_stock": p.current_quantity,
                    "unit_cost": p.unit_cost,
                    "total_value": round(p.current_quantity * p.unit_cost, 2),
                    "minimum_stock": p.minimum_stock,
                    "maximum_stock": p.maximum_stock,
                    "status": "OK" if p.current_quantity > p.minimum_stock else ("LOW" if p.current_quantity > 0 else "OUT"),
                })
            return ledger
        except Exception as e:
            logger.warning(f"Error in stock ledger: {e}")
            return []

    @staticmethod
    async def get_consumption_report(db: AsyncSession, days: int = 30) -> List[Dict[str, Any]]:
        try:
            since = datetime.utcnow() - timedelta(days=days)
            result = await db.execute(
                select(StockMovement.spare_part_id, func.sum(func.abs(StockMovement.quantity)).label("total_consumed"),
                       func.sum(StockMovement.total_cost).label("total_cost"))
                .where(and_(StockMovement.movement_type == "stock_out",
                            StockMovement.created_at >= since))
                .group_by(StockMovement.spare_part_id)
                .order_by(desc("total_cost"))
            )
            report = []
            for row in result.all():
                part_name = None
                part_number = None
                try:
                    p_result = await db.execute(select(SparePart).where(SparePart.id == row.spare_part_id))
                    part = p_result.scalar_one_or_none()
                    if part:
                        part_name = part.name
                        part_number = part.part_number
                except Exception:
                    pass
                report.append({
                    "part_id": row.spare_part_id,
                    "part_name": part_name, "part_number": part_number,
                    "total_consumed": round(float(row.total_consumed or 0), 2),
                    "total_cost": round(float(row.total_cost or 0), 2),
                })
            return report
        except Exception as e:
            logger.warning(f"Error in consumption report: {e}")
            return []

    @staticmethod
    async def get_low_stock_report(db: AsyncSession) -> List[Dict[str, Any]]:
        try:
            result = await db.execute(
                select(SparePart).where(
                    and_(SparePart.is_active == True,
                         SparePart.current_quantity <= SparePart.minimum_stock)
                ).order_by(SparePart.current_quantity)
            )
            report = []
            for p in result.scalars().all():
                deficit = max(0, p.minimum_stock - p.current_quantity)
                report.append({
                    "part_id": p.id, "part_number": p.part_number, "name": p.name,
                    "category": p.category, "unit": p.unit,
                    "current_stock": p.current_quantity,
                    "minimum_stock": p.minimum_stock,
                    "deficit": deficit,
                    "reorder_cost": round(deficit * p.unit_cost, 2),
                    "supplier": p.supplier,
                    "status": "OUT_OF_STOCK" if p.current_quantity <= 0 else "LOW_STOCK",
                })
            return report
        except Exception as e:
            logger.warning(f"Error in low stock report: {e}")
            return []

    @staticmethod
    async def get_workshop_parts_usage(db: AsyncSession, days: int = 30) -> List[Dict[str, Any]]:
        try:
            since = datetime.utcnow() - timedelta(days=days)
            result = await db.execute(
                select(StockMovement.reference_number, StockMovement.reference_id,
                       func.count().label("parts_count"),
                       func.sum(StockMovement.total_cost).label("total_cost"))
                .where(and_(StockMovement.reference_type == "workshop_job",
                            StockMovement.created_at >= since))
                .group_by(StockMovement.reference_number, StockMovement.reference_id)
                .order_by(desc("total_cost"))
            )
            usage = []
            for row in result.all():
                usage.append({
                    "job_id": row.reference_id, "job_number": row.reference_number,
                    "parts_count": row.parts_count,
                    "total_parts_cost": round(float(row.total_cost or 0), 2),
                })
            return usage
        except Exception as e:
            logger.warning(f"Error in workshop parts usage: {e}")
            return []

    # ==================== HELPERS ====================

    @staticmethod
    async def _add_movement(db: AsyncSession, spare_part_id: int, movement_type: str,
                            quantity: float, reference_type: str = None,
                            reference_id: int = None, reference_number: str = None,
                            unit_cost: float = 0, total_cost: float = 0,
                            stock_before: float = 0, stock_after: float = 0,
                            reason: str = None, from_location: str = None,
                            to_location: str = None, performed_by: str = None):
        try:
            movement = StockMovement(
                spare_part_id=spare_part_id,
                movement_type=movement_type,
                quantity=quantity,
                reference_type=reference_type,
                reference_id=reference_id,
                reference_number=reference_number,
                unit_cost=unit_cost, total_cost=total_cost,
                stock_before=stock_before, stock_after=stock_after,
                reason=reason, from_location=from_location,
                to_location=to_location, performed_by=performed_by,
            )
            db.add(movement)
        except Exception as e:
            logger.warning(f"Error adding movement: {e}")


inventory_service = InventoryService()
