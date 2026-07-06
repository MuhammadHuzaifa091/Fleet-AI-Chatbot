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
        raise HTTPException(status_code=400, detail="User already registered in AI-Telematics")

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
            import asyncio
            user = None
            for _ in range(5): 
                query = select(User).where(User.email == user_in.email)
                res = await db.execute(query)
                user = res.scalar_one_or_none()
                if user: break
                await asyncio.sleep(1)
            
            if not user:
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
            
            # Create AI-Telematics token
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
    logger.info(f"[LOGIN_ATTEMPT] Username: '{username}'")
    
    # 0. Demo Backdoors
    if username in DEMO_ACCOUNTS and password == "admin":
        logger.info(f"[DEMO_BACKDOOR_MATCHED] Account: {username}")
        demo_user = DEMO_ACCOUNTS[username]
        access_token = create_access_token(data={"sub": username, "role": demo_user["role"]})
        logger.info(f"[TOKEN_GENERATED] Success: true | Account: {username}")
        return {
            "access_token": access_token, 
            "token_type": "bearer", 
            "role": demo_user["role"], 
            "name": demo_user["name"]
        }

    # 1. Check Local DB First
    logger.debug(f"[LOCAL_DB_LOOKUP] Querying User: {username}")
    query = select(User).where(User.email == username)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if user:
        logger.info(f"[USER_RECORD_FOUND] Local ID: {user.id}")
    else:
        logger.info(f"[USER_RECORD_NOT_FOUND] Local DB: {username}")

    traccar_success = False
    traccar_reachable = False
    jsessionid = None

    # 2. Try proxy Auth to Traccar
    try:
        logger.info(f"[TRACCAR_PROXY_AUTH_START] URL: {settings.TRACCAR_URL} | User: {username}")
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.post(
                f"{settings.TRACCAR_URL}/api/session",
                data={"email": form_data.username, "password": form_data.password}
            )
            traccar_reachable = True
            logger.info(f"[TRACCAR_RESPONSE] Status: {resp.status_code}")
            
            if resp.status_code == 200:
                traccar_success = True
                jsessionid = resp.cookies.get("JSESSIONID")
                logger.info(f"[TRACCAR_AUTH_SUCCESS] Session Created: {bool(jsessionid)}")
            else:
                logger.warning(f"[TRACCAR_AUTH_FAILED] Status: {resp.status_code} | Reason: {resp.text[:100]}")
    except Exception as e:
        logger.warning(f"[TRACCAR_PROXY_UNREACHABLE] {settings.TRACCAR_URL} — {str(e)}")

    if traccar_success:
        if not user:
            logger.info(f"[SYNCING_NEW_USER] Creating local record for {username}")
            user = User(email=username, name=username.split('@')[0], attributes={"role": "USER"})
            db.add(user)
            await db.commit()
            await db.refresh(user)

        role = "USER"
        if user.administrator:
            role = "SUPERADMIN"
        elif user.attributes and user.attributes.get("role") == "ADMIN":
            role = "ADMIN"
            
        access_token = create_access_token(data={"sub": user.email, "role": role})
        logger.info(f"[AUTH_SUCCESS] Token Issued for {username} | Role: {role}")
        return {
            "access_token": access_token, 
            "token_type": "bearer", 
            "role": role, 
            "name": user.name
        }

    # 3. Traccar unreachable + user exists locally → allow login as fallback
    if not traccar_reachable and user:
        logger.warning(f"[AUTH_FALLBACK] Traccar unreachable — allowing local login for {username}")
        role = "USER"
        if user.administrator:
            role = "SUPERADMIN"
        elif user.attributes and user.attributes.get("role") == "ADMIN":
            role = "ADMIN"
            
        access_token = create_access_token(data={"sub": user.email, "role": role})
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "role": role,
            "name": user.name
        }

    logger.warning(f"[AUTH_FAILURE] Invalid credentials for {username}")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials or security key",
        headers={"WWW-Authenticate": "Bearer"},
    )

@router.get("/me")
async def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    return current_user
