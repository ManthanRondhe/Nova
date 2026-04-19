"""
Nova AI - Estimation Engine
Calculates cost and time estimates for repairs.
"""
import csv, os

class EstimationEngine:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.parts_file = os.path.join(data_dir, "spare_parts.csv")
        self.labour_rate = 500  # INR per hour
        self._load_parts()
    
    def _load_parts(self):
        self.parts_map = {}
        try:
            with open(self.parts_file, "r", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    self.parts_map[row["part_id"]] = row
        except FileNotFoundError:
            pass
    
    def estimate(self, diagnosis_result):
        """Generate detailed cost and time estimate from diagnosis."""
        if not diagnosis_result:
            return self._empty_estimate()
        
        parts_cost = 0
        parts_breakdown = []
        required_parts = diagnosis_result.get("required_parts", "")
        
        if required_parts:
            part_ids = [p.strip() for p in required_parts.split(",")]
            for pid in part_ids:
                if pid in self.parts_map:
                    part = self.parts_map[pid]
                    price = int(part.get("unit_price", 0))
                    parts_cost += price
                    parts_breakdown.append({
                        "part_id": pid,
                        "name": part.get("part_name", "Unknown"),
                        "price": price,
                        "quantity": 1
                    })
        
        # Time estimation
        estimated_hours = float(diagnosis_result.get("estimated_time_hours", 2))
        
        # Adjust time based on severity
        severity = diagnosis_result.get("severity", "Medium")
        severity_multiplier = {"Critical": 1.3, "High": 1.1, "Medium": 1.0, "Low": 0.9}
        adjusted_hours = round(estimated_hours * severity_multiplier.get(severity, 1.0), 1)
        
        # Labour cost
        labour_cost = int(adjusted_hours * self.labour_rate)
        
        # Total estimate
        total_min = parts_cost + labour_cost
        total_max = int(total_min * 1.3)  # 30% buffer for unforeseen
        
        # Parse cost range from diagnosis
        cost_range = diagnosis_result.get("estimated_cost_range", "")
        if cost_range and "-" in str(cost_range):
            try:
                range_parts = str(cost_range).split("-")
                diag_min = int(range_parts[0])
                diag_max = int(range_parts[1])
                # Use diagnostic range if significantly different
                if diag_max > total_max:
                    total_max = diag_max
                if diag_min < total_min:
                    total_min = max(diag_min, parts_cost + labour_cost)
            except (ValueError, IndexError):
                pass
        
        return {
            "fault_name": diagnosis_result.get("fault_name", ""),
            "severity": severity,
            "confidence": diagnosis_result.get("confidence", 0),
            "parts_breakdown": parts_breakdown,
            "parts_cost": parts_cost,
            "labour_hours": adjusted_hours,
            "labour_rate_per_hour": self.labour_rate,
            "labour_cost": labour_cost,
            "total_estimate_min": total_min,
            "total_estimate_max": total_max,
            "estimated_time_hours": adjusted_hours,
            "estimated_completion": f"{adjusted_hours} hours",
            "notes": self._generate_notes(diagnosis_result, severity)
        }
    
    def quick_estimate(self, cost_range_str, time_hours):
        """Quick estimate from simple cost range and time."""
        if "-" in str(cost_range_str):
            parts = str(cost_range_str).split("-")
            try:
                return {
                    "total_estimate_min": int(parts[0]),
                    "total_estimate_max": int(parts[1]),
                    "estimated_time_hours": float(time_hours),
                    "labour_cost": int(float(time_hours) * self.labour_rate)
                }
            except (ValueError, IndexError):
                pass
        return self._empty_estimate()
    
    def _empty_estimate(self):
        return {
            "parts_breakdown": [],
            "parts_cost": 0,
            "labour_hours": 1,
            "labour_rate_per_hour": self.labour_rate,
            "labour_cost": self.labour_rate,
            "total_estimate_min": self.labour_rate,
            "total_estimate_max": self.labour_rate * 2,
            "estimated_time_hours": 1,
            "estimated_completion": "1 hour (inspection only)",
            "notes": "Estimate based on inspection only. Detailed estimate after diagnosis."
        }
    
    def _generate_notes(self, diagnosis, severity):
        notes = []
        conf = float(diagnosis.get("confidence", 0))
        
        if conf >= 0.85:
            notes.append("High confidence diagnosis - estimate is reliable")
        elif conf >= 0.70:
            notes.append("Moderate confidence - actual cost may vary ±20%")
        else:
            notes.append("Low confidence - further inspection recommended before repair")
        
        if severity == "Critical":
            notes.append("⚠️ Critical issue - immediate attention required")
        
        obd = diagnosis.get("obd_code", "")
        if obd:
            notes.append(f"OBD Codes: {obd}")
        
        return " | ".join(notes)
    
    def bulk_estimate(self, diagnosis_results):
        """Estimate for multiple faults (composite job)."""
        total_parts = 0
        total_hours = 0
        all_parts = []
        
        for diag in diagnosis_results:
            est = self.estimate(diag)
            total_parts += est["parts_cost"]
            total_hours += est["labour_hours"]
            all_parts.extend(est["parts_breakdown"])
        
        total_labour = int(total_hours * self.labour_rate)
        
        return {
            "total_faults": len(diagnosis_results),
            "parts_breakdown": all_parts,
            "total_parts_cost": total_parts,
            "total_labour_hours": total_hours,
            "total_labour_cost": total_labour,
            "grand_total_min": total_parts + total_labour,
            "grand_total_max": int((total_parts + total_labour) * 1.25)
        }
