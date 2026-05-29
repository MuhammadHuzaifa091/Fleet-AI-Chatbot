"""
PC12 → PC14 Automated Data Synchronization Service
====================================================
Dual-Mode Fetcher (API + DB Fallback)
--------------------------------------
1. Tries PC12 Traccar API first (REST API)
2. If API fails, falls back to Direct DB
3. Upserts data into local PC14 DB (Handles camelCase mapping)
"""

import asyncio
import datetime
import json
import os
from typing import Any, Dict, List, Optional, Tuple

import httpx
from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings

# ──────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────
PC12_API_URL: str  = getattr(settings, "PC12_API_URL",  "http://202.141.246.12:8082")
PC12_API_USER: str = getattr(settings, "PC12_API_USER", "aima@admin.com")
PC12_API_PASS: str = getattr(settings, "PC12_API_PASS", "traccar12344321")

# Direct DB credentials for fallback
PC12_DB_HOST = "202.141.246.12"
PC12_DB_USER = "traccar"
PC12_DB_PASS = "traccar12344321"
PC12_DB_NAME = "traccar"

SYNC_LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs", "sync.log")

# Mandatory columns that cannot be NULL in local DB
MANDATORY_COLS = {
    "tc_devices": {"uniqueid": "UNKNOWN", "name": "Unnamed Device"},
    "tc_users": {"email": "no-email@example.com", "name": "Unknown User"}
}

# ══════════════════════════════════════════════════════════════
# Global Sync Lock — prevents concurrent sync runs
# ══════════════════════════════════════════════════════════════
_sync_lock = asyncio.Lock()
_is_syncing: bool = False


def is_sync_running() -> bool:
    return _is_syncing


# ══════════════════════════════════════════════════════════════
# Internal Tools
# ══════════════════════════════════════════════════════════════

def _now_iso() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")

def _append_sync_log(entry: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(SYNC_LOG_FILE), exist_ok=True)
    with open(SYNC_LOG_FILE, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")

_INVALID_DATES = {"0000-00-00 00:00:00", "0000-00-00", ""}
def _sanitize(value: Any) -> Any:
    if isinstance(value, str) and value in _INVALID_DATES:
        return None
    return value

# ══════════════════════════════════════════════════════════════
# PROVIDER A: Traccar REST API (Priority)
# ══════════════════════════════════════════════════════════════

async def _fetch_from_api() -> Tuple[Optional[List], Optional[List], Optional[List]]:
    logger.info(f"[SYNC] Mode: API Fetch (Target: {PC12_API_URL})")
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            auth_resp = await client.post(
                f"{PC12_API_URL}/api/session",
                data={"email": PC12_API_USER, "password": PC12_API_PASS},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            if auth_resp.status_code != 200:
                logger.warning(f"[SYNC] API Login failed ({auth_resp.status_code}).")
                return None, None, None
        except Exception as e:
            logger.warning(f"[SYNC] API Connection error: {e}.")
            return None, None, None

        try:
            r_users = await client.get(f"{PC12_API_URL}/api/users")
            users = r_users.json() if r_users.status_code == 200 else None
            
            r_devices = await client.get(f"{PC12_API_URL}/api/devices", params={"all": "true"})
            devices = r_devices.json() if r_devices.status_code == 200 else None
            
            permissions = []
            if users:
                for u in users:
                    uid = u.get("id")
                    if uid:
                        r_perms = await client.get(f"{PC12_API_URL}/api/devices", params={"userId": uid})
                        if r_perms.status_code == 200:
                            for d in r_perms.json():
                                permissions.append({"userId": uid, "deviceId": d.get("id")})
            
            return users, devices, permissions
        except Exception as e:
            logger.error(f"[SYNC] API data fetch error: {e}")
            return None, None, None


# ══════════════════════════════════════════════════════════════
# PROVIDER B: Direct Remote DB (Fallback)
# ══════════════════════════════════════════════════════════════

async def _fetch_core_from_db() -> Tuple[Optional[List], Optional[List], Optional[List]]:
    """Phase-1: fast fetch of users, devices, permissions only."""
    logger.info("[SYNC] Mode: Direct DB Fallback (core tables)")
    db_url = f"mysql+aiomysql://{PC12_DB_USER}:{PC12_DB_PASS}@{PC12_DB_HOST}/{PC12_DB_NAME}"
    remote_engine = create_async_engine(db_url, connect_args={"connect_timeout": 15})
    try:
        async with remote_engine.connect() as conn:
            await conn.execute(text("SET SESSION sql_mode = '';"))
            res_u = await conn.execute(text("SELECT * FROM tc_users"))
            users = [dict(row._mapping) for row in res_u]
            res_d = await conn.execute(text("SELECT * FROM tc_devices"))
            devices = [dict(row._mapping) for row in res_d]
            res_p = await conn.execute(text(
                "SELECT userid as userId, deviceid as deviceId FROM tc_user_device"
            ))
            permissions = [dict(row._mapping) for row in res_p]
            logger.info(f"[SYNC] Core fetched: users={len(users)} devices={len(devices)}")
            return users, devices, permissions
    except Exception as e:
        logger.error(f"[SYNC] Core DB fetch failed: {e}")
        return None, None, None
    finally:
        await remote_engine.dispose()


async def _fetch_telemetry_from_db() -> Tuple[List, List]:
    """Phase-2 (background): fetch recent events + positions."""
    logger.info("[SYNC-BG] Fetching telemetry from PC12 DB...")
    db_url = f"mysql+aiomysql://{PC12_DB_USER}:{PC12_DB_PASS}@{PC12_DB_HOST}/{PC12_DB_NAME}"
    remote_engine = create_async_engine(db_url, connect_args={"connect_timeout": 30})
    events: List[Dict] = []
    positions: List[Dict] = []
    try:
        async with remote_engine.connect() as conn:
            await conn.execute(text("SET SESSION sql_mode = '';"))
            # tc_events uses 'eventtime' (NOT 'servertime')
            try:
                res_ev = await conn.execute(text(
                    "SELECT * FROM tc_events "
                    "WHERE eventtime > NOW() - INTERVAL 7 DAY "
                    "ORDER BY eventtime DESC LIMIT 10000"
                ))
                events = [dict(row._mapping) for row in res_ev]
                logger.info(f"[SYNC-BG] Fetched {len(events)} events")
            except Exception as ev_err:
                logger.warning(f"[SYNC-BG] tc_events fetch skipped: {ev_err}")
            # tc_positions uses 'servertime'
            try:
                res_pos = await conn.execute(text(
                    "SELECT * FROM tc_positions "
                    "WHERE servertime > NOW() - INTERVAL 3 DAY "
                    "ORDER BY servertime DESC LIMIT 50000"
                ))
                positions = [dict(row._mapping) for row in res_pos]
                logger.info(f"[SYNC-BG] Fetched {len(positions)} positions")
            except Exception as pos_err:
                logger.warning(f"[SYNC-BG] tc_positions fetch skipped: {pos_err}")
    except Exception as e:
        logger.error(f"[SYNC-BG] Telemetry DB connection failed: {e}")
    finally:
        await remote_engine.dispose()
    return events, positions


# Keep old name as alias so nothing else breaks
async def _fetch_from_db():
    users, devices, perms = await _fetch_core_from_db()
    events, positions = await _fetch_telemetry_from_db()
    return users, devices, perms, events, positions



# ══════════════════════════════════════════════════════════════
# Sync Logic
# ══════════════════════════════════════════════════════════════

async def _upsert_batch(db: AsyncSession, table: str, rows: List[Dict]):
    if not rows: return 0

    # Discover table columns once from DB schema
    column_res = await db.execute(text(f"DESC `{table}`"))
    allowed_cols = [row[0] for row in column_res.fetchall()]
    mandatory = MANDATORY_COLS.get(table, {})

    bulk_data = []

    for row in rows:
        # 1. Normalize Keys (Lowercase + camelCase fix)
        clean_row = {}
        for k, v in row.items():
            lk = k.lower()
            if lk == "uniqueid":     clean_row["uniqueid"] = v
            elif lk == "id":         clean_row["id"] = v
            elif lk == "userid":     clean_row["userid"] = v
            elif lk == "deviceid":   clean_row["deviceid"] = v
            elif lk == "hashedpassword": clean_row["hashedpassword"] = v
            elif lk == "password" and "hashedpassword" not in clean_row:
                clean_row["hashedpassword"] = v
            else:
                clean_row[lk] = v

        # 2. Build a row dict with EXACTLY allowed_cols keys (fixes column mismatch)
        data = {}
        for col in allowed_cols:
            val = clean_row.get(col)
            sanitized = _sanitize(val)
            if sanitized is None and col in mandatory:
                sanitized = mandatory[col]
            if col == "attributes" and isinstance(sanitized, dict):
                sanitized = json.dumps(sanitized)
            data[col] = sanitized  # Always included, even if None

        if not data.get("id"):
            continue  # Skip rows without a primary key
        bulk_data.append(data)

    if bulk_data:
        cols    = ", ".join(f"`{k}`" for k in allowed_cols)
        places  = ", ".join(f":{k}" for k in allowed_cols)
        updates = ", ".join(
            f"`{k}`=VALUES(`{k}`)"
            for k in allowed_cols
            if k not in ("id", "userid", "deviceid")
        )
        sql = f"INSERT INTO `{table}` ({cols}) VALUES ({places}) ON DUPLICATE KEY UPDATE {updates}"

        # Chunked inserts — yield control every 500 rows so event loop stays alive
        chunk_size = 500
        for i in range(0, len(bulk_data), chunk_size):
            await db.execute(text(sql), bulk_data[i : i + chunk_size])
            await asyncio.sleep(0)   # Yield control back to event loop

    await db.commit()
    return len(bulk_data)


class SyncService:
    @staticmethod
    async def sync_from_pc12(db: AsyncSession) -> Dict[str, Any]:
        """Phase 1 (fast): sync users, devices, permissions. Returns in ~1-2s."""
        global _is_syncing

        if _is_syncing:
            return {
                "status": "busy",
                "message": "A sync is already in progress. Please wait.",
                "synced": {"users": 0, "devices": 0, "permissions": 0},
            }

        async with _sync_lock:
            _is_syncing = True
            start_time = _now_iso()
            results = {
                "start_time": start_time,
                "status": "partial",
                "synced": {"users": 0, "devices": 0, "permissions": 0, "events": 0, "positions": 0},
                "mode": "API",
                "errors": []
            }

            try:
                # ── Fetch Phase-1 only (fast: users/devices/permissions) ──
                users, devices, perms = await _fetch_from_api()

                if users is None or devices is None:
                    results["mode"] = "DB_FALLBACK"
                    users, devices, perms = await _fetch_core_from_db()

                if users is None or devices is None:
                    results["status"] = "error"
                    results["errors"].append("Data fetch failed from both API and DB.")
                    _append_sync_log(results)
                    return results

                # ── Write Phase 1 to local DB ──────────────────────
                await db.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
                await db.execute(text("SET SESSION sql_mode = ''"))

                results["synced"]["users"]   = await _upsert_batch(db, "tc_users",   users)
                results["synced"]["devices"] = await _upsert_batch(db, "tc_devices", devices)

                if perms:
                    p_data = [
                        {"u": p.get("userId") or p.get("userid"),
                         "d": p.get("deviceId") or p.get("deviceid")}
                        for p in perms
                        if (p.get("userId") or p.get("userid"))
                        and (p.get("deviceId") or p.get("deviceid"))
                    ]
                    for i in range(0, len(p_data), 500):
                        await db.execute(
                            text("INSERT INTO tc_user_device (userid, deviceid)"
                                 " VALUES (:u, :d)"
                                 " ON DUPLICATE KEY UPDATE userid=userid"),
                            p_data[i : i + 500]
                        )
                        await asyncio.sleep(0)
                    await db.commit()
                    results["synced"]["permissions"] = len(p_data)

                await db.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
                results["status"] = "success"
                logger.success(
                    f"[SYNC] Phase-1 done — mode={results['mode']} "
                    f"users={results['synced']['users']}  "
                    f"devices={results['synced']['devices']}"
                )

                # Always kick off background telemetry sync
                asyncio.create_task(SyncService._fetch_and_write_telemetry())
                results["message"] = (
                    "Phase-1 complete. Telemetry (events/positions) "
                    "syncing in background — check /api/v1/sync/status."
                )

            except Exception as exc:
                results["status"] = "error"
                results["errors"].append(str(exc))
                logger.error(f"[SYNC] Exception during sync: {exc}", exc_info=True)
                try:
                    await db.rollback()
                except Exception:
                    pass

            finally:
                _is_syncing = False
                results["end_time"] = _now_iso()
                _append_sync_log(results)

        return results

    # ── Phase-2 helpers ────────────────────────────────────────────────────────

    @staticmethod
    async def _fetch_and_write_telemetry() -> None:
        """Background: fetch events+positions from PC12 DB then write to local DB."""
        try:
            events, positions = await _fetch_telemetry_from_db()
            await SyncService._write_telemetry(events, positions)
        except Exception as exc:
            logger.error(f"[SYNC-BG] Telemetry fetch error: {exc}")

    @staticmethod
    async def _write_telemetry(events: List[Dict], positions: List[Dict]) -> None:
        """Write events and positions to local DB using an independent session."""
        from app.db.session import SessionLocal
        try:
            async with SessionLocal() as bg_db:
                await bg_db.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
                await bg_db.execute(text("SET SESSION sql_mode = ''"))

                ev_count  = await _upsert_batch(bg_db, "tc_events",    events)
                pos_count = await _upsert_batch(bg_db, "tc_positions", positions)

                await bg_db.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
                logger.success(
                    f"[SYNC-BG] Telemetry done — "
                    f"events={ev_count}  positions={pos_count}"
                )
                _append_sync_log({
                    "phase": "telemetry_background",
                    "events": ev_count,
                    "positions": pos_count,
                    "time": _now_iso()
                })
        except Exception as exc:
            logger.error(f"[SYNC-BG] Telemetry write error: {exc}")

    @staticmethod
    async def start_sync(db: AsyncSession):
        return await SyncService.sync_from_pc12(db)

    @staticmethod
    async def deploy_to_prod():
        return {"status": "success", "message": "Development -> Production logic updated."}
