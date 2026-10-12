import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000/api/v1"

def print_res(name, res):
    print(f"\n--- {name} ---")
    print(f"Status: {res.status_code}")
    try:
        print(json.dumps(res.json(), indent=2))
    except:
        print(res.text)

# 1. Ask unrelated question
res = requests.post(f"{BASE_URL}/sessions", json={"title": "Unrelated"})
s_id = res.json()["id"]
res = requests.post(f"{BASE_URL}/sessions/{s_id}/chat", json={"content": "What is the recipe for a chocolate cake?", "provider": "ollama"})
print_res("Unrelated Question", res)

# 2. Nonexistent session
res = requests.get(f"{BASE_URL}/sessions/invalid-id/messages")
print_res("Nonexistent Session", res)

# 3. Invalid provider
res = requests.post(f"{BASE_URL}/sessions/{s_id}/chat", json={"content": "Hello", "provider": "invalid_provider"})
print_res("Invalid Provider", res)

# 4. Generate Essay
res = requests.post(f"{BASE_URL}/sessions/{s_id}/essay", json={"topic": "Product led growth", "target_audience": "Founders", "central_argument": "Growth is hard", "provider": "ollama"})
print_res("Essay Generation", res)
