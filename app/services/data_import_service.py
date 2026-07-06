"""
FDB Data Import Service
========================
Smart diff-based import of Fleet Database Excel uploads.
Only updates columns that actually changed — skips unchanged rows.
"""

import openpyxl
from datetime import datetime, time, date
from typing import Dict, List, Any, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from loguru import logger
import io


# ── Excel Column → DB Column Mapping ──────────────────────────────────────────
# Maps the FDB Excel header names to ke_fleet_database column names.
# Keys are lowercase Excel headers, values are DB column names.
FDB_COLUMN_MAP = {
    "s.no.": "sno",
    "merge": "merge_registration",
    "vehicle": "vehicle_registration",
    "replacement": "replacement_registration",
    "replacement / deploymenet date": "replacement_date",
    "current status": "current_status",
    "last working date": "last_working_date",
    "ams card 1": "ams_card1",
    "ams card 2": "ams_card2",
    "vehicle category": "vehicle_category",
    "vehicle category 2": "vehicle_category2",
    "tonnage of truck": "tonnage",
    "robust status": "robust_status",
    "robust detail": "robust_detail",
    "ladder length": "ladder_length",
    "sun canopy": "sun_canopy",
    "branding": "branding",
    "make": "make",
    "type": "vehicle_type",
    "model year": "model_year",
    "base unit": "base_unit",
    "fuel type2": "fuel_type",
    "allocated km as per service code": "allocated_km",
    "shift type": "shift_type",
    "time in": "time_in",
    "time out": "time_out",
    "shift hrs.": "shift_hrs",
    "weekdays": "weekdays",
    "shift hrs.2": "shift_hrs2",
    "saturday": "saturday",
    "cc + cluster head - update": "cc_cluster_head",
    "tracker vendor": "tracker_vendor",
    "cost center": "cost_center",
    "new cc": "new_cc",
    "group": "fleet_group",
    "region": "region",
    "cluster": "cluster",
    "ibc/vIBC/dept.": "ibc_vibc",
    "sub department": "sub_department",
    "cluster head / gm": "cluster_head_gm",
    "regional head / director & above": "regional_head",
    "fleet department": "fleet_department",
    "attendance department": "attendance_department",
    "fleet coordinator name": "fleet_coordinator",
    "fc sap id": "fc_sap_id",
    "fleet coordinator email": "fleet_coordinator_email",
    "fleet vendor": "fleet_vendor",
    "project": "project",
    "user": "user_name",
    "cro ": "cro",
    "description": "description",
    "validity": "validity",
    "start date": "start_date",
    "end date": "end_date",
    "status": "status",
    "benchmark": "benchmark_kmpl",
    "imei": "uniqueid",
    "unique id": "uniqueid",
    "uniqueid": "uniqueid",
}


def _parse_time_val(val) -> Optional[str]:
    """Convert Excel time values to HH:MM:SS string for MySQL TIME column."""
    if val is None:
        return None
    if isinstance(val, time):
        return val.strftime("%H:%M:%S")
    if isinstance(val, datetime):
        return val.strftime("%H:%M:%S")
    if isinstance(val, str):
        val = val.strip()
        if not val or val.lower() in ("none", "null", ""):
            return None
        # Try parsing "09:00:00.0 To 09:00:00.0" → just the first time
        if " to " in val.lower():
            val = val.split(" to ")[0].strip()
        # Try "HH:MM" or "HH:MM:SS"
        for fmt in ("%H:%M:%S", "%H:%M", "%I:%M %p"):
            try:
                return datetime.strptime(val, fmt).strftime("%H:%M:%S")
            except ValueError:
                continue
        return val  # Return as-is if can't parse
    return str(val)


def _parse_date_val(val) -> Optional[str]:
    """Convert Excel date values to YYYY-MM-DD string for MySQL DATE column."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d")
    if isinstance(val, date):
        return val.strftime("%Y-%m-%d")
    if isinstance(val, str):
        val = val.strip()
        if not val or val.lower() in ("none", "null", ""):
            return None
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%d-%b-%y", "%d %b %Y"):
            try:
                return datetime.strptime(val, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return val
    return str(val)


def _parse_float_val(val) -> Optional[float]:
    """Safely convert a value to float."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        val = val.strip()
        if not val or val.lower() in ("none", "null", ""):
            return None
        try:
            return float(val)
        except ValueError:
            return None
    return None


def _parse_int_val(val) -> Optional[int]:
    """Safely convert a value to int."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return int(val)
    if isinstance(val, str):
        val = val.strip()
        if not val or val.lower() in ("none", "null", ""):
            return None
        try:
            return int(float(val))
        except ValueError:
            return None
    return None


def _clean_str_val(val) -> Optional[str]:
    """Clean string values — strip whitespace, convert empty to None."""
    if val is None:
        return None
    if isinstance(val, str):
        val = val.strip()
        if not val or val.lower() in ("none", "null", ""):
            return None
        # Clean up weird timedelta strings
        if val.startswith("0 days ") or val.startswith("Timedelta"):
            return None
        return val
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(val, time):
        return val.strftime("%H:%M:%S")
    if isinstance(val, date):
        return val.strftime("%Y-%m-%d")
    return str(val)


# Type parsers per DB column
PARSERS = {
    "sno": _parse_int_val,
    "model_year": _parse_int_val,
    "shift_hrs": _parse_float_val,
    "shift_hrs2": _parse_float_val,
    "cost_center": _parse_int_val,
    "cro": _parse_int_val,
    "benchmark_kmpl": _parse_float_val,
    "time_in": _parse_time_val,
    "time_out": _parse_time_val,
    "replacement_date": _parse_date_val,
    "last_working_date": _parse_date_val,
    "start_date": _parse_date_val,
    "end_date": _parse_date_val,
}


async def parse_fdb_excel(file_bytes: bytes) -> Tuple[List[Dict], str]:
    """
    Parse an FDB Excel file and return a list of row dicts.
    Returns (rows, sheet_name).
    """
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)

    # Try to find FDB sheet first, fall back to active sheet
    sheet_name = None
    for name in wb.sheetnames:
        if name.upper() == "FDB" or "FLEET" in name.upper():
            sheet_name = name
            break
    if not sheet_name:
        sheet_name = wb.sheetnames[0]

    ws = wb[sheet_name]
    rows_iter = ws.iter_rows(values_only=True)

    # First row = headers
    headers_raw = next(rows_iter)
    if not headers_raw:
        wb.close()
        raise ValueError("Excel file has no headers")

    # Map headers to DB columns
    header_map = {}
    for i, h in enumerate(headers_raw):
        if h is None:
            continue
        h_lower = str(h).strip().lower()
        db_col = FDB_COLUMN_MAP.get(h_lower)
        if db_col:
            header_map[i] = db_col
        else:
            logger.debug(f"Unmapped Excel column: '{h}' (index {i})")

    if "vehicle_registration" not in header_map.values():
        wb.close()
        raise ValueError("Excel file must contain a 'Vehicle' column")

    rows = []
    for row_idx, row in enumerate(rows_iter, start=2):
        if not row or not any(row):
            continue  # Skip empty rows

        row_dict = {}
        for excel_idx, db_col in header_map.items():
            if excel_idx < len(row):
                val = row[excel_idx]
                parser = PARSERS.get(db_col, _clean_str_val)
                parsed = parser(val)
                row_dict[db_col] = parsed

        # Skip rows without vehicle registration
        if not row_dict.get("vehicle_registration"):
            continue

        rows.append(row_dict)

    wb.close()
    logger.info(f"Parsed {len(rows)} vehicles from FDB sheet '{sheet_name}'")
    return rows, sheet_name


async def import_fdb_to_db(
    db: AsyncSession,
    rows: List[Dict],
) -> Dict[str, Any]:
    """
    Smart diff-based import: compare each row with DB, only update changed columns.
    Returns summary dict with counts.
    """
    if not rows:
        return {"inserted": 0, "updated": 0, "unchanged": 0, "errors": 0, "total": 0, "changes": []}

    # Get DB schema for allowed columns
    col_result = await db.execute(text("SHOW COLUMNS FROM ke_fleet_database"))
    allowed_cols = {row[0] for row in col_result.fetchall()}

    # Filter rows to only allowed columns
    filtered_rows = []
    for row in rows:
        filtered = {k: v for k, v in row.items() if k in allowed_cols}
        if filtered.get("vehicle_registration"):
            filtered_rows.append(filtered)

    # Fetch all existing vehicles from DB
    existing_result = await db.execute(text(
        "SELECT * FROM ke_fleet_database"
    ))
    existing_rows = existing_result.fetchall()
    existing_map = {}
    # Get column names from the result keys
    col_names = list(existing_result.keys())
    for er in existing_rows:
        vreg = er[col_names.index("vehicle_registration")]
        if vreg:
            existing_map[vreg.upper().strip()] = dict(zip(col_names, er))

    inserted = 0
    updated = 0
    unchanged = 0
    errors = 0
    changes_log = []

    insert_rows = []
    update_rows = []

    for row in filtered_rows:
        vreg = row.get("vehicle_registration", "").upper().strip()
        if not vreg:
            errors += 1
            continue

        existing = existing_map.get(vreg)

        if not existing:
            # New vehicle — INSERT
            insert_rows.append(row)
            inserted += 1
        else:
            # Compare columns — only update what changed
            changed_cols = {}
            for k, v in row.items():
                if k in ("id", "vehicle_registration", "created_at"):
                    continue
                db_val = existing.get(k)
                # Normalize for comparison
                new_val = v
                if str(v).strip() == "" or v is None:
                    new_val = None
                if str(db_val).strip() == "" or db_val is None:
                    db_val = None
                # Compare as strings for safety
                if str(new_val) != str(db_val):
                    changed_cols[k] = {"old": db_val, "new": new_val}

            if changed_cols:
                update_data = {k: v["new"] for k, v in changed_cols.items()}
                update_data["vehicle_registration"] = vreg
                update_rows.append(update_data)
                updated += 1
                changes_log.append({
                    "vehicle": vreg,
                    "changes": {k: {"from": v["old"], "to": v["new"]} for k, v in changed_cols.items()}
                })
            else:
                unchanged += 1

    # Execute inserts in batch
    if insert_rows:
        cols = list(insert_rows[0].keys())
        cols_str = ", ".join(f"`{c}`" for c in cols)
        placeholders = ", ".join(f":{c}" for c in cols)
        updates_str = ", ".join(f"`{c}`=VALUES(`{c}`)" for c in cols if c not in ("id",))
        sql = f"INSERT INTO ke_fleet_database ({cols_str}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {updates_str}"

        chunk_size = 200
        for i in range(0, len(insert_rows), chunk_size):
            await db.execute(text(sql), insert_rows[i:i + chunk_size])

    # Execute updates in batch
    if update_rows:
        for update_data in update_rows:
            vreg = update_data.pop("vehicle_registration")
            if not update_data:
                continue
            set_parts = []
            params = {"vreg": vreg}
            for k, v in update_data.items():
                set_parts.append(f"`{k}` = :{k}")
                params[k] = v
            set_str = ", ".join(set_parts)
            sql = f"UPDATE ke_fleet_database SET {set_str} WHERE vehicle_registration = :vreg"
            await db.execute(text(sql), params)

    await db.commit()

    summary = {
        "inserted": inserted,
        "updated": updated,
        "unchanged": unchanged,
        "errors": errors,
        "total": len(filtered_rows),
        "changes": changes_log[:100],  # Cap at 100 changes in response
    }
    logger.info(f"FDB import complete: {inserted} inserted, {updated} updated, {unchanged} unchanged, {errors} errors")
    return summary


# ============================================================
# FUEL TRANSACTION REPORT IMPORT
# ============================================================

FUEL_TXN_COLUMNS = {
    "card number": "card_number",
    "name on card": "vehicle_registration",
    "rrn": "rrn",
    "retail outlet": "retail_outlet",
    "city": "city",
    "date": "txn_date",
    "time": "txn_time",
    "product": "product",
    "quantity": "quantity_liters",
    "amount": "amount_pkr",
    "txn type": "txn_type",
}


def _parse_txn_date(val):
    if not val:
        return None
    try:
        from datetime import datetime
        if isinstance(val, datetime):
            return val.strftime("%Y-%m-%d")
        s = str(val).strip()
        for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y"):
            try:
                return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return s
    except Exception:
        return None


def _parse_txn_time(val):
    if not val:
        return None
    try:
        from datetime import datetime
        if isinstance(val, datetime):
            return val.strftime("%H:%M:%S")
        s = str(val).strip()
        for fmt in ("%H:%M:%S", "%H:%M"):
            try:
                return datetime.strptime(s, fmt).strftime("%H:%M:%S")
            except ValueError:
                continue
        return s
    except Exception:
        return None


def parse_fuel_excel(file_bytes: bytes):
    import openpyxl
    from io import BytesIO

    wb = openpyxl.load_workbook(BytesIO(file_bytes), read_only=True, data_only=True)

    sheet_name = None
    for name in wb.sheetnames:
        if "trans" in name.lower() or "txn" in name.lower() or "fuel" in name.lower():
            sheet_name = name
            break
    if not sheet_name:
        sheet_name = wb.sheetnames[0]

    ws = wb[sheet_name]
    rows_iter = ws.iter_rows(min_row=1, values_only=True)
    headers_raw = next(rows_iter, None)
    if not headers_raw:
        wb.close()
        return [], sheet_name

    headers = []
    for h in headers_raw:
        headers.append(str(h).strip().lower() if h else "")

    col_map = {}
    for idx, h in enumerate(headers):
        if h in FUEL_TXN_COLUMNS:
            col_map[idx] = FUEL_TXN_COLUMNS[h]

    if "vehicle_registration" not in col_map.values():
        wb.close()
        return [], sheet_name

    rows = []
    for row in rows_iter:
        if not row or all(c is None for c in row):
            continue
        rec = {}
        for idx, db_col in col_map.items():
            if idx < len(row):
                rec[db_col] = row[idx]
        if not rec.get("vehicle_registration"):
            continue
        rec["vehicle_registration"] = str(rec["vehicle_registration"]).strip().upper()
        rec["txn_date"] = _parse_txn_date(rec.get("txn_date"))
        rec["txn_time"] = _parse_txn_time(rec.get("txn_time"))
        rec["quantity_liters"] = _parse_float_val(rec.get("quantity_liters"))
        rec["amount_pkr"] = _parse_float_val(rec.get("amount_pkr"))
        rec["txn_type"] = str(rec.get("txn_type", "")).strip()
        rec["product"] = str(rec.get("product", "")).strip()
        rec["retail_outlet"] = str(rec.get("retail_outlet", "")).strip()
        rec["city"] = str(rec.get("city", "")).strip()
        rec["card_number"] = str(rec.get("card_number", "")).strip()
        rec["rrn"] = str(rec.get("rrn", "")).strip()
        rows.append(rec)

    wb.close()
    return rows, sheet_name


async def import_fuel_to_db(db, rows: list):
    from sqlalchemy import text
    from loguru import logger

    skipped_void = 0
    skipped_empty = 0
    inserted = 0
    duplicates = 0
    errors = 0
    daily_ops_updated = 0
    total_fuel = 0.0
    total_amount = 0.0

    valid_rows = []
    for r in rows:
        if r.get("txn_type", "").lower() == "void":
            skipped_void += 1
            continue
        if not r.get("txn_date") or not r.get("vehicle_registration"):
            skipped_empty += 1
            continue
        valid_rows.append(r)

    if valid_rows:
        insert_sql = text("""
            INSERT IGNORE INTO ke_fuel_transactions
            (vehicle_registration, card_number, rrn, retail_outlet, city, txn_date, txn_time, product, quantity_liters, amount_pkr, txn_type)
            VALUES (:vehicle_registration, :card_number, :rrn, :retail_outlet, :city, :txn_date, :txn_time, :product, :quantity_liters, :amount_pkr, :txn_type)
        """)

        for r in valid_rows:
            try:
                result = await db.execute(insert_sql, r)
                if result.rowcount and result.rowcount > 0:
                    inserted += 1
                    total_fuel += r.get("quantity_liters") or 0
                    total_amount += r.get("amount_pkr") or 0
                else:
                    duplicates += 1
            except Exception as e:
                logger.error(f"Fuel insert error for {r.get('vehicle_registration')}: {e}")
                errors += 1

        await db.commit()

        agg_sql = text("""
            SELECT vehicle_registration, txn_date, SUM(quantity_liters) as total_fuel, SUM(amount_pkr) as total_amt
            FROM ke_fuel_transactions
            GROUP BY vehicle_registration, txn_date
        """)
        result = await db.execute(agg_sql)
        agg_rows = result.fetchall()

        upsert_sql = text("""
            INSERT INTO ke_daily_operations (vehicle_registration, op_date, fuel_drawn)
            VALUES (:vreg, :odate, :fuel)
            ON DUPLICATE KEY UPDATE fuel_drawn = :fuel
        """)

        for ar in agg_rows:
            try:
                await db.execute(upsert_sql, {"vreg": ar[0], "odate": ar[1], "fuel": ar[2]})
                daily_ops_updated += 1
            except Exception as e:
                logger.error(f"Daily ops upsert error for {ar[0]}: {e}")

        await db.commit()

    summary = {
        "inserted": inserted,
        "skipped_void": skipped_void,
        "skipped_empty": skipped_empty,
        "duplicates_skipped": duplicates,
        "errors": errors,
        "total_fuel_liters": round(total_fuel, 2),
        "total_amount_pkr": round(total_amount, 2),
        "daily_ops_updated": daily_ops_updated,
        "total_valid_rows": len(valid_rows),
    }
    logger.info(f"Fuel import: {inserted} inserted, {skipped_void} voids, {duplicates} dupes")
    return summary
