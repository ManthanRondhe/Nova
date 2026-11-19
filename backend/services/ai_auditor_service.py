"""
Nova AI - Independent AI Diagnostic Auditor & Anti-Overreplacement Arbiter
Autonomous Quality Assurance & Diagnostic Integrity System.
Scrutinizes diagnostic proposals, detects unnecessary replacements,
eliminates predatory upsells, and issues autonomous green-flags.
"""
import os
import re
import json
import uuid
import hmac
import hashlib
from datetime import datetime, timezone
import pandas as pd

from config import config


class AuditVerdict:
    GREEN_FLAG_APPROVED = "GREEN_FLAG_APPROVED"
    GREEN_FLAG_OPTIMIZED = "GREEN_FLAG_OPTIMIZED"
    FLAGGED_OVERREPLACEMENT = "FLAGGED_OVERREPLACEMENT"
    REJECTED = "REJECTED"


class PartNecessityStatus:
    ESSENTIAL = "ESSENTIAL"
    PREVENTATIVE_VALID = "PREVENTATIVE_VALID"
    QUESTIONABLE = "QUESTIONABLE"
    UNNECESSARY_OVERREPLACEMENT = "UNNECESSARY_OVERREPLACEMENT"
    REDUNDANT = "REDUNDANT"


class AIAuditorService:
    """
    Independent AI Automotive Diagnostic Arbiter.
    Operates isolated from the primary diagnosis engine with its own
    automotive component causal graph, anti-overreplacement rules,
    and rigorous engineering evaluation heuristics.
    """

    # Subsystem taxonomy
    SUBSYSTEMS = [
        "Engine", "Transmission", "Brakes", "Electrical", "Cooling",
        "Fuel", "Suspension", "Steering", "Exhaust", "AC"
    ]

    # Well-known over-replacement patterns and minimum targeted fix pairings
    # maps: (symptom/fault pattern keywords) -> {
    #    "allowed_essential": [...],
    #    "preventative_valid": [...],
    #    "overreplacement_suspects": { part_substring: reason },
    #    "minimum_fix_procedure": "..."
    # }
    CAUSAL_RULES = {
        "alternator": {
            "keywords": ["battery light", "charging", "alternator", "dim light", "battery drain"],
            "allowed_essential": ["alternator", "drive belt", "serpentine belt", "voltage regulator", "battery cable"],
            "preventative_valid": ["battery", "belt tensioner"],
            "overreplacement_suspects": {
                "starter motor": "Starter motor operates on separate starting circuit; replacing starter during alternator fault is unnecessary upsell.",
                "fuel pump": "Fuel pump is entirely unlinked to charging system symptoms.",
                "spark plug": "Ignition consumables do not resolve alternator charging issues.",
                "ac compressor": "Unrelated auxiliary system replacement."
            },
            "minimum_fix_procedure": "Perform alternator load test with carbon pile & multimeter. Verify 13.8V-14.4V charging voltage, test belt tension, and inspect ground wiring before condemning assembly."
        },
        "starter": {
            "keywords": ["no crank", "starter", "clicking noise", "won't start", "engine does not turn"],
            "allowed_essential": ["starter motor", "starter relay", "ignition switch", "neutral safety switch", "battery"],
            "preventative_valid": ["battery terminal", "ground strap"],
            "overreplacement_suspects": {
                "alternator": "Vehicle fails to crank; replacing alternator when vehicle does not even start is premature and unnecessary.",
                "fuel pump": "Cranking failure is electrical/mechanical starter issue; fuel pump does not influence starter motor engagement.",
                "timing chain": "Severe overhaul without confirming starter motor relay or solenoid voltage drops is extreme overreplacement.",
                "radiator": "Unrelated cooling system part."
            },
            "minimum_fix_procedure": "Perform 12V voltage drop test across starter B+ terminal and starter relay. Check for solenoid click and battery CCA test before replacing starter motor assembly."
        },
        "brakes": {
            "keywords": ["brake squeal", "grinding brake", "soft pedal", "spongy brake", "brake pad", "stopping distance"],
            "allowed_essential": ["brake pad", "brake rotor", "brake disc", "brake shoe", "brake fluid"],
            "preventative_valid": ["brake caliper pin", "hardware kit", "caliper slide pin lubricant"],
            "overreplacement_suspects": {
                "abs module": "Brake squeal/wear is mechanical friction wear; replacing ABS electronic control unit without active ABS CAN-bus error is predatory.",
                "brake booster": "Friction pad wear does not warrant vacuum brake booster replacement unless diaphragm leak is verified.",
                "master cylinder": "Hydraulic master cylinder replacement is unjustified for routine pad squeal or normal pad thinning.",
                "suspension strut": "Cross-system upsell unrelated to brake friction service."
            },
            "minimum_fix_procedure": "Measure pad lining thickness (>3mm specification) and rotor lateral runout with dial indicator. Replace pads and resurface/replace rotors only if below minimum stamped thickness."
        },
        "misfire": {
            "keywords": ["misfire", "rough idle", "p0300", "p0301", "p0302", "p0303", "p0304", "jerking", "engine shake"],
            "allowed_essential": ["spark plug", "ignition coil", "fuel injector", "spark plug wire"],
            "preventative_valid": ["valve cover gasket", "fuel filter", "pcv valve"],
            "overreplacement_suspects": {
                "ecu": "Engine control module replacement for basic cylinder misfire is extreme parts-cannon swap. Must perform primary/secondary ignition sweep first.",
                "catalytic converter": "Prematurely replacing catalytic converter prior to eliminating raw fuel misfire cause is wasteful; converter will foul again if misfire persists.",
                "cylinder head": "Full cylinder head replacement without compression or leak-down test below 100 PSI is predatory over-service.",
                "transmission assembly": "Misfire hesitation under load is engine ignition/combustion, not transmission gear failure."
            },
            "minimum_fix_procedure": "Read live OBD-II misfire counts, perform cylinder power balance test, inspect spark plug gap, and swap ignition coil to adjacent cylinder to observe DTC migration."
        },
        "overheating": {
            "keywords": ["overheating", "temperature gauge", "coolant leak", "steam from hood", "radiator"],
            "allowed_essential": ["thermostat", "radiator", "water pump", "coolant hose", "coolant", "radiator cap", "cooling fan"],
            "preventative_valid": ["thermostat housing", "expansion tank cap"],
            "overreplacement_suspects": {
                "engine overhaul": "Replacing whole engine or short block for a stuck thermostat or hose split without verified cylinder head warp or crack is severe overreplacement.",
                "starter motor": "Electrical starting components have zero causal relation to coolant temperature regulation.",
                "steering rack": "Hydraulic or electronic power steering is completely unassociated with engine cooling.",
                "catalytic converter": "Exhaust catalyst replacement is unrelated to cooling loop fluid circulation."
            },
            "minimum_fix_procedure": "Perform cooling system pressure test at 15 PSI to locate external leaks. Test thermostat opening in heated water bath, verify electric fan PWM trigger, and test for combustion gas in coolant (block test)."
        },
        "fuel_system": {
            "keywords": ["fuel pump", "hesitation", "stalling", "poor fuel economy", "long crank", "fuel smell"],
            "allowed_essential": ["fuel pump", "fuel filter", "fuel pressure regulator", "fuel rail pressure sensor", "injector"],
            "preventative_valid": ["fuel tank lock ring", "fuel filter o-ring"],
            "overreplacement_suspects": {
                "fuel tank": "Replacing the complete fuel tank for a pump or sender fault is excessive unless tank has puncture or severe inner corrosion.",
                "throttle body": "Replacing electronic throttle body for fuel pressure drop is unscientific component swapping.",
                "alternator": "Alternator replacement for fuel delivery symptoms is an unrelated upsell.",
                "exhaust muffler": "Exhaust rear silencer has no direct relation to fuel pressure supply."
            },
            "minimum_fix_procedure": "Connect manual fuel pressure gauge to Schrader test valve; compare deadhead and running fuel pressure against OEM specification (typically 45-60 PSI). Check fuel pump relay voltage."
        },
        "suspension": {
            "keywords": ["knocking over bumps", "clunk noise", "suspension", "wheel wobble", "strut noise"],
            "allowed_essential": ["sway bar bush", "sway bar link", "strut mount", "shock absorber", "ball joint", "tie rod"],
            "preventative_valid": ["strut boot", "bump stop", "wheel alignment"],
            "overreplacement_suspects": {
                "steering column assembly": "Complete steering column replacement for suspension clunks over bumps is an egregious unnecessary swap.",
                "brake caliper": "Brake hydraulic calipers do not cause chassis thumps over road irregularities.",
                "catalytic converter": "Exhaust emission equipment is unlinked to chassis suspension articulation."
            },
            "minimum_fix_procedure": "Place vehicle on two-post lift; apply pry bar to stabilizer bushings, lower control arm ball joints, and tie-rod ends to measure radial and axial play against OEM tolerance (<1.5mm)."
        },
        "ac": {
            "keywords": ["ac not cooling", "warm air from vents", "ac blower", "compressor clutch"],
            "allowed_essential": ["ac compressor", "ac condenser", "expansion valve", "refrigerant r134a", "ac pressure switch", "blower motor"],
            "preventative_valid": ["ac o-rings", "cabin air filter", "receiver drier"],
            "overreplacement_suspects": {
                "radiator": "Replacing engine cooling radiator when only AC condenser or O-ring is leaking is unnecessary cross-system over-replacement.",
                "alternator": "Charging system swap for AC refrigerant loss is completely ungrounded.",
                "head gasket": "Engine head gasket replacement for cabin HVAC warm air is an unacceptable, predatory upsell."
            },
            "minimum_fix_procedure": "Attach HVAC manifold gauges; check high and low side static and running pressures. Conduct UV dye or electronic halogen sniffer leak detection around compressor seal and service ports before replacing compressor."
        },
        "engine_mechanical": {
            "keywords": ["knocking", "rod bearing", "piston", "cylinder", "oil pan", "crankshaft"],
            "allowed_essential": ["rod bearing", "connecting rod", "bearing set", "crankshaft", "piston ring", "head gasket"],
            "preventative_valid": ["oil pan gasket", "engine oil", "oil filter", "cylinder head bolt", "seal"],
            "overreplacement_suspects": {
                "starter motor": "Starting circuit is independent from mechanical crankshaft bearing failure.",
                "alternator": "Charging system replacement is unlinked to internal engine bearing knock.",
                "ac compressor": "Auxiliary belt accessory has no relation to internal rod bearing clearance.",
                "steering rack": "Cross-system upsell unrelated to engine reciprocating assembly."
            },
            "minimum_fix_procedure": "Remove oil pan to inspect rod bearing journals with Plastigage. Measure journal ovality with micrometer (<0.025mm). Replace bearing shells and torque to OEM spec with new oil pan gasket."
        }
    }

    def __init__(self, data_dir=None):
        self.data_dir = data_dir or config.DATA_DIR
        self.parts_df = None
        self._load_parts_catalog()

    def _load_parts_catalog(self):
        """Loads spare parts catalog into memory for rapid pricing and categorization."""
        try:
            parts_path = os.path.join(self.data_dir, "spare_parts.csv")
            if os.path.exists(parts_path):
                self.parts_df = pd.read_csv(parts_path)
            else:
                self.parts_df = pd.DataFrame(columns=["part_id", "part_name", "category", "unit_price"])
        except Exception as e:
            print(f"[AIAuditor] Warning: could not load spare parts CSV: {e}")
            self.parts_df = pd.DataFrame(columns=["part_id", "part_name", "category", "unit_price"])

    def get_part_info(self, identifier):
        """Look up part metadata by ID or part name."""
        if self.parts_df is None or self.parts_df.empty:
            return None
        ident_str = str(identifier).strip()
        # By part_id
        match = self.parts_df[self.parts_df["part_id"].str.strip().str.upper() == ident_str.upper()]
        if not match.empty:
            return match.iloc[0].to_dict()
        # By part_name exact/fuzzy
        match = self.parts_df[self.parts_df["part_name"].str.contains(re.escape(ident_str), case=False, na=False)]
        if not match.empty:
            return match.iloc[0].to_dict()
        return None

    # ─────────────────────────────────────────────────────────────
    # Core Anti-Overreplacement & Necessity Evaluation Engine
    # ─────────────────────────────────────────────────────────────
    def evaluate_diagnosis_and_parts(self, complaint, diagnosis, parts_input, vehicle=None, strictness="balanced"):
        """
        Deep-evaluates proposed diagnosis and all associated parts.
        Identifies unnecessary replacements, predatory upsells,
        assembly overkills, and computes savings.

        :param complaint: Customer symptom text
        :param diagnosis: Dict with fault_name, confidence, severity, etc.
        :param parts_input: Comma-separated part_ids, list of part IDs, or list of part dicts
        :param vehicle: Dict with make, model, year, reg
        :param strictness: 'strict' | 'balanced' | 'permissive'
        :return: Comprehensive audit dossier dictionary
        """
        strictness = (strictness or config.AI_AUDITOR_STRICTNESS).lower()
        if strictness not in ("strict", "balanced", "permissive"):
            strictness = "balanced"

        complaint_lower = (complaint or "").lower()
        diag_name = (diagnosis.get("fault_name") if diagnosis else "") or ""
        diag_lower = diag_name.lower()
        combined_context = f"{complaint_lower} {diag_lower}"

        # Resolve parts list into normalized objects
        raw_parts = self._normalize_parts_input(parts_input)

        # Detect primary causal rule or system domain
        matched_domain, rule_data = self._match_causal_domain(combined_context)

        parts_analysis = []
        original_parts_cost = 0
        audited_parts_cost = 0
        unnecessary_count = 0
        pruned_part_ids = []
        approved_parts = []

        seen_categories = set()
        assemblies_present = []

        for p in raw_parts:
            pid = p.get("part_id", "")
            pname = p.get("name") or p.get("part_name", "")
            price = int(p.get("unit_price", 0))
            category = p.get("category", "")
            original_parts_cost += price

            # Check if this part is an assembly
            is_assembly = any(kw in pname.lower() for kw in ["assembly", "complete", "unit", "system", "gearbox"])
            if is_assembly:
                assemblies_present.append((pid, pname, price))

            # Run Multi-Heuristic Necessity Evaluation
            score, status, rationale, suggested_alt = self._score_part_necessity(
                part_name=pname,
                part_id=pid,
                unit_price=price,
                category=category,
                combined_context=combined_context,
                matched_domain=matched_domain,
                rule_data=rule_data,
                strictness=strictness
            )

            # Check redundancy against other items (e.g. assembly + subcomponent)
            if not is_assembly and any(a[1].lower() in pname.lower() for a in assemblies_present):
                status = PartNecessityStatus.REDUNDANT
                score = min(score, 25)
                rationale += " [REDUNDANCY DETECTED: A higher-level complete assembly has also been included in this quotation]."

            # Check duplicate category over-concentration
            if category and category in seen_categories and score < 70:
                score -= 10
            if category:
                seen_categories.add(category)

            # Determine Auditor Action
            is_unnecessary = status in (PartNecessityStatus.UNNECESSARY_OVERREPLACEMENT, PartNecessityStatus.REDUNDANT)
            if is_unnecessary:
                unnecessary_count += 1
                action_taken = "PRUNED"
                pruned_part_ids.append(pid or pname)
            else:
                action_taken = "APPROVED"
                audited_parts_cost += price
                approved_parts.append(p)

            parts_analysis.append({
                "part_id": pid or "CUSTOM",
                "part_name": pname,
                "category": category or "Mechanical",
                "unit_price": price,
                "necessity_score": max(0, min(100, score)),
                "status": status,
                "action_taken": action_taken,
                "technical_rationale": rationale,
                "suggested_alternative": suggested_alt
            })

        # Calculate Financial & Risk Metrics
        customer_savings = max(0, original_parts_cost - audited_parts_cost)
        savings_pct = round((customer_savings / original_parts_cost * 100), 1) if original_parts_cost > 0 else 0.0

        total_parts_evaluated = len(raw_parts)
        overrep_ratio = (unnecessary_count / total_parts_evaluated) if total_parts_evaluated > 0 else 0

        # Calculate Overall Diagnostic Integrity Score (0-100)
        avg_necessity = sum(p["necessity_score"] for p in parts_analysis) / max(1, total_parts_evaluated)
        integrity_score = int(round(avg_necessity * (1.0 - (overrep_ratio * 0.3))))
        integrity_score = max(10, min(100, integrity_score))

        # Risk Classification
        if overrep_ratio == 0:
            overreplacement_risk = "LOW"
        elif overrep_ratio <= 0.35:
            overreplacement_risk = "MODERATE"
        elif overrep_ratio <= 0.65:
            overreplacement_risk = "HIGH"
        else:
            overreplacement_risk = "CRITICAL_OVERREPLACEMENT"

        # Determine Final Verdict
        if unnecessary_count == 0:
            verdict = AuditVerdict.GREEN_FLAG_APPROVED
            verdict_badge = "✅ GREEN FLAG (VERIFIED ACCURATE)"
            verdict_summary = "All proposed components and repair actions are verified as strictly necessary. Zero wasteful or unnecessary replacements detected."
            autonomous_green_flag = True
        elif unnecessary_count > 0 and overreplacement_risk in ("LOW", "MODERATE", "HIGH") and config.AI_AUDITOR_AUTO_PRUNE:
            verdict = AuditVerdict.GREEN_FLAG_OPTIMIZED
            verdict_badge = "⚡ GREEN FLAG (PRUNED & OPTIMIZED)"
            verdict_summary = f"Detected {unnecessary_count} unnecessary/redundant replacement part(s). The AI Auditor has autonomously pruned these parts from the estimate, saving the customer ₹{customer_savings:,} while preserving full mechanical reliability."
            autonomous_green_flag = True
        elif overreplacement_risk == "CRITICAL_OVERREPLACEMENT":
            verdict = AuditVerdict.FLAGGED_OVERREPLACEMENT
            verdict_badge = "⛔ FLAGGED: SEVERE OVER-REPLACEMENT"
            verdict_summary = f"High over-replacement alert! Over {int(overrep_ratio*100)}% of quoted parts are unnecessary or unrelated to the reported symptoms. Workshop re-diagnosis or supervisor justification required."
            autonomous_green_flag = False
        else:
            verdict = AuditVerdict.FLAGGED_OVERREPLACEMENT
            verdict_badge = "⚠️ FLAGGED FOR WORKSHOP REVIEW"
            verdict_summary = f"{unnecessary_count} part(s) flagged as questionable or unnecessary replacements. Requires manual confirmation before proceeding."
            autonomous_green_flag = False

        # Generate HMAC audit security seal
        audit_id = f"AUD-{uuid.uuid4().hex[:8].upper()}"
        seal_payload = f"{audit_id}:{verdict}:{customer_savings}:{config.APPROVAL_HMAC_SECRET}"
        audit_seal = hmac.new(config.APPROVAL_HMAC_SECRET.encode(), seal_payload.encode(), hashlib.sha256).hexdigest()[:20]

        # Engineering notes
        min_proc = rule_data.get("minimum_fix_procedure") if rule_data else "Follow standard OEM diagnostic verification protocols before component replacement."

        return {
            "audit_id": audit_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ai_auditor_version": f"{config.AI_AUDITOR_MODEL} (Isolated Diagnostic Integrity Core)",
            "strictness_mode": strictness,
            "verdict": verdict,
            "verdict_badge": verdict_badge,
            "verdict_summary": verdict_summary,
            "autonomous_green_flag_granted": autonomous_green_flag,
            "integrity_score": integrity_score,
            "overreplacement_risk": overreplacement_risk,
            "metrics": {
                "total_parts_evaluated": total_parts_evaluated,
                "essential_parts_count": total_parts_evaluated - unnecessary_count,
                "unnecessary_parts_blocked": unnecessary_count,
                "original_parts_cost": original_parts_cost,
                "audited_parts_cost": audited_parts_cost,
                "customer_savings": customer_savings,
                "savings_percentage": savings_pct
            },
            "parts_analysis": parts_analysis,
            "approved_parts": approved_parts,
            "pruned_part_ids": pruned_part_ids,
            "engineering_guidance": {
                "matched_domain": matched_domain or "General Mechanical",
                "recommended_diagnostic_procedure": min_proc,
                "frugality_advice": "Component replacement should always be preceded by direct measurement, signal probing, or physical tolerance gauge verification."
            },
            "audit_seal": audit_seal
        }

    def _normalize_parts_input(self, parts_input):
        """Converts diverse parts inputs (CSV string, list of IDs, list of dicts) into rich part dictionaries."""
        if not parts_input:
            return []
        resolved = []
        if isinstance(parts_input, str):
            pids = [p.strip() for p in parts_input.split(",") if p.strip()]
            for pid in pids:
                info = self.get_part_info(pid)
                if info:
                    resolved.append({
                        "part_id": info.get("part_id", pid),
                        "name": info.get("part_name", "Automotive Component"),
                        "category": info.get("category", "General"),
                        "unit_price": int(info.get("unit_price", 0))
                    })
                else:
                    resolved.append({
                        "part_id": pid,
                        "name": pid,
                        "category": "Unknown",
                        "unit_price": 0
                    })
        elif isinstance(parts_input, list):
            for item in parts_input:
                if isinstance(item, dict):
                    pid = item.get("part_id") or ""
                    pname = item.get("name") or item.get("part_name") or ""
                    price = item.get("unit_price") or item.get("price") or 0
                    category = item.get("category") or ""
                    if (not pname or price == 0) and pid:
                        catalog_info = self.get_part_info(pid)
                        if catalog_info:
                            pname = pname or catalog_info.get("part_name", "")
                            price = price or int(catalog_info.get("unit_price", 0))
                            category = category or catalog_info.get("category", "")
                    resolved.append({
                        "part_id": pid,
                        "name": pname or "Certified Replacement Component",
                        "category": category,
                        "unit_price": int(price)
                    })
                elif isinstance(item, str):
                    info = self.get_part_info(item)
                    if info:
                        resolved.append({
                            "part_id": info.get("part_id", item),
                            "name": info.get("part_name", item),
                            "category": info.get("category", "General"),
                            "unit_price": int(info.get("unit_price", 0))
                        })
                    else:
                        resolved.append({
                            "part_id": item,
                            "name": item,
                            "category": "General",
                            "unit_price": 0
                        })
        return resolved

    def _match_causal_domain(self, context_lower):
        """Matches context against automotive causal rules."""
        best_domain = None
        best_count = 0
        best_rule = None
        for domain, rule in self.CAUSAL_RULES.items():
            matches = sum(1 for kw in rule["keywords"] if kw in context_lower)
            if matches > best_count:
                best_count = matches
                best_domain = domain
                best_rule = rule
        if best_count > 0:
            return best_domain, best_rule
        return None, {}

    def _score_part_necessity(self, part_name, part_id, unit_price, category,
                              combined_context, matched_domain, rule_data, strictness):
        """
        Calculates necessity score (0-100), status, and engineering rationale for an individual part.
        """
        pname_lower = part_name.lower()
        score = 70
        status = PartNecessityStatus.QUESTIONABLE
        rationale = ""
        suggested_alt = ""

        threshold_unnecessary = 45 if strictness == "strict" else (35 if strictness == "balanced" else 25)

        # 1. Check against known over-replacement suspects for this failure mode
        if rule_data and "overreplacement_suspects" in rule_data:
            suspects = rule_data["overreplacement_suspects"]
            for suspect_kw, reason in suspects.items():
                if suspect_kw in pname_lower:
                    score = 15 if strictness == "strict" else 20
                    status = PartNecessityStatus.UNNECESSARY_OVERREPLACEMENT
                    rationale = f"UNNECESSARY REPLACEMENT FLAGGED: {reason}"
                    suggested_alt = f"Eliminate {part_name} replacement. Perform circuit continuity and signal trace tests instead."
                    return score, status, rationale, suggested_alt

        # 2. Check if part is explicitly listed as ESSENTIAL
        if rule_data and "allowed_essential" in rule_data:
            if any(kw in pname_lower for kw in rule_data["allowed_essential"]):
                score = 95
                status = PartNecessityStatus.ESSENTIAL
                rationale = "Direct mechanical remediation: Part directly targets and rectifies the verified root failure mode."
                suggested_alt = "Proceed with OEM/OES certified component."
                return score, status, rationale, suggested_alt

        # 3. Check if part is listed as PREVENTATIVE_VALID
        if rule_data and "preventative_valid" in rule_data:
            if any(kw in pname_lower for kw in rule_data["preventative_valid"]):
                score = 82
                status = PartNecessityStatus.PREVENTATIVE_VALID
                rationale = "Valid preventative maintenance: Part is accessible during primary repair labor and is a high-wear consumable."
                suggested_alt = "Recommended to replace concurrently to save future teardown labor."
                return score, status, rationale, suggested_alt

        # 4. Context keyword match: does part name or keywords appear in the complaint/diagnosis?
        words = [w for w in re.split(r"\W+", pname_lower) if len(w) > 3]
        matched_words = [w for w in words if w in combined_context]
        if len(matched_words) >= 2:
            score = 90
            status = PartNecessityStatus.ESSENTIAL
            rationale = f"Strong contextual match: Component '{part_name}' aligns with diagnostic complaint indicators."
            suggested_alt = "Proceed with replacement."
            return score, status, rationale, suggested_alt
        elif len(matched_words) == 1:
            score = 75
            status = PartNecessityStatus.PREVENTATIVE_VALID
            rationale = f"Partial symptom correlation: Component '{part_name}' relates to stated issue."
            suggested_alt = "Inspect component physical condition before installing."
            return score, status, rationale, suggested_alt

        # 5. Cross-System leakage detection:
        # If category belongs to an entirely different system than matched domain
        if matched_domain and category:
            sys_mismatch = False
            if matched_domain in ("alternator", "starter") and category in ("Suspension", "Exhaust", "Brakes"):
                sys_mismatch = True
            elif matched_domain == "brakes" and category in ("Electrical", "Cooling", "Fuel"):
                sys_mismatch = True
            elif matched_domain == "overheating" and category in ("Suspension", "Brakes", "Electrical"):
                sys_mismatch = True

            if sys_mismatch:
                score = 10
                status = PartNecessityStatus.UNNECESSARY_OVERREPLACEMENT
                rationale = f"CROSS-SYSTEM UNNECESSARY UPSELL: Part belongs to '{category}' subsystem, while active failure domain is '{matched_domain}'. No diagnostic link exists."
                suggested_alt = f"Remove {part_name} from quotation; it does not address the customer's reported issue."
                return score, status, rationale, suggested_alt

        # 6. Expensive assembly penalty without proven symptom need
        if any(term in pname_lower for term in ["assembly", "complete", "module", "system"]) and unit_price > 4000:
            score = 30
            status = PartNecessityStatus.UNNECESSARY_OVERREPLACEMENT
            rationale = f"HIGH-COST ASSEMBLY OVERKILL: Quoting complete '{part_name}' (₹{unit_price:,}) without bench-testing serviceable individual subcomponents constitutes premature assembly replacement."
            suggested_alt = f"Inspect and test individual subcomponents (gaskets, relays, brushes, O-rings) before full assembly replacement."
            return score, status, rationale, suggested_alt

        # Default classification based on score vs threshold
        if score < threshold_unnecessary:
            status = PartNecessityStatus.UNNECESSARY_OVERREPLACEMENT
            rationale = f"Low necessity index ({score}%): Insufficient diagnostic evidence linking '{part_name}' to reported problem."
            suggested_alt = "Omit part or obtain workshop physical diagnostic proof (photos/telemetry)."
        else:
            status = PartNecessityStatus.QUESTIONABLE
            rationale = f"Moderate necessity index ({score}%): Part may provide minor preventative value but is not critical to resolving core fault."
            suggested_alt = "Advise customer that this part is optional preventative service."

        return score, status, rationale, suggested_alt

    # ─────────────────────────────────────────────────────────────
    # Autonomous JobCard Audit & Green Flag Workflow Execution
    # ─────────────────────────────────────────────────────────────
    def audit_jobcard(self, jobcard, diagnosis=None, auto_greenflag=True, auto_prune=True):
        """
        Executes complete independent audit on a jobcard instance.
        - Checks for unnecessary replacement
        - Attaches certified audit report
        - Grants autonomous green flag if verified or optimized
        - Prunes unnecessary parts and recomputes quotation if auto_prune is enabled
        """
        complaint = jobcard.get("complaint", "")
        diag = diagnosis or {
            "fault_name": jobcard.get("diagnosis_fault", ""),
            "confidence": float(jobcard.get("diagnosis_confidence", 0.8)),
            "severity": jobcard.get("priority", "Medium")
        }
        parts_str = jobcard.get("required_parts", "")
        vehicle = {
            "make": jobcard.get("vehicle_make", ""),
            "model": jobcard.get("vehicle_model", ""),
            "year": jobcard.get("vehicle_year", ""),
            "reg": jobcard.get("vehicle_reg", "")
        }

        # Run AI Evaluation
        audit_result = self.evaluate_diagnosis_and_parts(
            complaint=complaint,
            diagnosis=diag,
            parts_input=parts_str,
            vehicle=vehicle,
            strictness=config.AI_AUDITOR_STRICTNESS
        )

        jobcard["ai_audit"] = audit_result

        # Autonomous Green Flag Application
        if auto_greenflag and audit_result["autonomous_green_flag_granted"]:
            # If parts were pruned, update jobcard required_parts with clean list
            if auto_prune and audit_result["verdict"] == AuditVerdict.GREEN_FLAG_OPTIMIZED:
                clean_pids = [p["part_id"] for p in audit_result["approved_parts"] if p.get("part_id")]
                jobcard["required_parts"] = ",".join(clean_pids)
                jobcard["unnecessary_parts_pruned"] = audit_result["pruned_part_ids"]
                jobcard["customer_savings"] = audit_result["metrics"]["customer_savings"]

            jobcard["ai_green_flag_at"] = datetime.now(timezone.utc).isoformat()
            jobcard["reviewed_by"] = f"AI_Sentinel_Arbiter:{config.AI_AUDITOR_MODEL}"
            jobcard["review_note"] = audit_result["verdict_summary"]

        return audit_result

    # ─────────────────────────────────────────────────────────────
    # Interactive AI Developer / Diagnostic Arbiter Assistant
    # ─────────────────────────────────────────────────────────────
    def chat_consultation(self, user_message, jobcard_context=None, history=None):
        """
        Conversational AI Assistant operating as an Ultra-Professional
        Principal Automotive Systems Architect & Diagnostic Arbiter.
        Provides pinpoint technical analysis, diagnostic trees,
        OBD-II logic, and explanations for why parts were deemed unnecessary.
        """
        user_msg = (user_message or "").strip()
        msg_lower = user_msg.lower()

        # Contextual metadata if a job card is being inspected
        jc_id = ""
        jc_summary = ""
        audit_info = None
        if jobcard_context:
            jc_id = jobcard_context.get("jobcard_id", "")
            veh = f"{jobcard_context.get('vehicle_make', '')} {jobcard_context.get('vehicle_model', '')}".strip()
            flt = jobcard_context.get("diagnosis_fault", "N/A")
            cmpl = jobcard_context.get("complaint", "N/A")
            jc_summary = f"[Active Context: Job {jc_id} | Vehicle: {veh} | Complaint: '{cmpl}' | Diagnosis: {flt}]"
            audit_info = jobcard_context.get("ai_audit")

        # Response routing based on inquiry type
        # 1. Why was a part flagged / pruned?
        if any(w in msg_lower for w in ["why", "reason", "unnecessary", "flagged", "pruned", "explain"]):
            return self._generate_audit_explanation_response(user_msg, audit_info, jc_summary)

        # 2. Minimum repair procedure / diagnostic tree
        elif any(w in msg_lower for w in ["procedure", "diagnostic tree", "test", "how to check", "steps", "multimeter", "oscilloscope"]):
            return self._generate_diagnostic_tree_response(user_msg, jc_summary)

        # 3. Simulate or evaluate custom parts quote
        elif any(w in msg_lower for w in ["evaluate", "audit", "check quote", "simulate", "parts:"]):
            return self._generate_custom_simulation_response(user_msg)

        # 4. General automotive architecture & integrity question
        else:
            return self._generate_general_architect_response(user_msg, jc_summary, audit_info)

    def _generate_audit_explanation_response(self, user_msg, audit_info, jc_summary):
        if not audit_info:
            return {
                "reply": (
                    f"### 🛡️ Sentinel AI Diagnostic Arbiter\n\n"
                    f"{jc_summary}\n\n"
                    f"**Diagnostic Evaluation Protocol:**\n"
                    f"Our anti-overreplacement algorithm applies strict causal verification between customer symptoms and proposed parts. "
                    f"Components are flagged as `UNNECESSARY_OVERREPLACEMENT` when:\n"
                    f"1. **Causal Disconnect:** The component belongs to an auxiliary circuit unaffected by the fault.\n"
                    f"2. **Premature Assembly Swap:** Quoting an entire assembly (e.g. Starter Motor, Alternator, Steering Rack) "
                    f"when standard diagnostic protocols call for testing relays, fuses, belts, or sensors first.\n"
                    f"3. **Predictive Redundancy:** Quoting individual replacement seals/bushings alongside a complete pre-assembled unit.\n\n"
                    f"*Select any job card from the queue or input a specific part name to see the exact engineering justification.*"
                ),
                "suggestions": [
                    "Why was the starter motor flagged?",
                    "What tests prove an alternator has failed?",
                    "Show minimal repair procedure"
                ]
            }

        parts_analysis = audit_info.get("parts_analysis", [])
        pruned = [p for p in parts_analysis if p["action_taken"] == "PRUNED"]
        approved = [p for p in parts_analysis if p["action_taken"] == "APPROVED"]

        reply_lines = [
            f"### 🛡️ Engineering Audit Dossier: {audit_info.get('audit_id')}",
            f"{jc_summary}\n",
            f"**Audit Verdict:** `{audit_info.get('verdict')}` | **Integrity Score:** `{audit_info.get('integrity_score')}/100`\n"
        ]

        if pruned:
            reply_lines.append("#### ✂️ Unnecessary Replacements Blocked:")
            for p in pruned:
                reply_lines.append(
                    f"- **{p['part_name']}** (₹{p['unit_price']:,}) — *Necessity: {p['necessity_score']}%*\n"
                    f"  - **Engineering Rationale:** {p['technical_rationale']}\n"
                    f"  - **Recommended Action:** {p['suggested_alternative']}\n"
                )
            savings = audit_info.get('metrics', {}).get('customer_savings', 0)
            reply_lines.append(f"**Net Customer Protection:** Blocked **₹{savings:,}** in unverified replacements.\n")
        else:
            reply_lines.append("#### ✅ Component Integrity Verified:")
            reply_lines.append("All quoted parts were verified as mathematically and mechanically essential. No predatory upsells detected.\n")

        reply_lines.append(
            f"**Recommended Diagnostic Telemetry:**\n"
            f"> {audit_info.get('engineering_guidance', {}).get('recommended_diagnostic_procedure')}"
        )

        return {
            "reply": "\n".join(reply_lines),
            "suggestions": [
                "How do I override this decision?",
                "Generate printable audit certificate",
                "Show wiring diagram test points"
            ]
        }

    def _generate_diagnostic_tree_response(self, user_msg, jc_summary):
        return {
            "reply": (
                f"### 🔬 Sentinel AI — Precision Diagnostic Protocol\n\n"
                f"{jc_summary}\n\n"
                f"To ensure zero unnecessary component replacements, perform the following ISO/SAE diagnostic tree:\n\n"
                f"```mermaid\ngraph TD\n"
                f"    A[Customer Symptom Reported] --> B[OBD-II DTC Freeze Frame Scan]\n"
                f"    B --> C{{Active DTC Present?}}\n"
                f"    C -->|Yes| D[Live PID Sensor Telemetry]\n"
                f"    C -->|No| E[Physical & Electrical Probing]\n"
                f"    D --> F[Component Voltage Drop Test <0.2V]\n"
                f"    E --> F\n"
                f"    F --> G{{Terminal/Wiring Defect?}}\n"
                f"    G -->|Yes| H[Clean Terminals / Repair Harness]\n"
                f"    G -->|No| I[Benchmark Waveform against OEM Spec]\n"
                f"    I --> J[Targeted Part Replacement Only]\n"
                f"```\n\n"
                f"**Verification Checkpoints:**\n"
                f"- **Circuit Ground Integrity:** Voltage drop from component ground stud to battery negative must be `< 0.10V` under load.\n"
                f"- **Power Feed Drop:** Voltage drop across control relay contacts must not exceed `0.20V`.\n"
                f"- **Mechanical Runout/Clearance:** Always confirm dial indicator or micrometer readings before condemning rotational assemblies."
            ),
            "suggestions": [
                "What oscilloscope waveform indicates a bad injector?",
                "How to test starter motor current draw?",
                "Check another job card"
            ]
        }

    def _generate_custom_simulation_response(self, user_msg):
        # Extract potential parts from user query
        parts_found = []
        if self.parts_df is not None:
            for idx, row in self.parts_df.iterrows():
                pname = str(row.get("part_name", ""))
                if pname.lower() in user_msg.lower() and len(pname) > 3:
                    parts_found.append({
                        "part_id": str(row.get("part_id", "")),
                        "part_name": pname,
                        "unit_price": int(row.get("unit_price", 0)),
                        "category": str(row.get("category", ""))
                    })
        if not parts_found:
            parts_found = [
                {"part_id": "SIM-01", "part_name": "Starter Motor Assembly", "unit_price": 3500, "category": "Engine"},
                {"part_id": "SIM-02", "part_name": "Alternator Assembly", "unit_price": 5000, "category": "Electrical"}
            ]

        # Run simulated evaluation
        sim_res = self.evaluate_diagnosis_and_parts(
            complaint=user_msg,
            diagnosis={"fault_name": "Simulated Workshop Quote", "confidence": 0.85},
            parts_input=parts_found
        )

        return {
            "reply": (
                f"### ⚡ Sentinel AI — What-If Audit Simulation\n\n"
                f"**Simulation Payload Evaluated:** `{user_msg}`\n\n"
                f"**Auditor Verdict:** `{sim_res['verdict_badge']}`\n"
                f"- **Total Components Evaluated:** `{sim_res['metrics']['total_parts_evaluated']}`\n"
                f"- **Unnecessary Replacements Caught:** `{sim_res['metrics']['unnecessary_parts_blocked']}`\n"
                f"- **Certified Customer Savings:** **₹{sim_res['metrics']['customer_savings']:,}** ({sim_res['metrics']['savings_percentage']}%)\n\n"
                f"| Component | Quoted Price | Necessity | Status | Verdict |\n"
                f"|:---|:---:|:---:|:---:|:---:|\n" +
                "\n".join([f"| {p['part_name']} | ₹{p['unit_price']:,} | {p['necessity_score']}% | {p['status']} | {p['action_taken']} |" for p in sim_res['parts_analysis']]) +
                f"\n\n**Arbiter Assessment:**\n> {sim_res['verdict_summary']}"
            ),
            "suggestions": [
                "Audit another custom parts list",
                "Apply strict frugality mode",
                "Export this simulation"
            ]
        }

    def _generate_general_architect_response(self, user_msg, jc_summary, audit_info):
        return {
            "reply": (
                f"### 🛡️ AutoMech Sentinel AI — Autonomous Diagnostic Arbiter\n\n"
                f"{jc_summary}\n\n"
                f"I am the isolated Quality Assurance & Anti-Overreplacement AI system powering the AutoMech platform. "
                f"My objective is to completely eliminate human review bottlenecks (the former Telegram 'man in the middle') "
                f"while providing flawless, mathematically validated protection against unnecessary parts replacement.\n\n"
                f"**Core Operational Capabilities:**\n"
                f"- **Autonomous Green-Flagging:** Validates job cards and green-flags work in sub-seconds.\n"
                f"- **Over-replacement Pruning:** Detects predatory upsells, assembly overkills, and strips redundant parts to save customers money.\n"
                f"- **Engineering Rationale:** Every decision is backed by SAE automotive engineering principles, voltage drop standards, and physical tolerances.\n\n"
                f"*How may I assist you with diagnostic verification, telemetry analysis, or quotation auditing today?*"
            ),
            "suggestions": [
                "Audit recent job cards for unnecessary parts",
                "Toggle Autonomous Green-Flag mode",
                "Simulate repair for engine misfire"
            ]
        }
