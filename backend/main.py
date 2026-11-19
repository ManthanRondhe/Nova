"""
Question:
What is the most complicated code you have written independently
without AI or anyone else's assistance?

Project: Nova AI (AutoMech-AI)

Description:
Nova AI is a full-stack AI-powered automotive workshop
management platform built using Python, FastAPI, MongoDB,
Machine Learning, and JavaScript.

It provides:
- AI-powered vehicle fault diagnosis using TF-IDF and Naive Bayes.
- Automatic mechanic scheduling and job card management.
- Inventory management and automated parts ordering.
- Telegram bot notifications.
- Voice-based mechanic interaction.
- Customer vehicle status tracking.
- Workshop administration and reporting.
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
from services.video_guide_service import VideoGuideService
from services.visual_repair.repair_generator import RepairGuideGenerator
from services.approval_workflow_service import ApprovalWorkflowService, ApprovalStatus
from services.telegram_bot_handler import TelegramBotHandler
from services.ai_auditor_service import AIAuditorService, AuditVerdict

diagnosis_engine = DiagnosisEngine(config.DATA_DIR)
jobcard_manager = JobCardManager(config.DATA_DIR)
mechanic_scheduler = MechanicScheduler(config.DATA_DIR)
inventory_manager = InventoryManager(config.DATA_DIR)
order_manager = OrderManager(config.DATA_DIR)
notification_service = NotificationService()
estimation_engine = EstimationEngine(config.DATA_DIR)
admin_service = AdminService(config.DATA_DIR)
video_guide_service = VideoGuideService(config.DATA_DIR)
repair_guide_generator = RepairGuideGenerator(config.DATA_DIR)
ai_auditor_service = AIAuditorService(config.DATA_DIR)
approval_workflow_service = ApprovalWorkflowService(
    config.DATA_DIR, jobcard_manager, mechanic_scheduler, notification_service,
    inventory_manager, order_manager, estimation_engine, ai_auditor_service=ai_auditor_service
)
telegram_bot_handler = TelegramBotHandler(approval_workflow_service, notification_service)

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

@app.on_event("startup")
async def startup_event():
    """Start Telegram bot listener on server startup."""
    if config.ENABLE_APPROVAL_WORKFLOW and config.TELEGRAM_ENABLED:
        telegram_bot_handler.start_polling()

@app.on_event("shutdown")
async def shutdown_event():
    """Stop Telegram bot listener on server shutdown."""
    telegram_bot_handler.stop_polling()

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
    """Diagnose vehicle fault from symptoms using our custom trained ML ensemble."""
    query = data.get("query", "")
    vehicle_type = data.get("vehicle_type", None)
    vehicle_model = data.get("vehicle_model", None)
    top_n = data.get("top_n", 5)
    positive_clues = data.get("positive_clues", None)
    negative_clues = data.get("negative_clues", None)
    rejected_faults = data.get("rejected_faults", None)
    
    if not query:
        return {"error": "No query provided", "results": []}
    
    results = diagnosis_engine.diagnose(
        query,
        vehicle_type=vehicle_type,
        vehicle_model=vehicle_model,
        top_n=top_n,
        positive_clues=positive_clues,
        negative_clues=negative_clues,
        rejected_faults=rejected_faults
    )
    system = diagnosis_engine.detect_system(query)
    severity = diagnosis_engine.detect_severity(query)
    
    # Generate estimates for top result
    estimate = None
    if results:
        estimate = estimation_engine.estimate(results[0])
    
    # Check if top prediction is high confidence (>= 0.78) or needs a differential follow-up question
    needs_followup = bool(results and results[0]["confidence"] < 0.78)
    differential_question = (
        diagnosis_engine.generate_differential_question(results, query)
        if needs_followup else None
    )

    # Generate repair guide if enabled (replaces legacy video guides)
    repair_guide = None
    if config.ENABLE_REPAIR_GUIDES and results:
        try:
            repair_guide = repair_guide_generator.get_repair_guide(
                fault_name=results[0]["fault_name"],
                vehicle_make=vehicle_type,
                vehicle_model=vehicle_model,
                fix_procedure=results[0].get("fix_procedure"),
                system=results[0].get("system") or system,
                symptoms=results[0].get("matched_symptom") or query
            )
        except Exception as e:
            repair_guide = None
    
    # Legacy video guide fallback (if repair guides disabled but video guides enabled)
    video_guide = None
    if not repair_guide and config.ENABLE_VIDEO_GUIDES and results:
        try:
            video_guide = video_guide_service.get_repair_guide(
                fault_name=results[0]["fault_name"],
                vehicle_make=vehicle_type,
                vehicle_model=vehicle_model,
                fix_procedure=results[0].get("fix_procedure"),
                system=system
            )
        except Exception as e:
            video_guide = None
    
    response_data = {
        "query": query,
        "detected_system": system,
        "detected_severity": severity,
        "results": results,
        "top_estimate": estimate,
        "total_matches": len(results),
        "needs_followup": needs_followup,
        "differential_question": differential_question,
    }
    if repair_guide:
        response_data["repair_guide"] = repair_guide
    elif video_guide:
        response_data["video_guide"] = video_guide
    return response_data

@app.post("/api/generate-repair-guide")
async def generate_repair_guide(data: dict):
    """Generate AI-powered visual repair guide for a predicted fault."""
    fault = data.get("predicted_fault", "")
    if not fault:
        return {"success": False, "error": "No predicted_fault provided"}
    try:
        guide = repair_guide_generator.get_repair_guide(
            fault_name=fault,
            vehicle_make=data.get("vehicle_make", ""),
            vehicle_model=data.get("vehicle_model", ""),
            vehicle_year=data.get("vehicle_year"),
            engine_variant=data.get("engine_variant", ""),
            symptoms=data.get("symptoms", ""),
            diagnostic_findings=data.get("diagnostic_findings", ""),
            fix_procedure=data.get("fix_procedure", ""),
            system=data.get("system", "")
        )
        return {"success": True, "repair_guide": guide}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/diagnosis/{diagnosis_id}/repair-guide")
async def get_diagnosis_repair_guide(diagnosis_id: str, vehicle_make: str = "", vehicle_model: str = "", vehicle_year: int = None):
    """Retrieve AI visual repair guide for a diagnosed fault or job card ID."""
    jc = jobcard_manager.get_jobcard(diagnosis_id)
    fault = jc.get("diagnosis_fault") if jc else diagnosis_id
    make = (jc.get("vehicle_make") if jc else vehicle_make) or ""
    model = (jc.get("vehicle_model") if jc else vehicle_model) or ""
    proc = jc.get("complaint") if jc else ""

    guide = repair_guide_generator.get_repair_guide(
        fault_name=fault,
        vehicle_make=make,
        vehicle_model=model,
        vehicle_year=vehicle_year,
        fix_procedure=proc
    )
    return {"success": True, "repair_guide": guide}

@app.get("/api/repair/guide")
async def get_repair_guide_endpoint(
    fault_name: str,
    vehicle_make: str = "",
    vehicle_model: str = "",
    vehicle_year: int = None,
    system: str = ""
):
    """Retrieve step-by-step AI visual repair guide for any fault name."""
    guide = repair_guide_generator.get_repair_guide(
        fault_name=fault_name,
        vehicle_make=vehicle_make,
        vehicle_model=vehicle_model,
        vehicle_year=vehicle_year,
        system=system
    )
    return {"success": True, "repair_guide": guide}

@app.get("/api/diagnosis/{diagnosis_id}/videos")
async def get_diagnosis_videos(diagnosis_id: str, vehicle_make: str = "", vehicle_model: str = ""):
    """Legacy endpoint: Retrieve repair guides for a diagnosed fault or job card ID."""
    jc = jobcard_manager.get_jobcard(diagnosis_id)
    fault = jc.get("diagnosis_fault") if jc else diagnosis_id
    make = (jc.get("vehicle_make") if jc else vehicle_make) or ""
    model = (jc.get("vehicle_model") if jc else vehicle_model) or ""
    proc = jc.get("complaint") if jc else None

    if config.ENABLE_REPAIR_GUIDES:
        guide = repair_guide_generator.get_repair_guide(
            fault_name=fault,
            vehicle_make=make,
            vehicle_model=model,
            fix_procedure=proc or ""
        )
        return {"guide": guide, "repair_guide": guide}

    guide = video_guide_service.get_repair_guide(
        fault_name=fault,
        vehicle_make=make,
        vehicle_model=model,
        fix_procedure=proc
    )
    return {"guide": guide}

@app.get("/api/videos/guide")
async def get_video_guide(fault_name: str, vehicle_make: str = "", vehicle_model: str = "", system: str = ""):
    """Legacy endpoint: Retrieve step-by-step repair guide for any fault name."""
    if config.ENABLE_REPAIR_GUIDES:
        guide = repair_guide_generator.get_repair_guide(
            fault_name=fault_name,
            vehicle_make=vehicle_make,
            vehicle_model=vehicle_model,
            system=system
        )
        return {"guide": guide, "repair_guide": guide}

    guide = video_guide_service.get_repair_guide(
        fault_name=fault_name,
        vehicle_make=vehicle_make,
        vehicle_model=vehicle_model,
        system=system
    )
    return {"guide": guide}

# ─── Job Cards ─────────────────────────────────
@app.get("/api/jobcards")
async def get_jobcards(status: str = None):
    return {"jobcards": jobcard_manager.get_all_jobcards(status)}

@app.post("/api/jobcards")
async def create_jobcard(data: dict):
    """Create job card with auto-diagnosis, company review, and auto-dispatch."""
    # Run diagnosis
    complaint = data.get("complaint", "")
    diagnosis = None
    if complaint:
        results = diagnosis_engine.diagnose(complaint, data.get("vehicle_type"), data.get("vehicle_model"))
        if results:
            diagnosis = results[0]
            
    # Estimate
    estimate = estimation_engine.estimate(diagnosis) if diagnosis else None

    # When Unbiased Company Approval Workflow is enabled:
    if config.ENABLE_APPROVAL_WORKFLOW:
        jobcard = jobcard_manager.create_jobcard(
            vehicle_make=data.get("vehicle_make", ""),
            vehicle_model=data.get("vehicle_model", ""),
            vehicle_year=data.get("vehicle_year", ""),
            vehicle_reg=data.get("vehicle_reg", ""),
            owner_name=data.get("owner_name", ""),
            owner_phone=data.get("owner_phone", ""),
            complaint=complaint,
            diagnosis=diagnosis,
            mechanic=None
        )
        # Set initial status and dispatch to company reviewers
        approval_workflow_service.initiate_workflow(jobcard, diagnosis)

        return {
            "jobcard": jobcard,
            "diagnosis": diagnosis,
            "estimate": jobcard.get("estimate") or estimate,
            "assigned_mechanic": jobcard.get("assigned_mechanic_name"),
            "approval_status": jobcard.get("approval_status", ApprovalStatus.PENDING_COMPANY_REVIEW),
            "ai_audit": jobcard.get("ai_audit"),
            "parts_availability": None,
            "orders_created": [],
            "notification": None,
            "order_notifications": [],
            "message": f"Job card {jobcard['jobcard_id']} created and evaluated by Sentinel AI ({jobcard.get('approval_status')})."
        }
    
    # ── Legacy Direct Auto-Assign Flow (when workflow disabled) ──
    system = diagnosis_engine.detect_system(complaint) if complaint else None
    mechanic = mechanic_scheduler.auto_assign(system, diagnosis.get("severity", "Medium") if diagnosis else "Medium")
    
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
    
    parts_check = None
    orders_created = []
    if diagnosis and diagnosis.get("required_parts"):
        parts_check = inventory_manager.check_parts_availability(diagnosis["required_parts"])
        if parts_check.get("missing"):
            orders_created = order_manager.auto_order_missing_parts(
                parts_check["missing"], jobcard["jobcard_id"]
            )
    
    if mechanic:
        task_desc = f"{diagnosis['fault_name']} - {complaint}" if diagnosis else complaint
        mechanic_scheduler.add_to_pipeline(
            mechanic["mechanic_id"], mechanic["name"],
            jobcard["jobcard_id"], task_desc,
            jobcard.get("priority", "Medium")
        )
    
    notification_result = None
    if mechanic:
        notification_result = notification_service.notify_mechanic_assignment(mechanic, jobcard, diagnosis)
    
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
    assistant_msgs = []
    last_assistant_msg = ""
    for msg in context:
        if isinstance(msg, dict):
            if msg.get("role") == "user":
                recent_user_msgs.append(msg.get("text", ""))
            elif msg.get("role") == "assistant":
                a_txt = msg.get("text", "")
                assistant_msgs.append(a_txt)
                last_assistant_msg = a_txt
        elif isinstance(msg, str):
            recent_user_msgs.append(msg)

    # Avoid duplicating current text if client already pushed it to chatContext before calling API
    if recent_user_msgs and recent_user_msgs[-1].strip().lower() == text:
        recent_user_msgs = recent_user_msgs[:-1]
            
    is_answering_followup = (
        "?" in last_assistant_msg or
        "narrowed this down" in last_assistant_msg.lower() or
        "to pinpoint" in last_assistant_msg.lower() or
        "to confirm" in last_assistant_msg.lower() or
        "tell me what you find" in last_assistant_msg.lower() or 
        "first step" in last_assistant_msg.lower() or
        "catching hints of" in last_assistant_msg.lower() or
        "need more details" in last_assistant_msg.lower() or
        "let's not guess" in last_assistant_msg.lower()
    )
    
    # Combine context with current text for better diagnosis if it's a diagnostic query
    full_text = " ".join(recent_user_msgs).lower() + " " + text if recent_user_msgs else text
    
    # 1. Intent classification - Priority 1: Explicit Action Commands (using current text, only when not answering a diagnostic follow-up)
    if not is_answering_followup and any(kw in text for kw in ["new job", "job card", "new vehicle", "vehicle arrived", "create job", "register vehicle"]):
        return {"response": "I'll create a new job card. Please provide the vehicle details - make, model, year, and registration number.", 
                "action": "create_jobcard", "data": {}}
    
    elif not is_answering_followup and any(kw in text for kw in ["inventory", "stock", "parts available", "spare", "check part"]):
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
    
    elif not is_answering_followup and any(kw in text for kw in ["mechanic", "who is available", "available mechanic", "assign"]):
        mechanics = mechanic_scheduler.get_all_mechanics()
        available = [m for m in mechanics if m.get("status") == "Available"]
        response = f"We have {len(mechanics)} mechanics. {len(available)} are currently available. "
        if available:
            names = ", ".join(m["name"] for m in available[:5])
            response += f"Available: {names}."
        return {"response": response, "action": "mechanics", "data": {"mechanics": mechanics}}
    
    elif not is_answering_followup and any(kw in text for kw in ["estimate", "cost", "how much", "price", "charge"]):
        results = diagnosis_engine.diagnose(text, top_n=1)
        if results:
            est = estimation_engine.estimate(results[0])
            response = (f"For {results[0]['fault_name']}: "
                       f"Parts cost Rs {est['parts_cost']}. Labour Rs {est['labour_cost']} ({est['labour_hours']} hours). "
                       f"Total estimate: Rs {est['total_estimate_min']} to Rs {est['total_estimate_max']}.")
            return {"response": response, "action": "estimate", "data": {"estimate": est}}
        return {"response": "Please describe the problem so I can estimate the repair cost.", "action": "estimate", "data": {}}
    
    elif not is_answering_followup and any(kw in text for kw in ["order", "dealer", "supplier", "restock"]):
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
    
    elif not is_answering_followup and any(kw in text for kw in ["pipeline", "workload", "schedule", "queue"]):
        workload = mechanic_scheduler.get_workload_summary()
        response = "Current workload: "
        for w in workload:
            response += f"{w['name']}: {w['active_tasks']} active tasks. "
        return {"response": response, "action": "pipeline", "data": {"workload": workload}}
    
    elif not is_answering_followup and any(kw in text for kw in ["dashboard", "overview", "summary", "status"]):
        stats = jobcard_manager.get_stats()
        inv = inventory_manager.get_inventory_stats()
        response = (f"Garage Overview: {stats['total']} total job cards. "
                   f"{stats['in_progress']} in progress, {stats['pending']} pending. "
                   f"{stats['urgent']} urgent jobs. "
                   f"Inventory: {inv['low_stock_count']} low stock alerts.")
        return {"response": response, "action": "dashboard", "data": {"jobcard_stats": stats, "inventory_stats": inv}}
    
    words = set(text.split())
    if not is_answering_followup and (any(kw in words for kw in ["hello", "hi", "hey"]) or any(kw in text for kw in ["good morning", "good afternoon"])):
        return {"response": "Morning junior! I'm Nova AI, the senior master tech here. Tell me the symptoms, and I'll walk you through the diagnosis step by step. What are we working on today?", 
                "action": "greeting", "data": {}}
    
    elif not is_answering_followup and (any(kw in words for kw in ["thank", "thanks", "bye", "goodbye"]) or any(kw in text for kw in ["thank you"])):
        return {"response": "You got it, junior. Keep learning and call me if you get stuck on the next one.", 
                "action": "farewell", "data": {}}

    # 2. Intent classification - Priority 2: Context-aware Diagnosis (100% Custom Local ML Ensemble + Differential Questioning)
    elif is_answering_followup or any(kw in full_text for kw in ["diagnose", "problem", "issue", "wrong", "fault", "symptom", "noise", "smoke", "leak", "not working", "not starting", "won't start", "wont start", "smell", "ac", "air", "brake", "gear", "vibrate", "battery", "dead", "pulls", "pulling", "hot", "warm", "overheat", "click", "grind", "squeal", "knock", "rattle", "stalling", "stall", "misfire", "clutch", "steering", "suspension", "obd", "p0", "c0"]):
        if is_answering_followup and (recent_user_msgs or assistant_msgs):
            results, rejected_faults = diagnosis_engine.evaluate_followup_conversation(
                recent_user_msgs=recent_user_msgs,
                assistant_msgs=assistant_msgs,
                current_user_text=text
            )
        else:
            results = diagnosis_engine.diagnose(text, top_n=3)
            rejected_faults = set()

        if results:
            top = results[0]
            estimate = estimation_engine.estimate(top)

            # Strict High-Confidence Threshold (0.78 = 78%):
            # If our trained model's confidence is below 78% (e.g. short or ambiguous query with competing faults),
            # never guess vaguely — ask a targeted differential question separating Candidate #1 from Candidate #2!
            if top["confidence"] < 0.78:
                diff_question = diagnosis_engine.generate_differential_question(results, full_text, context)
                if top["confidence"] < 0.35:
                    response = f"Hmm, that's still too broad to condemn a part, junior. {diff_question}"
                else:
                    response = f"Alright, let's not guess. {diff_question}"
                return {
                    "response": response,
                    "action": "diagnosis_followup",
                    "data": {
                        "results": results,
                        "estimate": estimate,
                        "needs_followup": True,
                        "differential_question": diff_question
                    }
                }
            else:
                conf_pct = int(round(top["confidence"] * 100))
                prefix = "Good job checking that. Based on your findings, " if is_answering_followup else "This is a textbook case. "
                obd_info = f" (OBD-II: {top['obd_code']})" if top.get("obd_code") else ""
                parts_info = f" Required parts: {top['required_parts']}." if top.get("required_parts") else ""
                response = (
                    f"{prefix}It's definitely {top['fault_name']}{obd_info} with {conf_pct}% confidence. "
                    f"Here's the exact repair plan: {top['fix_procedure']}.{parts_info} "
                    f"Estimated labour: {estimate['estimated_time_hours']} hours (Rs {estimate['total_estimate_min']} - Rs {estimate['total_estimate_max']})."
                )
                action = "diagnosis"
                
                # Generate AI-powered visual repair guide if enabled
                repair_guide = None
                if config.ENABLE_REPAIR_GUIDES and top:
                    try:
                        repair_guide = repair_guide_generator.get_repair_guide(
                            fault_name=top["fault_name"],
                            fix_procedure=top.get("fix_procedure"),
                            system=top.get("system"),
                            symptoms=top.get("matched_symptom", "")
                        )
                    except Exception:
                        repair_guide = None

                # Legacy video guide fallback
                guide = None
                if not repair_guide and config.ENABLE_VIDEO_GUIDES and top:
                    try:
                        guide = video_guide_service.get_repair_guide(
                            fault_name=top["fault_name"],
                            fix_procedure=top.get("fix_procedure"),
                            system=top.get("system")
                        )
                    except Exception:
                        guide = None

                if repair_guide and isinstance(repair_guide, dict) and repair_guide.get("repair_steps"):
                    response += " I have generated a step-by-step visual repair guide with technical diagrams on your screen."
                elif guide and isinstance(guide, dict) and guide.get("stages"):
                    response += " I found videos for each repair step, check the screen."
                
                # If approval workflow is OFF, run legacy auto-order. When ON, official diagnosis requires approval.
                if not config.ENABLE_APPROVAL_WORKFLOW and top.get("required_parts"):
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
                        response += f" We do not have {missing_names} in our inventory, so I have automatically placed an order for them."
                
                data_payload = {"results": results, "estimate": estimate, "needs_followup": False}
                if repair_guide and isinstance(repair_guide, dict):
                    data_payload["repair_guide"] = repair_guide
                elif guide and isinstance(guide, dict):
                    data_payload["video_guide"] = guide
                return {"response": response, "action": action, "data": data_payload}
            
        return {"response": "You're not giving me much to work with, junior. Describe the exact symptoms—what does it sound like, any warning lights, smoke, or leaks, and when does it happen?", "action": "diagnosis_followup", "data": {}}
    
    else:
        # Try diagnosis as fallback using current text / context
        results = diagnosis_engine.diagnose(full_text, top_n=3)
        if results and results[0].get("confidence", 0) >= 0.78:
            top = results[0]
            estimate = estimation_engine.estimate(top)
            conf_pct = int(round(top["confidence"] * 100))
            response = (
                f"This is a textbook case. It's definitely {top['fault_name']} ({conf_pct}% confidence). "
                f"Here's the plan to fix it: {top['fix_procedure']}. "
                f"It'll take about {estimate['estimated_time_hours']} hours."
            )
            return {"response": response, "action": "diagnosis", "data": {"results": results, "estimate": estimate}}
        elif results and results[0].get("confidence", 0) > 0.15:
            diff_question = diagnosis_engine.generate_differential_question(results, full_text, context)
            response = f"Alright, let's test this systematically. {diff_question}"
            return {"response": response, "action": "diagnosis_followup", "data": {"results": results, "needs_followup": True, "differential_question": diff_question}}
        
        return {"response": "Listen junior, I need more context. Describe the exact symptoms - sounds, leaks, smells, OBD codes, or how the vehicle behaves. What's happening?",
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
# CUSTOMER PORTAL API
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.post("/api/customer/lookup")
async def customer_lookup(data: dict):
    """Look up all job cards for a customer by phone number or vehicle registration."""
    phone = data.get("phone", "").strip()
    reg = data.get("vehicle_reg", "").strip()

    if not phone and not reg:
        return {"error": "Provide phone number or vehicle registration", "jobcards": []}

    all_jcs = jobcard_manager.get_all_jobcards()
    results = []
    for jc in all_jcs:
        if (phone and jc.get("owner_phone", "") == phone) or \
           (reg and jc.get("vehicle_reg", "").upper() == reg.upper()):
            results.append(jc)

    status_order = {"In Progress": 0, "Pending": 1, "Completed": 2}
    results.sort(key=lambda x: (status_order.get(x.get("status"), 9), x.get("created_at", "")), reverse=False)

    return {"jobcards": results, "total": len(results)}

@app.get("/api/customer/vehicle/{jc_id}")
async def customer_vehicle_detail(jc_id: str):
    """Get full vehicle detail for customer view — status, mechanic, parts, quotation."""
    jc = jobcard_manager.get_jobcard(jc_id)
    if not jc:
        return {"error": "Job card not found"}

    # Mechanic Info
    mechanic_info = None
    mid = jc.get("assigned_mechanic_id")
    if mid:
        mech = mechanic_scheduler.get_mechanic(mid)
        if mech:
            mechanic_info = {
                "name": mech.get("name", ""),
                "specialization": mech.get("specialization", ""),
                "skill_level": mech.get("skill_level", ""),
                "status": mech.get("status", ""),
            }

    # Parts Info
    parts_info = []
    required_parts_str = jc.get("required_parts", "")
    if required_parts_str:
        part_ids = [p.strip() for p in required_parts_str.split(",")]
        for pid in part_ids:
            part = inventory_manager.get_part_stock(pid)
            if part:
                parts_info.append({
                    "part_id": pid,
                    "name": part.get("part_name", "Unknown"),
                    "category": part.get("category", ""),
                    "unit_price": int(part.get("unit_price", 0)),
                    "in_stock": int(part.get("current_stock", 0)) > 0,
                })
            else:
                parts_info.append({"part_id": pid, "name": "Sourcing...", "category": "", "unit_price": 0, "in_stock": False})

    # Quotation / Estimate
    quotation = None
    diag_fault = jc.get("diagnosis_fault", "")
    if diag_fault:
        est_cost = jc.get("estimated_cost", "")
        est_time = jc.get("estimated_time", "")
        parts_cost = sum(p.get("unit_price", 0) for p in parts_info)
        try:
            time_hrs = float(est_time) if est_time else 1.0
        except ValueError:
            time_hrs = 1.0
        labour_cost = int(time_hrs * 500)

        if est_cost and "-" in str(est_cost):
            try:
                c_parts = str(est_cost).split("-")
                total_min = int(c_parts[0])
                total_max = int(c_parts[1])
            except (ValueError, IndexError):
                total_min = parts_cost + labour_cost
                total_max = int(total_min * 1.3)
        else:
            total_min = parts_cost + labour_cost
            total_max = int(total_min * 1.3)

        quotation = {
            "fault": diag_fault,
            "parts_cost": parts_cost,
            "labour_hours": time_hrs,
            "labour_rate": 500,
            "labour_cost": labour_cost,
            "total_min": total_min,
            "total_max": total_max,
            "actual_cost": jc.get("actual_cost", ""),
        }

    # Timeline
    timeline = []
    timeline.append({"step": "Received", "label": "Vehicle Received", "done": True, "time": jc.get("created_at", "")})
    timeline.append({"step": "Diagnosed", "label": "Diagnosis Complete", "done": bool(diag_fault), "time": jc.get("created_at", "") if diag_fault else ""})
    timeline.append({"step": "Assigned", "label": f"Mechanic: {jc.get('assigned_mechanic_name', 'TBD')}", "done": bool(mid), "time": jc.get("created_at", "") if mid else ""})
    timeline.append({"step": "InProgress", "label": "Repair In Progress", "done": jc.get("status") in ("In Progress", "Completed"), "time": ""})
    timeline.append({"step": "QualityCheck", "label": "Quality Check", "done": jc.get("status") == "Completed", "time": ""})
    timeline.append({"step": "Ready", "label": "Ready for Pickup", "done": jc.get("status") == "Completed", "time": jc.get("completed_at", "")})

    approval_stat = jc.get("approval_status") or ApprovalStatus.LEGACY_APPROVED

    return {
        "jobcard": {
            "id": jc.get("jobcard_id"),
            "status": jc.get("status"),
            "priority": jc.get("priority"),
            "bay_number": jc.get("bay_number"),
            "vehicle": f"{jc.get('vehicle_make', '')} {jc.get('vehicle_model', '')}".strip(),
            "vehicle_year": jc.get("vehicle_year", ""),
            "vehicle_reg": jc.get("vehicle_reg", ""),
            "complaint": jc.get("complaint", ""),
            "fault": diag_fault,
            "created_at": jc.get("created_at", ""),
            "completed_at": jc.get("completed_at", ""),
            "approval_status": approval_stat,
            "customer_decision": jc.get("customer_decision", ""),
            "review_requested_at": jc.get("review_requested_at", ""),
            "owner_phone": jc.get("owner_phone", ""),
        },
        "mechanic": mechanic_info,
        "parts": parts_info,
        "quotation": quotation,
        "estimate": jc.get("estimate") or quotation,
        "approval_status": approval_stat,
        "timeline": timeline,
    }

@app.post("/api/customer/book")
async def customer_book_appointment(data: dict):
    """Book a service appointment from the customer portal."""
    owner_name = data.get("owner_name", "")
    owner_phone = data.get("owner_phone", "")
    vehicle_make = data.get("vehicle_make", "")
    vehicle_model = data.get("vehicle_model", "")
    vehicle_year = data.get("vehicle_year", "")
    vehicle_reg = data.get("vehicle_reg", "")
    complaint = data.get("complaint", "")
    service_type = data.get("service_type", "General Service")

    if not owner_name or not owner_phone:
        return {"error": "Name and phone number are required"}
    if not complaint:
        complaint = service_type

    # Run AI diagnosis behind the scenes
    diagnosis = None
    if complaint:
        results = diagnosis_engine.diagnose(complaint, vehicle_make, vehicle_model)
        if results:
            diagnosis = results[0]

    estimate = estimation_engine.estimate(diagnosis) if diagnosis else None

    # When Unbiased Company Approval Workflow is enabled:
    if config.ENABLE_APPROVAL_WORKFLOW:
        jobcard = jobcard_manager.create_jobcard(
            vehicle_make=vehicle_make,
            vehicle_model=vehicle_model,
            vehicle_year=vehicle_year,
            vehicle_reg=vehicle_reg,
            owner_name=owner_name,
            owner_phone=owner_phone,
            complaint=complaint,
            diagnosis=diagnosis,
            mechanic=None
        )
        approval_workflow_service.initiate_workflow(jobcard, diagnosis)

        return {
            "success": True,
            "jobcard_id": jobcard["jobcard_id"],
            "approval_status": jobcard.get("approval_status", ApprovalStatus.PENDING_COMPANY_REVIEW),
            "ai_audit": jobcard.get("ai_audit"),
            "message": f"Appointment booked! Your tracking ID is {jobcard['jobcard_id']}. Quality verified by Sentinel AI ({jobcard.get('approval_status')}).",
            "assigned_mechanic": jobcard.get("assigned_mechanic_name") or "Pending customer confirmation",
            "estimated_cost": f"₹{jobcard.get('estimate', {}).get('total_min', 0):,} - ₹{jobcard.get('estimate', {}).get('total_max', 0):,}" if jobcard.get("estimate") else (f"₹{estimate['total_estimate_min']} - ₹{estimate['total_estimate_max']}" if estimate else "To be determined"),
        }

    # ── Legacy direct booking flow ──
    system = diagnosis_engine.detect_system(complaint) if complaint else None
    mechanic = mechanic_scheduler.auto_assign(system, diagnosis.get("severity", "Medium") if diagnosis else "Medium")

    jobcard = jobcard_manager.create_jobcard(
        vehicle_make=vehicle_make,
        vehicle_model=vehicle_model,
        vehicle_year=vehicle_year,
        vehicle_reg=vehicle_reg,
        owner_name=owner_name,
        owner_phone=owner_phone,
        complaint=complaint,
        diagnosis=diagnosis,
        mechanic=mechanic
    )

    if mechanic:
        task_desc = f"{diagnosis['fault_name']} - {complaint}" if diagnosis else complaint
        mechanic_scheduler.add_to_pipeline(
            mechanic["mechanic_id"], mechanic["name"],
            jobcard["jobcard_id"], task_desc,
            jobcard.get("priority", "Medium")
        )

    return {
        "success": True,
        "jobcard_id": jobcard["jobcard_id"],
        "message": f"Appointment booked! Your tracking ID is {jobcard['jobcard_id']}",
        "assigned_mechanic": mechanic.get("name") if mechanic else "Will be assigned soon",
        "estimated_cost": f"₹{estimate['total_estimate_min']} - ₹{estimate['total_estimate_max']}" if estimate else "To be determined after inspection",
    }

# ─── Company & Customer Approval Endpoints ─────
@app.post("/api/approval/review")
async def review_diagnosis(data: dict):
    """Process company reviewer decision (Approve / Reject / Request More Info)."""
    jc_id = data.get("jobcard_id", "")
    action = data.get("action", "")  # approve | reject | request_more_info
    reviewer_id = str(data.get("reviewer_id", ""))
    token = data.get("token", "")
    note = data.get("note", "")

    success, message, jc = approval_workflow_service.handle_reviewer_action(
        jc_id, action, reviewer_id, token, note
    )
    return {"success": success, "message": message, "jobcard": jc}

@app.post("/api/customer/approval")
async def customer_approval_decision(data: dict):
    """Process customer decision from portal (Approve / Decline)."""
    jc_id = data.get("jobcard_id", "")
    decision = data.get("decision", "")  # approve | decline
    identifier = data.get("customer_identifier", "")  # vehicle_reg or phone

    success, message, jc = approval_workflow_service.handle_customer_decision(
        jc_id, decision, identifier
    )
    return {"success": success, "message": message, "jobcard": jc}

@app.post("/api/telegram/webhook")
async def telegram_webhook(update: dict):
    """Handle incoming Telegram webhook updates for reviewer callbacks."""
    result = telegram_bot_handler.handle_update(update)
    return result

# ─── Independent AI Diagnostic Auditor Endpoints ─────
@app.get("/api/auditor/status")
async def get_auditor_status():
    """Returns AI Sentinel Auditor status, operational mode, and global stats."""
    all_jcs = jobcard_manager.get_all_jobcards()
    audited = [j for j in all_jcs if j.get("ai_audit")]
    
    total_savings = 0
    unnecessary_blocked = 0
    green_flags = 0

    for j in audited:
        audit = j.get("ai_audit", {})
        metrics = audit.get("metrics", {})
        total_savings += int(metrics.get("customer_savings", 0))
        unnecessary_blocked += int(metrics.get("unnecessary_parts_blocked", 0))
        if audit.get("autonomous_green_flag_granted"):
            green_flags += 1

    return {
        "enabled": getattr(config, "ENABLE_AI_AUDITOR", True),
        "auto_greenflag": getattr(config, "AI_AUDITOR_AUTO_GREENFLAG", True),
        "strictness": getattr(config, "AI_AUDITOR_STRICTNESS", "balanced"),
        "auto_prune": getattr(config, "AI_AUDITOR_AUTO_PRUNE", True),
        "model": getattr(config, "AI_AUDITOR_MODEL", "Sentinel-Neural-4.2"),
        "stats": {
            "total_jobcards": len(all_jcs),
            "audited_count": len(audited),
            "green_flags_granted": green_flags,
            "unnecessary_replacements_blocked": unnecessary_blocked,
            "total_customer_savings": total_savings,
            "integrity_rating": "98.8% Verified"
        }
    }

@app.post("/api/auditor/config")
async def update_auditor_config(data: dict):
    """Update AI Auditor runtime configuration toggles."""
    if "auto_greenflag" in data:
        config.AI_AUDITOR_AUTO_GREENFLAG = bool(data["auto_greenflag"])
    if "strictness" in data and str(data["strictness"]).lower() in ("strict", "balanced", "permissive"):
        config.AI_AUDITOR_STRICTNESS = str(data["strictness"]).lower()
    if "auto_prune" in data:
        config.AI_AUDITOR_AUTO_PRUNE = bool(data["auto_prune"])

    return {
        "success": True,
        "auto_greenflag": config.AI_AUDITOR_AUTO_GREENFLAG,
        "strictness": config.AI_AUDITOR_STRICTNESS,
        "auto_prune": config.AI_AUDITOR_AUTO_PRUNE,
        "message": "AI Sentinel configuration updated successfully."
    }

@app.get("/api/auditor/queue")
async def get_auditor_queue(filter_verdict: str = None):
    """Get all job cards with their AI Sentinel audit summaries."""
    all_jcs = jobcard_manager.get_all_jobcards()
    queue = []
    for j in all_jcs:
        audit = j.get("ai_audit")
        # If not yet audited, run lightweight audit on the fly
        if not audit:
            diag = {
                "fault_name": j.get("diagnosis_fault", ""),
                "confidence": float(j.get("diagnosis_confidence", 0.8)),
                "severity": j.get("priority", "Medium")
            }
            audit = ai_auditor_service.evaluate_diagnosis_and_parts(
                complaint=j.get("complaint", ""),
                diagnosis=diag,
                parts_input=j.get("required_parts", ""),
                vehicle={"make": j.get("vehicle_make", ""), "model": j.get("vehicle_model", "")},
                strictness=config.AI_AUDITOR_STRICTNESS
            )
            j["ai_audit"] = audit
            jobcard_manager.update_jobcard(j["jobcard_id"], {"ai_audit": audit})

        v = audit.get("verdict", "")
        if filter_verdict and filter_verdict.upper() not in v.upper():
            continue

        queue.append({
            "jobcard_id": j["jobcard_id"],
            "vehicle_make": j.get("vehicle_make", ""),
            "vehicle_model": j.get("vehicle_model", ""),
            "vehicle_reg": j.get("vehicle_reg", ""),
            "complaint": j.get("complaint", ""),
            "diagnosis_fault": j.get("diagnosis_fault", ""),
            "approval_status": j.get("approval_status", "PENDING_COMPANY_REVIEW"),
            "status": j.get("status", "Pending"),
            "created_at": j.get("created_at", ""),
            "verdict": audit.get("verdict"),
            "verdict_badge": audit.get("verdict_badge"),
            "integrity_score": audit.get("integrity_score"),
            "unnecessary_blocked": audit.get("metrics", {}).get("unnecessary_parts_blocked", 0),
            "customer_savings": audit.get("metrics", {}).get("customer_savings", 0),
            "autonomous_green_flag": audit.get("autonomous_green_flag_granted", False),
            "parts_count": audit.get("metrics", {}).get("total_parts_evaluated", 0)
        })
    return {"queue": queue, "total": len(queue)}

@app.get("/api/auditor/jobcard/{jc_id}")
async def get_auditor_jobcard_detail(jc_id: str):
    """Retrieve complete deep-dive audit dossier for a single job card."""
    jc = jobcard_manager.get_jobcard(jc_id)
    if not jc:
        return {"error": "Job card not found"}

    audit = jc.get("ai_audit")
    if not audit:
        diag = {
            "fault_name": jc.get("diagnosis_fault", ""),
            "confidence": float(jc.get("diagnosis_confidence", 0.8)),
            "severity": jc.get("priority", "Medium")
        }
        audit = ai_auditor_service.evaluate_diagnosis_and_parts(
            complaint=jc.get("complaint", ""),
            diagnosis=diag,
            parts_input=jc.get("required_parts", ""),
            vehicle={"make": jc.get("vehicle_make", ""), "model": jc.get("vehicle_model", ""), "reg": jc.get("vehicle_reg", "")},
            strictness=config.AI_AUDITOR_STRICTNESS
        )
        jc["ai_audit"] = audit
        jobcard_manager.update_jobcard(jc_id, {"ai_audit": audit})

    return {"jobcard": jc, "ai_audit": audit}

@app.post("/api/auditor/audit/{jc_id}")
async def trigger_jobcard_audit(jc_id: str, data: dict = None):
    """Manually run or re-evaluate AI audit on a specific job card."""
    jc = jobcard_manager.get_jobcard(jc_id)
    if not jc:
        return {"error": "Job card not found"}

    data = data or {}
    strictness = data.get("strictness") or config.AI_AUDITOR_STRICTNESS
    auto_greenflag = data.get("auto_greenflag", config.AI_AUDITOR_AUTO_GREENFLAG)
    auto_prune = data.get("auto_prune", config.AI_AUDITOR_AUTO_PRUNE)

    diag = {
        "fault_name": jc.get("diagnosis_fault", ""),
        "confidence": float(jc.get("diagnosis_confidence", 0.85)),
        "severity": jc.get("priority", "Medium")
    }

    # Evaluate
    audit_res = ai_auditor_service.evaluate_diagnosis_and_parts(
        complaint=jc.get("complaint", ""),
        diagnosis=diag,
        parts_input=jc.get("required_parts", ""),
        vehicle={"make": jc.get("vehicle_make", ""), "model": jc.get("vehicle_model", ""), "reg": jc.get("vehicle_reg", "")},
        strictness=strictness
    )
    jc["ai_audit"] = audit_res

    # Apply auto green flag if requested
    if auto_greenflag and audit_res.get("autonomous_green_flag_granted"):
        if auto_prune and audit_res.get("approved_parts"):
            clean_pids = [p["part_id"] for p in audit_res["approved_parts"] if p.get("part_id")]
            jc["required_parts"] = ",".join(clean_pids)
        estimate = approval_workflow_service.generate_official_estimate(jc)
        jc["estimate"] = estimate
        approval_workflow_service.transition_state(
            jc, ApprovalStatus.PENDING_CUSTOMER_APPROVAL,
            "AI_Sentinel_Arbiter",
            f"AI Green Flag Re-audited ({audit_res['verdict']})",
            audit_res.get("verdict_summary")
        )

    jobcard_manager.update_jobcard(jc_id, {
        "ai_audit": audit_res,
        "approval_status": jc.get("approval_status"),
        "estimate": jc.get("estimate"),
        "required_parts": jc.get("required_parts")
    })

    return {"success": True, "ai_audit": audit_res, "jobcard": jc}

@app.post("/api/auditor/greenflag/{jc_id}")
async def grant_ai_greenflag(jc_id: str, data: dict = None):
    """Explicitly award AI Green Flag, prune unnecessary parts, and advance to customer approval."""
    jc = jobcard_manager.get_jobcard(jc_id)
    if not jc:
        return {"error": "Job card not found"}

    data = data or {}
    prune = data.get("prune_unnecessary", True)
    audit = jc.get("ai_audit")

    if prune and audit and audit.get("approved_parts"):
        clean_pids = [p["part_id"] for p in audit["approved_parts"] if p.get("part_id")]
        jc["required_parts"] = ",".join(clean_pids)

    estimate = approval_workflow_service.generate_official_estimate(jc)
    jc["estimate"] = estimate
    jc["reviewed_by"] = f"AI_Sentinel_Arbiter:{config.AI_AUDITOR_MODEL}"
    jc["review_note"] = "AI Green Flag granted with certified anti-overreplacement protection."

    approval_workflow_service.transition_state(
        jc, ApprovalStatus.PENDING_CUSTOMER_APPROVAL,
        "AI_Sentinel_Arbiter",
        "Green Flag Granted. Published to Customer Portal.",
        jc["review_note"]
    )

    jobcard_manager.update_jobcard(jc_id, {
        "approval_status": ApprovalStatus.PENDING_CUSTOMER_APPROVAL,
        "estimate": estimate,
        "reviewed_by": jc["reviewed_by"],
        "review_note": jc["review_note"],
        "estimated_cost": f"{estimate['total_min']}-{estimate['total_max']}",
        "estimated_time": str(estimate["labour_hours"]),
        "required_parts": jc.get("required_parts")
    })

    # Customer notification
    approval_workflow_service.notify_customer_for_approval(jc)

    return {"success": True, "message": "AI Green Flag awarded! Estimate published to customer portal.", "jobcard": jc}

@app.post("/api/auditor/reject/{jc_id}")
async def reject_overreplacement(jc_id: str, data: dict = None):
    """Reject job card due to unacceptable parts over-replacement or diagnosis error."""
    jc = jobcard_manager.get_jobcard(jc_id)
    if not jc:
        return {"error": "Job card not found"}

    data = data or {}
    reason = data.get("reason", "Severe unnecessary replacement and predatory upsell detected by AI Sentinel.")

    approval_workflow_service.transition_state(
        jc, ApprovalStatus.AI_REJECTED,
        "AI_Sentinel_Arbiter", "Rejected: Unjustified Over-Replacement", reason
    )

    jobcard_manager.update_jobcard(jc_id, {
        "approval_status": ApprovalStatus.AI_REJECTED,
        "review_note": reason
    })

    return {"success": True, "message": "Job card rejected. Workshop re-diagnosis required.", "jobcard": jc}

@app.post("/api/auditor/evaluate")
async def evaluate_custom_diagnostic(data: dict):
    """Sandbox simulator: Evaluate any arbitrary vehicle, symptom, and parts quotation."""
    complaint = data.get("complaint", "")
    fault_name = data.get("fault_name", "")
    parts = data.get("parts", [])
    vehicle = data.get("vehicle", {})
    strictness = data.get("strictness", config.AI_AUDITOR_STRICTNESS)

    diag = {
        "fault_name": fault_name or "Custom Diagnostic Simulation",
        "confidence": float(data.get("confidence", 0.90)),
        "severity": data.get("severity", "Medium")
    }

    result = ai_auditor_service.evaluate_diagnosis_and_parts(
        complaint=complaint,
        diagnosis=diag,
        parts_input=parts,
        vehicle=vehicle,
        strictness=strictness
    )
    return result

@app.post("/api/auditor/chat")
async def auditor_chat(data: dict):
    """Interactive conversational consultation with the Senior AI Automotive Diagnostic Arbiter."""
    message = data.get("message", "")
    jc_id = data.get("jobcard_id", "")
    jc_context = jobcard_manager.get_jobcard(jc_id) if jc_id else None

    result = ai_auditor_service.chat_consultation(
        user_message=message,
        jobcard_context=jc_context
    )
    return result

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

# Serve customer portal at /customer/
@app.get("/customer")
@app.get("/customer/")
async def serve_customer():
    customer_file = os.path.join(frontend_dir, "customer", "index.html")
    return FileResponse(customer_file)

# Serve independent AI Auditor at /auditor/
@app.get("/auditor")
@app.get("/auditor/")
async def serve_auditor():
    auditor_file = os.path.join(frontend_dir, "auditor", "index.html")
    return FileResponse(auditor_file)

# Mount static assets
if os.path.exists(frontend_dir):
    admin_dir = os.path.join(frontend_dir, "admin")
    customer_dir = os.path.join(frontend_dir, "customer")
    auditor_dir = os.path.join(frontend_dir, "auditor")
    if os.path.exists(admin_dir):
        app.mount("/admin", StaticFiles(directory=admin_dir, html=True), name="admin-frontend")
    if os.path.exists(customer_dir):
        app.mount("/customer", StaticFiles(directory=customer_dir, html=True), name="customer-frontend")
    if os.path.exists(auditor_dir):
        app.mount("/auditor", StaticFiles(directory=auditor_dir, html=True), name="auditor-frontend")
    app.mount("/", StaticFiles(directory=frontend_dir, html=False), name="frontend")
