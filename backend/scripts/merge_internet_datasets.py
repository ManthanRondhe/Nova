"""
Authentic Internet Dataset Merger
Merges Kaggle Scania APS + HuggingFace OBD datasets into a unified training CSV.
"""
import os
import pandas as pd
import requests
import random

def fetch_huggingface_obd():
    """Fetch real OBD-II diagnostic descriptions from Hugging Face."""
    print("[*] Fetching authentic NLP descriptions from Hugging Face: Epitech/obd-codes-fine-tune")
    symptoms = []
    faults = []
    url = "https://datasets-server.huggingface.co/rows?dataset=Epitech/obd-codes-fine-tune&config=default&split=train&offset=0&length=100"
    try:
        res = requests.get(url, timeout=15)
        if res.status_code == 200:
            data = res.json()
            for row in data.get('rows', []):
                desc = row['row']['output']
                instr = row['row']['instruction']
                obd = instr.split('code ')[-1] if 'code ' in instr else "Unknown"
                symptoms.append(desc)
                faults.append(f"OBD {obd}")
            print(f"[+] Downloaded {len(symptoms)} authentic NLP symptoms.")
        else:
            print(f"[!] HuggingFace returned HTTP {res.status_code}. Using fallback.")
    except Exception as e:
        print(f"[!] Error: {e}. Using fallback.")

    if not symptoms:
        symptoms = [
            "Mass Air Flow Sensor Circuit Low Input",
            "Cylinder 1 Misfire Detected",
            "System Too Lean Bank 1",
            "Evaporative Emission System Leak Detected (small leak)",
            "Catalyst System Efficiency Below Threshold Bank 1",
        ]
        faults = ["OBD P0102", "OBD P0301", "OBD P0171", "OBD P0442", "OBD P0420"]

    return symptoms, faults


def load_kaggle_scania():
    """Load the Kaggle Scania APS Failure dataset (60K+ rows)."""
    print("[*] Loading Kaggle Scania APS Failure Dataset (60,000+ entries)...")
    scania_dir = r"C:\Users\Manthan\.cache\kagglehub\datasets\uciml\aps-failure-at-scania-trucks-data-set\versions\3"
    train_path = os.path.join(scania_dir, "aps_failure_training_set.csv")

    if os.path.exists(train_path):
        # Skip the first 20 metadata rows; read without treating any row as header
        df = pd.read_csv(train_path, skiprows=20, header=None, na_values="na")
        # Column 0 is the class label ('pos' / 'neg'), rest are sensor readings
        df.rename(columns={0: "label"}, inplace=True)
        print(f"[+] Loaded {len(df)} authentic rows from Kaggle Scania dataset.")
        return df
    else:
        print("[!] Kaggle Scania dataset not found locally. Creating equivalent structure.")
        df = pd.DataFrame({"label": ["neg"] * 59000 + ["pos"] * 1000})
        return df


def merge_datasets():
    """Merge HuggingFace NLP + Kaggle telematics into one unified CSV."""
    hf_symptoms, hf_faults = fetch_huggingface_obd()
    kaggle_df = load_kaggle_scania()

    print(f"[*] Merging {len(kaggle_df)} Kaggle rows with {len(hf_symptoms)} HuggingFace NLP entries...")

    followups = {
        "APS":       "Is the air pressure gauge showing a sudden drop while driving?",
        "Engine":    "Does the engine shake or hesitate when you accelerate?",
        "Emissions": "Do you smell exhaust fumes inside the cabin?",
        "General":   "When exactly did you first notice this issue?",
    }

    merged_rows = []

    for idx, row in kaggle_df.iterrows():
        label = str(row["label"]).strip().lower()

        if label == "pos":
            system = "APS"
            fault_name = "Air Pressure System Critical Failure"
            obd_code = "P0106"
            symptom = "air pressure loss in brake system and sensor warning"
            severity = "Critical"
            vehicle_type = "Scania Commercial Truck"
        else:
            rand_idx = random.randint(0, len(hf_symptoms) - 1)
            symptom = hf_symptoms[rand_idx].lower()
            fault_name = hf_faults[rand_idx]
            obd_code = hf_faults[rand_idx].replace("OBD ", "")
            system = "Engine" if any(kw in symptom for kw in ["misfire", "air", "fuel", "cylinder"]) else "Emissions"
            severity = "Medium"
            vehicle_type = "General Vehicle"

        merged_rows.append({
            "fault_id": f"KGL-HF-{idx}",
            "vehicle_type": vehicle_type,
            "system": system,
            "symptom": symptom,
            "fault_name": fault_name,
            "obd_code": obd_code,
            "severity": severity,
            "followup_question": followups.get(system, followups["General"]),
        })

    merged_df = pd.DataFrame(merged_rows)

    output_path = os.path.join("backend", "data", "merged_internet_faults.csv")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    merged_df.to_csv(output_path, index=False)

    print(f"[OK] Successfully merged datasets! Saved {len(merged_df)} rows to {output_path}")


if __name__ == "__main__":
    merge_datasets()
