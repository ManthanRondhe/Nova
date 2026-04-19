"""
Nova AI - Mechanic Scheduler
Handles mechanic management, auto-assignment, and pipeline optimization.
"""
import csv, os
from datetime import datetime

from database import db

class MechanicScheduler:
    def __init__(self, data_dir):
        self.mechanics_file = "mechanics"
        self.pipeline_file = "pipeline"
        self.mech_headers = ["mechanic_id","name","phone","specialization","status","current_jobs","skill_level","telegram_chat_id"]
        self.pipe_headers = ["pipeline_id","mechanic_id","mechanic_name","jobcard_id","task_description","priority","status","start_time","estimated_end","actual_end"]
    
    def _read_csv(self, file_key):
        if file_key == self.mechanics_file:
            return list(db.mechanics.find({}, {"_id": 0}))
        elif file_key == self.pipeline_file:
            return list(db.pipeline.find({}, {"_id": 0}))
        return []
    
    def _write_csv(self, file_key, headers, rows):
        if file_key == self.mechanics_file:
            db.mechanics.delete_many({})
            if rows:
                db.mechanics.insert_many([{**r} for r in rows])
        elif file_key == self.pipeline_file:
            db.pipeline.delete_many({})
            if rows:
                db.pipeline.insert_many([{**r} for r in rows])
    
    # ─── Mechanic CRUD ───
    
    def add_mechanic(self, name, phone, specialization="General", skill_level="Senior", telegram_chat_id=""):
        """Add a new mechanic."""
        rows = self._read_csv(self.mechanics_file)
        next_id = f"M-{len(rows) + 1:03d}"
        
        mechanic = {
            "mechanic_id": next_id,
            "name": name,
            "phone": phone,
            "specialization": specialization,
            "status": "Available",
            "current_jobs": "0",
            "skill_level": skill_level,
            "telegram_chat_id": telegram_chat_id
        }
        rows.append(mechanic)
        self._write_csv(self.mechanics_file, self.mech_headers, rows)
        return mechanic
    
    def get_mechanic(self, mechanic_id):
        rows = self._read_csv(self.mechanics_file)
        for r in rows:
            if r["mechanic_id"] == mechanic_id:
                return r
        return None
    
    def get_all_mechanics(self):
        return self._read_csv(self.mechanics_file)
    
    def update_mechanic(self, mechanic_id, updates):
        rows = self._read_csv(self.mechanics_file)
        for r in rows:
            if r["mechanic_id"] == mechanic_id:
                for k, v in updates.items():
                    if k in self.mech_headers:
                        r[k] = v
                self._write_csv(self.mechanics_file, self.mech_headers, rows)
                return r
        return None
    
    def delete_mechanic(self, mechanic_id):
        rows = self._read_csv(self.mechanics_file)
        rows = [r for r in rows if r["mechanic_id"] != mechanic_id]
        self._write_csv(self.mechanics_file, self.mech_headers, rows)
        return True
    
    def set_mechanic_status(self, mechanic_id, status):
        return self.update_mechanic(mechanic_id, {"status": status})
    
    # ─── Auto Assignment ───
    
    def auto_assign(self, specialization_needed=None, severity="Medium"):
        """
        Find the best available mechanic for a job.
        Priority: specialization match > lowest workload > highest skill
        """
        mechanics = self._read_csv(self.mechanics_file)
        available = [m for m in mechanics if m.get("status") == "Available"]
        
        if not available:
            # Fall back to mechanics with least jobs
            busy = [m for m in mechanics if m.get("status") == "Busy"]
            if busy:
                available = sorted(busy, key=lambda x: int(x.get("current_jobs", 99)))[:3]
            else:
                return None
        
        # Score each mechanic
        scored = []
        for m in available:
            score = 0
            # Specialization match
            if specialization_needed and m.get("specialization","").lower() == specialization_needed.lower():
                score += 50
            elif m.get("specialization","").lower() == "general":
                score += 20
            
            # Lower workload = higher score
            jobs = int(m.get("current_jobs", 0))
            score += max(0, 30 - (jobs * 10))
            
            # Higher skill = higher score
            skill_scores = {"Expert": 20, "Senior": 15, "Junior": 10}
            score += skill_scores.get(m.get("skill_level", "Senior"), 10)
            
            # Critical jobs should go to experts
            if severity in ("Critical", "Urgent") and m.get("skill_level") == "Expert":
                score += 15
            
            scored.append((m, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        
        if scored:
            best = scored[0][0]
            # Update mechanic status
            new_jobs = int(best.get("current_jobs", 0)) + 1
            self.update_mechanic(best["mechanic_id"], {
                "current_jobs": str(new_jobs),
                "status": "Busy" if new_jobs >= 2 else "Available"
            })
            return best
        return None
    
    def release_mechanic(self, mechanic_id):
        """Release a mechanic when job is completed."""
        mechanic = self.get_mechanic(mechanic_id)
        if mechanic:
            jobs = max(0, int(mechanic.get("current_jobs", 1)) - 1)
            self.update_mechanic(mechanic_id, {
                "current_jobs": str(jobs),
                "status": "Available" if jobs == 0 else "Busy"
            })
    
    # ─── Pipeline Management ───
    
    def add_to_pipeline(self, mechanic_id, mechanic_name, jobcard_id, task_desc, priority="Medium", estimated_hours=0):
        """Add a task to the mechanic's pipeline."""
        rows = self._read_csv(self.pipeline_file)
        next_id = f"PL-{len(rows) + 1:04d}"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        task = {
            "pipeline_id": next_id,
            "mechanic_id": mechanic_id,
            "mechanic_name": mechanic_name,
            "jobcard_id": jobcard_id,
            "task_description": task_desc,
            "priority": priority,
            "status": "Queued",
            "start_time": now,
            "estimated_end": "",
            "actual_end": ""
        }
        rows.append(task)
        self._write_csv(self.pipeline_file, self.pipe_headers, rows)
        return task
    
    def get_mechanic_pipeline(self, mechanic_id):
        """Get all pipeline tasks for a mechanic."""
        rows = self._read_csv(self.pipeline_file)
        return [r for r in rows if r.get("mechanic_id") == mechanic_id and r.get("status") != "Done"]
    
    def get_full_pipeline(self):
        """Get complete pipeline for all mechanics."""
        return self._read_csv(self.pipeline_file)
    
    def update_pipeline_status(self, pipeline_id, status):
        rows = self._read_csv(self.pipeline_file)
        for r in rows:
            if r["pipeline_id"] == pipeline_id:
                r["status"] = status
                if status == "Done":
                    r["actual_end"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self._write_csv(self.pipeline_file, self.pipe_headers, rows)
                return r
        return None
    
    def complete_pipeline_task(self, pipeline_id, mechanic_id):
        """Complete a pipeline task and release mechanic if no more tasks."""
        self.update_pipeline_status(pipeline_id, "Done")
        pending = self.get_mechanic_pipeline(mechanic_id)
        if not pending:
            self.release_mechanic(mechanic_id)
    
    def get_workload_summary(self):
        """Get workload summary for all mechanics."""
        mechanics = self.get_all_mechanics()
        pipeline = self._read_csv(self.pipeline_file)
        
        summary = []
        for m in mechanics:
            mid = m["mechanic_id"]
            active_tasks = [p for p in pipeline if p.get("mechanic_id") == mid and p.get("status") != "Done"]
            summary.append({
                "mechanic_id": mid,
                "name": m["name"],
                "specialization": m.get("specialization", ""),
                "status": m.get("status", ""),
                "skill_level": m.get("skill_level", ""),
                "active_tasks": len(active_tasks),
                "tasks": active_tasks
            })
        return summary
