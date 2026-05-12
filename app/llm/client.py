from openai import AsyncOpenAI
from app.core.config import settings
from typing import List, Dict, Any, AsyncGenerator

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
        stream: bool = False
    ) -> Any:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            stream=stream
        )
        return response

    async def stream_chat(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        response = await self.chat_completion(messages, temperature, stream=True)
        async for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

deepseek_client = DeepSeekClient()
