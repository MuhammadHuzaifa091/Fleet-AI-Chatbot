import httpx
import asyncio

async def test_login():
    url = "http://localhost:8000/api/v1/auth/login"
    data = {
        "username": "farhan@gmail.com",
        "password": "somepassword" # Doesn't matter if it falls back
    }
    try:
        async with httpx.AsyncClient() as client:
            print(f"Testing login for farhan@gmail.com...")
            resp = await client.post(url, data=data)
            print(f"Status: {resp.status_code}")
            print(f"Body: {resp.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_login())
