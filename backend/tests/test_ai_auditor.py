"""
Unit and Integration Tests for Feature 3:
Independent AI Diagnostic Auditor & Anti-Overreplacement Quality Assurance System
"""
import unittest
import os
import sys

# Ensure backend directory is in path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from config import config
from services.ai_auditor_service import AIAuditorService, AuditVerdict, PartNecessityStatus
from services.approval_workflow_service import ApprovalWorkflowService, ApprovalStatus
from tests.test_features import (
    MockJobCardManager,
    MockMechanicScheduler,
    MockNotificationService,
    MockInventoryManager,
    MockOrderManager,
    MockEstimationEngine
)


class TestAIAuditorCore(unittest.TestCase):
    """Tests for the isolated AI Auditor component evaluation and unnecessary replacement detection."""

    def setUp(self):
        self.data_dir = os.path.join(backend_dir, "data")
        self.auditor = AIAuditorService(self.data_dir)

    def test_unnecessary_replacement_detection_alternator(self):
        """
        Verify that quoting an unrelated Starter Motor or Fuel Pump
        during an Alternator failure is caught as UNNECESSARY_OVERREPLACEMENT.
        """
        complaint = "Battery warning light illuminated, headlights flickering and dimming at night"
        diagnosis = {
            "fault_name": "Alternator Diode Pack & Voltage Regulator Failure",
            "confidence": 0.94,
            "severity": "High"
        }
        parts = [
            {"part_id": "P-ALT-01", "name": "Alternator Assembly", "unit_price": 5500, "category": "Electrical"},
            {"part_id": "P-BLT-01", "name": "Serpentine Drive Belt", "unit_price": 600, "category": "Engine"},
            # Unnecessary replacement suspect:
            {"part_id": "P-STR-01", "name": "Starter Motor Assembly", "unit_price": 3800, "category": "Electrical"},
        ]

        result = self.auditor.evaluate_diagnosis_and_parts(
            complaint=complaint,
            diagnosis=diagnosis,
            parts_input=parts,
            strictness="balanced"
        )

        self.assertIsNotNone(result)
        self.assertEqual(result["metrics"]["total_parts_evaluated"], 3)
        self.assertEqual(result["metrics"]["unnecessary_parts_blocked"], 1)
        self.assertEqual(result["metrics"]["customer_savings"], 3800)

        # Ensure starter motor was pruned and flagged
        starter_analysis = next(p for p in result["parts_analysis"] if "Starter Motor" in p["part_name"])
        self.assertEqual(starter_analysis["status"], PartNecessityStatus.UNNECESSARY_OVERREPLACEMENT)
        self.assertEqual(starter_analysis["action_taken"], "PRUNED")
        self.assertIn("Starter motor operates on separate starting circuit", starter_analysis["technical_rationale"])

        # Ensure alternator was approved
        alt_analysis = next(p for p in result["parts_analysis"] if "Alternator" in p["part_name"])
        self.assertEqual(alt_analysis["status"], PartNecessityStatus.ESSENTIAL)
        self.assertEqual(alt_analysis["action_taken"], "APPROVED")

        # Verdict should be GREEN_FLAG_OPTIMIZED because unnecessary part was pruned
        self.assertEqual(result["verdict"], AuditVerdict.GREEN_FLAG_OPTIMIZED)
        self.assertTrue(result["autonomous_green_flag_granted"])

    def test_cross_system_predatory_upsell(self):
        """
        Verify that adding unrelated parts from an entirely different subsystem
        (e.g. suspension strut during a brake service) is flagged as cross-system upsell.
        """
        complaint = "High pitched brake squeal when pressing brake pedal"
        diagnosis = {
            "fault_name": "Worn Front Brake Pads and Disc Glazing",
            "confidence": 0.91,
            "severity": "Medium"
        }
        parts = [
            {"part_id": "P-BRK-01", "name": "Front Brake Pad Set", "unit_price": 1400, "category": "Brakes"},
            # Predatory cross-system addition:
            {"part_id": "P-SUS-01", "name": "Suspension Strut Bushing Kit", "unit_price": 2800, "category": "Suspension"},
        ]

        result = self.auditor.evaluate_diagnosis_and_parts(
            complaint=complaint,
            diagnosis=diagnosis,
            parts_input=parts,
            strictness="strict"
        )

        self.assertEqual(result["metrics"]["unnecessary_parts_blocked"], 1)
        susp_part = next(p for p in result["parts_analysis"] if "Suspension" in p["part_name"])
        self.assertEqual(susp_part["status"], PartNecessityStatus.UNNECESSARY_OVERREPLACEMENT)
        self.assertIn("CROSS-SYSTEM", susp_part["technical_rationale"].upper())
        self.assertEqual(result["metrics"]["customer_savings"], 2800)

    def test_perfect_diagnosis_approved_cleanly(self):
        """
        Verify that an honest repair quotation with only essential and valid
        consumable parts receives GREEN_FLAG_APPROVED with 0 unnecessary parts.
        """
        complaint = "Deep metallic knocking sound from bottom engine block under acceleration"
        diagnosis = {
            "fault_name": "Connecting Rod Bearing Failure",
            "confidence": 0.89,
            "severity": "Critical"
        }
        parts = [
            {"part_id": "P-001", "name": "Connecting Rod Bearing Set", "unit_price": 1200, "category": "Engine"},
            {"part_id": "P-002", "name": "Oil Pan Gasket", "unit_price": 350, "category": "Engine"}
        ]

        result = self.auditor.evaluate_diagnosis_and_parts(
            complaint=complaint,
            diagnosis=diagnosis,
            parts_input=parts
        )

        self.assertEqual(result["metrics"]["unnecessary_parts_blocked"], 0)
        self.assertEqual(result["metrics"]["customer_savings"], 0)
        self.assertEqual(result["verdict"], AuditVerdict.GREEN_FLAG_APPROVED)
        self.assertTrue(result["autonomous_green_flag_granted"])
        self.assertGreaterEqual(result["integrity_score"], 85)

    def test_critical_overreplacement_blocked(self):
        """
        Verify that an egregious quote where over 60% of parts are unnecessary
        is FLAGGED_OVERREPLACEMENT and blocked from autonomous green flag.
        """
        complaint = "Car clicks once but starter will not spin"
        diagnosis = {
            "fault_name": "Starter Motor Relay Failure",
            "confidence": 0.88,
            "severity": "Medium"
        }
        parts = [
            {"part_id": "P-REL-01", "name": "Starter Relay", "unit_price": 450, "category": "Electrical"},
            # Excessive replacements:
            {"part_id": "P-ALT-01", "name": "Alternator Assembly", "unit_price": 5500, "category": "Electrical"},
            {"part_id": "P-FUL-01", "name": "Fuel Pump Assembly", "unit_price": 4800, "category": "Fuel"},
            {"part_id": "P-TMC-01", "name": "Timing Chain Kit", "unit_price": 3500, "category": "Engine"},
        ]

        result = self.auditor.evaluate_diagnosis_and_parts(
            complaint=complaint,
            diagnosis=diagnosis,
            parts_input=parts
        )

        self.assertEqual(result["overreplacement_risk"], "CRITICAL_OVERREPLACEMENT")
        self.assertEqual(result["verdict"], AuditVerdict.FLAGGED_OVERREPLACEMENT)
        self.assertFalse(result["autonomous_green_flag_granted"])


class TestAIAuditorWorkflowIntegration(unittest.TestCase):
    """Tests integrating the Independent AI Auditor into ApprovalWorkflowService to replace Telegram human bottleneck."""

    def setUp(self):
        self.data_dir = os.path.join(backend_dir, "data")
        self.jobcard_mgr = MockJobCardManager()
        self.mech_sched = MockMechanicScheduler()
        self.notif_svc = MockNotificationService()
        self.inv_mgr = MockInventoryManager()
        self.ord_mgr = MockOrderManager()
        self.est_engine = MockEstimationEngine()
        self.ai_auditor = AIAuditorService(self.data_dir)

        self.service = ApprovalWorkflowService(
            data_dir=self.data_dir,
            jobcard_manager=self.jobcard_mgr,
            mechanic_scheduler=self.mech_sched,
            notification_service=self.notif_svc,
            inventory_manager=self.inv_mgr,
            order_manager=self.ord_mgr,
            estimation_engine=self.est_engine,
            ai_auditor_service=self.ai_auditor
        )

    def test_autonomous_green_flag_replaces_man_in_the_middle(self):
        """
        Test that when AI Auditor is active, a valid job card is automatically evaluated,
        green-flagged, and advanced directly to PENDING_CUSTOMER_APPROVAL without waiting
        for a human company reviewer callback on Telegram!
        """
        diag = {
            "fault_name": "Connecting Rod Bearing Failure",
            "confidence": 0.90,
            "severity": "Critical",
            "required_parts": "P-001,P-002"
        }
        jc = self.jobcard_mgr.create_jobcard(
            vehicle_make="Maruti", vehicle_model="Swift", vehicle_year="2022",
            vehicle_reg="MH-12-DE-1111", owner_name="Vikram Singh", owner_phone="9988776655",
            complaint="engine making loud knocking noise when accelerating", diagnosis=diag
        )

        # Initiate workflow
        self.service.initiate_workflow(jc, diag)

        # Verify state progressed immediately to PENDING_CUSTOMER_APPROVAL
        self.assertEqual(jc["approval_status"], ApprovalStatus.PENDING_CUSTOMER_APPROVAL)
        self.assertIn("AI_Sentinel_Arbiter", jc["reviewed_by"])
        self.assertIsNotNone(jc.get("ai_audit"))
        self.assertTrue(jc["ai_audit"]["autonomous_green_flag_granted"])

        # Verify audit trail contains the autonomous AI Green Flag entry
        ai_entries = [e for e in jc["audit_log"] if "AI_Sentinel_Arbiter" in e.get("actor", "")]
        self.assertTrue(len(ai_entries) > 0)
        self.assertIn("Autonomous Green Flag", ai_entries[0]["action"])

        # Verify customer notification was prepared
        self.assertTrue(len(self.notif_svc.sent_messages) > 0)

    def test_autonomous_pruning_reduces_customer_estimate(self):
        """
        Test that when an unnecessary part is included, the AI Auditor
        autonomously prunes the part from the jobcard and official quote.
        """
        diag = {
            "fault_name": "Alternator diode failure",
            "confidence": 0.88,
            "severity": "High",
            # P-008 is Starter Motor Assembly, unnecessary for alternator!
            "required_parts": "P-001,P-008"
        }
        jc = self.jobcard_mgr.create_jobcard(
            vehicle_make="Hyundai", vehicle_model="i20", vehicle_year="2021",
            vehicle_reg="MH-02-XY-9999", owner_name="Pooja Sharma", owner_phone="9876501234",
            complaint="battery light on dashboard, dim light, charging problem", diagnosis=diag
        )

        self.service.initiate_workflow(jc, diag)

        self.assertEqual(jc["approval_status"], ApprovalStatus.PENDING_CUSTOMER_APPROVAL)
        # Ensure P-008 (Starter Motor) was pruned from required_parts
        self.assertNotIn("P-008", jc["required_parts"])
        self.assertEqual(jc["required_parts"], "P-001")
        self.assertTrue(jc.get("customer_savings", 0) > 0)


class TestAIAssistantChatConsultation(unittest.TestCase):
    """Tests for the interactive AI Developer / Diagnostic Arbiter conversational interface."""

    def setUp(self):
        self.data_dir = os.path.join(backend_dir, "data")
        self.auditor = AIAuditorService(self.data_dir)

    def test_audit_explanation_query(self):
        """Verify the AI developer provides rich technical reasons for flagged parts."""
        mock_audit = {
            "audit_id": "AUD-TEST-01",
            "verdict": AuditVerdict.GREEN_FLAG_OPTIMIZED,
            "integrity_score": 88,
            "metrics": {"customer_savings": 3500},
            "parts_analysis": [
                {
                    "part_name": "Starter Motor Assembly",
                    "unit_price": 3500,
                    "necessity_score": 15,
                    "action_taken": "PRUNED",
                    "technical_rationale": "Starter circuit operates independently from charging circuit.",
                    "suggested_alternative": "Test relay voltage drop first."
                }
            ],
            "engineering_guidance": {"recommended_diagnostic_procedure": "Check alternator output with carbon pile."}
        }
        mock_jc = {
            "jobcard_id": "JC-5555",
            "vehicle_make": "Toyota",
            "vehicle_model": "Innova",
            "complaint": "battery drain",
            "diagnosis_fault": "Alternator failure",
            "ai_audit": mock_audit
        }

        resp = self.auditor.chat_consultation("Why was the starter motor pruned?", jobcard_context=mock_jc)
        self.assertIn("Starter Motor Assembly", resp["reply"])
        self.assertIn("3,500", resp["reply"])
        self.assertIn("Unnecessary Replacements Blocked", resp["reply"])
        self.assertTrue(len(resp["suggestions"]) > 0)

    def test_diagnostic_tree_query(self):
        """Verify the AI returns ISO/SAE diagnostic trees and voltage drop thresholds."""
        resp = self.auditor.chat_consultation("Show me the diagnostic procedure and test steps")
        self.assertIn("Precision Diagnostic Protocol", resp["reply"])
        self.assertIn("merma", resp["reply"])
        self.assertIn("0.20V", resp["reply"])


if __name__ == "__main__":
    unittest.main()
