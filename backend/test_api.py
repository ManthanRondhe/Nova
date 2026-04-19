"""Quick API test for Nova AI"""
import requests, json

BASE = "http://localhost:8000/api"

# Test 1: Diagnosis
print("=" * 50)
print("TEST 1: Diagnosis Engine")
print("=" * 50)
r = requests.post(f"{BASE}/diagnose", json={
    "query": "engine making knocking noise and blue smoke from exhaust",
    "vehicle_type": "Car"
})
data = r.json()
print(f"Status: {r.status_code}")
print(f"Detected System: {data['detected_system']}")
print(f"Detected Severity: {data['detected_severity']}")
print(f"Total Matches: {data['total_matches']}")
for i, d in enumerate(data["results"]):
    print(f"  [{i+1}] {d['fault_name']} - {d['confidence']*100:.0f}% - {d['severity']}")

# Test 2: Voice Command
print("\n" + "=" * 50)
print("TEST 2: Voice Command Processing")
print("=" * 50)
r = requests.post(f"{BASE}/voice/process", json={"text": "my car brake is making grinding noise"})
vdata = r.json()
print(f"Action: {vdata['action']}")
print(f"Response: {vdata['response'][:200]}")

# Test 3: Add another mechanic
print("\n" + "=" * 50)
print("TEST 3: Add Mechanic")
print("=" * 50)
r = requests.post(f"{BASE}/mechanics", json={
    "name": "Sunil Sharma", "phone": "9988776655",
    "specialization": "Brakes", "skill_level": "Senior"
})
print(f"Added: {r.json()['mechanic']['name']} ({r.json()['mechanic']['mechanic_id']})")

# Test 4: Create Job Card (auto-diagnose + auto-assign + pipeline)
print("\n" + "=" * 50)
print("TEST 4: Full Job Card Flow")
print("=" * 50)
r = requests.post(f"{BASE}/jobcards", json={
    "vehicle_make": "Maruti", "vehicle_model": "Swift",
    "vehicle_year": "2022", "vehicle_reg": "MH-12-AB-1234",
    "owner_name": "Amit Patel", "owner_phone": "9876543210",
    "complaint": "engine making knocking noise when accelerating and blue smoke"
})
jc = r.json()
print(f"Message: {jc['message']}")
print(f"Job Card: {jc['jobcard']['jobcard_id']}")
print(f"Status: {jc['jobcard']['status']}")
print(f"Priority: {jc['jobcard']['priority']}")
if jc.get("diagnosis"):
    print(f"Auto-Diagnosis: {jc['diagnosis']['fault_name']} ({jc['diagnosis']['confidence']*100:.0f}%)")
if jc.get("assigned_mechanic"):
    print(f"Auto-Assigned: {jc['assigned_mechanic']['name']} ({jc['assigned_mechanic']['mechanic_id']})")
if jc.get("estimate"):
    print(f"Estimate: Rs {jc['estimate']['total_estimate_min']} - Rs {jc['estimate']['total_estimate_max']}")
if jc.get("notification"):
    print(f"Notification: {jc['notification']['status']}")
if jc.get("orders_created"):
    print(f"Parts Auto-Ordered: {len(jc['orders_created'])}")

# Test 5: Pipeline
print("\n" + "=" * 50)
print("TEST 5: Pipeline Workload")
print("=" * 50)
r = requests.get(f"{BASE}/pipeline/workload")
for w in r.json()["workload"]:
    print(f"  {w['name']}: {w['active_tasks']} active tasks - {w['status']}")

# Test 6: Inventory Stats
print("\n" + "=" * 50)
print("TEST 6: Inventory Stats")
print("=" * 50)
r = requests.get(f"{BASE}/dashboard")
inv = r.json()["inventory"]
print(f"Total Items: {inv['total_items']}")
print(f"Total Stock: {inv['total_stock_units']} units")
print(f"Low Stock Alerts: {inv['low_stock_count']}")
print(f"Inventory Value: Rs {inv['total_inventory_value']:,}")

print("\n" + "=" * 50)
print("ALL TESTS PASSED!")
print("=" * 50)
