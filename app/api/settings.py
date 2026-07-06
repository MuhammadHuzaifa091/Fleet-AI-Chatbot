from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.api.auth import get_current_user
from app.models.traccar import User
from typing import Dict, Any, List

router = APIRouter()

@router.get("/alert-preferences")
async def get_alert_preferences(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    user_id = current_user.get("id")
    if user_id == 0 or user_id is None: # Demo admin or unknown
         # Demo accounts don't persist in DB the same way, but let's try to fetch if exists
         pass
    
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        # Fallback for demo users or if user not in local DB yet
        return {"preferences": {}}

    attrs = user.attributes or {}
    return {"preferences": attrs.get("alertPreferences", {})}

@router.post("/alert-preferences")
async def update_alert_preferences(
    preferences: Dict[str, bool],
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    user_id = current_user.get("id")
    if user_id == 0 or user_id is None:
        raise HTTPException(status_code=403, detail="Preferences cannot be saved for demo accounts")

    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found in local database")

    attrs = user.attributes or {}
    attrs["alertPreferences"] = preferences
    user.attributes = attrs
    db.add(user)
    await db.commit()
    
    return {"status": "success", "preferences": attrs["alertPreferences"]}
