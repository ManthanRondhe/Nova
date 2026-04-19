"""
Nova AI - Diagnosis Engine
Multi-model fusion: TF-IDF + Fuzzy Matching + Keyword Extraction
"""
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from rapidfuzz import fuzz
import os, re

class DiagnosisEngine:
    """Multi-model diagnosis engine with confidence scoring."""
    
    # Automotive system keywords for intent detection
    SYSTEM_KEYWORDS = {
        "Engine": ["engine", "motor", "cylinder", "piston", "crank", "cam", "valve", "turbo", "oil", "spark", "ignition", "timing", "compression", "misfire", "knock", "overheat", "stall", "idle", "rpm", "smoke"],
        "Transmission": ["gear", "clutch", "transmission", "gearbox", "shift", "synchro", "flywheel", "differential", "driveshaft", "cvt", "automatic", "manual"],
        "Brakes": ["brake", "pad", "disc", "rotor", "caliper", "abs", "pedal", "handbrake", "parking brake", "squeal", "grind", "stopping"],
        "Electrical": ["battery", "alternator", "starter", "fuse", "wire", "wiring", "light", "headlight", "window", "lock", "horn", "sensor", "ecu", "immobilizer", "dashboard"],
        "Suspension": ["suspension", "shock", "absorber", "spring", "ball joint", "bush", "strut", "bearing", "wheel bearing", "alignment", "bounce", "noise bump"],
        "Cooling": ["coolant", "radiator", "water pump", "thermostat", "overheat", "fan", "temperature", "steam", "heater core", "expansion tank"],
        "Fuel System": ["fuel", "petrol", "diesel", "injector", "pump", "filter", "carburetor", "cng", "fuel tank", "fuel smell", "economy", "mileage"],
        "Exhaust": ["exhaust", "catalytic", "silencer", "muffler", "dpf", "egr", "emission", "smoke exhaust", "tailpipe"],
        "Steering": ["steering", "power steering", "rack", "tie rod", "eps", "wheel vibration", "pulling", "wander"],
        "AC/HVAC": ["ac", "air conditioning", "cooling", "compressor", "refrigerant", "blower", "heater", "hvac", "condenser", "evaporator", "smell vent"],
        "Body": ["door", "window", "mirror", "wiper", "lock", "hinge", "boot", "sunroof", "windshield", "panel"],
        "Bike": ["bike", "motorcycle", "chain", "sprocket", "kick", "carb", "cdi", "fork", "throttle cable"],
        "Truck/Commercial": ["truck", "commercial", "air brake", "leaf spring", "king pin", "heavy vehicle"]
    }
    
    SEVERITY_INDICATORS = {
        "Critical": ["won't start", "not starting", "overheat", "smoke", "fire", "leak", "brake fail", "no brakes", "critical", "dangerous"],
        "High": ["noise", "grinding", "knocking", "vibration", "loss of power", "warning light", "leak", "stalling"],
        "Medium": ["rough idle", "hesitation", "poor mileage", "intermittent", "squealing", "smell"],
        "Low": ["minor", "cosmetic", "squeak", "rattle", "wear"]
    }
    
    def __init__(self, data_dir):
        faults_path = os.path.join(data_dir, "vehicle_faults.csv")
        self.df = pd.read_csv(faults_path)
        self.symptoms = self.df["symptom"].tolist()
        
        # Build TF-IDF model
        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 3),
            max_features=10000,
            sublinear_tf=True
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(self.symptoms)
        print(f"[OK] Diagnosis Engine loaded: {len(self.symptoms)} fault patterns")
    
    def diagnose(self, query, vehicle_type=None, vehicle_model=None, top_n=5):
        """
        Run multi-model diagnosis on a symptom query.
        Returns list of diagnosis results with confidence scores.
        """
        query_clean = self._preprocess(query)
        
        # Model 1: TF-IDF Cosine Similarity (50% weight)
        tfidf_scores = self._tfidf_score(query_clean)
        
        # Model 2: Fuzzy String Matching (30% weight)
        fuzzy_scores = self._fuzzy_score(query_clean)
        
        # Model 3: Keyword System Matching (20% weight)
        keyword_scores = self._keyword_score(query_clean)
        
        # Weighted fusion
        final_scores = (0.50 * tfidf_scores + 0.30 * fuzzy_scores + 0.20 * keyword_scores)
        
        # Apply vehicle filter boost
        if vehicle_type:
            vtype_mask = self.df["vehicle_type"].str.lower().str.contains(vehicle_type.lower(), na=False)
            final_scores = np.where(vtype_mask, final_scores * 1.2, final_scores)
        
        if vehicle_model:
            vmodel_mask = self.df["common_vehicles"].str.lower().str.contains(vehicle_model.lower(), na=False)
            final_scores = np.where(vmodel_mask, final_scores * 1.15, final_scores)
        
        # Get top N unique faults
        top_indices = final_scores.argsort()[::-1]
        
        results = []
        seen_faults = set()
        
        for idx in top_indices:
            if len(results) >= top_n:
                break
            
            score = float(final_scores[idx])
            if score < 0.10:
                break
            
            fault_name = self.df.iloc[idx]["fault_name"]
            if fault_name in seen_faults:
                continue
            seen_faults.add(fault_name)
            
            row = self.df.iloc[idx]
            base_conf = float(row.get("confidence", 0.8))
            combined_confidence = min(round(score * base_conf * 1.5, 2), 0.99)
            
            # Sanitize numpy/pandas types
            def safe_str(val):
                return "" if pd.isna(val) else str(val)

            results.append({
                "fault_id": safe_str(row["fault_id"]),
                "fault_name": str(fault_name),
                "system": safe_str(row["system"]),
                "vehicle_type": safe_str(row["vehicle_type"]),
                "matched_symptom": safe_str(row["symptom"]),
                "obd_code": safe_str(row.get("obd_code", "")),
                "confidence": combined_confidence,
                "severity": safe_str(row["severity"]),
                "required_parts": safe_str(row.get("required_parts", "")),
                "estimated_time_hours": float(row.get("estimated_time_hours", 0)) if not pd.isna(row.get("estimated_time_hours")) else 0.0,
                "estimated_cost_range": safe_str(row.get("estimated_cost_range", "")),
                "fix_procedure": safe_str(row.get("fix_procedure", "")),
                "common_vehicles": safe_str(row.get("common_vehicles", "")),
                "tfidf_score": round(float(tfidf_scores[idx]), 3),
                "fuzzy_score": round(float(fuzzy_scores[idx]), 3),
                "keyword_score": round(float(keyword_scores[idx]), 3)
            })
        
        return results
    
    def detect_system(self, query):
        """Detect which vehicle system the query is about."""
        query_lower = query.lower()
        scores = {}
        for system, keywords in self.SYSTEM_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            if score > 0:
                scores[system] = score
        
        if scores:
            return max(scores, key=scores.get)
        return "Unknown"
    
    def detect_severity(self, query):
        """Estimate severity from query language."""
        query_lower = query.lower()
        for severity, indicators in self.SEVERITY_INDICATORS.items():
            if any(ind in query_lower for ind in indicators):
                return severity
        return "Medium"
    
    def _preprocess(self, text):
        """Clean and normalize input text."""
        text = text.lower().strip()
        # Common voice recognition corrections for automotive terms
        corrections = {
            "break": "brake", "breaks": "brakes",
            "clutch plate": "clutch disc",
            "silencer": "muffler silencer",
            "dickey": "boot trunk",
            "bonnet": "hood bonnet",
            "stepney": "spare tyre",
            "indicator": "turn signal indicator",
            "accelerator": "throttle accelerator",
            "self start": "starter motor self start",
            "timing belt": "timing chain belt",
        }
        for wrong, right in corrections.items():
            text = text.replace(wrong, right)
        return text
    
    def _tfidf_score(self, query):
        """Calculate TF-IDF cosine similarity scores."""
        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        return scores
    
    def _fuzzy_score(self, query):
        """Calculate fuzzy string matching scores."""
        scores = np.array([
            fuzz.token_sort_ratio(query, symptom) / 100.0
            for symptom in self.symptoms
        ])
        return scores
    
    def _keyword_score(self, query):
        """Calculate keyword-based matching scores."""
        query_words = set(re.findall(r'\b\w+\b', query.lower()))
        scores = np.zeros(len(self.symptoms))
        
        for i, symptom in enumerate(self.symptoms):
            symptom_words = set(re.findall(r'\b\w+\b', symptom.lower()))
            if len(query_words) > 0:
                intersection = query_words & symptom_words
                scores[i] = len(intersection) / max(len(query_words), 1)
        
        return scores
    
    def get_all_systems(self):
        """Return all unique systems in the database."""
        return self.df["system"].unique().tolist()
    
    def get_faults_by_system(self, system):
        """Return all faults for a given system."""
        filtered = self.df[self.df["system"].str.lower() == system.lower()]
        return filtered[["fault_id", "fault_name", "severity"]].drop_duplicates("fault_name").to_dict("records")
