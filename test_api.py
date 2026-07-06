import sys, json, urllib.request, urllib.parse

# Login with form data
data = urllib.parse.urlencode({"username":"admin@fleet.ai","password":"admin"}).encode()
req = urllib.request.Request("http://localhost:8000/api/v1/auth/login",
    data=data,
    headers={"Content-Type":"application/x-www-form-urlencoded"})
resp = json.loads(urllib.request.urlopen(req).read())
token = resp["access_token"]

# Test May
req2 = urllib.request.Request(f"http://localhost:8000/api/fleet/fdb/monthly-mis?month=2026-05",
    headers={"Authorization": f"Bearer {token}"})
data = json.loads(urllib.request.urlopen(req2).read())
s = data["summary"]
print(f"May: {s['total_vehicles']} vehicles, {s['total_km']} km, {s['fuel_consumed']} L fuel")
print(f"On-peak: {s['on_peak_km']}, Off-peak: {s['off_peak_km']}")
print(f"Vendors: {len(data['vendors'])}, Categories: {len(data['categories'])}")

# Test March
req3 = urllib.request.Request(f"http://localhost:8000/api/fleet/fdb/monthly-mis?month=2026-03",
    headers={"Authorization": f"Bearer {token}"})
data3 = json.loads(urllib.request.urlopen(req3).read())
s3 = data3["summary"]
print(f"\nMarch: {s3['total_vehicles']} vehicles, {s3['total_km']} km, {s3['fuel_consumed']} L fuel")
