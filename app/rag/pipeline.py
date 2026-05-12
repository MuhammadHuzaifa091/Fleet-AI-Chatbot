from sqlalchemy import select
from app.models.traccar import UserDevice
from app.rag.intent_router import intent_router
from app.retrievers.sql_retriever import SQLRetriever
from app.vector.qdrant import qdrant_service
from app.llm.client import deepseek_client
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List

class RAGPipeline:
    def __init__(self, db: AsyncSession, current_user: Dict[str, Any]):
        self.db = db
        self.current_user = current_user
        self.sql_retriever = SQLRetriever(db, current_user)

    async def process_query(self, query: str, history: List[Dict[str, str]] = []) -> Dict[str, Any]:
        # 1. Routing
        routing_decision = await intent_router.route(query)
        intent = routing_decision["intent"]
        
        context = []
        
        # 2. Retrieval based on intent
        if intent in ["SQL_QUERY", "ANALYTICS"]:
            # RBAC Enforcement: Use SQL JOIN to enforce security at db level
            rbac_restriction = ""
            count_clause = "SELECT COUNT(*) as total FROM tc_devices"

            if self.current_user["role"] == "USER":
                user_id = self.current_user["id"]
                # Tell LLM to explicitly join the user device mapping
                rbac_restriction = f"CRITICAL SECURITY RULE: You MUST join tc_user_device and include 'WHERE tc_user_device.userid = {user_id}' in EVERY query. Never query tc_devices or tc_positions without this filter."
                count_clause = f"SELECT COUNT(*) as total FROM tc_devices JOIN tc_user_device ON tc_devices.id = tc_user_device.deviceid WHERE tc_user_device.userid = {user_id}"

            # Generate SQL dynamically based on user query
            sql_prompt = f"""
            Write ONLY a valid MySQL query for the following request. Do not explain. Do not use formatting like ```sql.
            The database structure is Traccar:
            - tc_devices (id, name, uniqueid, positionid, status, disabled)
            - tc_positions (id, deviceid, latitude, longitude, speed, attributes, address, servertime)
            - tc_events (id, type, servertime, deviceid, geofenceid, attributes)
            - tc_users (id, name, email, administrator)
            - tc_user_device (userid, deviceid)

            {rbac_restriction}

            IF the user asks for count/total of vehicles/devices, use: {count_clause};

            Request: {query}
            """
            sql_resp = await deepseek_client.chat_completion([{"role": "user", "content": sql_prompt}], temperature=0)
            sql_query = sql_resp.choices[0].message.content.replace("```sql", "").replace("```", "").strip()
            
            try:
                sql_result = await self.sql_retriever.execute_custom_query(sql_query)
                # Cap the output to prevent huge context, but show count
                if len(sql_result) > 10:
                    context.append(f"SQL Execution Result: {len(sql_result)} rows found. Sample data: {sql_result[:10]}")
                else:
                    context.append(f"SQL Execution Result: {sql_result}")
            except Exception as e:
                context.append(f"SQL Execution error: {str(e)}")
        
        if intent in ["SEMANTIC_SEARCH", "HYBRID"]:
            semantic_data = await qdrant_service.search(query)
            context.append(f"Semantic Search Results: {semantic_data}")

        # 3. Final Response Generation
        system_prompt = f"""
You are an enterprise-grade AI Fleet Intelligence Assistant connected to a live Traccar MySQL database.

Your primary responsibility is to provide 100% accurate, real-time, data-driven responses.

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
🚫 LIMIT & SAMPLING PROTECTION
──────────────────────────────
- NEVER add LIMIT automatically
- NEVER truncate results silently
- NEVER reduce dataset size internally
If dataset is large: summarize AFTER fetching correct data, but NEVER change actual numbers.

──────────────────────────────
🧠 INTENT HANDLING
──────────────────────────────
1. COUNT / TOTAL queries: ALWAYS SQL COUNT(*)
2. LIST queries: FULL DATA (no limit unless asked)
3. ANALYTICS queries: SQL aggregation (GROUP BY, SUM, AVG)
4. SEMANTIC / NATURAL queries: vector + SQL hybrid
5. REAL-TIME STATUS: ALWAYS SQL (tc_devices / tc_positions)

──────────────────────────────
🔁 FAILSAFE MECHANISM
──────────────────────────────
If result seems too small (e.g., only 5 rows): RECHECK query → REMOVE any LIMIT → RE-RUN SQL

──────────────────────────────
🧾 RESPONSE RULES
──────────────────────────────
- Always reflect exact database values. Never round off or approximate counts.
- If total vehicles = 918 → MUST say 918. Do not say "around" or "approximately".

──────────────────────────────
🧩 HYBRID RAG RULE
──────────────────────────────
1. Fetch data using SQL
2. Use vector search ONLY if needed for meaning
3. Merge context
4. Generate response
SQL = FACTS | VECTOR = CONTEXT | LLM = RESPONSE

──────────────────────────────
⚠️ EDGE CASE & FORMATTING
──────────────────────────────
- If no data found → clearly say "No data found".
- CRITICAL FORMATTING INSTRUCTION: Whenever presenting multiple vehicles, telemetry stats, tracking positions, or column-wise data, YOU MUST use a Markdown table format. Do not use bullet points if data has multiple attributes. Use a Markdown table.

Context Context:
{chr(10).join(context)}
"""
        
        messages = history + [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]
        
        # We can stream this in the API
        response = await deepseek_client.chat_completion(messages)
        return {
            "answer": response.choices[0].message.content,
            "intent": intent,
            "context_sources": context
        }
