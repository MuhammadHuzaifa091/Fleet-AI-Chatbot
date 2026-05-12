from app.llm.client import deepseek_client
from typing import Dict, Any
import json

class IntentRouter:
    def __init__(self):
        self.prompt_template = """
        Analyze the user query for a fleet management system and categorize it.
        Available categories:
        1. SQL_QUERY: Live status, location, speed, fuel, ignition, historical GPS data, specific device info.
        2. SEMANTIC_SEARCH: Documentation, driver behavior manuals, general fleet policies, non-structured insights.
        3. ANALYTICS: Summary of trips, idling analysis, overspeed trends, fuel efficiency over time, driver scoring.
        4. MAINTENANCE: Maintenance alerts, upcoming services, maintenance history.
        5. HYBRID: If it needs both structured data and semantic understanding.

        Query: "{query}"

        Return JSON format: {{"intent": "CATEGORY", "reasoning": "...", "extracted_params": {{...}}}}
        """

    async def route(self, query: str) -> Dict[str, Any]:
        messages = [
            {"role": "system", "content": "You are an intelligent intent router for a Fleet Management RAG system."},
            {"role": "user", "content": self.prompt_template.format(query=query)}
        ]
        response = await deepseek_client.chat_completion(messages, temperature=0)
        content = response.choices[0].message.content
        # Basic JSON extraction (DeepSeek might return markdown)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
             content = content.split("```")[1].split("```")[0].strip()
        
        try:
            return json.loads(content)
        except:
            return {"intent": "HYBRID", "reasoning": "Failed to parse intent, defaulting to hybrid", "extracted_params": {}}

intent_router = IntentRouter()
