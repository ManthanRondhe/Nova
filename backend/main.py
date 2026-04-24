"""
Nova AI - FastAPI Main Application
"""
import os, sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from config import config

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Initialize services
from services.diagnosis_engine import DiagnosisEngine
from services.jobcard_manager import JobCardManager
from services.mechanic_scheduler import MechanicScheduler
from services.inventory_manager import InventoryManager
from services.order_manager import OrderManager
from services.notification_service import NotificationService
from services.estimation_engine import EstimationEngine
from services.admin_service import AdminService

diagnosis_engine = DiagnosisEngine(config.DATA_DIR)
jobcard_manager = JobCardManager(config.DATA_DIR)
mechanic_scheduler = MechanicScheduler(config.DATA_DIR)
inventory_manager = InventoryManager(config.DATA_DIR)
order_manager = OrderManager(config.DATA_DIR)
notification_service = NotificationService()
estimation_engine = EstimationEngine(config.DATA_DIR)
admin_service = AdminService(config.DATA_DIR)

# Create FastAPI app
app = FastAPI(title=config.APP_NAME, version=config.VERSION,
              description="Voice-Powered Intelligent Garage Management Assistant")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# API ROUTES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# ─── Dashboard ─────────────────────────────────
@app.get("/api/dashboard")
async def get_dashboard():
    """Get dashboard statistics."""
    return {
        "jobcards": jobcard_manager.get_stats(),
        "inventory": inventory_manager.get_inventory_stats(),
        "orders": order_manager.get_order_stats(),
        "mechanics": {
            "total": len(mechanic_scheduler.get_all_mechanics()),
            "available": len([m for m in mechanic_scheduler.get_all_mechanics() if m.get("status") == "Available"]),
            "busy": len([m for m in mechanic_scheduler.get_all_mechanics() if m.get("status") == "Busy"])
        },
        "telegram": notification_service.get_telegram_bot_info()
    }

# ─── Diagnosis ─────────────────────────────────
@app.post("/api/diagnose")
async def diagnose(data: dict):
    """Diagnose vehicle fault from symptoms."""
    query = data.get("query", "")
    vehicle_type = data.get("vehicle_type", None)
    vehicle_model = data.get("vehicle_model", None)
    top_n = data.get("top_n", 5)
    
    if not query:
        return {"error": "No query provided", "results": []}
    
    results = diagnosis_engine.diagnose(query, vehicle_type, vehicle_model, top_n)
    system = diagnosis_engine.detect_system(query)
    severity = diagnosis_engine.detect_severity(query)
    
    # Generate estimates for top result
    estimate = None
    if results:
        estimate = estimation_engine.estimate(results[0])
    
    return {
        "query": query,
        "detected_system": system,
        "detected_severity": severity,
        "results": results,
        "top_estimate": estimate,
        "total_matches": len(results)
    }

# ─── Job Cards ─────────────────────────────────
@app.get("/api/jobcards")
async def get_jobcards(status: str = None):
    return {"jobcards": jobcard_manager.get_all_jobcards(status)}

@app.post("/api/jobcards")
async def create_jobcard(data: dict):
    """Create job card with auto-diagnosis, auto-assign, auto-notify."""
    # Run diagnosis
    complaint = data.get("complaint", "")
    diagnosis = None
    if complaint:
        results = diagnosis_engine.diagnose(complaint, data.get("vehicle_type"), data.get("vehicle_model"))
        if results:
            diagnosis = results[0]
    
    # Auto-assign mechanic
    system = diagnosis_engine.detect_system(complaint) if complaint else None
    mechanic = mechanic_scheduler.auto_assign(system, diagnosis.get("severity", "Medium") if diagnosis else "Medium")
    
    # Create job card
    jobcard = jobcard_manager.create_jobcard(
        vehicle_make=data.get("vehicle_make", ""),
        vehicle_model=data.get("vehicle_model", ""),
        vehicle_year=data.get("vehicle_year", ""),
        vehicle_reg=data.get("vehicle_reg", ""),
        owner_name=data.get("owner_name", ""),
        owner_phone=data.get("owner_phone", ""),
        complaint=complaint,
        diagnosis=diagnosis,
        mechanic=mechanic
    )
    
    # Generate estimate
    estimate = estimation_engine.estimate(diagnosis) if diagnosis else None
    
    # Check parts availability
    parts_check = None
    orders_created = []
    if diagnosis and diagnosis.get("required_parts"):
        parts_check = inventory_manager.check_parts_availability(diagnosis["required_parts"])
        # Auto-order missing parts
        if parts_check.get("missing"):
            orders_created = order_manager.auto_order_missing_parts(
                parts_check["missing"], jobcard["jobcard_id"]
            )
    
    # Add to pipeline
    if mechanic:
        task_desc = f"{diagnosis['fault_name']} - {complaint}" if diagnosis else complaint
        mechanic_scheduler.add_to_pipeline(
            mechanic["mechanic_id"], mechanic["name"],
            jobcard["jobcard_id"], task_desc,
            jobcard.get("priority", "Medium")
        )
    
    # Send notifications
    notification_result = None
    if mechanic:
        notification_result = notification_service.notify_mechanic_assignment(mechanic, jobcard, diagnosis)
    
    # Notify dealers for orders
    order_notifications = []
    for order in orders_created:
        dealer = order.get("dealer")
        if dealer:
            notif = notification_service.notify_dealer_order(dealer, order)
            order_notifications.append(notif)
    
    return {
        "jobcard": jobcard,
        "diagnosis": diagnosis,
        "estimate": estimate,
        "assigned_mechanic": mechanic,
        "parts_availability": parts_check,
        "orders_created": orders_created,
        "notification": notification_result,
        "order_notifications": order_notifications,
        "message": f"Job card {jobcard['jobcard_id']} created successfully" + 
                   (f". Assigned to {mechanic['name']}" if mechanic else ". No mechanic available")
    }

@app.put("/api/jobcards/{jc_id}")
async def update_jobcard(jc_id: str, data: dict):
    result = jobcard_manager.update_jobcard(jc_id, data)
    return {"jobcard": result}

@app.put("/api/jobcards/{jc_id}/complete")
async def complete_jobcard(jc_id: str, data: dict = {}):
    result = jobcard_manager.complete_jobcard(jc_id, data.get("actual_cost", ""))
    # Release mechanic
    if result:
        mid = result.get("assigned_mechanic_id")
        if mid:
            mechanic_scheduler.release_mechanic(mid)
    return {"jobcard": result}

@app.delete("/api/jobcards/{jc_id}")
async def delete_jobcard(jc_id: str):
    jobcard_manager.delete_jobcard(jc_id)
    return {"success": True}

# ─── Mechanics ─────────────────────────────────
@app.get("/api/mechanics")
async def get_mechanics():
    return {"mechanics": mechanic_scheduler.get_all_mechanics()}

@app.post("/api/mechanics")
async def add_mechanic(data: dict):
    m = mechanic_scheduler.add_mechanic(
        name=data.get("name", ""),
        phone=data.get("phone", ""),
        specialization=data.get("specialization", "General"),
        skill_level=data.get("skill_level", "Senior"),
        telegram_chat_id=data.get("telegram_chat_id", "")
    )
    return {"mechanic": m}

@app.put("/api/mechanics/{mid}")
async def update_mechanic(mid: str, data: dict):
    return {"mechanic": mechanic_scheduler.update_mechanic(mid, data)}

@app.delete("/api/mechanics/{mid}")
async def delete_mechanic(mid: str):
    mechanic_scheduler.delete_mechanic(mid)
    return {"success": True}

@app.put("/api/mechanics/{mid}/status")
async def set_mechanic_status(mid: str, data: dict):
    return {"mechanic": mechanic_scheduler.set_mechanic_status(mid, data.get("status", "Available"))}

# ─── Inventory ─────────────────────────────────
@app.get("/api/inventory")
async def get_inventory():
    return {"inventory": inventory_manager.get_all_inventory()}

@app.get("/api/inventory/alerts")
async def get_inventory_alerts():
    return {"alerts": inventory_manager.get_low_stock_alerts()}

@app.get("/api/inventory/search/{query}")
async def search_inventory(query: str):
    return {"results": inventory_manager.search_parts(query)}

@app.put("/api/inventory/{part_id}/add")
async def add_stock(part_id: str, data: dict):
    result = inventory_manager.add_stock(part_id, int(data.get("quantity", 1)))
    return {"part": result}

@app.get("/api/parts")
async def get_parts_catalog():
    return {"parts": inventory_manager.get_parts_catalog()}

# ─── Dealers ───────────────────────────────────
@app.get("/api/dealers")
async def get_dealers():
    return {"dealers": order_manager.get_all_dealers()}

@app.post("/api/dealers")
async def add_dealer(data: dict):
    d = order_manager.add_dealer(
        name=data.get("name", ""),
        phone=data.get("phone", ""),
        email=data.get("email", ""),
        parts_category=data.get("parts_category", "General"),
        location=data.get("location", ""),
        delivery_time_days=int(data.get("delivery_time_days", 2)),
        rating=int(data.get("rating", 4)),
        telegram_chat_id=data.get("telegram_chat_id", "")
    )
    return {"dealer": d}

@app.put("/api/dealers/{did}")
async def update_dealer(did: str, data: dict):
    return {"dealer": order_manager.update_dealer(did, data)}

@app.delete("/api/dealers/{did}")
async def delete_dealer(did: str):
    order_manager.delete_dealer(did)
    return {"success": True}

# ─── Orders ────────────────────────────────────
@app.get("/api/orders")
async def get_orders(status: str = None):
    return {"orders": order_manager.get_all_orders(status)}

@app.put("/api/orders/{oid}/status")
async def update_order_status(oid: str, data: dict):
    result = order_manager.update_order_status(oid, data.get("status", ""))
    # If delivered, add to inventory
    if data.get("status") == "Delivered" and result:
        inventory_manager.add_stock(result["part_id"], int(result.get("quantity", 1)))
    return {"order": result}

# ─── Pipeline ──────────────────────────────────
@app.get("/api/pipeline")
async def get_pipeline():
    return {"pipeline": mechanic_scheduler.get_full_pipeline()}

@app.get("/api/pipeline/workload")
async def get_workload():
    return {"workload": mechanic_scheduler.get_workload_summary()}

@app.put("/api/pipeline/{pid}/status")
async def update_pipeline(pid: str, data: dict):
    status = data.get("status", "")
    mechanic_id = data.get("mechanic_id", "")
    if status == "Done" and mechanic_id:
        mechanic_scheduler.complete_pipeline_task(pid, mechanic_id)
    else:
        mechanic_scheduler.update_pipeline_status(pid, status)
    return {"success": True}

# ─── Estimates ─────────────────────────────────
@app.post("/api/estimate")
async def get_estimate(data: dict):
    query = data.get("query", "")
    if query:
        results = diagnosis_engine.diagnose(query, top_n=3)
        if results:
            estimates = [estimation_engine.estimate(r) for r in results]
            return {"estimates": estimates, "diagnosis_results": results}
    return {"estimates": [], "diagnosis_results": []}

# ─── Notifications ─────────────────────────────
@app.get("/api/notifications")
async def get_notifications():
    return {"notifications": notification_service.get_notification_log(50)}

@app.get("/api/telegram/status")
async def telegram_status():
    return notification_service.get_telegram_bot_info()

# ─── Voice Command Processing ─────────────────
@app.post("/api/voice/process")
async def process_voice(data: dict):
    """Process a voice command and route to appropriate service."""
    text = data.get("text", "").lower().strip()
    context = data.get("context", [])
    
    if not text:
        return {"response": "I didn't catch that. Could you please repeat?", "action": "none"}
    
    # Parse structured context to track conversation state
    recent_user_msgs = []
    last_assistant_msg = ""
    for msg in context:
        if isinstance(msg, dict):
            if msg.get("role") == "user":
                recent_user_msgs.append(msg.get("text", ""))
            elif msg.get("role") == "assistant":
                last_assistant_msg = msg.get("text", "")
        elif isinstance(msg, str):
            recent_user_msgs.append(msg)
            
    is_answering_followup = (
        "tell me what you find" in last_assistant_msg.lower() or 
        "first step" in last_assistant_msg.lower() or
        "catching hints of" in last_assistant_msg.lower() or
        "need more details" in last_assistant_msg.lower() or
        "let's not guess" in last_assistant_msg.lower()
    )
    
    # Combine context with current text for better diagnosis if it's a diagnostic query
    full_text = " ".join(recent_user_msgs).lower() + " " + text if recent_user_msgs else text
    
    # 1. Intent classification - Priority 1: Explicit Action Commands (using current text)
    if any(kw in text for kw in ["new job", "job card", "new vehicle", "vehicle arrived", "create job", "register vehicle"]):
        return {"response": "I'll create a new job card. Please provide the vehicle details - make, model, year, and registration number.", 
                "action": "create_jobcard", "data": {}}
    
    elif any(kw in text for kw in ["inventory", "stock", "parts available", "spare", "check part"]):
        # 1. Reverse part matching (check if any part name is in the sentence)
        all_parts = inventory_manager.get_all_inventory()
        found_parts = []
        for p in all_parts:
            name_lower = p['part_name'].lower()
            simplified_name = name_lower.replace("assembly", "").replace("set", "").replace("kit", "").replace("service", "").strip()
            
            if simplified_name and simplified_name in text:
                found_parts.append(p)
            elif p['part_id'].lower() in text:
                found_parts.append(p)
                
        # 2. Try the old query approach if reverse match didn't find anything
        if not found_parts:
            query = text
            for word in ["do we have", "how many", "is there any", "check", "inventory", "stock", "parts", "available", "spare", "part", "in our", "tell me"]:
                query = query.replace(word, "")
            query = query.strip()
            
            if query and len(query) > 2:
                found_parts = inventory_manager.search_parts(query)
                
        if found_parts:
            part = found_parts[0]
            response = f"{part['part_name']} - Current stock: {part['current_stock']} units. "
            if int(part.get('current_stock', 0)) <= int(part.get('min_stock_level', 0)):
                response += "Warning: Stock is below minimum level!"
            return {"response": response, "action": "inventory", "data": {"results": found_parts}}
        
        # 3. Fallback to general inventory overview
        alerts = inventory_manager.get_low_stock_alerts()
        stats = inventory_manager.get_inventory_stats()
        response = (f"Inventory Overview: {stats['total_items']} items, {stats['total_stock_units']} total units. "
                    f"{stats['low_stock_count']} items below minimum stock. "
                    f"Total inventory value: Rs {stats['total_inventory_value']:,}.")
        return {"response": response, "action": "inventory", "data": {"stats": stats, "alerts": alerts}}
    
    elif any(kw in text for kw in ["mechanic", "who is available", "available mechanic", "assign"]):
        mechanics = mechanic_scheduler.get_all_mechanics()
        available = [m for m in mechanics if m.get("status") == "Available"]
        response = f"We have {len(mechanics)} mechanics. {len(available)} are currently available. "
        if available:
            names = ", ".join(m["name"] for m in available[:5])
            response += f"Available: {names}."
        return {"response": response, "action": "mechanics", "data": {"mechanics": mechanics}}
    
    elif any(kw in text for kw in ["estimate", "cost", "how much", "price", "charge"]):
        results = diagnosis_engine.diagnose(text, top_n=1)
        if results:
            est = estimation_engine.estimate(results[0])
            response = (f"For {results[0]['fault_name']}: "
                       f"Parts cost Rs {est['parts_cost']}. Labour Rs {est['labour_cost']} ({est['labour_hours']} hours). "
                       f"Total estimate: Rs {est['total_estimate_min']} to Rs {est['total_estimate_max']}.")
            return {"response": response, "action": "estimate", "data": {"estimate": est}}
        return {"response": "Please describe the problem so I can estimate the repair cost.", "action": "estimate", "data": {}}
    
    elif any(kw in text for kw in ["order", "dealer", "supplier", "restock"]):
        # Handle "restock" logic first
        if "restock" in text:
            alerts = inventory_manager.get_low_stock_alerts()
            if not alerts:
                return {"response": "All parts are currently above their minimum stock levels. No restocking needed.", "action": "orders", "data": {}}
            
            # Use auto-order for missing parts (handles finding best dealer and creating order)
            orders_created = order_manager.auto_order_missing_parts(alerts, "Restock")
            
            # Send Notifications
            for order in orders_created:
                dealer = order.get("dealer")
                if dealer:
                    notification_service.notify_dealer_order(dealer, order)
            
            response = f"I have automatically placed orders for {len(orders_created)} low stock parts via Telegram."
            return {"response": response, "action": "orders", "data": {"orders_created": orders_created}}
        
        # Handle explicit "order [part_name]" logic
        if "order" in text and len(text.split("order")) > 1:
            part_query = text.split("order")[-1].strip()
            # Attempt to find the part
            found_parts = inventory_manager.search_parts(part_query)
            if found_parts:
                part = found_parts[0]
                # To use auto_order, fake an alert format temporarily
                part["deficit"] = "1" # Default order 1 unit if not specified
                orders_created = order_manager.auto_order_missing_parts([part], "Direct Order")
                
                for order in orders_created:
                    dealer = order.get("dealer")
                    if dealer:
                        notification_service.notify_dealer_order(dealer, order)
                
                response = f"I have automatically placed an order for {part['part_name']} via Telegram."
                return {"response": response, "action": "orders", "data": {"orders_created": orders_created}}

        # Fallback to order tracking
        orders = order_manager.get_all_orders()
        pending = [o for o in orders if o.get("status") == "Ordered"]
        response = f"We have {len(orders)} total orders. {len(pending)} are currently pending delivery."
        return {"response": response, "action": "orders", "data": {"orders": orders}}
    
    elif any(kw in text for kw in ["pipeline", "workload", "schedule", "queue"]):
        workload = mechanic_scheduler.get_workload_summary()
        response = "Current workload: "
        for w in workload:
            response += f"{w['name']}: {w['active_tasks']} active tasks. "
        return {"response": response, "action": "pipeline", "data": {"workload": workload}}
    
    elif any(kw in text for kw in ["dashboard", "overview", "summary", "status"]):
        stats = jobcard_manager.get_stats()
        inv = inventory_manager.get_inventory_stats()
        response = (f"Garage Overview: {stats['total']} total job cards. "
                   f"{stats['in_progress']} in progress, {stats['pending']} pending. "
                   f"{stats['urgent']} urgent jobs. "
                   f"Inventory: {inv['low_stock_count']} low stock alerts.")
        return {"response": response, "action": "dashboard", "data": {"jobcard_stats": stats, "inventory_stats": inv}}
    
    elif any(kw in text for kw in ["hello", "hi", "hey", "good morning", "good afternoon"]):
        return {"response": "Morning junior! I'm Nova AI, the senior master tech here. Tell me the symptoms, and I'll walk you through the diagnosis step by step. What are we working on today?", 
                "action": "greeting", "data": {}}
    
    elif any(kw in text for kw in ["thank", "thanks", "bye", "goodbye"]):
        return {"response": "You got it, junior. Keep learning and call me if you get stuck on the next one.", 
                "action": "farewell", "data": {}}

    # 2. Intent classification - Priority 2: Context-aware Diagnosis
    elif is_answering_followup or any(kw in full_text for kw in ["diagnose", "problem", "issue", "wrong", "fault", "symptom", "noise", "smoke", "leak", "not working", "not starting"]):
        results = diagnosis_engine.diagnose(full_text, top_n=3)
        if results:
            top = results[0]
            
            # --- CONFIDENCE BOOST LOGIC ---
            user_confirmed = False
            if is_answering_followup:
                import re
                followup_keywords = set(re.findall(r'\b\w{4,}\b', last_assistant_msg.lower()))
                user_keywords = set(re.findall(r'\b\w{4,}\b', text.lower()))
                is_positive = any(w in text.lower() for w in ["yes", "yeah", "yep", "it does", "it is", "exactly", "true", "correct"])
                is_negative = any(w in text.lower() for w in ["no", "nope", "doesn't", "does not", "isn't", "is not", "false"])
                
                if (followup_keywords & user_keywords) or (is_positive and not is_negative):
                    top['confidence'] = min(0.95, top['confidence'] + 0.40)
                    user_confirmed = True
                elif is_negative:
                    # They denied it. Lower confidence.
                    top['confidence'] = max(0.10, top['confidence'] - 0.40)

            # Prevent repeating exact same question
            if top.get('followup_question') and top['followup_question'] in last_assistant_msg and top['confidence'] < 0.85 and not user_confirmed:
                # We asked this, they didn't confirm or deny clearly, but we can't ask it again.
                top['confidence'] = 0.85
            # --------------------------------
            
            estimate = estimation_engine.estimate(top)
            
            # Senior Mechanic Persona Logic
            first_step = top.get('fix_procedure', 'Check the basics').split('.')[0]
            symptoms = top.get('matched_symptom', '').split(',')
            primary_symptom = symptoms[0].strip() if symptoms else "any other signs"
            
            if top['confidence'] < 0.50:
                follow_up = top.get('followup_question', f"Are you also noticing {primary_symptom}?")
                response = f"Hmm, that's not enough to go on, junior. I need more details. {follow_up}"
                action = "diagnosis_followup"
            elif top['confidence'] < 0.85: 
                follow_up = top.get('followup_question', f"First step: {first_step}. Can you check that and tell me what you find?")
                response = f"Alright, listen up. My gut says this is {top['fault_name']}, but let's not guess. {follow_up}"
                action = "diagnosis_followup"
            else:
                prefix = "Good job checking that. Based on your findings, " if is_answering_followup else "This is a textbook case. "
                response = (f"{prefix}It's definitely {top['fault_name']}. "
                           f"Here's the plan to fix it: {top['fix_procedure']}. "
                           f"It'll take about {estimate['estimated_time_hours']} hours. Get on it!")
                action = "diagnosis"
                
                # Check required parts and auto-order if missing
                if top.get("required_parts"):
                    parts_check = inventory_manager.check_parts_availability(top["required_parts"])
                    if parts_check.get("missing"):
                        orders_created = order_manager.auto_order_missing_parts(
                            parts_check["missing"], "Diagnosis Auto-Order"
                        )
                        for order in orders_created:
                            dealer = order.get("dealer")
                            if dealer:
                                notification_service.notify_dealer_order(dealer, order)
                        
                        missing_names = ", ".join([p.get("part_name", "Unknown part") for p in parts_check["missing"]])
                        response += f" We do not have {missing_names} in our inventory, so I have automatically placed an order for them without asking."
                
            return {"response": response, "action": action, "data": {"results": results, "estimate": estimate}}
            
        return {"response": "You're not giving me much to work with, junior. Describe exactly what's happening. What does it sound like? Any smoke or leaks?", "action": "diagnosis_followup", "data": {}}
    
    else:
        # Try diagnosis as fallback using full context
        results = diagnosis_engine.diagnose(full_text, top_n=1)
        if results and results[0].get("confidence", 0) > 0.2:
            top = results[0]
            first_step = top.get('fix_procedure', 'Check the basics').split('.')[0]
            symptoms = top.get('matched_symptom', '').split(',')
            primary_symptom = symptoms[0].strip() if symptoms else "similar issues"
            
            if top['confidence'] < 0.60:
                follow_up = top.get('followup_question', f"Are you noticing {primary_symptom}?")
                response = f"I'm catching hints of {top['fault_name']}, but I need more details from you. {follow_up}"
            else:
                follow_up = top.get('followup_question', f"{first_step}? Do that and report back.")
                response = f"We might be looking at {top['fault_name']}. Let's test that theory. {follow_up}"
                
            return {"response": response, "action": "diagnosis_followup", "data": {"results": results}}
        
        return {"response": "Listen junior, I need more context. Describe the exact symptoms - sounds, leaks, smells, or how the car behaves. What's happening?",
                "action": "help", "data": {}}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ADMIN API ROUTES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.post("/api/admin/login")
async def admin_login(data: dict):
    """Authenticate admin by password."""
    password = data.get("password", "")
    result = admin_service.authenticate(password)
    if result:
        return {"success": True, "admin": result}
    return {"success": False, "error": "Invalid password"}

@app.get("/api/admin/dashboard")
async def admin_dashboard():
    """Admin dashboard overview stats."""
    return admin_service.get_admin_dashboard()

# ─── Attendance ────────────────────────────────
@app.get("/api/admin/attendance")
async def get_attendance(date: str = None, mechanic_id: str = None):
    if date is None and mechanic_id is None:
        return {"attendance": admin_service.get_today_attendance()}
    return {"attendance": admin_service.get_attendance(date, mechanic_id)}

@app.post("/api/admin/attendance")
async def mark_attendance(data: dict):
    record = admin_service.mark_attendance(
        mechanic_id=data.get("mechanic_id", ""),
        mechanic_name=data.get("mechanic_name", ""),
        status=data.get("status", "Present"),
        check_in=data.get("check_in", ""),
        check_out=data.get("check_out", ""),
        att_date=data.get("date", None)
    )
    return {"attendance": record}

@app.get("/api/admin/attendance/monthly/{mechanic_id}")
async def monthly_attendance(mechanic_id: str, month: int = None, year: int = None):
    from datetime import datetime as dt
    month = month or dt.now().month
    year = year or dt.now().year
    return admin_service.get_monthly_attendance(mechanic_id, month, year)

# ─── Salaries ──────────────────────────────────
@app.get("/api/admin/salaries/auto-calculate/{mechanic_id}")
async def auto_calculate_salary(mechanic_id: str, month: int = None, year: int = None):
    data = admin_service.auto_calculate_salary_preview(mechanic_id, month, year)
    return {"auto_calculated": data}

@app.get("/api/admin/salaries")
async def get_salaries(month: int = None, year: int = None, mechanic_id: str = None):
    return {"salaries": admin_service.get_salaries(month, year, mechanic_id)}

@app.post("/api/admin/salaries")
async def create_salary(data: dict):
    record = admin_service.create_salary_record(
        mechanic_id=data.get("mechanic_id", ""),
        mechanic_name=data.get("mechanic_name", ""),
        base_salary=data.get("base_salary", config.DEFAULT_BASE_SALARY),
        bonus=data.get("bonus", 0),
        deductions=data.get("deductions", 0),
        month=data.get("month"),
        year=data.get("year"),
        notes=data.get("notes", "")
    )
    return {"salary": record}

@app.put("/api/admin/salaries/{salary_id}/pay")
async def pay_salary(salary_id: str):
    result = admin_service.mark_salary_paid(salary_id)
    if result:
        return {"salary": result}
    return {"error": "Salary record not found"}

@app.get("/api/admin/salaries/summary")
async def salary_summary():
    return admin_service.get_salary_summary()

@app.get("/api/admin/salaries/reminder")
async def salary_reminder():
    reminder = admin_service.check_salary_reminder()
    if reminder.get("is_reminder_day") and config.ADMIN_TELEGRAM_CHAT_ID:
        notification_service.send_message(
            config.ADMIN_TELEGRAM_CHAT_ID, reminder["message"]
        )
    return reminder

# ─── Performance ───────────────────────────────
@app.get("/api/admin/performance")
async def get_performance():
    return {"performance": admin_service.get_performance()}

@app.get("/api/admin/performance/{mechanic_id}")
async def get_mechanic_performance(mechanic_id: str):
    result = admin_service.get_performance(mechanic_id)
    return {"performance": result[0] if result else None}

@app.get("/api/admin/mechanic-of-month")
async def mechanic_of_month(month: int = None, year: int = None):
    return admin_service.get_mechanic_of_month(month, year)

@app.get("/api/admin/employee-of-year")
async def employee_of_year(year: int = None):
    return admin_service.get_employee_of_year(year)

# ─── Live Status ───────────────────────────────
@app.get("/api/admin/live-status")
async def live_status():
    return {"status": admin_service.get_live_status()}

# ─── Insurance ─────────────────────────────────
@app.get("/api/admin/insurance")
async def get_insurance(status: str = None):
    return {"insurance": admin_service.get_insurance(status)}

@app.post("/api/admin/insurance")
async def add_insurance(data: dict):
    record = admin_service.add_insurance(
        vehicle_reg=data.get("vehicle_reg", ""),
        owner_name=data.get("owner_name", ""),
        owner_phone=data.get("owner_phone", ""),
        provider=data.get("provider", ""),
        policy_number=data.get("policy_number", ""),
        expiry_date=data.get("expiry_date", ""),
        ins_type=data.get("type", "Comprehensive"),
        premium=data.get("premium", 0),
        status=data.get("status", "Active"),
        notes=data.get("notes", "")
    )
    return {"insurance": record}

@app.put("/api/admin/insurance/{ins_id}")
async def update_insurance(ins_id: str, data: dict):
    result = admin_service.update_insurance(ins_id, data)
    return {"insurance": result}

@app.delete("/api/admin/insurance/{ins_id}")
async def delete_insurance(ins_id: str):
    admin_service.delete_insurance(ins_id)
    return {"success": True}

@app.get("/api/admin/insurance/expiring")
async def expiring_insurance(days: int = 30):
    return {"expiring": admin_service.get_expiring_insurance(days)}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SERVE FRONTEND STATIC FILES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")

# Serve login page at root
@app.get("/")
async def serve_login():
    login_file = os.path.join(frontend_dir, "index.html")
    return FileResponse(login_file)

# Serve assistant at /assistant/
@app.get("/assistant")
@app.get("/assistant/")
async def serve_assistant():
    return FileResponse(os.path.join(frontend_dir, "assistant.html"))

# Serve admin at /admin/
@app.get("/admin")
@app.get("/admin/")
async def serve_admin():
    admin_file = os.path.join(frontend_dir, "admin", "index.html")
    return FileResponse(admin_file)

# Mount static assets
if os.path.exists(frontend_dir):
    admin_dir = os.path.join(frontend_dir, "admin")
    if os.path.exists(admin_dir):
        app.mount("/admin", StaticFiles(directory=admin_dir, html=True), name="admin-frontend")
    app.mount("/", StaticFiles(directory=frontend_dir, html=False), name="frontend")
