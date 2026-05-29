from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.rag.intent_router import intent_router
from app.retrievers.sql_retriever import SQLRetriever
from app.vector.qdrant import qdrant_service
from app.llm.client import deepseek_client
from app.rag.database_brain import get_sql_prompt, get_business_rules

class RAGPipeline:
    def __init__(self, db: AsyncSession, current_user: Dict[str, Any]):
        self.db = db
        self.current_user = current_user
        self.sql_retriever = SQLRetriever(db, current_user)

    async def process_query(self, query: str, history: List[Dict[str, str]] = []) -> Dict[str, Any]:
        try:
            # 1. Routing
            routing_decision = await intent_router.route(query)
            intent = routing_decision["intent"]
            
            context = []
            
            # 2. Retrieval based on intent
            if intent in ["SQL_QUERY", "ANALYTICS"]:
                # RBAC Enforcement: Use SQL JOIN to enforce security at db level
                user_id = self.current_user.get("id", 0)

                if self.current_user["role"] in ["SUPERADMIN", "ADMIN"]:
                    # Admins can see all devices, no JOIN filter needed
                    rbac_restriction = f"The current user is an ADMIN (user_id={user_id}). They can see ALL devices. Do NOT use placeholders like ? or %s. Write concrete values only."
                    count_clause = "SELECT COUNT(*) as total FROM tc_devices"
                else:
                    # Regular users: restrict to their assigned devices
                    rbac_restriction = f"CRITICAL SECURITY RULE: You MUST join tc_user_device and include 'WHERE tc_user_device.userid = {user_id}' in EVERY query. Never query tc_devices or tc_positions without this filter. Do NOT use placeholders like ? or %s."
                    count_clause = f"SELECT COUNT(*) as total FROM tc_devices JOIN tc_user_device ON tc_devices.id = tc_user_device.deviceid WHERE tc_user_device.userid = {user_id}"

                # Generate SQL dynamically based on user query
                from app.rag.database_brain import get_sql_prompt
                sql_prompt = get_sql_prompt(query, rbac_restriction, count_clause)
                
                try:
                    sql_resp = await deepseek_client.chat_completion([{"role": "user", "content": sql_prompt}], temperature=0)
                    if not sql_resp or not sql_resp.choices:
                        raise ValueError("LLM failed to generate SQL query")
                        
                    sql_query = sql_resp.choices[0].message.content.replace("```sql", "").replace("```", "").strip()
                    
                    try:
                        sql_result = await self.sql_retriever.execute_custom_query(sql_query)
                        # Cap the output to prevent huge context, but show count
                        if len(sql_result) > 10:
                            context.append(f"SQL Execution Result: {len(sql_result)} rows found. Sample data: {sql_result[:10]}")
                        else:
                            context.append(f"SQL Execution Result: {sql_result}")
                    except Exception as e:
                        print(f"SQL Execution error on query [{sql_query}]: {e}")
                        context.append(f"SQL Execution error: {str(e)}")
                except Exception as e:
                    print(f"LLM SQL Generation error: {e}")
                    context.append(f"SQL Generation error: {str(e)}")
            
            if intent in ["SEMANTIC_SEARCH", "HYBRID"]:
                try:
                    semantic_data = await qdrant_service.search(query)
                    context.append(f"Semantic Search Results: {semantic_data}")
                except Exception as e:
                    print(f"Semantic search error: {e}")
                    context.append(f"Semantic search unavailable: {str(e)}")

            # 3. Final Response Generation
            from app.rag.database_brain import get_business_rules
            system_prompt = f"{get_business_rules()}\nContext Context:\n{chr(10).join(context)}"
            
            messages = history + [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ]
            
            response = await deepseek_client.chat_completion(messages)
            if not response or not response.choices:
                return {
                    "answer": "I'm sorry, I encountered an issue generating a response. Please try again.",
                    "intent": intent,
                    "context_sources": context
                }
                
            return {
                "answer": response.choices[0].message.content,
                "intent": intent,
                "context_sources": context
            }
        except Exception as e:
            print(f"Global Pipeline Error: {e}")
            return {
                "answer": f"Internal Intelligence Engine Error: {str(e)}",
                "intent": "ERROR",
                "context_sources": []
            }
