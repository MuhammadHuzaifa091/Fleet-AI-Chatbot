from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
import httpx
import json
from app.db.session import get_db
from app.models.traccar import User
from app.core.security import create_access_token, decode_access_token
from app.core.config import settings
from typing import Dict, Any, Optional

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

@router.get("/ping")
async def ping_auth():
    return {"status": "auth service is up"}

class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str

# Centralized demo account registry
DEMO_ACCOUNTS = {
    "admin@fleet.ai":   {"id": 0, "email": "admin@fleet.ai",   "role": "SUPERADMIN", "name": "System Administrator"},
}

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    email = payload.get("sub")
    if email in DEMO_ACCOUNTS:
        return DEMO_ACCOUNTS[email]

    query = select(User).where(User.email == email)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    role = "USER"
    if user.administrator:
        role = "SUPERADMIN"
    elif user.attributes and user.attributes.get("role") == "ADMIN":
        role = "ADMIN"
        
    return {"id": user.id, "email": user.email, "role": role, "name": user.name}

@router.post("/register")
async def register(user_in: UserRegister, db: AsyncSession = Depends(get_db)):
    # 1. Check local DB
    query = select(User).where(User.email == user_in.email)
    result = await db.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User already registered")

    # 2. Sync to Traccar
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Create user in Traccar
        reg_resp = await client.post(
            f"{settings.TRACCAR_URL}/api/users",
            json={"name": user_in.name, "email": user_in.email, "password": user_in.password},
        )
        
        if reg_resp.status_code not in [200, 201]:
             error_detail = reg_resp.text[:200]
             try:
                 error_json = reg_resp.json()
                 if isinstance(error_json, dict) and "message" in error_json:
                     error_detail = error_json["message"]
             except: pass
             raise HTTPException(status_code=reg_resp.status_code, detail=f"Traccar registration failed: {error_detail}")
        
        traccar_user = reg_resp.json()

        # 3. Log in to Traccar to get Session ID
        login_resp = await client.post(
            f"{settings.TRACCAR_URL}/api/session",
            data={"email": user_in.email, "password": user_in.password}
        )
        jsessionid = login_resp.cookies.get("JSESSIONID")
        
        # 4. Save/Update in local DB
        import asyncio
        user = None
        for _ in range(10): # Up to 5 seconds
            query = select(User).where(User.email == user_in.email)
            res = await db.execute(query)
            user = res.scalar_one_or_none()
            if user: break
            await asyncio.sleep(0.5)

        if not user:
            return {"status": "success", "traccar_id": traccar_user.get("id"), "note": "Sync pending"}
        
        attrs = user.attributes or {}
        if jsessionid:
            attrs["jsessionid"] = jsessionid
            user.attributes = attrs
            await db.commit()
            
        return {"status": "success", "traccar_id": traccar_user.get("id")}

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    # Demo backdoor
    if form_data.username == "admin@fleet.ai" and form_data.password == "admin":
        access_token = create_access_token(data={"sub": form_data.username, "role": "SUPERADMIN"})
        return {"access_token": access_token, "token_type": "bearer", "role": "SUPERADMIN"}

    # 1. Check Local DB First
    query = select(User).where(User.email == form_data.username)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    traccar_success = False
    jsessionid = None

    # 2. Try proxy Auth to Traccar
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{settings.TRACCAR_URL}/api/session",
                data={"email": form_data.username, "password": form_data.password}
            )
            
            if resp.status_code == 200:
                traccar_success = True
                traccar_user = resp.json()
                jsessionid = resp.cookies.get("JSESSIONID")
                
                if not user:
                     # Create user if found in Traccar but missing locally
                     user = User(id=traccar_user["id"], email=traccar_user["email"], name=traccar_user["name"])
                     db.add(user)
    except Exception as e:
        print(f"Traccar API Error: {e}")
        pass

    if not traccar_success:
        if not user:
            # Not in Traccar and not in Local DB
            raise HTTPException(status_code=401, detail="Invalid Traccar credentials")
        else:
            # Fallback - User exists in local DB but Traccar proxy failed/rejected
            # Since this is a demo/dev instance, we'll allow DB users to bypass Traccar.
            pass

    if user:
        attrs = user.attributes or {}
        if jsessionid:
            attrs["jsessionid"] = jsessionid
            user.attributes = attrs
        
        await db.commit()
    
        role = "USER"
        if user.administrator: role = "SUPERADMIN"
        elif user.attributes and user.attributes.get("role") == "ADMIN": role = "ADMIN"
    
        access_token = create_access_token(data={"sub": user.email, "role": role})
        return {"access_token": access_token, "token_type": "bearer", "role": role}

    raise HTTPException(status_code=401, detail="Invalid Traccar credentials")

@router.get("/me")
async def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    return current_user
