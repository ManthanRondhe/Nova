import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend'))
from services.diagnosis_engine import DiagnosisEngine
from services.estimation_engine import EstimationEngine

print("Initializing...")
diag = DiagnosisEngine("backend/data")
est = EstimationEngine("backend/data")

print("Testing...")
text = "engine cranks but car is not starting."
results = diag.diagnose(text, top_n=3)
print(f"Results: {results}")

if results:
    e = est.estimate(results[0])
    print(f"Estimate: {e}")
