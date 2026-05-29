import requests, json

# Login
r = requests.post('http://localhost:8000/api/v1/auth/login', data={'username': 'admin@fleet.ai', 'password': 'admin'})
token = r.json().get('access_token')

# Chat - with full error detail
r2 = requests.post(
    'http://localhost:8000/api/v1/chat/', 
    headers={'Authorization': 'Bearer ' + token}, 
    json={'query': 'show my vehicles', 'session_id': 'test1'}
)

with open("chat_error.txt", "w", encoding="utf-8") as f:
    f.write(f"Status: {r2.status_code}\n")
    f.write(f"Headers: {dict(r2.headers)}\n")
    f.write(f"Body: {r2.text}\n")
print("Done - check chat_error.txt")
