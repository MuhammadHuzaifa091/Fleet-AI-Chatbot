from openai import AsyncOpenAI
from app.core.config import settings
from typing import List, Dict, Any, AsyncGenerator, Optional
import time
from loguru import logger

class DeepSeekClient:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL
        )
        self.model = settings.DEEPSEEK_MODEL

    async def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.7,
        stream: bool = False,
        max_tokens: int = 2048
    ) -> Any:
        start_time = time.time()
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                stream=stream,
                max_tokens=max_tokens
            )
            # We don't log latency here for streaming as it will be logged in stream_chat
            if not stream:
                latency = time.time() - start_time
                logger.info(f"[LLM] Non-stream completion took {latency:.2f}s")
            return response
        except Exception as e:
            logger.error(f"[LLM] Error in chat_completion: {e}")
            raise

    async def stream_chat(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> AsyncGenerator[str, None]:
        start_time = time.time()
        first_token_received = False
        
        try:
            response = await self.chat_completion(messages, temperature, stream=True, max_tokens=max_tokens)
            async for chunk in response:
                if not first_token_received:
                    latency = time.time() - start_time
                    logger.info(f"[LLM] First token received in {latency:.2f}s")
                    first_token_received = True
                
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            
            total_time = time.time() - start_time
            logger.info(f"[LLM] Stream completed in {total_time:.2f}s")
        except Exception as e:
            logger.error(f"[LLM] Error in stream_chat: {e}")
            yield f"\n[Error: {str(e)}]"

deepseek_client = DeepSeekClient()
