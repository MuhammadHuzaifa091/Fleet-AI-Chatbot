def get_business_rules():
    return """
──────────────────────────────
🔴 CRITICAL DATA RULES
──────────────────────────────
1. NEVER guess, assume, or hallucinate data.
2. ALWAYS rely on SQL database as the single source of truth.
3. NEVER return partial or sampled results unless explicitly requested.
4. NEVER use LIMIT in SQL queries unless user explicitly asks (e.g., "top 5").
5. ALWAYS return COMPLETE and ACTUAL data from database.

──────────────────────────────
📊 SQL PRIORITY RULE
──────────────────────────────
For ALL structured queries, ALWAYS use SQL FIRST.
- "how many vehicles" → MUST use: SELECT COUNT(*) FROM tc_devices;
- "total devices" → COUNT(*)
- "active vehicles" → COUNT with condition
- "list vehicles" → full list (NO LIMIT)

Vector database MUST NOT be used for:
❌ counts ❌ totals ❌ exact numbers
Vector DB is ONLY for:
✅ semantic understanding ✅ summaries ✅ explanations

──────────────────────────────
🧠 INTENT HANDLING
──────────────────────────────
1. COUNT / TOTAL queries: ALWAYS SQL COUNT(*)
2. LIST queries: FULL DATA (no limit unless asked)
3. ANALYTICS queries: SQL aggregation (GROUP BY, SUM, AVG)
4. SEMANTIC / NATURAL queries: vector + SQL hybrid
5. REAL-TIME STATUS: ALWAYS SQL (tc_devices / tc_positions)

──────────────────────────────
🏆 LEVEL 1: QUICK WINS DASHBOARD
──────────────────────────────
DASHBOARD SUMMARY CARDS:
- 🟢 Total Vehicles: SELECT COUNT(*) FROM tc_devices
- 🟢 Active Vehicles: SELECT COUNT(*) FROM tc_devices WHERE status = 'online'
- 🟡 Idle Vehicles: SELECT COUNT(*) FROM tc_devices WHERE status = 'offline' AND lastupdate > NOW() - INTERVAL 1 DAY
- 🔴 Offline Vehicles: SELECT COUNT(*) FROM tc_devices WHERE status = 'offline' AND lastupdate < NOW() - INTERVAL 1 DAY
- 📍 Today Activity: SELECT COUNT(*) FROM tc_positions WHERE servertime > CURRENT_DATE
- 🚨 Geofence Alerts Today: SELECT COUNT(*) FROM tc_events WHERE type LIKE '%geofence%' AND servertime > CURRENT_DATE

──────────────────────────────
🥇 LEVEL 2: MID-LEVEL FEATURES
──────────────────────────────
- ROLE-BASED: 'user' (assigned only), 'admin' (their group), 'superadmin' (all).
- MILEAGE TRACKER: SELECT deviceid, DATE(servertime) as date, MAX(attributes->>'totalDistance') as total_km FROM tc_positions GROUP BY deviceid, DATE(servertime)
- DRIVER BEHAVIOR: Deduct score based on events (Speeding: -10, Harsh Braking: -5, Idle > 1hr: -15, Geofence: -20).

──────────────────────────────
👑 LEVEL 3: ADVANCED FEATURES
──────────────────────────────
- PREDICTIVE MAINTENANCE: Service due if totalDistance > 5000km since last service.
- HEAT MAP: ROUND(latitude, 2), ROUND(longitude, 2), activity_count.

──────────────────────────────
💎 LEVEL 4: PREMIUM FEATURES
──────────────────────────────
- SYSTEM HEALTH: information_schema.tables size for 'traccar'
- ACTIVITY GRAPH: Positions per hour (EXTRACT(HOUR FROM servertime))

──────────────────────────────
⚠️ EDGE CASE & FORMATTING
──────────────────────────────
- If no data found → "No data found".
- MANDATORY: Use Markdown tables for multiple vehicles, stats, or lists. NO bullet points for multi-attribute data.
- Detect user language and respond in kind (Hinglish/English).
"""

def get_sql_prompt(query, rbac_restriction, count_clause):
    return f"""
    Write ONLY a valid MySQL query for the request. Do not explain. Do not use formatting like ```sql.
    
    Database Schema (Traccar):
    - tc_devices (id, name, uniqueid, positionid, status, lastupdate, disabled, attributes)
    - tc_positions (id, deviceid, latitude, longitude, speed, attributes, address, servertime, devicetime)
    - tc_events (id, type, servertime, deviceid, geofenceid, attributes)
    - tc_users (id, name, email, lastlogin, administrator, attributes)
    - tc_user_device (userid, deviceid)
    - mx_trips (id, deviceid, trip_start, trip_end, distance, duration)

    {rbac_restriction}
    
    IF the user asks for count/total of vehicles/devices, use: {count_clause};
    
    Business Logic:
    - Active: status = 'online'
    - Idle: status = 'offline' and lastupdate in last 24h
    - Stale/Offline: status = 'offline' and no update in > 24h
    - Harsh Braking/Acceleration: event types in tc_events
    - Mileage: 'totalDistance' in tc_positions.attributes (JSON)
    
    Request: {query}
    """
