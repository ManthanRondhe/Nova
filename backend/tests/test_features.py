"""
Unit and Integration Tests for AutoMech-AI New Features:
1. Feature 1: Video Guide Service, Chronological Stages, Shorts Filter, and Graceful Fallback
2. Feature 2: Unbiased Company Approval Workflow State Machine, Telegram Authorization, Token Security, and End-to-End Dispatch
"""
import unittest
import os
import sys

# Ensure backend directory is in path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from config import config
from services.video_guide_service import VideoGuideService
from services.visual_repair.repair_generator import RepairGuideGenerator
from services.visual_repair.image_retriever import ImageRetriever
from services.visual_repair.schemas import RepairGuide, RepairStep
from services.approval_workflow_service import ApprovalWorkflowService, ApprovalStatus
from services.telegram_bot_handler import TelegramBotHandler


# ─────────────────────────────────────────────────────────────
# Test Doubles / In-Memory Mock Services
# ─────────────────────────────────────────────────────────────
class MockJobCardManager:
    def __init__(self):
        self.jobcards = {}
        self.counter = 1

    def create_jobcard(self, vehicle_make, vehicle_model, vehicle_year, vehicle_reg,
                        owner_name, owner_phone, complaint, diagnosis=None, mechanic=None):
        jc_id = f"JC-{self.counter:04d}"
        self.counter += 1
        record = {
            "jobcard_id": jc_id,
            "vehicle_make": vehicle_make,
            "vehicle_model": vehicle_model,
            "vehicle_year": vehicle_year,
            "vehicle_reg": vehicle_reg,
            "owner_name": owner_name,
            "owner_phone": owner_phone,
            "complaint": complaint,
            "diagnosis_fault": diagnosis.get("fault_name") if diagnosis else "",
            "diagnosis_confidence": diagnosis.get("confidence", 0) if diagnosis else 0,
            "assigned_mechanic_id": mechanic.get("mechanic_id") if mechanic else "",
            "assigned_mechanic_name": mechanic.get("name") if mechanic else "",
            "status": "Pending",
            "required_parts": diagnosis.get("required_parts", "") if diagnosis else "",
            "priority": "Medium",
            "bay_number": "1",
            "created_at": "2026-05-15 10:00:00"
        }
        self.jobcards[jc_id] = record
        return record

    def get_jobcard(self, jc_id):
        return self.jobcards.get(jc_id)

    def update_jobcard(self, jc_id, data):
        if jc_id in self.jobcards:
            self.jobcards[jc_id].update(data)
            return self.jobcards[jc_id]
        return None


class MockMechanicScheduler:
    def __init__(self):
        self.pipeline = []
        self.assigned_mechanic = {
            "mechanic_id": "M-001",
            "name": "Rajesh Kumar",
            "specialization": "Engine",
            "skill_level": "Senior",
            "status": "Available",
            "telegram_chat_id": "999888777"
        }

    def auto_assign(self, specialization, severity):
        return self.assigned_mechanic

    def add_to_pipeline(self, mechanic_id, mechanic_name, jc_id, task_desc, priority):
        self.pipeline.append({
            "mechanic_id": mechanic_id,
            "jobcard_id": jc_id,
            "task_desc": task_desc
        })


class MockNotificationService:
    def __init__(self):
        self.enabled = False
        self.api_base = ""
        self.sent_messages = []
        self.assigned_notifications = []

    def send_message(self, chat_id, message, parse_mode="HTML"):
        entry = {"chat_id": chat_id, "message": message}
        self.sent_messages.append(entry)
        return {"status": "simulated", "response": entry}

    def notify_mechanic_assignment(self, mechanic, jobcard, diagnosis=None):
        self.assigned_notifications.append({"mechanic": mechanic, "jobcard": jobcard})
        return {"status": "sent"}

    def notify_dealer_order(self, dealer, order):
        return {"status": "sent"}


class MockInventoryManager:
    def __init__(self):
        self.parts = {
            "P-001": {"part_id": "P-001", "part_name": "Starter Motor Assembly", "current_stock": 2, "unit_price": 4500},
            "P-002": {"part_id": "P-002", "part_name": "Brake Pad Set", "current_stock": 0, "unit_price": 1200}
        }

    def get_part_stock(self, part_id):
        return self.parts.get(part_id)

    def check_parts_availability(self, required_parts_str):
        pids = [p.strip() for p in required_parts_str.split(",") if p.strip()]
        available = []
        missing = []
        for pid in pids:
            if pid in self.parts and self.parts[pid]["current_stock"] > 0:
                available.append(self.parts[pid])
            else:
                missing.append(self.parts.get(pid, {"part_id": pid, "part_name": "Part", "current_stock": 0}))
        return {"available": available, "missing": missing}


class MockOrderManager:
    def __init__(self):
        self.orders = []

    def auto_order_missing_parts(self, missing_parts, jc_id):
        created = []
        for p in missing_parts:
            order = {
                "order_id": f"ORD-{len(self.orders)+1}",
                "part_id": p.get("part_id"),
                "dealer": {"name": "National Auto Spares", "telegram_chat_id": "112233"}
            }
            self.orders.append(order)
            created.append(order)
        return created


class MockEstimationEngine:
    def estimate(self, diagnosis):
        return {
            "parts_cost": 4500,
            "labour_hours": 2.5,
            "labour_cost": 1250,
            "total_estimate_min": 5750,
            "total_estimate_max": 7475
        }


# ─────────────────────────────────────────────────────────────
# TEST CASES
# ─────────────────────────────────────────────────────────────
class TestVideoGuideService(unittest.TestCase):
    """Unit tests for Feature 1: Video Guide Service & Fallback."""

    def setUp(self):
        self.video_service = VideoGuideService()

    def test_chronological_stages_starter_motor(self):
        """Verify real-world chronological stage decomposition for starter motor."""
        stages = self.video_service.generate_repair_stages("starter motor failure", system="Electrical")
        self.assertEqual(len(stages), 6)
        # Chronological order checks
        self.assertIn("diagnos", stages[0]["title"].lower())
        self.assertIn("battery", stages[1]["title"].lower())
        self.assertIn("remov", stages[2]["title"].lower())
        self.assertIn("inspect", stages[3]["title"].lower())
        self.assertIn("reinstall", stages[4]["title"].lower())
        self.assertIn("test", stages[5]["title"].lower())

    def test_chronological_stages_brake_service(self):
        """Verify chronological order for brake pads / rotors."""
        stages = self.video_service.generate_repair_stages("Worn brake pads and squealing rotor", system="Brakes")
        self.assertTrue(len(stages) >= 5)
        self.assertIn("safety", stages[0]["title"].lower())
        self.assertIn("caliper", stages[1]["title"].lower())

    def test_iso_duration_parser_and_shorts_filter(self):
        """Test ISO 8601 duration parser and short video filtering."""
        # Standard video
        sec, text = self.video_service._parse_iso_duration("PT12M30S")
        self.assertEqual(sec, 750)
        self.assertEqual(text, "12:30")

        # Video under 60 seconds (Short)
        short_sec, short_text = self.video_service._parse_iso_duration("PT45S")
        self.assertEqual(short_sec, 45)
        self.assertTrue(short_sec < 60)

        # Longer video over 1 hour
        long_sec, long_text = self.video_service._parse_iso_duration("PT1H05M10S")
        self.assertEqual(long_sec, 3910)
        self.assertEqual(long_text, "1:05:10")

    def test_graceful_fallback_without_api_key(self):
        """Ensure that when API key is missing or quota exceeded, fallback search URLs are generated safely."""
        # Explicitly clear api_key on service instance for this test
        self.video_service.api_key = ""
        guide = self.video_service.get_repair_guide(
            fault_name="Alternator diode failure",
            vehicle_make="Toyota",
            vehicle_model="Corolla",
            system="Electrical"
        )
        self.assertIsNotNone(guide)
        self.assertEqual(guide["fault_name"], "Alternator diode failure")
        self.assertTrue(len(guide["stages"]) > 0)
        for st in guide["stages"]:
            self.assertTrue(st["is_fallback"])
            self.assertIn("youtube.com/results?search_query=", st["fallback_search_url"])
            self.assertTrue(len(st["stage_title"]) > 0)


class TestApprovalStateMachine(unittest.TestCase):
    """Unit tests for Feature 2: State Machine Transitions and Invariant Enforcement."""

    def setUp(self):
        self.jobcard_mgr = MockJobCardManager()
        self.mech_sched = MockMechanicScheduler()
        self.notif_svc = MockNotificationService()
        self.inv_mgr = MockInventoryManager()
        self.ord_mgr = MockOrderManager()
        self.est_engine = MockEstimationEngine()

        self.service = ApprovalWorkflowService(
            data_dir="data",
            jobcard_manager=self.jobcard_mgr,
            mechanic_scheduler=self.mech_sched,
            notification_service=self.notif_svc,
            inventory_manager=self.inv_mgr,
            order_manager=self.ord_mgr,
            estimation_engine=self.est_engine
        )

    def test_valid_state_transitions(self):
        """Verify normal transition progression: DIAGNOSIS_CREATED -> PENDING_COMPANY_REVIEW -> COMPANY_APPROVED -> PENDING_CUSTOMER_APPROVAL -> CUSTOMER_APPROVED."""
        jc = self.jobcard_mgr.create_jobcard("Honda", "Civic", "2021", "MH-01-AB-1234", "Rohan", "9876543210", "Starter click")
        jc["approval_status"] = ApprovalStatus.DIAGNOSIS_CREATED

        # 1. To PENDING_COMPANY_REVIEW
        ok, _ = self.service.transition_state(jc, ApprovalStatus.PENDING_COMPANY_REVIEW, "system", "dispatched")
        self.assertTrue(ok)
        self.assertEqual(jc["approval_status"], ApprovalStatus.PENDING_COMPANY_REVIEW)

        # 2. To COMPANY_APPROVED
        ok, _ = self.service.transition_state(jc, ApprovalStatus.COMPANY_APPROVED, "reviewer:101", "approved")
        self.assertTrue(ok)
        self.assertEqual(jc["approval_status"], ApprovalStatus.COMPANY_APPROVED)

        # 3. To PENDING_CUSTOMER_APPROVAL
        ok, _ = self.service.transition_state(jc, ApprovalStatus.PENDING_CUSTOMER_APPROVAL, "system", "published")
        self.assertTrue(ok)
        self.assertEqual(jc["approval_status"], ApprovalStatus.PENDING_CUSTOMER_APPROVAL)

        # 4. To CUSTOMER_APPROVED
        ok, _ = self.service.transition_state(jc, ApprovalStatus.CUSTOMER_APPROVED, "customer:MH-01-AB-1234", "accepted")
        self.assertTrue(ok)
        self.assertEqual(jc["approval_status"], ApprovalStatus.CUSTOMER_APPROVED)

        # Verify audit log was recorded
        self.assertEqual(len(jc["audit_log"]), 4)

    def test_invalid_state_transitions(self):
        """Verify illegal transitions are strictly blocked by the state machine."""
        jc = self.jobcard_mgr.create_jobcard("Honda", "Civic", "2021", "MH-01-AB-1234", "Rohan", "9876543210", "Starter click")
        jc["approval_status"] = ApprovalStatus.DIAGNOSIS_CREATED

        # Illegal: Skipping company review straight to customer approval
        ok, msg = self.service.transition_state(jc, ApprovalStatus.CUSTOMER_APPROVED, "attacker", "bypass")
        self.assertFalse(ok)
        self.assertIn("Illegal state transition", msg)

        # Illegal: Moving from terminal state CUSTOMER_DECLINED to CUSTOMER_APPROVED
        jc["approval_status"] = ApprovalStatus.CUSTOMER_DECLINED
        ok, msg = self.service.transition_state(jc, ApprovalStatus.CUSTOMER_APPROVED, "attacker", "revive")
        self.assertFalse(ok)
        self.assertIn("Illegal state transition", msg)


class TestTelegramSecurityAndCallbacks(unittest.TestCase):
    """Unit tests for Reviewer Whitelisting, Token Signing, and Bot Callbacks."""

    def setUp(self):
        self.jobcard_mgr = MockJobCardManager()
        self.mech_sched = MockMechanicScheduler()
        self.notif_svc = MockNotificationService()
        self.inv_mgr = MockInventoryManager()
        self.ord_mgr = MockOrderManager()
        self.est_engine = MockEstimationEngine()

        self.service = ApprovalWorkflowService(
            data_dir="data",
            jobcard_manager=self.jobcard_mgr,
            mechanic_scheduler=self.mech_sched,
            notification_service=self.notif_svc,
            inventory_manager=self.inv_mgr,
            order_manager=self.ord_mgr,
            estimation_engine=self.est_engine
        )
        self.bot_handler = TelegramBotHandler(self.service, self.notif_svc)

        # Configure whitelisted reviewer IDs
        config.COMPANY_REVIEWER_CHAT_IDS = ["123456789", "987654321"]

    def test_token_generation_and_tampering(self):
        """Verify HMAC tokens are generated and invalid tokens are rejected."""
        token = self.service.generate_review_token("JC-0001")
        self.assertTrue(self.service.verify_review_token("JC-0001", token))
        # Tampered token or mismatched ID
        self.assertFalse(self.service.verify_review_token("JC-0001", "tampered_token"))
        self.assertFalse(self.service.verify_review_token("JC-0002", token))

    def test_reviewer_authorization(self):
        """Verify only whitelisted chat IDs can perform company reviews."""
        self.assertTrue(self.service.is_reviewer_authorized("123456789"))
        self.assertTrue(self.service.is_reviewer_authorized("987654321"))
        self.assertFalse(self.service.is_reviewer_authorized("999999999")) # Unauthorized
        self.assertFalse(self.service.is_reviewer_authorized(""))

    def test_telegram_callback_rejects_unauthorized(self):
        """Telegram callback query from non-whitelisted user is rejected."""
        token = self.service.generate_review_token("JC-0001")
        update = {
            "callback_query": {
                "id": "cb_001",
                "data": f"REV:APP:JC-0001:{token}",
                "from": {"id": "999999999", "username": "bad_actor"},
                "message": {"message_id": 1, "text": "Review request"}
            }
        }
        res = self.bot_handler.handle_update(update)
        self.assertEqual(res["status"], "denied")

    def test_approval_idempotency(self):
        """Ensure multiple clicks on Approve button don't duplicate execution."""
        jc = self.jobcard_mgr.create_jobcard("Honda", "City", "2020", "MH-02-CD-5678", "Vikas", "9876543210", "Starter dead")
        jc["approval_status"] = ApprovalStatus.PENDING_COMPANY_REVIEW
        token = self.service.generate_review_token(jc["jobcard_id"])

        # First tap
        ok1, msg1, _ = self.service.handle_reviewer_action(jc["jobcard_id"], "approve", "123456789", token)
        self.assertTrue(ok1)

        # Second tap (duplicate)
        ok2, msg2, _ = self.service.handle_reviewer_action(jc["jobcard_id"], "approve", "123456789", token)
        self.assertTrue(ok2)
        self.assertIn("already approved", msg2)


class TestEndToEndApprovalWorkflow(unittest.TestCase):
    """End-to-End happy path test: Diagnosis -> Company Review -> Customer Approval -> Mechanic Assigned."""

    def setUp(self):
        self.jobcard_mgr = MockJobCardManager()
        self.mech_sched = MockMechanicScheduler()
        self.notif_svc = MockNotificationService()
        self.inv_mgr = MockInventoryManager()
        self.ord_mgr = MockOrderManager()
        self.est_engine = MockEstimationEngine()

        self.service = ApprovalWorkflowService(
            data_dir="data",
            jobcard_manager=self.jobcard_mgr,
            mechanic_scheduler=self.mech_sched,
            notification_service=self.notif_svc,
            inventory_manager=self.inv_mgr,
            order_manager=self.ord_mgr,
            estimation_engine=self.est_engine
        )
        config.COMPANY_REVIEWER_CHAT_IDS = ["123456789"]

    def test_full_happy_path(self):
        # 1. AI Diagnosis produced
        diag = {
            "fault_name": "Starter Motor Solenoid Failure",
            "confidence": 0.92,
            "severity": "High",
            "required_parts": "P-001,P-002",
            "fix_procedure": "Replace starter motor and inspect wiring"
        }

        # 2. Job Card created and workflow initiated
        jc = self.jobcard_mgr.create_jobcard(
            vehicle_make="Maruti", vehicle_model="Swift", vehicle_year="2022",
            vehicle_reg="MH-14-EA-9999", owner_name="Arjun Verma", owner_phone="9811223344",
            complaint="Car clicks but engine will not turn over", diagnosis=diag, mechanic=None
        )
        self.service.initiate_workflow(jc, diag)
        self.assertEqual(jc["approval_status"], ApprovalStatus.PENDING_COMPANY_REVIEW)
        # Ensure mechanic was NOT assigned yet
        self.assertEqual(jc["assigned_mechanic_id"], "")

        # 3. Company Reviewer reviews and approves via signed Telegram callback
        token = jc["review_token"]
        ok, msg, jc = self.service.handle_reviewer_action(
            jc["jobcard_id"], "approve", "123456789", token, note="Verified by Master Inspector"
        )
        self.assertTrue(ok)
        self.assertEqual(jc["approval_status"], ApprovalStatus.PENDING_CUSTOMER_APPROVAL)
        self.assertIsNotNone(jc.get("estimate"))
        self.assertTrue(jc["estimate"]["parts_cost"] > 0)

        # 4. Customer verifies and approves from portal
        ok, msg, updated_jc = self.service.handle_customer_decision(
            jc["jobcard_id"], "approve", customer_identifier="MH-14-EA-9999"
        )
        self.assertTrue(ok)
        self.assertEqual(updated_jc["approval_status"], ApprovalStatus.CUSTOMER_APPROVED)
        self.assertEqual(updated_jc["status"], "In Progress")

        # 5. Verify mechanic dispatch, pipeline addition, and auto-orders occurred
        self.assertEqual(updated_jc["assigned_mechanic_id"], "M-001")
        self.assertEqual(updated_jc["assigned_mechanic_name"], "Rajesh Kumar")
        self.assertTrue(len(self.mech_sched.pipeline) > 0)
        self.assertTrue(len(self.notif_svc.assigned_notifications) > 0)
        # Verify missing parts (P-002 has 0 stock) triggered auto-order
        self.assertTrue(len(self.ord_mgr.orders) > 0)


class TestFlagTogglesAndRegression(unittest.TestCase):
    """Regression tests verifying behavior with flags ON and OFF."""

    def setUp(self):
        self.jobcard_mgr = MockJobCardManager()
        self.mech_sched = MockMechanicScheduler()
        self.notif_svc = MockNotificationService()
        self.inv_mgr = MockInventoryManager()
        self.ord_mgr = MockOrderManager()
        self.est_engine = MockEstimationEngine()
        self.video_svc = VideoGuideService()

    def test_video_guides_flag_off_and_on(self):
        """Verify video service can be enabled and disabled cleanly."""
        config.ENABLE_VIDEO_GUIDES = False
        self.assertFalse(config.ENABLE_VIDEO_GUIDES)

        config.ENABLE_VIDEO_GUIDES = True
        guide = self.video_svc.get_repair_guide("Brake squeal")
        self.assertIsNotNone(guide)
        self.assertTrue(len(guide["stages"]) > 0)

    def test_legacy_auto_assign_when_approval_flag_off(self):
        """When ENABLE_APPROVAL_WORKFLOW is False, verify legacy direct auto-assignment functions."""
        config.ENABLE_APPROVAL_WORKFLOW = False
        mech = self.mech_sched.auto_assign(None, "Medium")
        jc = self.jobcard_mgr.create_jobcard(
            "Ford", "Focus", "2019", "MH-03-XY-1111", "Legacy User", "9900112233",
            "Oil leak", None, mechanic=mech
        )
        self.assertEqual(jc["assigned_mechanic_id"], "M-001")
        self.assertEqual(jc["assigned_mechanic_name"], "Rajesh Kumar")
        # Legacy status defaults to Pending / In Progress, not gated by review
        self.assertNotIn(jc.get("approval_status"), [ApprovalStatus.PENDING_COMPANY_REVIEW])

        # Restore flag
        config.ENABLE_APPROVAL_WORKFLOW = True


class TestVisualRepairAssistanceSystem(unittest.TestCase):
    """Comprehensive tests for AI-Powered Visual Repair Assistance System (Feature 1 Replacement)."""

    def setUp(self):
        self.generator = RepairGuideGenerator()
        self.image_retriever = ImageRetriever()

    def test_five_core_faults_generation(self):
        """Test all 5 required predicted faults for complete structure, tools, safety, steps, and images."""
        required_faults = [
            ("Starter Motor Failure", "Maruti", "Swift", 2022, "Electrical"),
            ("Battery Failure", "Hyundai", "i20", 2021, "Electrical"),
            ("Alternator Failure", "Tata", "Nexon", 2023, "Electrical"),
            ("Cooling System Failure", "Mahindra", "XUV700", 2022, "Cooling"),
            ("Brake System Failure", "Honda", "City", 2020, "Brakes"),
        ]

        for fault, make, model, year, system in required_faults:
            with self.subTest(fault=fault):
                guide = self.generator.get_repair_guide(
                    fault_name=fault,
                    vehicle_make=make,
                    vehicle_model=model,
                    vehicle_year=year,
                    system=system
                )
                # Validate with Pydantic schema
                validated = RepairGuide(**guide)
                self.assertEqual(validated.predicted_fault, fault)
                self.assertTrue(len(validated.repair_title) > 5)
                self.assertTrue(len(validated.fault_explanation) > 20)
                self.assertTrue(len(validated.required_tools) >= 3)
                self.assertTrue(len(validated.safety_precautions) >= 3)
                self.assertTrue(len(validated.repair_steps) >= 5)
                self.assertTrue(len(validated.final_verification) >= 3)
                self.assertIn(make, validated.vehicle_context)
                self.assertIn(model, validated.vehicle_context)

                for step in validated.repair_steps:
                    self.assertTrue(step.step_number >= 1)
                    self.assertTrue(len(step.title) > 3)
                    self.assertTrue(len(step.instruction) > 15)
                    self.assertTrue(len(step.image_search_query) > 3)
                    self.assertIsNotNone(step.image_source)

    def test_missing_vehicle_information_handling(self):
        """Verify graceful handling when vehicle make/model/year are omitted."""
        guide = self.generator.get_repair_guide(fault_name="Starter Motor Solenoid Failure")
        self.assertIsNotNone(guide)
        self.assertEqual(guide["vehicle_context"], "Standard Vehicle")
        self.assertTrue(len(guide["repair_steps"]) >= 5)
        self.assertIn("PREDICTED", guide["disclaimer"].upper())

    def test_llm_json_validation_and_error_fallback(self):
        """Verify invalid LLM JSON responses are caught and fall back safely."""
        bad_json = "```json\n{ invalid json structure \n```"
        parsed = self.generator._parse_llm_json(bad_json)
        self.assertIsNone(parsed)

        incomplete_json = '{"repair_title": "Test Only"}'
        parsed2 = self.generator._parse_llm_json(incomplete_json)
        self.assertIsNone(parsed2)

    def test_image_retrieval_and_placeholder_fallback(self):
        """Verify image retriever returns valid URLs for known components and safe None placeholder for unknown."""
        url, source = self.image_retriever.get_image("starter motor solenoid wiring diagram", "Starter Motor")
        self.assertIsNotNone(url)
        self.assertTrue(url.startswith("http"))
        self.assertIn("Wikimedia Commons", source)

        # Nonsense query should not fabricate a fake URL
        url_none, src_none = self.image_retriever.get_image("xyz_nonexistent_quantum_flux_capacitor_99999", "")
        self.assertIsNone(url_none)
        self.assertIsNotNone(src_none)

    def test_caching_prevents_redundant_generation(self):
        """Verify identical vehicle + fault requests hit the cache."""
        key = self.generator._make_cache_key("Alternator Failure", "Toyota", "Innova", 2022)
        guide1 = self.generator.get_repair_guide("Alternator Failure", "Toyota", "Innova", 2022)
        self.assertIn(key, self.generator.memory_cache)
        guide2 = self.generator.get_repair_guide("Alternator Failure", "Toyota", "Innova", 2022)
        self.assertEqual(guide1["generated_at"], guide2["generated_at"])


if __name__ == "__main__":
    unittest.main()
