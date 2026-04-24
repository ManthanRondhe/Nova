import requests
import json

base_url = "http://127.0.0.1:8000/api/voice/process"

print("--- Start Session ---")

# Step 1: Initial query
payload1 = {
    "text": "diagnose engine running rough at idle speed",
    "context": []
}
r1 = requests.post(base_url, json=payload1)
resp1 = r1.json()
print("User: My car has OBD P0171")
print(f"Bot [{resp1.get('action')}]: {resp1.get('response')}")

# Step 2: Answer followup
payload2 = {
    "text": "Yes the engine shakes",
    "context": [
        {"role": "user", "text": "diagnose engine running rough at idle speed"},
        {"role": "assistant", "text": resp1.get('response')}
    ]
}
r2 = requests.post(base_url, json=payload2)
resp2 = r2.json()
print("\nUser: Yes the engine shakes")
print(f"Bot [{resp2.get('action')}]: {resp2.get('response')}")

# Step 3: Different scenario - answer no
payload3 = {
    "text": "No it doesn't",
    "context": [
        {"role": "user", "text": "diagnose engine running rough at idle speed"},
        {"role": "assistant", "text": resp1.get('response')}
    ]
}
r3 = requests.post(base_url, json=payload3)
resp3 = r3.json()
print("\nUser: No it doesn't")
print(f"Bot [{resp3.get('action')}]: {resp3.get('response')}")

