import json
import logging
import redis.asyncio as redis
from app.core.config import settings
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class RedisMemory:
    def __init__(self):
        self.use_mock = False
        self._checked = False
        try:
            self.client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                decode_responses=True,
                socket_timeout=0.5,
                socket_connect_timeout=0.5,
                retry_on_errorup=False
            )
        except Exception as e:
            logger.warning(f"Failed to initialize Redis client: {e}. Using mock memory.")
            self.use_mock = True
            self.memory: Dict[str, List[Dict[str, str]]] = {}

        self.ttl = 3600 * 24

    async def _check_connection(self):
        if self.use_mock or self._checked:
            return not self.use_mock
        if not hasattr(self, "client"):
            self.use_mock = True
            return False
        try:
            await self.client.ping()
            self._checked = True
            return True
        except Exception:
            self.use_mock = True
            self._checked = True
            self.memory = {}
            return False

    async def get_history(self, session_id: str) -> List[Dict[str, str]]:
        if await self._check_connection():
            try:
                data = await self.client.get(f"chat:{session_id}")
                return json.loads(data) if data else []
            except Exception:
                return []
        else:
            return self.memory.get(session_id, [])

    async def add_message(self, session_id: str, role: str, content: str):
        if await self._check_connection():
            try:
                data = await self.client.get(f"chat:{session_id}")
                history = json.loads(data) if data else []
                history.append({"role": role, "content": content})
                history = history[-5:]
                await self.client.setex(
                    f"chat:{session_id}",
                    self.ttl,
                    json.dumps(history)
                )
            except Exception as e:
                logger.error(f"Error saving to Redis: {e}")
        else:
            if session_id not in self.memory:
                self.memory[session_id] = []
            history = self.memory[session_id]
            history.append({"role": role, "content": content})
            self.memory[session_id] = history[-5:]

redis_memory = RedisMemory()
