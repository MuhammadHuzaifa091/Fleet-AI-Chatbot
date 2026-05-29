import asyncio
import httpx
import json

async def test_webhook():
    test_payload = {
        "device": {
            "id": 1,
            "name": "Test Asset",
            "uniqueId": "ABC12345"
        },
        "position": {
            "id": 1001,
            "deviceId": 1,
            "attributes": {
                "obdVin": "1HGCM82633A004XXX" # Mock Valid VIN
            }
        }
    }
    
    # We will assume server is running on http://127.0.0.1:8000
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://127.0.0.1:8000/api/traccar/webhook",
                json=test_payload
            )
            print("Webhook Status Code:", response.status_code)
            print("Webhook Response:", response.text)
    except Exception as e:
        print("Failed to send webhook. Ensure server is running.", e)

if __name__ == "__main__":
    asyncio.run(test_webhook())
