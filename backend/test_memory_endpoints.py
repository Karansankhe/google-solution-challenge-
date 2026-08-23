import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8000/api/v1"

print("1. Testing POST /api/v1/surveillance/analyze_memory")
payload = {"location": "Delhi, India", "time_horizon": "medium"}
try:
    resp1 = requests.post(f"{BASE_URL}/surveillance/analyze_memory", json=payload, timeout=120)
    print(f"Status Code: {resp1.status_code}")
    if resp1.status_code == 200:
        print("Response OK. Report generated and saved to memory.")
    else:
        print("Response Body:")
        print(resp1.text)
except Exception as e:
    print(f"Request failed: {e}")
    sys.exit(1)

print("\n-----------------------------------\n")

print("2. Testing POST /api/v1/distribution/plan_memory")
try:
    resp2 = requests.post(f"{BASE_URL}/distribution/plan_memory", json=payload, timeout=120)
    print(f"Status Code: {resp2.status_code}")
    if resp2.status_code == 200:
        print("Response OK. Distribution plan generated using memory.")
    else:
        print("Response Body:")
        print(resp2.text)
except Exception as e:
    print(f"Request failed: {e}")
    sys.exit(1)
