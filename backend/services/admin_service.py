"""
AutoMech AI - Admin Service
Handles attendance, salary, performance analytics, insurance, and admin features.
"""
import csv, os, hashlib
from datetime import datetime, date
from collections import defaultdict


from database import db

class AdminService:
    def __init__(self, data_dir):
        self.attendance_file = "attendance"
        self.salaries_file = "salaries"
        self.insurance_file = "insurance"
        self.admin_users_file = "admin_users"
        self.mechanics_file = "mechanics"
        self.jobcards_file = "jobcards"
        self.pipeline_file = "pipeline"

        self.att_headers = ["date", "mechanic_id", "mechanic_name", "status", "check_in", "check_out"]
        self.sal_headers = ["salary_id", "mechanic_id", "mechanic_name", "base_salary", "bonus", "deductions",
                            "net_salary", "month", "year", "paid", "paid_date", "notes"]
        self.ins_headers = ["insurance_id", "vehicle_reg", "owner_name", "owner_phone", "provider",
                            "policy_number", "expiry_date", "type", "premium", "status", "notes"]
        self.admin_headers = ["admin_id", "name", "role", "password_hash"]

        # Seed default admin if empty
        admins = self._read_csv(self.admin_users_file)
        if not admins:
            self._seed_default_admins()

    def _read_csv(self, file_key):
        if file_key == self.attendance_file:
            return list(db.attendance.find({}, {"_id": 0}))
        elif file_key == self.salaries_file:
            return list(db.salaries.find({}, {"_id": 0}))
        elif file_key == self.insurance_file:
            return list(db.insurance.find({}, {"_id": 0}))
        elif file_key == self.admin_users_file:
            return list(db.admin_users.find({}, {"_id": 0}))
        elif file_key == self.mechanics_file:
            return list(db.mechanics.find({}, {"_id": 0}))
        elif file_key == self.jobcards_file:
            return list(db.jobcards.find({}, {"_id": 0}))
        elif file_key == self.pipeline_file:
            return list(db.pipeline.find({}, {"_id": 0}))
        return []

    def _write_csv(self, file_key, headers, rows):
        collection_map = {
            self.attendance_file: db.attendance,
            self.salaries_file: db.salaries,
            self.insurance_file: db.insurance,
            self.admin_users_file: db.admin_users,
            self.mechanics_file: db.mechanics,
            self.jobcards_file: db.jobcards,
            self.pipeline_file: db.pipeline
        }
        col = collection_map.get(file_key)
        if col is not None:
            col.delete_many({})
            if rows:
                col.insert_many([{**r} for r in rows])

    def _hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def _seed_default_admins(self):
        defaults = [
            {"admin_id": "ADM-001", "name": "Admin", "role": "super_admin",
             "password_hash": self._hash_password("automech2024")},
            {"admin_id": "ADM-002", "name": "Accountant", "role": "accountant",
             "password_hash": self._hash_password("automech2024")},
            {"admin_id": "ADM-003", "name": "Mechanic Head", "role": "mechanic_head",
             "password_hash": self._hash_password("automech2024")},
            {"admin_id": "ADM-004", "name": "Insurance Admin", "role": "insurance_admin",
             "password_hash": self._hash_password("automech2024")},
        ]
        self._write_csv(self.admin_users_file, self.admin_headers, defaults)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # AUTHENTICATION
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def authenticate(self, password, role=None):
        """Authenticate admin by password. Returns admin info or None."""
        hashed = self._hash_password(password)
        admins = self._read_csv(self.admin_users_file)
        for admin in admins:
            if admin["password_hash"] == hashed:
                if role and admin["role"] != role and admin["role"] != "super_admin":
                    continue
                return {"admin_id": admin["admin_id"], "name": admin["name"], "role": admin["role"]}
        return None

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ATTENDANCE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def mark_attendance(self, mechanic_id, mechanic_name, status="Present", check_in="", check_out="", att_date=None):
        """Mark attendance for a mechanic. Status: Present, Absent, Half-Day, Leave."""
        rows = self._read_csv(self.attendance_file)
        today = att_date or date.today().isoformat()

        # Check if already marked today
        for r in rows:
            if r["mechanic_id"] == mechanic_id and r["date"] == today:
                r["status"] = status
                r["check_in"] = check_in or r.get("check_in", "")
                r["check_out"] = check_out or r.get("check_out", "")
                self._write_csv(self.attendance_file, self.att_headers, rows)
                return r

        record = {
            "date": today,
            "mechanic_id": mechanic_id,
            "mechanic_name": mechanic_name,
            "status": status,
            "check_in": check_in or datetime.now().strftime("%H:%M"),
            "check_out": check_out
        }
        rows.append(record)
        self._write_csv(self.attendance_file, self.att_headers, rows)
        return record

    def get_attendance(self, att_date=None, mechanic_id=None):
        """Get attendance records by date or mechanic."""
        rows = self._read_csv(self.attendance_file)
        if att_date:
            rows = [r for r in rows if r["date"] == att_date]
        if mechanic_id:
            rows = [r for r in rows if r["mechanic_id"] == mechanic_id]
        return rows

    def get_monthly_attendance(self, mechanic_id, month, year):
        """Get monthly attendance summary for a mechanic."""
        rows = self._read_csv(self.attendance_file)
        prefix = f"{year}-{month:02d}" if isinstance(month, int) else f"{year}-{month}"
        filtered = [r for r in rows if r["mechanic_id"] == mechanic_id and r["date"].startswith(prefix)]

        present = sum(1 for r in filtered if r["status"] == "Present")
        absent = sum(1 for r in filtered if r["status"] == "Absent")
        half_day = sum(1 for r in filtered if r["status"] == "Half-Day")
        leave = sum(1 for r in filtered if r["status"] == "Leave")

        return {
            "mechanic_id": mechanic_id,
            "month": prefix,
            "total_records": len(filtered),
            "present": present,
            "absent": absent,
            "half_day": half_day,
            "leave": leave,
            "effective_days": present + (half_day * 0.5),
            "records": filtered
        }

    def get_today_attendance(self):
        """Get today's attendance with all mechanics (marked + unmarked)."""
        mechanics = self._read_csv(self.mechanics_file)
        today = date.today().isoformat()
        attendance = self.get_attendance(att_date=today)
        marked_ids = {r["mechanic_id"] for r in attendance}

        result = []
        for m in mechanics:
            record = next((r for r in attendance if r["mechanic_id"] == m["mechanic_id"]), None)
            result.append({
                "mechanic_id": m["mechanic_id"],
                "mechanic_name": m["name"],
                "status": record["status"] if record else "Not Marked",
                "check_in": record.get("check_in", "") if record else "",
                "check_out": record.get("check_out", "") if record else "",
                "marked": m["mechanic_id"] in marked_ids
            })
        return result

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SALARY MANAGEMENT
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def create_salary_record(self, mechanic_id, mechanic_name, base_salary, bonus=0,
                              deductions=0, month=None, year=None, notes=""):
        """Create a monthly salary record."""
        rows = self._read_csv(self.salaries_file)
        now = datetime.now()
        month = month or now.month
        year = year or now.year

        # Check duplicate
        for r in rows:
            if r["mechanic_id"] == mechanic_id and str(r["month"]) == str(month) and str(r["year"]) == str(year):
                return {"error": f"Salary already exists for {mechanic_name} in {month}/{year}"}

        net = float(base_salary) + float(bonus) - float(deductions)
        salary_id = f"SAL-{len(rows) + 1:04d}"
        record = {
            "salary_id": salary_id,
            "mechanic_id": mechanic_id,
            "mechanic_name": mechanic_name,
            "base_salary": str(base_salary),
            "bonus": str(bonus),
            "deductions": str(deductions),
            "net_salary": str(net),
            "month": str(month),
            "year": str(year),
            "paid": "No",
            "paid_date": "",
            "notes": notes
        }
        rows.append(record)
        self._write_csv(self.salaries_file, self.sal_headers, rows)
        return record

    def get_salaries(self, month=None, year=None, mechanic_id=None):
        """Get salary records with optional filters."""
        rows = self._read_csv(self.salaries_file)
        if month:
            rows = [r for r in rows if str(r["month"]) == str(month)]
        if year:
            rows = [r for r in rows if str(r["year"]) == str(year)]
        if mechanic_id:
            rows = [r for r in rows if r["mechanic_id"] == mechanic_id]
        return rows

    def mark_salary_paid(self, salary_id):
        """Mark a salary as paid."""
        rows = self._read_csv(self.salaries_file)
        for r in rows:
            if r["salary_id"] == salary_id:
                r["paid"] = "Yes"
                r["paid_date"] = datetime.now().strftime("%Y-%m-%d")
                self._write_csv(self.salaries_file, self.sal_headers, rows)
                return r
        return None

    def get_salary_summary(self):
        """Get overall salary statistics."""
        rows = self._read_csv(self.salaries_file)
        total_paid = sum(float(r.get("net_salary", 0)) for r in rows if r["paid"] == "Yes")
        total_pending = sum(float(r.get("net_salary", 0)) for r in rows if r["paid"] == "No")
        return {
            "total_records": len(rows),
            "total_paid": total_paid,
            "total_pending": total_pending,
            "unpaid_count": sum(1 for r in rows if r["paid"] == "No"),
        }

    def check_salary_reminder(self):
        """Check if today is the 10th — return pending salary info for reminders."""
        today = date.today()
        if today.day == 10:
            now = datetime.now()
            month = now.month
            year = now.year
            pending = [r for r in self._read_csv(self.salaries_file)
                       if r["paid"] == "No" and str(r["month"]) == str(month) and str(r["year"]) == str(year)]
            mechanics = self._read_csv(self.mechanics_file)
            # Also include mechanics without any salary record this month
            existing_ids = {r["mechanic_id"] for r in pending}
            missing = [m for m in mechanics if m["mechanic_id"] not in existing_ids]

            return {
                "is_reminder_day": True,
                "pending_salaries": pending,
                "mechanics_without_salary": [{"mechanic_id": m["mechanic_id"], "name": m["name"]} for m in missing],
                "message": f"⚠️ Salary Reminder: {len(pending)} pending salaries for {month}/{year}. "
                           f"{len(missing)} mechanics have no salary record this month."
            }
        return {"is_reminder_day": False, "message": "Today is not the 10th. No reminder needed."}

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PERFORMANCE ANALYTICS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def get_performance(self, mechanic_id=None):
        """Get performance analytics for mechanics."""
        mechanics = self._read_csv(self.mechanics_file)
        jobcards = self._read_csv(self.jobcards_file)
        pipeline = self._read_csv(self.pipeline_file)
        attendance = self._read_csv(self.attendance_file)

        results = []
        for m in mechanics:
            mid = m["mechanic_id"]
            if mechanic_id and mid != mechanic_id:
                continue

            # Count completed jobs
            completed = [j for j in jobcards if j.get("assigned_mechanic_id") == mid and j.get("status") == "Completed"]
            pending = [j for j in jobcards if j.get("assigned_mechanic_id") == mid and j.get("status") != "Completed"]
            total_jobs = [j for j in jobcards if j.get("assigned_mechanic_id") == mid]

            # Pipeline tasks
            done_tasks = [p for p in pipeline if p.get("mechanic_id") == mid and p.get("status") == "Done"]
            active_tasks = [p for p in pipeline if p.get("mechanic_id") == mid and p.get("status") != "Done"]

            # Attendance stats
            att_records = [a for a in attendance if a["mechanic_id"] == mid]
            present_days = sum(1 for a in att_records if a["status"] == "Present")
            total_att_days = len(att_records) if att_records else 1

            # Completion rate
            completion_rate = round(len(completed) / max(len(total_jobs), 1) * 100, 1)

            # Avg repair time (from pipeline done tasks)
            avg_time = 0
            time_count = 0
            for t in done_tasks:
                if t.get("start_time") and t.get("actual_end"):
                    try:
                        start = datetime.strptime(t["start_time"], "%Y-%m-%d %H:%M:%S")
                        end = datetime.strptime(t["actual_end"], "%Y-%m-%d %H:%M:%S")
                        hours = (end - start).total_seconds() / 3600
                        if 0 < hours < 200:  # sanity check
                            avg_time += hours
                            time_count += 1
                    except (ValueError, TypeError):
                        pass
            avg_time = round(avg_time / max(time_count, 1), 1)

            results.append({
                "mechanic_id": mid,
                "name": m["name"],
                "specialization": m.get("specialization", ""),
                "skill_level": m.get("skill_level", ""),
                "total_jobs": len(total_jobs),
                "completed_jobs": len(completed),
                "pending_jobs": len(pending),
                "completion_rate": completion_rate,
                "active_pipeline_tasks": len(active_tasks),
                "completed_pipeline_tasks": len(done_tasks),
                "avg_repair_time_hrs": avg_time,
                "present_days": present_days,
                "total_attendance_records": len(att_records),
                "attendance_rate": round(present_days / max(total_att_days, 1) * 100, 1),
            })

        results.sort(key=lambda x: x["completed_jobs"], reverse=True)
        return results

    def get_mechanic_of_month(self, month=None, year=None):
        """Auto-calculate Mechanic of the Month."""
        now = datetime.now()
        month = month or now.month
        year = year or now.year
        prefix = f"{year}-{month:02d}" if isinstance(month, int) else f"{year}-{month}"

        mechanics = self._read_csv(self.mechanics_file)
        jobcards = self._read_csv(self.jobcards_file)
        attendance = self._read_csv(self.attendance_file)

        scores = []
        for m in mechanics:
            mid = m["mechanic_id"]

            # Jobs completed this month
            completed_this_month = sum(1 for j in jobcards
                                        if j.get("assigned_mechanic_id") == mid
                                        and j.get("status") == "Completed"
                                        and j.get("completed_at", "").startswith(prefix))
            total_this_month = sum(1 for j in jobcards
                                    if j.get("assigned_mechanic_id") == mid
                                    and j.get("created_at", "").startswith(prefix))

            # Attendance this month
            att_month = [a for a in attendance if a["mechanic_id"] == mid and a["date"].startswith(prefix)]
            present = sum(1 for a in att_month if a["status"] == "Present")
            half_day = sum(1 for a in att_month if a["status"] == "Half-Day")
            leaves = sum(1 for a in att_month if a["status"] in ("Absent", "Leave"))

            # Score formula:
            # vehicles_completed × 3 + attendance_days × 2 - leaves × 1
            score = (completed_this_month * 3) + (present * 2) + (half_day * 1) - (leaves * 1)

            scores.append({
                "mechanic_id": mid,
                "name": m["name"],
                "specialization": m.get("specialization", ""),
                "completed_jobs": completed_this_month,
                "total_jobs": total_this_month,
                "present_days": present,
                "half_days": half_day,
                "leaves": leaves,
                "score": score
            })

        scores.sort(key=lambda x: x["score"], reverse=True)
        winner = scores[0] if scores else None
        return {
            "month": prefix,
            "winner": winner,
            "all_scores": scores
        }

    def get_employee_of_year(self, year=None):
        """Calculate Employee of the Year based on annual cumulative scores."""
        year = year or datetime.now().year
        mechanics = self._read_csv(self.mechanics_file)

        annual_scores = []
        for m in mechanics:
            total_score = 0
            monthly_data = []
            for month in range(1, 13):
                motm = self.get_mechanic_of_month(month, year)
                for s in motm["all_scores"]:
                    if s["mechanic_id"] == m["mechanic_id"]:
                        total_score += s["score"]
                        monthly_data.append({"month": month, "score": s["score"]})
                        break

            annual_scores.append({
                "mechanic_id": m["mechanic_id"],
                "name": m["name"],
                "specialization": m.get("specialization", ""),
                "annual_score": total_score,
                "monthly_breakdown": monthly_data
            })

        annual_scores.sort(key=lambda x: x["annual_score"], reverse=True)
        winner = annual_scores[0] if annual_scores else None
        return {
            "year": year,
            "winner": winner,
            "all_scores": annual_scores
        }

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # LIVE STATUS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def get_live_status(self):
        """Get real-time mechanic-vehicle mapping from pipeline + jobcards."""
        mechanics = self._read_csv(self.mechanics_file)
        pipeline = self._read_csv(self.pipeline_file)
        jobcards = self._read_csv(self.jobcards_file)

        jc_map = {j["jobcard_id"]: j for j in jobcards}
        result = []

        for m in mechanics:
            mid = m["mechanic_id"]
            active = [p for p in pipeline if p.get("mechanic_id") == mid and p.get("status") != "Done"]

            vehicles = []
            for task in active:
                jc = jc_map.get(task.get("jobcard_id", ""), {})
                vehicles.append({
                    "jobcard_id": task.get("jobcard_id", ""),
                    "vehicle": f"{jc.get('vehicle_make', '')} {jc.get('vehicle_model', '')}".strip() or "Unknown",
                    "vehicle_reg": jc.get("vehicle_reg", ""),
                    "owner": jc.get("owner_name", ""),
                    "task": task.get("task_description", ""),
                    "priority": task.get("priority", ""),
                    "status": task.get("status", ""),
                    "start_time": task.get("start_time", ""),
                })

            result.append({
                "mechanic_id": mid,
                "name": m["name"],
                "specialization": m.get("specialization", ""),
                "status": m.get("status", ""),
                "current_jobs": int(m.get("current_jobs", 0)),
                "vehicles": vehicles
            })

        return result

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # INSURANCE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def add_insurance(self, vehicle_reg, owner_name, owner_phone, provider, policy_number,
                      expiry_date, ins_type, premium, status="Active", notes=""):
        """Add an insurance record."""
        rows = self._read_csv(self.insurance_file)
        ins_id = f"INS-{len(rows) + 1:04d}"
        record = {
            "insurance_id": ins_id,
            "vehicle_reg": vehicle_reg,
            "owner_name": owner_name,
            "owner_phone": owner_phone,
            "provider": provider,
            "policy_number": policy_number,
            "expiry_date": expiry_date,
            "type": ins_type,
            "premium": str(premium),
            "status": status,
            "notes": notes
        }
        rows.append(record)
        self._write_csv(self.insurance_file, self.ins_headers, rows)
        return record

    def get_insurance(self, status=None):
        """Get insurance records."""
        rows = self._read_csv(self.insurance_file)
        if status:
            rows = [r for r in rows if r.get("status", "").lower() == status.lower()]
        return rows

    def update_insurance(self, insurance_id, updates):
        """Update an insurance record."""
        rows = self._read_csv(self.insurance_file)
        for r in rows:
            if r["insurance_id"] == insurance_id:
                for k, v in updates.items():
                    if k in self.ins_headers:
                        r[k] = v
                self._write_csv(self.insurance_file, self.ins_headers, rows)
                return r
        return None

    def delete_insurance(self, insurance_id):
        """Delete an insurance record."""
        rows = self._read_csv(self.insurance_file)
        rows = [r for r in rows if r["insurance_id"] != insurance_id]
        self._write_csv(self.insurance_file, self.ins_headers, rows)
        return True

    def get_expiring_insurance(self, days=30):
        """Get insurance policies expiring within N days."""
        rows = self._read_csv(self.insurance_file)
        today = date.today()
        expiring = []
        for r in rows:
            try:
                exp = datetime.strptime(r["expiry_date"], "%Y-%m-%d").date()
                diff = (exp - today).days
                if 0 <= diff <= days:
                    r["days_until_expiry"] = diff
                    expiring.append(r)
                elif diff < 0:
                    r["days_until_expiry"] = diff
                    r["status"] = "Expired"
                    expiring.append(r)
            except (ValueError, KeyError):
                pass
        expiring.sort(key=lambda x: x.get("days_until_expiry", 999))
        return expiring

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ADMIN DASHBOARD STATS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def get_admin_dashboard(self):
        """Get overview stats for admin dashboard."""
        mechanics = self._read_csv(self.mechanics_file)
        jobcards = self._read_csv(self.jobcards_file)
        attendance = self.get_today_attendance()
        salary_summary = self.get_salary_summary()
        insurance = self._read_csv(self.insurance_file)
        expiring = self.get_expiring_insurance(30)

        present_today = sum(1 for a in attendance if a["status"] == "Present")
        absent_today = sum(1 for a in attendance if a["status"] in ("Absent", "Not Marked"))

        total_completed = sum(1 for j in jobcards if j.get("status") == "Completed")
        total_pending = sum(1 for j in jobcards if j.get("status") != "Completed")

        now = datetime.now()
        motm = self.get_mechanic_of_month(now.month, now.year)

        return {
            "total_mechanics": len(mechanics),
            "present_today": present_today,
            "absent_today": absent_today,
            "total_jobs_completed": total_completed,
            "total_jobs_pending": total_pending,
            "salary_summary": salary_summary,
            "total_insurance": len(insurance),
            "expiring_soon": len(expiring),
            "mechanic_of_month": motm.get("winner"),
            "live_status": self.get_live_status()
        }
