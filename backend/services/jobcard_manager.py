"""
AutoMech AI - Job Card Manager
Handles job card CRUD operations with auto-assignment.
"""
import csv, os, uuid
from datetime import datetime

from database import db

class JobCardManager:
    def __init__(self, data_dir):
        self.collection = db.jobcards
        self.headers = [
            "jobcard_id","vehicle_make","vehicle_model","vehicle_year","vehicle_reg",
            "owner_name","owner_phone","complaint","diagnosis_fault","diagnosis_confidence",
            "assigned_mechanic_id","assigned_mechanic_name","status","required_parts",
            "estimated_time","estimated_cost","actual_cost","priority","bay_number",
            "created_at","updated_at","completed_at"
        ]
    
    def _read_all(self):
        rows = list(self.collection.find({}, {"_id": 0}))
        # ensure string keys if needed, but MongoDB keeps types
        return rows
    
    def _write_all(self, rows):
        self.collection.delete_many({})
        if rows:
            self.collection.insert_many([{**r} for r in rows])
    
    def _next_id(self, rows):
        if not rows:
            return "JC-0001"
        ids = [r["jobcard_id"] for r in rows if r.get("jobcard_id","").startswith("JC-")]
        if not ids:
            return "JC-0001"
        max_num = max(int(id.split("-")[1]) for id in ids)
        return f"JC-{max_num + 1:04d}"
    
    def _next_bay(self, rows):
        active = [r for r in rows if r.get("status") in ("Pending", "In Progress")]
        used_bays = {int(r.get("bay_number", 0)) for r in active if r.get("bay_number","0").isdigit()}
        for bay in range(1, 20):
            if bay not in used_bays:
                return str(bay)
        return "1"
    
    def create_jobcard(self, vehicle_make, vehicle_model, vehicle_year, vehicle_reg,
                       owner_name, owner_phone, complaint, diagnosis=None, mechanic=None):
        """Create a new job card."""
        rows = self._read_all()
        jc_id = self._next_id(rows)
        bay = self._next_bay(rows)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        priority = "Medium"
        if diagnosis and diagnosis.get("severity") == "Critical":
            priority = "Urgent"
        elif diagnosis and diagnosis.get("severity") == "High":
            priority = "High"
        elif diagnosis and diagnosis.get("severity") == "Low":
            priority = "Low"
        
        jobcard = {
            "jobcard_id": jc_id,
            "vehicle_make": vehicle_make,
            "vehicle_model": vehicle_model,
            "vehicle_year": vehicle_year,
            "vehicle_reg": vehicle_reg,
            "owner_name": owner_name,
            "owner_phone": owner_phone,
            "complaint": complaint,
            "diagnosis_fault": diagnosis.get("fault_name", "") if diagnosis else "",
            "diagnosis_confidence": diagnosis.get("confidence", 0) if diagnosis else 0,
            "assigned_mechanic_id": mechanic.get("mechanic_id", "") if mechanic else "",
            "assigned_mechanic_name": mechanic.get("name", "") if mechanic else "",
            "status": "Pending",
            "required_parts": diagnosis.get("required_parts", "") if diagnosis else "",
            "estimated_time": diagnosis.get("estimated_time_hours", "") if diagnosis else "",
            "estimated_cost": diagnosis.get("estimated_cost_range", "") if diagnosis else "",
            "actual_cost": "",
            "priority": priority,
            "bay_number": bay,
            "created_at": now,
            "updated_at": now,
            "completed_at": ""
        }
        
        rows.append(jobcard)
        self._write_all(rows)
        return jobcard
    
    def get_jobcard(self, jc_id):
        """Get a single job card by ID."""
        rows = self._read_all()
        for r in rows:
            if r["jobcard_id"] == jc_id:
                return r
        return None
    
    def get_all_jobcards(self, status=None):
        """Get all job cards, optionally filtered by status."""
        rows = self._read_all()
        if status:
            rows = [r for r in rows if r.get("status","").lower() == status.lower()]
        return rows
    
    def update_jobcard(self, jc_id, updates):
        """Update a job card with given fields."""
        rows = self._read_all()
        for r in rows:
            if r["jobcard_id"] == jc_id:
                for k, v in updates.items():
                    if k in self.headers:
                        r[k] = v
                r["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self._write_all(rows)
                return r
        return None
    
    def complete_jobcard(self, jc_id, actual_cost=""):
        """Mark a job card as completed."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return self.update_jobcard(jc_id, {
            "status": "Completed",
            "actual_cost": actual_cost,
            "completed_at": now
        })
    
    def assign_mechanic(self, jc_id, mechanic_id, mechanic_name):
        """Assign a mechanic to a job card."""
        return self.update_jobcard(jc_id, {
            "assigned_mechanic_id": mechanic_id,
            "assigned_mechanic_name": mechanic_name,
            "status": "In Progress"
        })
    
    def get_stats(self):
        """Get job card statistics."""
        rows = self._read_all()
        total = len(rows)
        pending = len([r for r in rows if r.get("status") == "Pending"])
        in_progress = len([r for r in rows if r.get("status") == "In Progress"])
        completed = len([r for r in rows if r.get("status") == "Completed"])
        urgent = len([r for r in rows if r.get("priority") == "Urgent" and r.get("status") != "Completed"])
        
        return {
            "total": total,
            "pending": pending,
            "in_progress": in_progress,
            "completed": completed,
            "urgent": urgent
        }
    
    def delete_jobcard(self, jc_id):
        """Delete a job card."""
        rows = self._read_all()
        rows = [r for r in rows if r["jobcard_id"] != jc_id]
        self._write_all(rows)
        return True
