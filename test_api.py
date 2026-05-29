import asyncio
import httpx

async def test():
    async with httpx.AsyncClient() as c:
        r = await c.post('http://localhost:8000/api/v1/auth/login', data={'username': 'admin@fleet.ai', 'password': 'admin'})
        token = r.json().get('access_token')
        r2 = await c.get('http://localhost:8000/api/analytics/summary', headers={'Authorization': f'Bearer {token}'})
        print('SUMMARY:', r2.json())

asyncio.run(test())
