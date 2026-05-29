import asyncio
import httpx
from typing import Dict, Any

async def test_vin_lookup(vin: str):
    vin = vin.strip().upper()
    print(f"TESTING VIN: {vin}")
    
    url = f"https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVin/{vin}?format=json"
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url)
        print(f"STATUS: {response.status_code}")
        if response.status_code == 200:
            raw_data = response.json()
            results = raw_data.get("Results", [])
            
            def get_val(key):
                item = next((r for r in results if r.get("Variable") == key), None)
                return item.get("Value") if item else None
            
            parsed = {
                "brand": get_val("Make"),
                "model": get_val("Model"),
                "year": get_val("Model Year"),
                "engine": get_val("Engine Model")
            }
            print(f"PARSED: {parsed}")
            return parsed
        else:
            print("FAILED")

if __name__ == "__main__":
    import sys
    vin = sys.argv[1] if len(sys.argv) > 1 else "1HGCM82633A004352"
    asyncio.run(test_vin_lookup(vin))
