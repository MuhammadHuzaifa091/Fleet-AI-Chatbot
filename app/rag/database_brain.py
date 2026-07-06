def get_business_rules():
    return """
CRITICAL: Never hallucinate. Use SQL as single source of truth. No LIMIT unless user asks.
Counts/totals: Use the provided count_clause exactly. For lists/shows: use SELECT with relevant columns.

SCHEMA:
- tc_devices: id, name, uniqueid, status, lastupdate, model, category, contact, phone, groupid, vin, disabled, attributes(JSON)
- tc_positions: id, deviceid, latitude, longitude, speed, course, altitude, address, servertime, devicetime, attributes(JSON)
- tc_events: id, type, servertime, deviceid, attributes(JSON)
- tc_users: id, name, email, administrator, attributes(JSON)
- tc_user_device: userid, deviceid
- tc_geofences: id, name, area(CIRCLE/POLYGON), attributes(JSON)
- mx_trips: id, deviceid, trip_start, trip_end, distance, duration

STATUS: online=active, offline+lastupdate>24h=idle, offline+lastupdate<24h=offline.
EVENTS: speeding=deviceOverspeed, harsh=harshBraking/harshAcceleration/harshCornering.
DATA: VIN=JSON_EXTRACT(attributes,'$.vin'), Fuel=JSON_EXTRACT(attributes,'$.fuelLevel'), Mileage=JSON_EXTRACT(attributes,'$.totalDistance')/1000km.

Use Markdown tables for multi-vehicle data. Respond in English or Roman Urdu only. Tone: clean, professional.
"""

def get_sql_prompt(query, rbac_restriction, count_clause):
    return f"""You are a MySQL query generator. Return ONLY a JSON object with "intent" and "sql" keys. No explanation, no markdown, no code blocks.

Schema:
- tc_devices(id, name, uniqueid, status, lastupdate, model, category, contact, phone, groupid, vin, disabled, attributes JSON)
- tc_positions(id, deviceid, latitude, longitude, speed, course, altitude, address, servertime, devicetime, attributes JSON)
- tc_events(id, type, servertime, deviceid, attributes JSON)
- tc_users(id, name, email, lastlogin, administrator, attributes JSON)
- tc_user_device(userid, deviceid)
- tc_geofences(id, name, area, attributes JSON)
- mx_trips(id, deviceid, trip_start, trip_end, distance, duration)

{rbac_restriction}

For COUNT/TOTAL queries, use EXACTLY this SQL: {count_clause}
For LIST/SHOW queries, use SELECT with relevant columns from tc_devices joined with tc_positions if needed.
For ACTIVE vehicles: WHERE tc_devices.status = 'online'
For IDLE vehicles: WHERE tc_devices.status = 'offline' AND tc_devices.lastupdate > NOW() - INTERVAL 1 DAY
For OFFLINE vehicles: WHERE tc_devices.status = 'offline' AND tc_devices.lastupdate <= NOW() - INTERVAL 1 DAY
For EVENTS: tc_events.type IN ('harshBraking','harshAcceleration','harshCornering','deviceOverspeed')
For VIN: JSON_EXTRACT(tc_devices.attributes,'$.vin')
For Fuel: JSON_EXTRACT(tc_devices.attributes,'$.fuelLevel')
For Mileage: JSON_EXTRACT(tc_devices.attributes,'$.totalDistance')/1000

IMPORTANT: Never use LIMIT unless user explicitly asks for a specific number. Return all matching rows.
IMPORTANT: For count queries, always use the exact count_clause provided above. Do NOT add WHERE filters to count queries unless user specifies.

Return format: {{"intent": "SQL_QUERY", "sql": "..."}}

Request: {query}
"""
