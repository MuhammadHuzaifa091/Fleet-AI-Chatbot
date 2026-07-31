import json
import time
from typing import Dict, Any, List, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.retrievers.sql_retriever import SQLRetriever
from app.vector.qdrant import qdrant_service
from app.llm.client import deepseek_client
from app.rag.database_brain import get_sql_prompt, get_business_rules
from app.services.fleet_data_service import fleet_data_service
from loguru import logger


class RAGPipeline:
    def __init__(self, db: AsyncSession, current_user: Dict[str, Any]):
        self.db = db
        self.current_user = current_user
        self.sql_retriever = SQLRetriever(db, current_user)

    async def _get_fleet_context(self) -> List[str]:
        try:
            ctx = []
            summary = await fleet_data_service.get_fleet_summary(self.db)
            ctx.append(f"Fleet Summary: {summary.get('total_vehicles', 'N/A')} vehicles, "
                       f"{summary.get('online_vehicles', 'N/A')} online, "
                       f"{summary.get('offline_vehicles', 'N/A')} offline, "
                       f"health avg {summary.get('fleet_health_avg', 'N/A')}%, "
                       f"total cost Rs.{summary.get('total_combined_cost', 0):,.2f}")
            health = await fleet_data_service.get_fleet_health(self.db)
            critical = [h for h in health if h.get('health_score', 100) < 40]
            warning = [h for h in health if 40 <= h.get('health_score', 100) < 70]
            if critical:
                ctx.append(f"Critical Health: {', '.join(h['device_name'] for h in critical[:5])}")
            if warning:
                ctx.append(f"Warning Health: {', '.join(h['device_name'] for h in warning[:5])}")
            inv = await fleet_data_service.get_inventory_status(self.db)
            if inv:
                ctx.append(f"Inventory: {inv.get('total_parts', 0)} parts, "
                           f"value Rs.{inv.get('total_value', 0):,.2f}, "
                           f"{inv.get('low_stock_items', 0)} low stock, "
                           f"{inv.get('out_of_stock_items', 0)} out of stock")
            return ctx
        except Exception as e:
            logger.debug(f"[FLEET_CTX] Fleet context unavailable: {e}")
            return []

    async def _get_optimized_context(self, history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Optimizes context by keeping recent messages raw and summarizing older ones.
        """
        if len(history) <= 10:
            return history
        
        # Keep last 5 messages raw
        recent = history[-5:]
        older = history[:-5]
        
        # Simplified 'summarization' for now: just take the most relevant snippets 
        # or a placeholder. In a full implementation, we'd call LLM to summarize.
        summary_content = f"[Summary of previous {len(older)} messages: User discussed fleet status and analytics.]"
        
        optimized = [{"role": "system", "content": summary_content}]
        optimized.extend(recent)
        return optimized

    async def process_query(self, query: str, history: List[Dict[str, str]] = []) -> Dict[str, Any]:
        # Legacy non-streaming method, redirected to stream for consistency if needed, 
        # but kept for now.
        full_answer = ""
        intent = "SQL_QUERY"
        context_sources = []
        async for chunk in self.stream_query(query, history):
            # In process_query, we just collect it. 
            # Note: The first chunk in stream_query might be metadata. 
            # This is a bit messy, let's keep it separate or fix stream_query.
            pass
        return {"answer": "Use streaming endpoint for best results.", "intent": intent, "context_sources": context_sources}

    async def stream_query(self, query: str, history: List[Dict[str, str]] = []) -> AsyncGenerator[str, None]:
        t_total = time.time()
        try:
            user_id = self.current_user.get("id", 0)
            role = self.current_user.get("role", "USER")
            now = self.current_user.get("now", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

            if role in ["SUPERADMIN", "ADMIN"]:
                rbac_restriction = f"ADMIN (user_id={user_id}). Can see ALL devices. Do NOT filter by userid."
                count_clause = "SELECT COUNT(*) as total FROM tc_devices"
            else:
                rbac_restriction = f"CRITICAL: MUST include 'WHERE tc_user_device.userid = {user_id}' in EVERY query."
                count_clause = f"SELECT COUNT(*) as total FROM tc_devices JOIN tc_user_device ON tc_devices.id = tc_user_device.deviceid WHERE tc_user_device.userid = {user_id}"

            context = []

            # STEP 1: Classify intent + generate SQL
            classify_prompt = get_sql_prompt(query, rbac_restriction, count_clause)

            classify_resp = await deepseek_client.chat_completion(
                [{"role": "user", "content": classify_prompt}],
                temperature=0, max_tokens=2048
            )
            
            raw = classify_resp.choices[0].message.content.strip() if classify_resp.choices else "{}"
            if "```json" in raw: raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw: raw = raw.split("```")[1].split("```")[0].strip()

            try:
                classified = json.loads(raw)
            except json.JSONDecodeError:
                classified = {"intent": "SQL_QUERY", "sql": raw}

            intent = classified.get("intent", "SQL_QUERY")
            sql_query = classified.get("sql")

            # STEP 2: Execute SQL / Retrieval
            if sql_query and intent in ["SQL_QUERY", "ANALYTICS", "MAINTENANCE", "HYBRID"]:
                try:
                    sql_result = await self.sql_retriever.execute_custom_query(sql_query)
                    if isinstance(sql_result, list):
                        total_rows = len(sql_result)
                        if total_rows > 20:
                            context.append(f"SQL Result: {total_rows} rows returned. Showing first 20:\n{json.dumps(sql_result[:20], default=str, ensure_ascii=False)}")
                        else:
                            context.append(f"SQL Result: {total_rows} rows returned.\n{json.dumps(sql_result, default=str, ensure_ascii=False)}")
                    else:
                        context.append(f"SQL Result: {sql_result}")
                except Exception as e:
                    context.append(f"SQL error: {e}")

            if intent in ["SEMANTIC_SEARCH", "HYBRID"]:
                try:
                    semantic_data = await qdrant_service.search(query)
                    context.append(f"Docs: {semantic_data}")
                except Exception as e:
                    logger.warning(f"Semantic search failed: {e}")

            # STEP 2b: Inject Fleet Data Service context for maintenance/workshop/inventory queries
            if intent in ["MAINTENANCE", "ANALYTICS", "HYBRID"] or any(kw in query.lower() for kw in
                ["health", "maintenance", "workshop", "inventory", "fleet", "summary", "cost", "parts"]):
                fleet_ctx = await self._get_fleet_context()
                context.extend(fleet_ctx)

            # STEP 3: Final Streamed Response
            rules = get_business_rules()
            # Inject memory/context optimization
            optimized_history = await self._get_optimized_context(history)
            
            final_prompt = f"{rules}\n\nData Context:\n{chr(10).join(context)}\n\nQuery: {query}"
            messages = [{"role": "system", "content": final_prompt}]
            messages.extend(optimized_history)
            messages.append({"role": "user", "content": query})

            async for chunk in deepseek_client.stream_chat(messages):
                yield chunk

        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            yield f"I encountered an error while processing your request: {str(e)}"

from datetime import datetime
