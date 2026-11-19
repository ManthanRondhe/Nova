"""
Nova AI - AI-Powered Visual Repair Guide Generator
Replaces the YouTube Video Guide Service.
Uses Google Gemini API (via REST) for structured repair guide generation,
with a comprehensive multi-system domain-expert engine covering all 13 automotive
systems and 450+ faults for offline / no-key operation.
Images and CAD technical schematics are retrieved via ImageRetriever.
"""
import os
import re
import json
import hashlib
from datetime import datetime, timezone
from typing import Optional, Dict, Any

import requests

from config import config
from database import db
from services.visual_repair.prompt_templates import SYSTEM_PROMPT, build_repair_guide_prompt
from services.visual_repair.image_retriever import ImageRetriever


class RepairGuideGenerator:
    """
    Generates step-by-step visual repair guides for diagnosed automotive faults.
    Replaces VideoGuideService entirely.
    """

    GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    DEFAULT_GEMINI_MODEL = "gemma-4-26b-a4b-it"

    def __init__(self, data_dir=None):
        self.data_dir = data_dir or config.DATA_DIR
        os.makedirs(self.data_dir, exist_ok=True)
        self.image_retriever = ImageRetriever(self.data_dir)
        self.cache_file = os.path.join(self.data_dir, "repair_guide_cache.json")
        self.memory_cache: Dict[str, Any] = {}
        self.cache_collection = getattr(db, "repair_guide_cache", None) if db is not None else None
        self._load_local_cache()

        self.gemini_api_key = getattr(config, "GEMINI_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")
        self.openai_api_key = getattr(config, "OPENAI_API_KEY", "") or os.environ.get("OPENAI_API_KEY", "")
        self.gemini_model = os.environ.get("GEMINI_MODEL", self.DEFAULT_GEMINI_MODEL)

    # ─────────────────────────────────────────────────────────────
    # Cache Layer
    # ─────────────────────────────────────────────────────────────
    def _load_local_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    # Only retain cached guides where all steps have valid image_urls
                    valid_cache = {}
                    for k, g in loaded.items():
                        steps = g.get("repair_steps", []) if isinstance(g, dict) else []
                        if steps and all(s.get("image_url") for s in steps):
                            valid_cache[k] = g
                    self.memory_cache = valid_cache
            except Exception:
                self.memory_cache = {}

    def _save_local_cache(self):
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.memory_cache, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _make_cache_key(self, fault: str, make: str, model: str, year: Optional[int]) -> str:
        raw = f"v2_{fault}_{make}_{model}_{year}".lower().strip()
        return hashlib.md5(raw.encode()).hexdigest()

    def _get_cached(self, key: str) -> Optional[Dict]:
        if key in self.memory_cache:
            return self.memory_cache[key]
        if self.cache_collection is not None:
            try:
                record = self.cache_collection.find_one({"cache_key": key})
                if record:
                    record.pop("_id", None)
                    guide = record.get("guide")
                    steps = guide.get("repair_steps", []) if isinstance(guide, dict) else []
                    if guide and steps and all(s.get("image_url") for s in steps):
                        self.memory_cache[key] = guide
                        return guide
            except Exception:
                pass
        return None

    def _save_to_cache(self, key: str, guide: Dict):
        self.memory_cache[key] = guide
        self._save_local_cache()
        if self.cache_collection is not None:
            try:
                self.cache_collection.update_one(
                    {"cache_key": key},
                    {"$set": {
                        "cache_key": key,
                        "guide": guide,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }},
                    upsert=True
                )
            except Exception:
                pass

    # ─────────────────────────────────────────────────────────────
    # Main Public API
    # ─────────────────────────────────────────────────────────────
    def get_repair_guide(
        self,
        fault_name: str,
        vehicle_make: str = "",
        vehicle_model: str = "",
        vehicle_year: int = None,
        engine_variant: str = "",
        symptoms: str = "",
        diagnostic_findings: str = "",
        fix_procedure: str = "",
        system: str = ""
    ) -> Dict:
        """
        Generate or retrieve a cached visual repair guide.
        Guaranteed to NEVER crash — always returns a valid dict with step images.
        """
        fault_name = (fault_name or "Unknown Fault").strip()
        vehicle_make = (vehicle_make or "").strip()
        vehicle_model = (vehicle_model or "").strip()

        cache_key = self._make_cache_key(fault_name, vehicle_make, vehicle_model, vehicle_year)
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        guide = None
        source_type = "domain_expert_fallback"

        if self.gemini_api_key:
            guide = self._generate_via_gemini(
                fault_name, vehicle_make, vehicle_model, vehicle_year,
                engine_variant, symptoms, diagnostic_findings, fix_procedure, system
            )
            if guide:
                source_type = "llm_gemini"

        if not guide and self.openai_api_key:
            guide = self._generate_via_openai(
                fault_name, vehicle_make, vehicle_model, vehicle_year,
                engine_variant, symptoms, diagnostic_findings, fix_procedure, system
            )
            if guide:
                source_type = "llm_openai"

        if not guide:
            guide = self._generate_domain_expert_guide(
                fault_name, vehicle_make, vehicle_model, vehicle_year,
                fix_procedure, system, symptoms, diagnostic_findings
            )

        guide = self._enrich_with_images(guide)

        vehicle_parts = [str(vehicle_year) if vehicle_year else "", vehicle_make, vehicle_model]
        vehicle_str = " ".join(p for p in vehicle_parts if p).strip() or "Standard Vehicle"
        guide["vehicle_context"] = vehicle_str
        guide["source_type"] = source_type
        guide["generated_at"] = datetime.now(timezone.utc).isoformat()
        guide["disclaimer"] = (
            "AI-assisted technical guidance based on a PREDICTED (not confirmed) fault. "
            "Always verify factory torque specifications, OEM component locations, and "
            "safety procedures in the vehicle manufacturer service manual before performing any repair."
        )

        self._save_to_cache(cache_key, guide)
        return guide

    # ─────────────────────────────────────────────────────────────
    # Gemini & OpenAI REST API Generation
    # ─────────────────────────────────────────────────────────────
    def _generate_via_gemini(self, fault_name, make, model, year, engine, symptoms, findings, fix, system) -> Optional[Dict]:
        try:
            user_prompt = build_repair_guide_prompt(
                fault_name, make, model, year, engine, symptoms, findings, fix, system
            )
            url = self.GEMINI_API_URL.format(model=self.gemini_model) + f"?key={self.gemini_api_key}"
            payload = {
                "contents": [{"role": "user", "parts": [{"text": SYSTEM_PROMPT + "\n\n" + user_prompt}]}],
                "generationConfig": {
                    "temperature": 0.3,
                    "maxOutputTokens": 4096,
                    "responseMimeType": "application/json"
                }
            }
            res = requests.post(url, json=payload, timeout=25)
            if res.status_code != 200:
                return None
            candidates = res.json().get("candidates", [])
            if not candidates:
                return None
            parts = candidates[0].get("content", {}).get("parts", [])
            texts = [p.get("text", "").strip() for p in parts if p.get("text", "").strip() and not p.get("thought")]
            if not texts and parts:
                texts = [parts[-1].get("text", "").strip()]
            text = texts[-1] if texts else ""
            return self._parse_llm_json(text) if text else None
        except Exception:
            return None

    def _generate_via_openai(self, fault_name, make, model, year, engine, symptoms, findings, fix, system) -> Optional[Dict]:
        try:
            user_prompt = build_repair_guide_prompt(
                fault_name, make, model, year, engine, symptoms, findings, fix, system
            )
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {self.openai_api_key}", "Content-Type": "application/json"}
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 4096,
                "response_format": {"type": "json_object"}
            }
            res = requests.post(url, json=payload, headers=headers, timeout=25)
            if res.status_code != 200:
                return None
            text = res.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            return self._parse_llm_json(text) if text else None
        except Exception:
            return None

    def _parse_llm_json(self, text: str) -> Optional[Dict]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r'^```(?:json)?\s*\n?', '', cleaned)
            cleaned = re.sub(r'\n?```\s*$', '', cleaned)
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict) and "repair_steps" in parsed:
                return self._validate_guide(parsed)
        except json.JSONDecodeError:
            pass
        match = re.search(r'\{[\s\S]*\}', cleaned)
        if match:
            try:
                parsed = json.loads(match.group())
                if isinstance(parsed, dict) and "repair_steps" in parsed:
                    return self._validate_guide(parsed)
            except json.JSONDecodeError:
                pass
        return None

    def _validate_guide(self, guide: Dict) -> Optional[Dict]:
        required = ["repair_title", "predicted_fault", "repair_steps"]
        for field in required:
            if field not in guide:
                return None
        steps = guide.get("repair_steps", [])
        if not isinstance(steps, list) or len(steps) == 0:
            return None

        cleaned_steps = []
        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                continue
            cleaned_steps.append({
                "step_number": step.get("step_number", i + 1),
                "title": step.get("title", f"Step {i + 1}"),
                "instruction": step.get("instruction", "Follow manufacturer service manual procedure."),
                "image_search_query": step.get("image_search_query", ""),
                "image_url": None,
                "image_source": None,
                "warning": step.get("warning")
            })
        guide["repair_steps"] = cleaned_steps
        guide.setdefault("fault_explanation", "")
        guide.setdefault("difficulty", "Intermediate")
        guide.setdefault("estimated_time", "")
        guide.setdefault("required_tools", [])
        guide.setdefault("safety_precautions", [])
        guide.setdefault("final_verification", [])
        return guide

    # ─────────────────────────────────────────────────────────────
    # Image Enrichment
    # ─────────────────────────────────────────────────────────────
    def _enrich_with_images(self, guide: Dict) -> Dict:
        fault = guide.get("predicted_fault", "")
        for step in guide.get("repair_steps", []):
            step_num = step.get("step_number", 1)
            step_title = step.get("title", "")
            query = step.get("image_search_query", "")
            context = f"{fault} {step_title}"
            try:
                url, source = self.image_retriever.get_image(
                    search_query=query,
                    component_context=context,
                    step_number=step_num,
                    step_title=step_title
                )
                step["image_url"] = url
                step["image_source"] = source or "Technical Reference"
            except Exception:
                svg_uri, svg_src = self.image_retriever.generate_technical_schematic_svg(
                    query=query, context=fault, step_number=step_num, step_title=step_title
                )
                step["image_url"] = svg_uri
                step["image_source"] = svg_src
        return guide

    # ─────────────────────────────────────────────────────────────
    # Multi-System Domain Expert Engine (Covers all 13 Systems)
    # ─────────────────────────────────────────────────────────────
    def _generate_domain_expert_guide(
        self,
        fault_name: str,
        vehicle_make: str = "",
        vehicle_model: str = "",
        vehicle_year: int = None,
        fix_procedure: str = "",
        system: str = "",
        symptoms: str = "",
        diagnostic_findings: str = ""
    ) -> Dict:
        fault_lower = fault_name.lower()
        sys_lower = (system or "").lower()
        combined = f"{fault_lower} {sys_lower}"

        # 1. Starter Motor
        if any(w in fault_lower for w in ["starter", "cranking", "start motor", "solenoid", "bendix"]):
            return self._starter_motor_guide(fault_name, fix_procedure)

        # 2. Battery
        if any(w in fault_lower for w in ["battery", "no start", "dead battery", "battery drain", "cdi"]):
            return self._battery_guide(fault_name, fix_procedure)

        # 3. Alternator / Charging
        if any(w in fault_lower for w in ["alternator", "charging", "battery light", "voltage regulator"]):
            return self._alternator_guide(fault_name, fix_procedure)

        # 4. Cooling System
        if any(w in combined for w in ["cooling", "radiator", "overheat", "thermostat", "coolant", "water pump", "heater core", "intercooler"]):
            return self._cooling_guide(fault_name, fix_procedure)

        # 5. Brake System
        if any(w in combined for w in ["brake", "braking", "pad", "rotor", "caliper", "abs", "master cylinder", "wheel cylinder"]):
            return self._brake_guide(fault_name, fix_procedure)

        # 6. Ignition / Spark / Coils / Sensors
        if any(w in fault_lower for w in ["spark plug", "ignition coil", "glow plug", "misfire", "crankshaft position", "camshaft position", "sensor", "oxygen", "maf", "mass air"]):
            return self._ignition_sensor_guide(fault_name, fix_procedure, system)

        # 7. Fuel System / Injectors / Pump / Carburetor / Throttle / EGR
        if any(w in combined for w in ["fuel", "injector", "carburetor", "cng", "throttle", "idle air", "egr", "intake", "vacuum"]):
            return self._fuel_induction_guide(fault_name, fix_procedure, system)

        # 8. Transmission / Clutch / Gearbox / Drivetrain
        if any(w in combined for w in ["clutch", "transmission", "gearbox", "synchronizer", "gear", "flywheel", "cvt", "differential", "driveshaft"]):
            return self._transmission_clutch_guide(fault_name, fix_procedure, system)

        # 9. Suspension & Wheel Bearings
        if any(w in combined for w in ["suspension", "shock", "strut", "ball joint", "bush", "spring", "wheel bearing", "anti roll", "stabilizer", "fork"]):
            return self._suspension_bearing_guide(fault_name, fix_procedure, system)

        # 10. Steering System
        if any(w in combined for w in ["steering", "tie rod", "rack", "alignment", "wheel balance", "king pin"]):
            return self._steering_guide(fault_name, fix_procedure, system)

        # 11. Exhaust / Catalytic / DPF
        if any(w in combined for w in ["exhaust", "catalytic", "dpf", "muffler", "silencer", "manifold"]):
            return self._exhaust_emissions_guide(fault_name, fix_procedure, system)

        # 12. AC / HVAC
        if any(w in combined for w in ["ac ", "a/c", "hvac", "refrigerant", "compressor", "condenser", "evaporator", "blower"]):
            return self._ac_hvac_guide(fault_name, fix_procedure, system)

        # 13. Engine Internal & Mechanical (Bearings, Piston Rings, Head Gasket, Timing, Valve Cover, Mounts)
        if any(w in combined for w in ["engine", "bearing", "piston", "gasket", "timing", "valve", "lifter", "tappet", "oil pump", "mount", "turbo", "belt", "chain"]):
            return self._engine_mechanical_guide(fault_name, fix_procedure, system)

        # 14. Dynamic Procedure Builder for any remaining specialized fault
        return self._dynamic_procedure_guide(fault_name, fix_procedure, system, symptoms, diagnostic_findings)

    def _starter_motor_guide(self, fault_name, fix_procedure=""):
        return {
            "repair_title": "Starter Motor Inspection, Testing and Replacement",
            "predicted_fault": fault_name,
            "fault_explanation": (
                "The starter motor converts electrical energy from the battery into mechanical "
                "torque to rotate the engine flywheel during cranking. Failure symptoms include "
                "clicking without cranking, intermittent starting, or complete silence when the "
                "ignition key is turned. Common causes include worn brushes, solenoid contact "
                "failure, or pinion gear damage."
            ),
            "difficulty": "Intermediate",
            "estimated_time": "1.5 - 2.5 hours",
            "required_tools": [
                "Socket wrench set (10mm, 12mm, 14mm)",
                "Digital multimeter",
                "Battery terminal puller / wire brush",
                "Inspection work light / LED flashlight",
                "Torque wrench",
                "Jack and rated jack stands",
                "Safety gloves and eye protection"
            ],
            "safety_precautions": [
                "Switch off ignition and remove key before beginning any work.",
                "Disconnect the NEGATIVE battery terminal first to prevent accidental short circuits.",
                "Never work under a vehicle supported only by a jack — always use rated jack stands.",
                "Allow the engine to cool before working near the exhaust manifold.",
                "Note: This is a PREDICTED fault. Confirm with physical testing before replacing the starter assembly."
            ],
            "repair_steps": [
                {
                    "step_number": 1,
                    "title": "Battery and Electrical Voltage Drop Test",
                    "instruction": (
                        "Measure resting battery voltage (should be 12.4V–12.7V with engine off). "
                        "Test voltage at the starter solenoid B+ terminal while an assistant cranks the ignition. "
                        "A drop below 10.5V at the battery or below 9.5V at the starter indicates a wiring or battery issue. "
                        "Also test the starter relay circuit if accessible."
                    ),
                    "image_search_query": "starter motor diagram",
                    "image_url": None,
                    "image_source": None,
                    "warning": "Keep hands and tools clear of moving engine components during cranking tests."
                },
                {
                    "step_number": 2,
                    "title": "Battery Isolation and Vehicle Safety Preparation",
                    "instruction": (
                        "Disconnect the NEGATIVE battery cable first, then the POSITIVE cable. "
                        "If working under the vehicle, raise and support it on rated jack stands. "
                        "Apply wheel chocks to prevent rolling. Ensure the gear selector is in Park (automatic) or Neutral (manual)."
                    ),
                    "image_search_query": "car battery terminal",
                    "image_url": None,
                    "image_source": None,
                    "warning": "Never disconnect the positive terminal first — a dropped spanner can short-circuit the battery to the chassis."
                },
                {
                    "step_number": 3,
                    "title": "Starter Motor Wiring Disconnection and Removal",
                    "instruction": (
                        "Locate the starter motor on the engine block (typically on the flywheel/flexplate side). "
                        "Disconnect the solenoid S-terminal (signal wire) and B-terminal (thick battery cable). "
                        "Remove the mounting bolts (usually 2–3 bolts, 12mm–14mm). Carefully withdraw the starter."
                    ),
                    "image_search_query": "starter motor solenoid wiring",
                    "image_url": None,
                    "image_source": None,
                    "warning": "Support the starter by hand as the last bolt is removed — it is heavy and may fall."
                },
                {
                    "step_number": 4,
                    "title": "Bench Inspection and New Starter Comparison",
                    "instruction": (
                        "Visually inspect the old starter for worn brushes, burnt solenoid contacts, or damaged pinion gear teeth. "
                        "Compare the old and new/refurbished starter: verify bolt spacing, pinion tooth count, and electrical connector alignment match."
                    ),
                    "image_search_query": "automobile starter component",
                    "image_url": None,
                    "image_source": None,
                    "warning": None
                },
                {
                    "step_number": 5,
                    "title": "Reinstallation, Torque, and Wiring Reconnection",
                    "instruction": (
                        "Position the new starter against the bell housing and hand-thread the mounting bolts to prevent cross-threading. "
                        "Torque fasteners to factory OEM specification as specified in the service manual. "
                        "Reconnect the B-terminal (battery cable) and S-terminal (signal wire)."
                    ),
                    "image_search_query": "torque wrench socket",
                    "image_url": None,
                    "image_source": None,
                    "warning": "Torque to OEM spec only — over-tightening can crack the starter housing or bell housing."
                },
                {
                    "step_number": 6,
                    "title": "System Testing and Cranking Verification",
                    "instruction": (
                        "Reconnect the POSITIVE battery terminal first, then the NEGATIVE. "
                        "Turn the ignition to verify the starter engages smoothly and the engine cranks without grinding. "
                        "Measure alternator charging voltage (should be 13.8V–14.5V at idle) to confirm normal operation."
                    ),
                    "image_search_query": "digital multimeter voltage test",
                    "image_url": None,
                    "image_source": None,
                    "warning": "If grinding noise persists, stop immediately — flywheel ring gear damage may require inspection."
                }
            ],
            "final_verification": [
                "Verify starter engages and disengages cleanly on three consecutive start cycles.",
                "Confirm no abnormal noises (grinding, clicking, or whining) during cranking.",
                "Check that all wiring connections are secure and insulated.",
                "Measure battery voltage after starting to confirm charging system operation (13.8V–14.5V).",
                "Lower the vehicle and verify it starts normally from the driver seat.",
                "Clear any diagnostic trouble codes (DTCs) if applicable."
            ]
        }

    def _battery_guide(self, fault_name, fix_procedure=""):
        return {
            "repair_title": f"{fault_name} — Battery & Electrical Load Service",
            "predicted_fault": fault_name,
            "fault_explanation": (
                "The 12V battery supplies starting current and stabilizes system voltage. "
                "Symptoms include slow cranking, clicking relays, dim lights, or electronic resets. "
                f"{fix_procedure}"
            ).strip(),
            "difficulty": "Beginner",
            "estimated_time": "0.5 - 1.0 hours",
            "required_tools": [
                "Digital multimeter & carbon pile load tester",
                "Battery terminal puller & wire brush",
                "Wrench set (10mm, 12mm, 13mm)",
                "Anti-corrosion terminal protector spray",
                "Safety gloves and acid-resistant goggles"
            ],
            "safety_precautions": [
                "Wear eye protection and gloves — battery electrolyte contains corrosive sulphuric acid.",
                "Keep sparks and flames away — lead-acid batteries emit flammable hydrogen gas.",
                "Always disconnect the NEGATIVE (-) cable first and reconnect it LAST.",
                "Confirm predicted fault via resting voltage and CCA load test before replacement."
            ],
            "repair_steps": [
                {
                    "step_number": 1,
                    "title": "Open-Circuit Voltage & Parasitic Draw Test",
                    "instruction": (
                        "Measure resting battery voltage with a digital multimeter: 12.6V+ indicates full charge; "
                        "below 12.0V indicates deep discharge or shorted cell. Perform a CCA load test to verify capacity under load."
                    ),
                    "image_search_query": "digital multimeter voltage test",
                    "image_url": None,
                    "image_source": None,
                    "warning": "Do not load-test a visibly swollen or cracked battery."
                },
                {
                    "step_number": 2,
                    "title": "Terminal Post Desulfation & Cable Inspection",
                    "instruction": (
                        "Inspect both battery posts and cable clamps for white/blue sulfate corrosion. "
                        "Neutralize corrosion and scrub contact surfaces bright with a battery terminal wire brush."
                    ),
                    "image_search_query": "corroded battery terminal post",
                    "image_url": None,
                    "image_source": None,
                    "warning": "Prevent cleaning residue from entering cell vent caps."
                },
                {
                    "step_number": 3,
                    "title": "Battery Isolation & Hold-Down Bracket Removal",
                    "instruction": (
                        "Loosen the 10mm clamp nut on the NEGATIVE (-) terminal and isolate the cable. "
                        "Disconnect the POSITIVE (+) terminal next. Unbolt the base hold-down clamp and lift the battery out level."
                    ),
                    "image_search_query": "car battery component",
                    "image_url": None,
                    "image_source": None,
                    "warning": "Support battery weight squarely; do not tilt over 45 degrees."
                },
                {
                    "step_number": 4,
                    "title": "Replacement Battery Installation & Clamping",
                    "instruction": (
                        "Seat the replacement battery matching OEM group size, terminal polarity, and CCA rating. "
                        "Torque the hold-down bracket so the casing cannot shift during braking or cornering."
                    ),
                    "image_search_query": "torque wrench socket",
                    "image_url": None,
                    "image_source": None,
                    "warning": "Verify polarity markings (+ and -) before touching cables to posts."
                },
                {
                    "step_number": 5,
                    "title": "Reconnection & Charging Voltage Verification",
                    "instruction": (
                        "Connect POSITIVE (+) clamp first, then NEGATIVE (-) clamp. Apply anti-corrosion grease. "
                        "Crank engine and verify charging voltage is between 13.8V and 14.5V at idle."
                    ),
                    "image_search_query": "alternator charging diagram",
                    "image_url": None,
                    "image_source": None,
                    "warning": None
                }
            ],
            "final_verification": [
                "Verify crisp engine cranking speed and immediate start.",
                "Confirm charging voltage reads 13.8V–14.5V with headlights and blower active.",
                "Ensure battery hold-down bracket is rock-solid.",
                "Verify battery/charging warning lamp on instrument cluster is extinguished."
            ]
        }

    def _alternator_guide(self, fault_name, fix_procedure=""):
        return {
            "repair_title": f"{fault_name} — Charging System & Alternator Service",
            "predicted_fault": fault_name,
            "fault_explanation": (
                "The alternator replenishes battery charge and powers vehicle electronics via a 3-phase stator and rectifier bridge. "
                f"{fix_procedure}"
            ).strip(),
            "difficulty": "Intermediate",
            "estimated_time": "1.5 - 2.5 hours",
            "required_tools": [
                "Socket wrench set (10mm, 12mm, 14mm)",
                "Serpentine belt tensioner bar",
                "Digital multimeter",
                "Torque wrench",
                "Safety glasses and work gloves"
            ],
            "safety_precautions": [
                "Disconnect the NEGATIVE battery cable before disconnecting the alternator B+ stud (live battery feed).",
                "Keep hands, hair, and meter leads clear of rotating accessory pulleys during running tests.",
                "Confirm predicted fault via charging output and ripple test before replacing the alternator."
            ],
            "repair_steps": [
                {
                    "step_number": 1,
                    "title": "Charging Output & Diode Ripple Diagnostic",
                    "instruction": (
                        "With engine idling, measure DC voltage across battery posts (normal: 13.8V–14.5V). "
                        "Switch multimeter to AC mode to check diode rectifier ripple (must be under 0.5V AC). "
                        + (fix_procedure if fix_procedure else "")
                    ),
                    "image_search_query": "digital multimeter voltage test",
                    "image_url": None,
                    "image_source": None,
                    "warning": "Keep meter leads clear of the spinning serpentine belt."
                },
                {
                    "step_number": 2,
                    "title": "Battery Isolation & Serpentine Belt Detensioning",
                    "instruction": (
                        "Disconnect the negative battery terminal. Sketch or photograph the serpentine belt routing diagram. "
                        "Rotate the automatic belt tensioner using a breaker bar and slip the belt off the alternator pulley."
                    ),
                    "image_search_query": "serpentine belt pulley",
                    "image_url": None,
                    "image_source": None,
                    "warning": "Release tensioner spring slowly to avoid pinched fingers."
                },
                {
                    "step_number": 3,
                    "title": "Electrical Connector & Alternator Unbolting",
                    "instruction": (
                        "Unclip the voltage regulator multi-pin harness plug. Remove the protective rubber boot and unbolt the B+ output nut. "
                        "Remove the upper and lower mounting bolts and lift the alternator clear of the bracket."
                    ),
                    "image_search_query": "alternator component",
                    "image_url": None,
                    "image_source": None,
                    "warning": None
                },
                {
                    "step_number": 4,
                    "title": "Pulley, Stator & Overrunning Clutch Inspection",
                    "instruction": (
                        "Spin the pulley by hand to check for rough rotor bearings. Verify the replacement alternator matches "
                        "the pulley rib count, mounting ear spacing, amperage rating, and regulator plug pinout."
                    ),
                    "image_search_query": "alternator cutaway diagram",
                    "image_url": None,
                    "image_source": None,
                    "warning": None
                },
                {
                    "step_number": 5,
                    "title": "Mounting, Belt Routing & Load Verification",
                    "instruction": (
                        "Bolt the alternator in place and torque mounting bolts to factory spec. Reconnect the B+ cable and regulator plug. "
                        "Seat the serpentine belt across all pulley grooves, reconnect the battery, and verify 14.0V+ charging under full load."
                    ),
                    "image_search_query": "torque wrench socket",
                    "image_url": None,
                    "image_source": None,
                    "warning": "Ensure belt ribs are centered on every pulley before starting the engine."
                }
            ],
            "final_verification": [
                "Confirm 13.8V–14.5V charging output at idle with high beams and AC blower ON.",
                "Verify battery warning icon on dashboard turns off immediately after start.",
                "Listen for smooth bearing rotation and zero belt chirp."
            ]
        }

    def _cooling_guide(self, fault_name, fix_procedure=""):
        return {
            "repair_title": f"{fault_name} — Engine Cooling & Thermal Service",
            "predicted_fault": fault_name,
            "fault_explanation": (
                "The pressurized cooling circuit regulates cylinder head and block temperature via the radiator, water pump, and thermostat. "
                f"{fix_procedure}"
            ).strip(),
            "difficulty": "Intermediate",
            "estimated_time": "1.5 - 3.0 hours",
            "required_tools": [
                "Cooling system pressure tester kit",
                "Hose clamp pliers & socket wrench set",
                "Coolant catch pan & spill-free bleed funnel",
                "Infrared thermometer / scan tool live data",
                "OEM-approved ethylene/propylene glycol coolant"
            ],
            "safety_precautions": [
                "NEVER open a radiator cap or expansion tank on a hot engine — scalding pressurized steam causes severe burns.",
                "Collect drained coolant in a sealed container; ethylene glycol is toxic.",
                "Disconnect cooling fan connector when working near fan shroud."
            ],
            "repair_steps": [
                {
                    "step_number": 1,
                    "title": "Cold Pressure Test & Leak Localization",
                    "instruction": (
                        "With engine completely cold, attach a radiator pressure tester and pressurize to the cap rating (typically 1.1–1.4 bar). "
                        "Inspect radiator seams, hose clamps, water pump weep hole, and thermostat housing for pressure drop or seepage."
                    ),
                    "image_search_query": "cooling system diagram",
                    "image_url": None,
                    "image_source": None,
                    "warning": "Do not exceed the maximum pressure stamped on the expansion cap."
                },
                {
                    "step_number": 2,
                    "title": "Controlled Coolant Drain & Hose Disconnection",
                    "instruction": (
                        "Place a drain pan beneath the radiator petcock valve and drain coolant below the target component level. "
                        "Release spring clamps with hose clamp pliers and twist hoses gently to break the seal without cracking plastic necks."
                    ),
                    "image_search_query": "car radiator cooling",
                    "image_url": None,
                    "image_source": None,
                    "warning": None
                },
                {
                    "step_number": 3,
                    "title": "Component Removal & Sealing Surface Prep",
                    "instruction": (
                        f"{fix_procedure or 'Unbolt the faulty cooling component (thermostat housing / radiator / water pump).'} "
                        "Clean mating flanges thoroughly and install a new OEM O-ring or gasket."
                    ),
                    "image_search_query": "wax pellet thermostat",
                    "image_url": None,
                    "image_source": None,
                    "warning": "Ensure thermostat jiggle/bleed pin is oriented at the 12 o'clock position."
                },
                {
                    "step_number": 4,
                    "title": "Reassembly & Factory Torque Application",
                    "instruction": (
                        "Mount the replacement component and tighten bolts evenly in a crisscross pattern to OEM torque spec. "
                        "Reconnect coolant hoses and position constant-tension clamps behind the pipe bead."
                    ),
                    "image_search_query": "torque wrench socket",
                    "image_url": None,
                    "image_source": None,
                    "warning": None
                },
                {
                    "step_number": 5,
                    "title": "Vacuum Refill, Air Bleeding & Fan Cycle Check",
                    "instruction": (
                        "Refill with 50/50 premixed OEM coolant. Open cooling circuit bleed screws until bubble-free coolant flows. "
                        "Run engine with cabin heater on MAX HOT until thermostat opens (~88°C–95°C) and radiator cooling fan cycles on and off."
                    ),
                    "image_search_query": "cooling system flow diagram",
                    "image_url": None,
                    "image_source": None,
                    "warning": "Trapped air pockets cause localized cylinder head overheating — bleed thoroughly."
                }
            ],
            "final_verification": [
                "Confirm engine temperature stabilizes at center gauge mark under load.",
                "Verify upper and lower radiator hoses pressurize and heat evenly once thermostat opens.",
                "Verify zero coolant drips under pressure and re-check expansion tank level when cold."
            ]
        }

    def _brake_guide(self, fault_name, fix_procedure=""):
        return {
            "repair_title": f"{fault_name} — Hydraulic Brake & Friction Service",
            "predicted_fault": fault_name,
            "fault_explanation": (
                "The hydraulic braking system converts pedal force into clamping pressure at the calipers/wheel cylinders. "
                f"{fix_procedure}"
            ).strip(),
            "difficulty": "Intermediate",
            "estimated_time": "1.5 - 2.5 hours",
            "required_tools": [
                "Socket wrench set & breaker bar",
                "Caliper piston compressor tool",
                "Micrometer & dial indicator (runout check)",
                "Torque wrench",
                "Brake cleaner spray & high-temp silicone pin grease",
                "DOT 3 / DOT 4 brake fluid & Vacuum bleeder"
            ],
            "safety_precautions": [
                "Support vehicle on rated jack stands on level ground and chock opposite wheels.",
                "Do not use compressed air on brake dust — clean only with dedicated brake cleaner spray.",
                "Never hang a brake caliper by its flexible rubber hydraulic hose.",
                "Always pump the brake pedal until firm BEFORE shifting into gear after service."
            ],
            "repair_steps": [
                {
                    "step_number": 1,
                    "title": "Wheel Removal & Friction / Hydraulic Inspection",
                    "instruction": (
                        "Chock wheels, raise vehicle on jack stands, and remove wheel assemblies. "
                        "Inspect brake pad lining thickness (minimum 3mm), rotor surface scoring, and hydraulic hoses/seals for weeping."
                    ),
                    "image_search_query": "disc brake caliper pads",
                    "image_url": None,
                    "image_source": None,
                    "warning": None
                },
                {
                    "step_number": 2,
                    "title": "Caliper Disassembly & Slide Pin Servicing",
                    "instruction": (
                        f"{fix_procedure or 'Unbolt caliper guide pins and suspend caliper from the coil spring with a wire hook.'} "
                        "Extract worn pads, clean Stainless hardware clips, and lubricate slide pins with high-temp silicone grease."
                    ),
                    "image_search_query": "disc brake caliper",
                    "image_url": None,
                    "image_source": None,
                    "warning": "Do not get grease or fluid on friction pad surfaces or rotor faces."
                },
                {
                    "step_number": 3,
                    "title": "Rotor Minimum Thickness & Lateral Runout Check",
                    "instruction": (
                        "Measure brake disc thickness across 4 points with a micrometer and compare with the cast minimum spec. "
                        "Degrease new or resurfaced rotors thoroughly with brake cleaner."
                    ),
                    "image_search_query": "ventilated brake disc rotor",
                    "image_url": None,
                    "image_source": None,
                    "warning": None
                },
                {
                    "step_number": 4,
                    "title": "Piston Retraction & Caliper Reassembly",
                    "instruction": (
                        "Monitor master cylinder reservoir level and slowly retract the caliper piston squarely using a piston press tool. "
                        "Fit new brake pads with shims, reinstall the caliper, and torque bracket and slide pin bolts to OEM spec."
                    ),
                    "image_search_query": "torque wrench socket",
                    "image_url": None,
                    "image_source": None,
                    "warning": "Electronic parking brake (EPB) rear calipers must be commanded into service mode via scan tool before retracting."
                },
                {
                    "step_number": 5,
                    "title": "Hydraulic Circuit Bleeding & Pedal Firmness Test",
                    "instruction": (
                        "Bleed hydraulic lines starting furthest from the master cylinder (RR -> LR -> RF -> LF) until clear, bubble-free DOT fluid flows. "
                        "Torque wheel lug nuts in a star pattern and pump brake pedal until rock-solid."
                    ),
                    "image_search_query": "bleeding brakes fluid",
                    "image_url": None,
                    "image_source": None,
                    "warning": "Never allow the master cylinder reservoir to drop below MIN during bleeding."
                }
            ],
            "final_verification": [
                "Pump brake pedal 10–15 times with engine off to confirm firm, high pedal travel.",
                "Verify master cylinder fluid level is at MAX and zero leaks exist at bleeder nipples.",
                "Perform a 30 km/h bedding-in road test confirming straight, vibration-free stopping."
            ]
        }

    def _engine_mechanical_guide(self, fault_name, fix_procedure="", system="Engine"):
        return {
            "repair_title": f"{fault_name} — Engine Mechanical & Valvetrain Overhaul",
            "predicted_fault": fault_name,
            "fault_explanation": (
                f"Diagnosed mechanical fault ({fault_name}) within the {system or 'Engine'} assembly. "
                f"{fix_procedure or 'Requires precision inspection of clearances, sealing surfaces, and lubrication passages.'}"
            ),
            "difficulty": "Advanced",
            "estimated_time": "3.0 - 6.5 hours",
            "required_tools": [
                "Socket, ratchet & breaker bar set",
                "Precision micrometer torque wrench & angle gauge",
                "Compression / cylinder leak-down tester",
                "Feeler gauge set & straightedge",
                "Gasket scraper, RTV sealant & assembly lube"
            ],
            "safety_precautions": [
                "Disconnect negative battery terminal and allow engine block and exhaust manifold to cool completely.",
                "Support engine block securely with a floor jack and wood block when removing engine mounts or oil pan.",
                "Keep timing marks locked at TDC #1 before loosening timing chain/belt tensioners.",
                f"Note: {fault_name} is a PREDICTED fault — verify via compression, oil pressure, or visual inspection first."
            ],
            "repair_steps": [
                {
                    "step_number": 1,
                    "title": "Compression, Oil Pressure & Mechanical Verification",
                    "instruction": (
                        f"Confirm {fault_name} before teardown. Check engine oil level and inspect drained oil or filter for metallic debris. "
                        f"{fix_procedure.split('.')[0] + '.' if fix_procedure else 'Perform cylinder compression or oil pressure gauge verification.'}"
                    ),
                    "image_search_query": f"{fault_name} engine piston connecting rod",
                    "image_url": None,
                    "image_source": None,
                    "warning": "Disable fuel injection and ignition before cranking for a compression test."
                },
                {
                    "step_number": 2,
                    "title": "Ancillary Disassembly & TDC Alignment",
                    "instruction": (
                        "Disconnect battery, drain fluids (oil/coolant as required), and label all vacuum lines, sensor connectors, and ignition leads. "
                        "Rotate crankshaft clockwise by hand to align Cylinder #1 Top Dead Center (TDC) timing marks."
                    ),
                    "image_search_query": "timing belt engine camshaft",
                    "image_url": None,
                    "image_source": None,
                    "warning": "Never rotate the engine backward (counter-clockwise) — timing chain could jump a tooth."
                },
                {
                    "step_number": 3,
                    "title": "Component Teardown & Precision Measurement",
                    "instruction": (
                        f"{fix_procedure or f'Unbolt and remove the affected assembly for {fault_name} in reverse-spiral sequence.'} "
                        "Check mating deck/journal surfaces for warpage, scoring, or bearing wear using feeler gauges or plastigauge."
                    ),
                    "image_search_query": "cylinder head gasket engine",
                    "image_url": None,
                    "image_source": None,
                    "warning": "Do not use abrasive discs on aluminum cylinder head or block mating faces."
                },
                {
                    "step_number": 4,
                    "title": "New Component Assembly & Multi-Stage Torque",
                    "instruction": (
                        "Pre-lubricate moving bearings/seals with clean engine oil or assembly lube. Install new OEM gaskets/seals and "
                        "tighten fasteners in the factory multi-stage crisscross sequence using a calibrated torque wrench."
                    ),
                    "image_search_query": "torque wrench socket",
                    "image_url": None,
                    "image_source": None,
                    "warning": "Torque-to-yield (TTY) head and rod bolts must be replaced with new fasteners — never reuse."
                },
                {
                    "step_number": 5,
                    "title": "Fluid Replenishment, Priming & Warm-Up Check",
                    "instruction": (
                        "Refill with fresh OEM-grade engine oil and coolant. Crank engine with fuel disabled for 10 seconds to build oil pressure, "
                        "then start engine and inspect for leaks, abnormal knocking, or warning lamps."
                    ),
                    "image_search_query": "digital multimeter voltage test",
                    "image_url": None,
                    "image_source": None,
                    "warning": "Shut down immediately if oil pressure warning light does not extinguish within 4 seconds."
                }
            ],
            "final_verification": [
                "Verify oil pressure light extinguishes immediately upon start-up.",
                "Confirm smooth idle with zero metallic knocking, ticking, orfluid seepage.",
                "Re-check oil and coolant levels after reaching full operating temperature."
            ]
        }

    def _ignition_sensor_guide(self, fault_name, fix_procedure="", system="Electrical"):
        return {
            "repair_title": f"{fault_name} — Ignition & Electronic Sensor Service",
            "predicted_fault": fault_name,
            "fault_explanation": (
                f"Electronic ignition and engine management sensors control spark timing and air-fuel stoichiometry. "
                f"{fix_procedure}"
            ).strip(),
            "difficulty": "Beginner",
            "estimated_time": "0.5 - 1.5 hours",
            "required_tools": [
                "OBD-II diagnostic scanner (live data & DTC reader)",
                "Digital multimeter",
                "Spark plug socket (14mm/16mm) & ratchet extension",
                "Wire feeler gauge & dielectric grease",
                "Electrical contact cleaner"
            ],
            "safety_precautions": [
                "Switch ignition OFF before unplugging ECU sensors or ignition coils to prevent voltage spikes.",
                "Allow exhaust manifold to cool before servicing Oxygen (O2) sensors or spark plugs.",
                "Blow compressed air around spark plug wells before removal so grit cannot fall into cylinders."
            ],
            "repair_steps": [
                {
                    "step_number": 1,
                    "title": "OBD-II Live Data Scan & Circuit Verification",
                    "instruction": (
                        f"Connect an OBD-II scan tool to retrieve stored and pending fault codes for {fault_name}. "
                        "Probe the harness connector with a digital multimeter to verify 5V/12V reference voltage and ground continuity."
                    ),
                    "image_search_query": "digital multimeter voltage test",
                    "image_url": None,
                    "image_source": None,
                    "warning": "Never back-probe waterproof ECU connectors with oversized probes that spread terminal pins."
                },
                {
                    "step_number": 2,
                    "title": "Connector Release & Component Extraction",
                    "instruction": (
                        f"{fix_procedure or f'Release the locking tab on the {fault_name} electrical connector and unbolt/unthread the component.'} "
                        "Inspect connector pins for green oxidation, oil intrusion, or bent terminals."
                    ),
                    "image_search_query": "spark plug ignition coil",
                    "image_url": None,
                    "image_source": None,
                    "warning": None
                },
                {
                    "step_number": 3,
                    "title": "Bench Inspection, Gap Check & Replacement",
                    "instruction": (
                        "Inspect the removed sensor/ignition part for carbon fouling, cracked ceramic insulation, or open coil windings. "
                        "Verify the replacement part matches OEM resistance and thread pitch."
                    ),
                    "image_search_query": "spark plug ignition",
                    "image_url": None,
                    "image_source": None,
                    "warning": "Do not pry against delicate platinum/iridium center electrodes when checking spark gap."
                },
                {
                    "step_number": 4,
                    "title": "Precision Installation & Harness Reconnection",
                    "instruction": (
                        "Thread the new component in by hand first to prevent cross-threading in aluminum threads, then torque to spec. "
                        "Apply a dab of dielectric grease to coil boots and click the wiring harness connector firmly into place."
                    ),
                    "image_search_query": "torque wrench socket",
                    "image_url": None,
                    "image_source": None,
                    "warning": None
                },
                {
                    "step_number": 5,
                    "title": "DTC Reset & Closed-Loop Telemetry Check",
                    "instruction": (
                        "Clear stored DTCs with the scan tool. Start the engine, monitor live misfire counters and fuel trims at idle, "
                        "and verify the Check Engine Light (MIL) remains off."
                    ),
                    "image_search_query": "electrical ignition diagnostic schematic",
                    "image_url": None,
                    "image_source": None,
                    "warning": None
                }
            ],
            "final_verification": [
                "Confirm zero misfire counts and stable idle RPM on scan tool live data.",
                "Verify Check Engine Light (MIL) remains extinguished after a road test.",
                "Ensure wiring harness is clipped away from hot exhaust components."
            ]
        }

    def _fuel_induction_guide(self, fault_name, fix_procedure="", system="Fuel System"):
        return {
            "repair_title": f"{fault_name} — Fuel Delivery & Air Induction Service",
            "predicted_fault": fault_name,
            "fault_explanation": (
                f"The fuel and air induction system meters atomized fuel and filtered air into the combustion chambers. "
                f"{fix_procedure}"
            ).strip(),
            "difficulty": "Intermediate",
            "estimated_time": "1.0 - 2.5 hours",
            "required_tools": [
                "Fuel rail pressure gauge kit",
                "Fuel line quick-disconnect tool set",
                "Socket wrench set & Torx drivers",
                "Throttle body / injector cleaner spray",
                "Class B fire extinguisher & nitrile gloves"
            ],
            "safety_precautions": [
                "RELIEVE FUEL SYSTEM PRESSURE before disconnecting any fuel line, filter, or injector rail.",
                "Work in a ventilated bay with zero ignition sources; keep a Class B fire extinguisher within reach.",
                "Disconnect the negative battery terminal before servicing fuel pumps or injectors."
            ],
            "repair_steps": [
                {
                    "step_number": 1,
                    "title": "Fuel Pressure Test & System Depressurization",
                    "instruction": (
                        "Check fuel rail pressure with a test gauge against factory spec (typically 3.0–4.5 bar for port injection). "
                        "Relieve residual fuel pressure by pulling the fuel pump relay and cranking the engine for 5 seconds."
                    ),
                    "image_search_query": "fuel injector nozzle",
                    "image_url": None,
                    "image_source": None,
                    "warning": "Wrap a shop towel around fuel fittings when disconnecting to catch residual spray."
                },
                {
                    "step_number": 2,
                    "title": "Air Ducting, Electrical & Fuel Line Disconnection",
                    "instruction": (
                        "Disconnect the negative battery cable. Remove intake air ducting and release quick-connect fuel line fittings "
                        "and injector/actuator electrical harness connectors."
                    ),
                    "image_search_query": "fuel delivery rail schematic",
                    "image_url": None,
                    "image_source": None,
                    "warning": None
                },
                {
                    "step_number": 3,
                    "title": "Component Removal, Cleaning & Seal Replacement",
                    "instruction": (
                        f"{fix_procedure or f'Unbolt and remove the faulty {fault_name} assembly.'} "
                        "Always install new Viton fuel O-rings lubricated with a drop of clean engine oil (never reuse old fuel O-rings)."
                    ),
                    "image_search_query": "fuel injector nozzle",
                    "image_url": None,
                    "image_source": None,
                    "warning": "Damaged injector O-rings cause high-risk external fuel leaks onto the hot engine block."
                },
                {
                    "step_number": 4,
                    "title": "Reassembly, Torque & Harness Locking",
                    "instruction": (
                        "Seat the cleaned or replacement component squarely without pinching O-rings. Torque mounting bolts evenly "
                        "and snap quick-connect fuel locks and wiring plugs securely into place."
                    ),
                    "image_search_query": "torque wrench socket",
                    "image_url": None,
                    "image_source": None,
                    "warning": None
                },
                {
                    "step_number": 5,
                    "title": "Key-On Fuel Prime Leak Check & Idle Calibration",
                    "instruction": (
                        "Cycle ignition key ON for 3 seconds (without starting) 3 times to pressurize the fuel rail and inspect every fitting for leaks. "
                        "Start engine and perform throttle body / idle relearn if applicable."
                    ),
                    "image_search_query": "digital multimeter voltage test",
                    "image_url": None,
                    "image_source": None,
                    "warning": "Inspect fuel rail and filter joints with a work light immediately upon pressurizing."
                }
            ],
            "final_verification": [
                "Verify zero fuel odor or wetness around all fuel rail and line connections.",
                "Confirm crisp throttle response, smooth idle, and normal short-term fuel trims."
            ]
        }

    def _transmission_clutch_guide(self, fault_name, fix_procedure="", system="Transmission"):
        return {
            "repair_title": f"{fault_name} — Transmission & Drivetrain Service",
            "predicted_fault": fault_name,
            "fault_explanation": (
                f"The transmission and clutch assembly transfer engine torque to the drive wheels smoothly. "
                f"{fix_procedure}"
            ).strip(),
            "difficulty": "Advanced",
            "estimated_time": "2.5 - 5.5 hours",
            "required_tools": [
                "Transmission jack & rated vehicle lift / stands",
                "Clutch alignment arbor tool",
                "Socket, breaker bar & torque wrench set",
                "Fluid transfer pump & OEM transmission/gear oil",
                "Dial indicator & brake cleaner"
            ],
            "safety_precautions": [
                "Support the vehicle securely on a lift or 4 rated jack stands and support the engine block before unbolting the transaxle.",
                "Secure the gearbox to a dedicated transmission jack with safety chains before pulling it off dowel pins.",
                "Wear eye protection when working beneath drivetrain assemblies."
            ],
            "repair_steps": [
                {
                    "step_number": 1,
                    "title": "Linkage, Hydraulic & Fluid Diagnostic Check",
                    "instruction": (
                        f"Inspect transmission fluid level/condition, clutch pedal free-play, and shift cable/hydraulic slave cylinder operation. "
                        f"{fix_procedure.split('.')[0] + '.' if fix_procedure else ''}"
                    ),
                    "image_search_query": "transmission gearbox schematic",
                    "image_url": None,
                    "image_source": None,
                    "warning": None
                },
                {
                    "step_number": 2,
                    "title": "Driveshaft, Starter & Bellhousing Preparation",
                    "instruction": (
                        "Disconnect battery, drain gear oil if removing axle shafts, unbolt starter motor and shift linkages, "
                        "and support both the engine oil pan (with a padded jack) and the transmission housing."
                    ),
                    "image_search_query": "clutch disc automotive",
                    "image_url": None,
                    "image_source": None,
                    "warning": "Never allow the transmission weight to hang on the clutch disc input spline."
                },
                {
                    "step_number": 3,
                    "title": "Component Inspection & Servicing",
                    "instruction": (
                        f"{fix_procedure or f'Inspect and replace the worn {fault_name} components.'} "
                        "Check flywheel friction surface for heat spots or scoring, and inspect the release bearing and input shaft oil seal."
                    ),
                    "image_search_query": "clutch disc automotive",
                    "image_url": None,
                    "image_source": None,
                    "warning": None
                },
                {
                    "step_number": 4,
                    "title": "Precision Alignment & Star-Pattern Torque",
                    "instruction": (
                        "Center the clutch disc using a splined alignment tool and tighten pressure plate bolts gradually in a star pattern to OEM torque. "
                        "Mate the transmission squarely onto the engine block alignment dowels and torque bellhousing bolts."
                    ),
                    "image_search_query": "torque wrench socket",
                    "image_url": None,
                    "image_source": None,
                    "warning": "Draw the bellhousing flush by hand on the dowels — never pull a binding gearbox in with bolts."
                },
                {
                    "step_number": 5,
                    "title": "Fluid Refill, Hydraulic Bleed & Shift Verification",
                    "instruction": (
                        "Refill transmission with the exact OEM-grade GL-4/ATF/CVT fluid to the fill plug level. "
                        "Bleed hydraulic clutch slave cylinder if equipped and verify smooth gear engagement across all forward and reverse gears."
                    ),
                    "image_search_query": "transmission gearbox",
                    "image_url": None,
                    "image_source": None,
                    "warning": None
                }
            ],
            "final_verification": [
                "Verify smooth, crunch-free shifting into 1st and Reverse with engine idling.",
                "Confirm clutch engagement point is progressive with zero judder or slip under load.",
                "Inspect axle seals and drain/fill plugs for zero fluid leaks."
            ]
        }

    def _suspension_bearing_guide(self, fault_name, fix_procedure="", system="Suspension"):
        return {
            "repair_title": f"{fault_name} — Suspension & Chassis Overhaul",
            "predicted_fault": fault_name,
            "fault_explanation": (
                f"Suspension struts, control arm bushings, ball joints, and wheel bearings maintain tire contact and steering stability. "
                f"{fix_procedure}"
            ).strip(),
            "difficulty": "Intermediate",
            "estimated_time": "1.5 - 3.0 hours",
            "required_tools": [
                "Socket wrench set, breaker bar & torque wrench",
                "Cage-type coil spring compressor (for strut service)",
                "Ball joint separator / bearing press kit",
                "Jack, rated jack stands & wheel chocks",
                "Pry bar & penetrating oil"
            ],
            "safety_precautions": [
                "Support vehicle on rated jack stands and chock rear wheels before removing suspension links.",
                "HIGH ENERGY HAZARD: Use a professional cage-style spring compressor before loosening a top strut shaft nut.",
                "Always torque rubber suspension control arm bushings at normal ride height (curb weight loaded) to prevent premature tearing."
            ],
            "repair_steps": [
                {
                    "step_number": 1,
                    "title": "Play Inspection & Suspension Load Check",
                    "instruction": (
                        "Raise vehicle safely on jack stands. Check for 12-and-6 o'clock and 3-and-9 o'clock wheel play, "
                        "oil leakage on shock bodies, cracked rubber bushings, or ball joint axial looseness."
                    ),
                    "image_search_query": "suspension shock strut schematic",
                    "image_url": None,
                    "image_source": None,
                    "warning": None
                },
                {
                    "step_number": 2,
                    "title": "Brake Hose, ABS Wire & Fastener Unbolting",
                    "instruction": (
                        "Remove the wheel. Unclip the ABS wheel speed sensor wire and brake hose bracket from the strut/knuckle so lines are never stretched. "
                        "Apply penetrating oil and remove the mounting bolts."
                    ),
                    "image_search_query": "suspension shock strut schematic",
                    "image_url": None,
                    "image_source": None,
                    "warning": "Support the steering knuckle with a jack stand so the CV axle joint does not over-extend."
                },
                {
                    "step_number": 3,
                    "title": "Component Extraction & Replacement",
                    "instruction": (
                        f"{fix_procedure or f'Remove the worn {fault_name} component and install the new OEM replacement assembly.'} "
                        "Inspect mating tapers, top strut mount bearings, and dust boots for damage."
                    ),
                    "image_search_query": "suspension shock strut schematic",
                    "image_url": None,
                    "image_source": None,
                    "warning": "Never strike a wheel bearing inner race directly when pressing into the hub."
                },
                {
                    "step_number": 4,
                    "title": "Ride-Height Preloading & Fastener Torque",
                    "instruction": (
                        "Install new self-locking nuts/bolts. Jack under the lower control arm to raise the suspension to normal curb ride height "
                        "before final-torquing bushing bolts with a torque wrench."
                    ),
                    "image_search_query": "torque wrench socket",
                    "image_url": None,
                    "image_source": None,
                    "warning": "Torquing rubber bushings at full droop twists and tears the rubber once lowered."
                },
                {
                    "step_number": 5,
                    "title": "Wheel Reinstallation & Four-Wheel Alignment",
                    "instruction": (
                        "Reattach ABS sensor leads, reinstall wheels, and torque lug nuts. "
                        "Perform a 4-wheel computerized alignment (camber, caster, and toe) to prevent uneven tire wear."
                    ),
                    "image_search_query": "steering rack pinion",
                    "image_url": None,
                    "image_source": None,
                    "warning": None
                }
            ],
            "final_verification": [
                "Confirm zero clunking, humming, or knocking over road bumps.",
                "Verify steering wheel is centered and vehicle tracks straight.",
                "Complete 4-wheel alignment verification sheet."
            ]
        }

    def _steering_guide(self, fault_name, fix_procedure="", system="Steering"):
        return {
            "repair_title": f"{fault_name} — Steering Gear & Linkage Service",
            "predicted_fault": fault_name,
            "fault_explanation": (
                f"The steering rack, tie rods, and power assist unit provide precise directional control. "
                f"{fix_procedure}"
            ).strip(),
            "difficulty": "Intermediate",
            "estimated_time": "1.5 - 3.0 hours",
            "required_tools": [
                "Socket wrench set & open-end jam nut wrenches",
                "Tie rod end puller",
                "Torque wrench & new cotter pins",
                "Steering wheel holder & alignment gauge"
            ],
            "safety_precautions": [
                "Lock the steering wheel straight ahead before disconnecting the steering column shaft to protect the airbag clockspring.",
                "Always install a new cotter pin on castle nuts and never back off a nut to align the cotter pin slot."
            ],
            "repair_steps": [
                {
                    "step_number": 1,
                    "title": "Steering Linkage Play & Hydraulic/EPS Inspection",
                    "instruction": (
                        "With an assistant rocking the steering wheel, inspect inner and outer tie rod ends, rack boots, "
                        "and power steering fluid lines or EPS motor couplers for play or leaks."
                    ),
                    "image_search_query": "steering rack pinion",
                    "image_url": None,
                    "image_source": None,
                    "warning": None
                },
                {
                    "step_number": 2,
                    "title": "Reference Marking & Disassembly",
                    "instruction": (
                        "Mark the thread position on tie rod shafts and count the exact number of turns during removal to preserve baseline toe alignment. "
                        f"{fix_procedure or ''}"
                    ),
                    "image_search_query": "steering rack pinion",
                    "image_url": None,
                    "image_source": None,
                    "warning": "Do not rotate the steering wheel while the intermediate shaft is disconnected."
                },
                {
                    "step_number": 3,
                    "title": "Component Replacement & Boot Sealing",
                    "instruction": (
                        f"Install the replacement {fault_name} assembly, secure bellows boots with new clamps, "
                        "and torque ball stud nuts and mounting bolts to factory specification."
                    ),
                    "image_search_query": "torque wrench socket",
                    "image_url": None,
                    "image_source": None,
                    "warning": None
                },
                {
                    "step_number": 4,
                    "title": "System Bleed / EPS Steering Angle Calibration",
                    "instruction": (
                        "For hydraulic systems: fill reservoir and turn wheel lock-to-lock 10 times with wheels off the ground to purge air. "
                        "For Electric Power Steering (EPS): perform Steering Angle Sensor (SAS) zero-point calibration via scan tool."
                    ),
                    "image_search_query": "electrical ignition diagnostic schematic",
                    "image_url": None,
                    "image_source": None,
                    "warning": None
                }
            ],
            "final_verification": [
                "Confirm smooth lock-to-lock steering assist with zero binding or groaning.",
                "Verify jam nuts and cotter pins are locked securely.",
                "Perform precision front-end toe alignment."
            ]
        }

    def _exhaust_emissions_guide(self, fault_name, fix_procedure="", system="Exhaust"):
        return {
            "repair_title": f"{fault_name} — Exhaust & Aftertreatment Service",
            "predicted_fault": fault_name,
            "fault_explanation": (
                f"The exhaust manifold, catalytic converter, DPF, and muffler route hot combustion gases and reduce emissions. "
                f"{fix_procedure}"
            ).strip(),
            "difficulty": "Intermediate",
            "estimated_time": "1.0 - 2.5 hours",
            "required_tools": [
                "Socket set, breaker bar & oxygen sensor socket (22mm)",
                "Penetrating oil & induction bolt heater",
                "Exhaust hanger removal pliers",
                "OBD-II scan tool & backpressure gauge",
                "New exhaust flange gaskets & copper locknuts"
            ],
            "safety_precautions": [
                "Allow the exhaust system and catalytic converter to cool completely (operating temps exceed 600°C).",
                "Never run the engine in an enclosed bay without an exhaust extraction hose attached.",
                "Wear safety goggles when working under rusted exhaust flanges."
            ],
            "repair_steps": [
                {
                    "step_number": 1,
                    "title": "Exhaust Backpressure, Leak & OBD Telemetry Check",
                    "instruction": (
                        f"Check upstream and downstream O2 sensor waveforms or DPF differential pressure on the scan tool. "
                        "Inspect manifold gaskets, flex pipes, and converter welds for black soot trails indicating leaks."
                    ),
                    "image_search_query": "catalytic converter exhaust",
                    "image_url": None,
                    "image_source": None,
                    "warning": None
                },
                {
                    "step_number": 2,
                    "title": "Penetrating Oil Soak & Sensor Unplugging",
                    "instruction": (
                        "Soak exhaust flange studs and O2 sensor bungs with penetrating oil. Unplug O2/exhaust temperature sensor harnesses "
                        "before unbolting flanges."
                    ),
                    "image_search_query": "catalytic converter exhaust",
                    "image_url": None,
                    "image_source": None,
                    "warning": "Do not twist O2 sensor pigtails when unthreading the sensor body."
                },
                {
                    "step_number": 3,
                    "title": "Component Removal, Gasket Prep & Installation",
                    "instruction": (
                        f"{fix_procedure or f'Unbolt the faulty {fault_name} section and support pipe weight on rubber hangers.'} "
                        "Clean flange mating surfaces, install new crush gaskets, and torque new copper exhaust nuts evenly."
                    ),
                    "image_search_query": "torque wrench socket",
                    "image_url": None,
                    "image_source": None,
                    "warning": None
                },
                {
                    "step_number": 4,
                    "title": "Leak Verification & Emissions Monitor Reset",
                    "instruction": (
                        "Start engine and inspect all exhaust joints for acoustic leaks. Clear DTCs (such as P0420/P2002) "
                        "and verify normal exhaust flow and catalyst monitor readiness."
                    ),
                    "image_search_query": "electrical ignition diagnostic schematic",
                    "image_url": None,
                    "image_source": None,
                    "warning": None
                }
            ],
            "final_verification": [
                "Confirm zero exhaust gas leaks at manifold and converter flanges.",
                "Verify exhaust pipe clearance against heat shields and chassis underbody.",
                "Confirm normal O2 sensor switching and DPF differential pressure."
            ]
        }

    def _ac_hvac_guide(self, fault_name, fix_procedure="", system="AC/HVAC"):
        return {
            "repair_title": f"{fault_name} — Automotive HVAC & Refrigerant Service",
            "predicted_fault": fault_name,
            "fault_explanation": (
                f"The automotive AC system circulates pressurized refrigerant (R134a / R1234yf) through the compressor, condenser, TXV, and evaporator. "
                f"{fix_procedure}"
            ).strip(),
            "difficulty": "Intermediate",
            "estimated_time": "1.5 - 3.0 hours",
            "required_tools": [
                "AC manifold gauge set & certified recovery/recharge station",
                "UV refrigerant leak detector & electronic sniffer",
                "Vacuum pump & PAG refrigerant oil",
                "Digital multimeter & vent thermometer"
            ],
            "safety_precautions": [
                "NEVER vent refrigerant to the atmosphere — always recover refrigerant with a certified recovery machine before opening AC lines.",
                "Wear safety goggles and insulated gloves — liquid refrigerant causes instant frostbite on skin or eyes.",
                "Keep PAG oil sealed from moisture and never mix incompatible refrigerant oils."
            ],
            "repair_steps": [
                {
                    "step_number": 1,
                    "title": "Manifold Pressure, UV Leak & Electrical Clutch Check",
                    "instruction": (
                        "Connect high/low manifold gauges and record static and running pressures. Inspect condenser fins, line crimps, "
                        "and compressor shaft seal with a UV light, and verify 12V supply to the compressor clutch/blower circuit."
                    ),
                    "image_search_query": "ac hvac compressor schematic",
                    "image_url": None,
                    "image_source": None,
                    "warning": None
                },
                {
                    "step_number": 2,
                    "title": "Refrigerant Recovery & Component Servicing",
                    "instruction": (
                        f"{fix_procedure or f'Recover refrigerant completely using an AC recovery station, then unbolt and service the {fault_name} component.'} "
                        "Install new HNBR (green) AC O-rings lubricated with fresh PAG oil on all opened joints."
                    ),
                    "image_search_query": "ac hvac compressor schematic",
                    "image_url": None,
                    "image_source": None,
                    "warning": "Cap open AC lines immediately to prevent atmospheric moisture from saturating the receiver-dryer."
                },
                {
                    "step_number": 3,
                    "title": "Deep Vacuum Evacuation & Decay Test",
                    "instruction": (
                        "Pull a deep vacuum (29 inHg / 500 microns) for at least 30 minutes to boil off moisture. "
                        "Close manifold valves and verify vacuum holds steady for 10 minutes with zero pressure rise."
                    ),
                    "image_search_query": "digital multimeter voltage test",
                    "image_url": None,
                    "image_source": None,
                    "warning": None
                },
                {
                    "step_number": 4,
                    "title": "Measured Weight Recharge & Vent Temp Verification",
                    "instruction": (
                        "Recharge the exact gram weight of refrigerant and PAG oil specified on the under-hood AC decal. "
                        "Run AC on MAX COLD and verify center cabin vent temperature drops to 4°C–8°C."
                    ),
                    "image_search_query": "ac hvac compressor schematic",
                    "image_url": None,
                    "image_source": None,
                    "warning": None
                }
            ],
            "final_verification": [
                "Verify high-side and low-side manifold pressures are within OEM ambient chart ranges.",
                "Confirm condenser fan engages when AC compressor clutch activates.",
                "Confirm center cabin vent discharge temperature reaches 4°C–8°C."
            ]
        }

    def _dynamic_procedure_guide(self, fault_name, fix_procedure="", system="", symptoms="", findings=""):
        sys_label = system or "Automotive System"
        proc_sentences = [s.strip() for s in re.split(r'[.\n;]', fix_procedure or "") if len(s.strip()) > 8]

        step1_desc = proc_sentences[0] + "." if len(proc_sentences) >= 1 else f"Inspect and verify the predicted fault ({fault_name}) using diagnostic tests."
        step2_desc = proc_sentences[1] + "." if len(proc_sentences) >= 2 else f"Isolate power, remove covers, and access the {fault_name} assembly."
        step3_desc = proc_sentences[2] + "." if len(proc_sentences) >= 3 else f"Service or replace the faulty {fault_name} component using OEM specifications."

        return {
            "repair_title": f"{fault_name} — Diagnostic & Repair Procedure",
            "predicted_fault": fault_name,
            "fault_explanation": (
                f"Predicted fault: {fault_name} ({sys_label}). "
                f"{fix_procedure or 'Requires systematic inspection and component servicing.'}"
            ),
            "difficulty": "Intermediate",
            "estimated_time": "1.0 - 2.5 hours",
            "required_tools": [
                "Socket and box wrench set",
                "Digital multimeter",
                "Torque wrench",
                "Inspection work light",
                "Safety gloves and eye protection"
            ],
            "safety_precautions": [
                "Disconnect negative battery terminal before working on electrical or motorized actuators.",
                "Support vehicle on rated jack stands if under-vehicle access is required.",
                f"Note: {fault_name} is a PREDICTED fault — confirm physically before replacing assemblies."
            ],
            "repair_steps": [
                {
                    "step_number": 1,
                    "title": f"Diagnostic Verification: {fault_name}",
                    "instruction": f"{step1_desc} Verify connector integrity, mechanical free-play, and power/ground feeds.",
                    "image_search_query": f"{fault_name} {sys_label} schematic",
                    "image_url": None,
                    "image_source": None,
                    "warning": "Confirm the predicted fault before unbolting major assemblies."
                },
                {
                    "step_number": 2,
                    "title": f"Component Access & Disassembly",
                    "instruction": f"{step2_desc} Label fasteners and electrical plugs prior to removal.",
                    "image_search_query": f"{fault_name} {sys_label} assembly",
                    "image_url": None,
                    "image_source": None,
                    "warning": None
                },
                {
                    "step_number": 3,
                    "title": f"Component Service / Replacement & Torque",
                    "instruction": f"{step3_desc} Compare replacement part dimensions against the original and torque fasteners to OEM spec.",
                    "image_search_query": "torque wrench socket",
                    "image_url": None,
                    "image_source": None,
                    "warning": "Tighten fasteners strictly to OEM service manual torque specifications."
                },
                {
                    "step_number": 4,
                    "title": "Post-Repair Calibration & Operational Test",
                    "instruction": f"Reconnect battery and harnesses, operate the {sys_label} through a full cycle, and verify {fault_name} symptoms are eliminated.",
                    "image_search_query": "digital multimeter voltage test",
                    "image_url": None,
                    "image_source": None,
                    "warning": None
                }
            ],
            "final_verification": [
                f"Confirm {fault_name} symptoms are completely resolved under normal operating load.",
                "Verify all fasteners, clips, and electrical connectors are locked securely.",
                "Clear any stored diagnostic trouble codes (DTCs) and road-test vehicle."
            ]
        }
