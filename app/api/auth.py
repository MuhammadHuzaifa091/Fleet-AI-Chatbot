from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
import httpx
import json
from loguru import logger
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
    "aima@admin.com":   {"id": 1, "email": "aima@admin.com",   "role": "ADMIN",      "name": "Fleet Manager"},
    "user@fleet.ai":    {"id": 2, "email": "user@fleet.ai",    "role": "USER",       "name": "Fleet Operator"},
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
    logger.info(f"Registration attempt for: {user_in.email}")
    # 1. Check local DB
    query = select(User).where(User.email == user_in.email)
    result = await db.execute(query)
    if result.scalar_one_or_none():
        logger.warning(f"Registration failed: User {user_in.email} already exists")
        raise HTTPException(status_code=400, detail="User already registered in Telemetrix")

    # 2. Sync to Traccar
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Create user in Traccar
            logger.info(f"Syncing registration to Traccar: {settings.TRACCAR_URL}")
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
                 logger.error(f"Traccar registration failed: {reg_resp.status_code} - {error_detail}")
                 raise HTTPException(status_code=reg_resp.status_code, detail=f"Traccar registration failed: {error_detail}")
            
            traccar_user = reg_resp.json()
            logger.info(f"Traccar registration success for {user_in.email}")

            # 3. Log in to Traccar to get Session ID
            login_resp = await client.post(
                f"{settings.TRACCAR_URL}/api/session",
                data={"email": user_in.email, "password": user_in.password}
            )
            jsessionid = login_resp.cookies.get("JSESSIONID")
            
            # 4. Save/Update in local DB
            # We wait a bit for Traccar to sync to its own DB if it's external, 
            # though usually it's immediate.
            import asyncio
            user = None
            for _ in range(5): 
                query = select(User).where(User.email == user_in.email)
                res = await db.execute(query)
                user = res.scalar_one_or_none()
                if user: break
                await asyncio.sleep(1)
            
            if not user:
                # If Traccar DB sync is slow, create it manually in local session if we share DB
                # But if we share DB, Traccar already created it.
                logger.warning(f"Local user record not found yet for {user_in.email}, creating placeholder")
                user = User(id=traccar_user["id"], email=user_in.email, name=user_in.name)
                db.add(user)
                await db.commit()
                await db.refresh(user)

            attrs = user.attributes or {}
            if jsessionid:
                attrs["jsessionid"] = jsessionid
                user.attributes = attrs
                await db.commit()
            
            # Create Telemetrix token
            access_token = create_access_token(data={"sub": user.email, "role": "USER"})
            return {"access_token": access_token, "token_type": "bearer", "role": "USER", "name": user.name}

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Internal Registration Error: {e}")
        raise HTTPException(status_code=500, detail=f"Registration node error: {str(e)}")

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    username = form_data.username.strip().lower()
    password = form_data.password
    logger.info(f"Login attempt for: '{username}'")
    
    # 0. Demo Backdoors
    if username in DEMO_ACCOUNTS and password == "admin":
        demo_user = DEMO_ACCOUNTS[username]
        access_token = create_access_token(data={"sub": username, "role": demo_user["role"]})
        logger.info(f"Demo login success for {username}")
        return {
            "access_token": access_token, 
            "token_type": "bearer", 
            "role": demo_user["role"], 
            "name": demo_user["name"]
        }

    # 1. Check Local DB First
    query = select(User).where(User.email == username)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    traccar_success = False
    jsessionid = None

    # 2. Try proxy Auth to Traccar
    try:
        logger.info(f"Attempting Traccar proxy auth for {form_data.username} at {settings.TRACCAR_URL}")
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.TRACCAR_URL}/api/session",
                data={"email": form_data.username, "password": form_data.password}
            )
            
            logger.info(f"Traccar response: {resp.status_code}")
            if resp.status_code == 200:
                traccar_success = True
                traccar_user = resp.json()
                jsessionid = resp.cookies.get("JSESSIONID")
                logger.info(f"Traccar login success for {form_data.username}")
                
                if not user:
                     logger.info(f"Creating missing local user for {form_data.username}")
                     user = User(id=traccar_user["id"], email=traccar_user["email"], name=traccar_user["name"])
                     db.add(user)
            else:
                logger.warning(f"Traccar login failed for {form_data.username}: {resp.status_code} - {resp.text[:100]}")
    except Exception as e:
        logger.error(f"Traccar API Error for {form_data.username}: {e}")
        pass

    if not traccar_success:
        logger.warning(f"Login failed for {form_data.username}: Traccar authentication failed.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user:
        try:
            attrs = user.attributes or {}
            if jsessionid:
                attrs["jsessionid"] = jsessionid
                user.attributes = attrs
            
            await db.commit()
            logger.info(f"Session updated for {user.email}")
        except Exception as e:
            logger.error(f"Database error during login commit for {user.email}: {e}")
            # Even if commit fails, we might want to let them in if it's just attributes
            await db.rollback()
    
        role = "USER"
        if user.administrator: role = "SUPERADMIN"
        elif user.attributes and user.attributes.get("role") == "ADMIN": role = "ADMIN"
    
        access_token = create_access_token(data={"sub": user.email, "role": role})
        logger.info(f"Login successful for {user.email} (Role: {role})")
        return {"access_token": access_token, "token_type": "bearer", "role": role, "name": user.name}

    raise HTTPException(status_code=401, detail="Authentication failed")

@router.get("/me")
async def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    return current_user
