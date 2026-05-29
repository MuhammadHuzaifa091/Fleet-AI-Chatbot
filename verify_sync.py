"""
Standalone Sync Verification Tool (PC12 vs PC14)
================================================
Checks if data counts match between Production (PC12) and Development (PC14).
Tries API first, then falls back to Direct DB for PC12 counts.
"""

import asyncio
import sys
import os
import json
import datetime
import httpx
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Config
PC12_API_URL  = os.getenv("PC12_API_URL",  "http://202.141.246.12:8082")
PC12_API_USER = os.getenv("PC12_API_USER", "aima@admin.com")
PC12_API_PASS = os.getenv("PC12_API_PASS", "traccar12344321")

PC12_DB_HOST = "202.141.246.12"
PC12_DB_USER = "traccar"
PC12_DB_PASS = "traccar12344321"
PC12_DB_NAME = "traccar"

LOCAL_DB_URL = f"mysql+aiomysql://{os.getenv('DB_USER','traccar')}:{os.getenv('DB_PASSWORD','traccar12344321')}@{os.getenv('DB_SERVER','localhost')}:{os.getenv('DB_PORT','3306')}/{os.getenv('DB_NAME','traccar')}"

async def get_remote_counts():
    """Tries API then DB Fallback for PC12 counts."""
    counts = {"users": -1, "devices": -1, "perms": -1, "mode": "API"}
    
    # 1. Try API
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            login = await client.post(f"{PC12_API_URL}/api/session", data={"email": PC12_API_USER, "password": PC12_API_PASS}, headers={"Content-Type": "application/x-www-form-urlencoded"})
            if login.status_code == 200:
                r_u = await client.get(f"{PC12_API_URL}/api/users")
                r_d = await client.get(f"{PC12_API_URL}/api/devices", params={"all": "true"})
                if r_u.status_code == 200: counts["users"] = len(r_u.json())
                if r_d.status_code == 200: counts["devices"] = len(r_d.json())
                return counts
        except: pass

    # 2. Try DB Fallback
    counts["mode"] = "DB"
    db_url = f"mysql+aiomysql://{PC12_DB_USER}:{PC12_DB_PASS}@{PC12_DB_HOST}/{PC12_DB_NAME}"
    try:
        engine = create_async_engine(db_url)
        async with engine.connect() as conn:
            counts["users"] = (await conn.execute(text("SELECT COUNT(*) FROM tc_users"))).scalar()
            counts["devices"] = (await conn.execute(text("SELECT COUNT(*) FROM tc_devices"))).scalar()
            counts["perms"] = (await conn.execute(text("SELECT COUNT(*) FROM tc_user_device"))).scalar()
        await engine.dispose()
    except: pass
    
    return counts

async def get_local_counts():
    engine = create_async_engine(LOCAL_DB_URL)
    counts = {"users": 0, "devices": 0, "perms": 0}
    try:
        async with engine.connect() as conn:
            counts["users"] = (await conn.execute(text("SELECT COUNT(*) FROM tc_users"))).scalar()
            counts["devices"] = (await conn.execute(text("SELECT COUNT(*) FROM tc_devices"))).scalar()
            counts["perms"] = (await conn.execute(text("SELECT COUNT(*) FROM tc_user_device"))).scalar()
    finally:
        await engine.dispose()
    return counts

async def run_verify():
    print("\n" + "="*60)
    print("  PC12 vs PC14 SYNC VERIFICATION")
    print("="*60)
    
    print("[1/2] Fetching Remote PC12 Counts...")
    remote = await get_remote_counts()
    print(f"      Mode: {remote['mode']}  Users: {remote['users']}  Devices: {remote['devices']}  Perms: {remote['perms']}")
    
    print("[2/2] Fetching Local PC14 Counts...")
    local = await get_local_counts()
    print(f"      Local:         Users: {local['users']}  Devices: {local['devices']}  Perms: {local['perms']}")
    
    # Compare
    print("-" * 60)
    u_match = remote["users"] == local["users"]
    d_match = remote["devices"] == local["devices"]
    p_match = (remote["perms"] == local["perms"]) if remote["perms"] != -1 else True
    
    print(f"  Users:       {'✓ MATCH' if u_match else '✗ MISMATCH'}")
    print(f"  Devices:     {'✓ MATCH' if d_match else '✗ MISMATCH'}")
    if remote["perms"] != -1:
        print(f"  Permissions: {'✓ MATCH' if p_match else '✗ MISMATCH'}")
        
    print("-" * 60)
    if u_match and d_match and p_match:
        print("  ✅ RESULT: DATA ACCURACY VERIFIED")
        return 0
    else:
        print("  ❌ RESULT: DATA DISCREPANCY DETECTED")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(run_verify()))
