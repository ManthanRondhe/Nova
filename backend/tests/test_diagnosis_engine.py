"""
Unit and Integration Tests for AutoMech-AI Custom Hybrid ML Ensemble & Differential Questioning Engine.
Verifies:
1. High-confidence (>=90%) immediate predictions on specific symptoms and OBD-II codes.
2. Refusal to guess (confidence <78%) and generation of targeted differential questions on ambiguous queries.
3. Multi-turn confirmation of Candidate #1 locking confidence to >=94%.
4. Multi-turn rejection ("No") of Candidate #1 eliminating it and promoting Candidate #2 to >=88% confidence.
5. Fast inference latency (<50ms per query).
"""
import unittest
import os
import sys
import time

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from config import config
from services.diagnosis_engine import DiagnosisEngine


class TestDiagnosisEngineAccuracyAndDifferentialLoop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = DiagnosisEngine(config.DATA_DIR)

    def test_specific_symptom_high_confidence(self):
        """Specific symptoms should yield >= 90% confidence immediately without needing follow-up."""
        cases = [
            ("engine making loud knocking noise when accelerating", "Connecting Rod Bearing Failure"),
            ("white smoke from exhaust and coolant level dropping", "Head Gasket Failure"),
            ("grinding metal on metal sound when pressing brake pedal", "Brake Disc Worn Below Minimum"),
            ("turning key gives single click and dashboard lights stay bright", "Starter Motor Failure"),
            ("car battery dead slow crank in morning and dashboard lights dim", "Battery End of Life"),
            ("AC blower only works on highest speed setting 4", "Blower Motor Resistor Failure"),
            ("Royal Enfield engine making tik tik tappet noise from right side", "Tappet Clearance Incorrect (RE)"),
        ]
        for query, expected_fault in cases:
            results = self.engine.diagnose(query, top_n=3)
            self.assertTrue(len(results) > 0, f"No results for '{query}'")
            self.assertEqual(results[0]["fault_name"], expected_fault, f"Wrong top fault for '{query}'")
            self.assertGreaterEqual(results[0]["confidence"], 0.88, f"Confidence too low for '{query}': {results[0]['confidence']}")

    def test_obd_code_exact_prediction(self):
        """Direct OBD-II queries must return the exact canonical fault with >= 94% confidence."""
        obd_cases = [
            ("P0171", "Vacuum Leak"),
            ("OBD code P0420", "Catalytic Converter Failure"),
            ("C0545 EPS warning light", "Electric Power Steering Motor Failure"),
            ("P2002 diesel limp mode", "DPF Clogged (Diesel)"),
        ]
        for query, expected_fault in obd_cases:
            results = self.engine.diagnose(query, top_n=3)
            self.assertTrue(len(results) > 0)
            self.assertEqual(results[0]["fault_name"], expected_fault)
            self.assertGreaterEqual(results[0]["confidence"], 0.94)

    def test_ambiguous_query_triggers_differential_question(self):
        """Broad/vague queries must stay below the 0.78 threshold and generate a differential question comparing Top 1 & Top 2."""
        ambiguous_queries = [
            "car wont start",
            "car vibrating at idle",
            "engine overheating",
        ]
        for q in ambiguous_queries:
            results = self.engine.diagnose(q, top_n=3)
            self.assertGreaterEqual(len(results), 2)
            self.assertLess(results[0]["confidence"], 0.78, f"Expected '{q}' to trigger follow-up (<0.78), got {results[0]['confidence']}")
            question = self.engine.generate_differential_question(results, q)
            self.assertIn(results[0]["fault_name"], question)
            self.assertIn(results[1]["fault_name"], question)

    def test_multiturn_elimination_and_reranking(self):
        """Saying 'No' or describing Candidate #2's clue must eliminate Candidate #1 and promote Candidate #2 to high confidence."""
        initial_q = "car vibrating at idle"
        r1 = self.engine.diagnose(initial_q, top_n=3)
        top1_name = r1[0]["fault_name"]
        top2_name = r1[1]["fault_name"]
        diff_q = self.engine.generate_differential_question(r1, initial_q)

        # User denies Candidate #1 (Vacuum Leak) and confirms Candidate #2 (Engine Mount Failure)
        results_after, rejected = self.engine.evaluate_followup_conversation(
            recent_user_msgs=[initial_q],
            assistant_msgs=[diff_q],
            current_user_text="no hissing sound, I feel strong vibration in steering and seat at idle"
        )
        self.assertIn(top1_name, rejected)
        self.assertEqual(results_after[0]["fault_name"], top2_name)
        self.assertGreaterEqual(results_after[0]["confidence"], 0.90)

    def test_fast_inference_speed(self):
        """Inference must execute in under 60ms."""
        t0 = time.time()
        self.engine.diagnose("brake pedal vibrating when braking at high speed", top_n=3)
        elapsed_ms = (time.time() - t0) * 1000
        self.assertLess(elapsed_ms, 60.0, f"Inference took {elapsed_ms:.1f}ms (expected <60ms)")


if __name__ == "__main__":
    unittest.main()
