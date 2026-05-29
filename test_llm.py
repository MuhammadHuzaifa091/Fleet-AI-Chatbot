import asyncio
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

async def test_llm():
    client = AsyncOpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url=os.getenv("DEEPSEEK_BASE_URL"))
    try:
        resp = await client.chat.completions.create(
            model=os.getenv("DEEPSEEK_MODEL"),
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=5
        )
        print(f"LLM Success: {resp.choices[0].message.content}")
    except Exception as e:
        print(f"LLM Fail: {e}")

if __name__ == "__main__":
    asyncio.run(test_llm())
