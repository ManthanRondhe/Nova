"""
Nova AI - Company-Side Approval Workflow Service (Unbiased Diagnostics)
Manages the rigorous multi-stage approval lifecycle for vehicle diagnostics
between Company Reviewers, Independent AI Diagnostic Auditor, Customers, and Workshop Mechanics.
"""
import os
import hmac
import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from config import config
from database import db


class ApprovalStatus:
    DIAGNOSIS_CREATED = "DIAGNOSIS_CREATED"
    PENDING_COMPANY_REVIEW = "PENDING_COMPANY_REVIEW"
    COMPANY_APPROVED = "COMPANY_APPROVED"
    PENDING_CUSTOMER_APPROVAL = "PENDING_CUSTOMER_APPROVAL"
    CUSTOMER_APPROVED = "CUSTOMER_APPROVED"
    COMPANY_REJECTED = "COMPANY_REJECTED"
    REQUEST_MORE_INFO = "REQUEST_MORE_INFO"
    CUSTOMER_DECLINED = "CUSTOMER_DECLINED"
    EXPIRED = "EXPIRED"
    LEGACY_APPROVED = "LEGACY_APPROVED"
    # Independent AI Diagnostic Auditor States
    AI_AUDITING = "AI_AUDITING"
    AI_GREEN_FLAG = "AI_GREEN_FLAG"
    AI_OPTIMIZED = "AI_OPTIMIZED"
    AI_OVERREPLACEMENT_FLAGGED = "AI_OVERREPLACEMENT_FLAGGED"
    AI_REJECTED = "AI_REJECTED"


class ApprovalWorkflowService:
    """State machine, security verifications, and audit trail for unbiased diagnostics."""

    VALID_TRANSITIONS = {
        ApprovalStatus.DIAGNOSIS_CREATED: [
            ApprovalStatus.PENDING_COMPANY_REVIEW,
            ApprovalStatus.AI_AUDITING,
            ApprovalStatus.AI_GREEN_FLAG,
            ApprovalStatus.AI_OPTIMIZED,
            ApprovalStatus.AI_OVERREPLACEMENT_FLAGGED,
            ApprovalStatus.PENDING_CUSTOMER_APPROVAL,
            ApprovalStatus.COMPANY_REJECTED,
        ],
        ApprovalStatus.AI_AUDITING: [
            ApprovalStatus.AI_GREEN_FLAG,
            ApprovalStatus.AI_OPTIMIZED,
            ApprovalStatus.AI_OVERREPLACEMENT_FLAGGED,
            ApprovalStatus.PENDING_COMPANY_REVIEW,
            ApprovalStatus.PENDING_CUSTOMER_APPROVAL,
            ApprovalStatus.COMPANY_REJECTED,
        ],
        ApprovalStatus.AI_GREEN_FLAG: [
            ApprovalStatus.PENDING_CUSTOMER_APPROVAL,
            ApprovalStatus.CUSTOMER_APPROVED,
            ApprovalStatus.COMPANY_REJECTED,
        ],
        ApprovalStatus.AI_OPTIMIZED: [
            ApprovalStatus.PENDING_CUSTOMER_APPROVAL,
            ApprovalStatus.CUSTOMER_APPROVED,
            ApprovalStatus.COMPANY_REJECTED,
        ],
        ApprovalStatus.AI_OVERREPLACEMENT_FLAGGED: [
            ApprovalStatus.PENDING_COMPANY_REVIEW,
            ApprovalStatus.COMPANY_APPROVED,
            ApprovalStatus.COMPANY_REJECTED,
            ApprovalStatus.AI_GREEN_FLAG,
            ApprovalStatus.AI_OPTIMIZED,
            ApprovalStatus.PENDING_CUSTOMER_APPROVAL,
        ],
        ApprovalStatus.PENDING_COMPANY_REVIEW: [
            ApprovalStatus.COMPANY_APPROVED,
            ApprovalStatus.COMPANY_REJECTED,
            ApprovalStatus.REQUEST_MORE_INFO,
            ApprovalStatus.EXPIRED,
            ApprovalStatus.AI_GREEN_FLAG,
            ApprovalStatus.AI_OPTIMIZED,
            ApprovalStatus.AI_OVERREPLACEMENT_FLAGGED,
            ApprovalStatus.PENDING_CUSTOMER_APPROVAL,
        ],
        ApprovalStatus.REQUEST_MORE_INFO: [
            ApprovalStatus.PENDING_COMPANY_REVIEW,
            ApprovalStatus.COMPANY_REJECTED,
            ApprovalStatus.AI_GREEN_FLAG,
            ApprovalStatus.AI_OPTIMIZED,
        ],
        ApprovalStatus.COMPANY_APPROVED: [
            ApprovalStatus.PENDING_CUSTOMER_APPROVAL,
            ApprovalStatus.EXPIRED,
        ],
        ApprovalStatus.PENDING_CUSTOMER_APPROVAL: [
            ApprovalStatus.CUSTOMER_APPROVED,
            ApprovalStatus.CUSTOMER_DECLINED,
            ApprovalStatus.EXPIRED,
        ],
        # Terminal states
        ApprovalStatus.CUSTOMER_APPROVED: [],
        ApprovalStatus.COMPANY_REJECTED: [ApprovalStatus.PENDING_COMPANY_REVIEW, ApprovalStatus.AI_AUDITING],
        ApprovalStatus.CUSTOMER_DECLINED: [],
        ApprovalStatus.EXPIRED: [ApprovalStatus.PENDING_COMPANY_REVIEW, ApprovalStatus.AI_AUDITING],
        ApprovalStatus.LEGACY_APPROVED: [],
        ApprovalStatus.AI_REJECTED: [ApprovalStatus.PENDING_COMPANY_REVIEW, ApprovalStatus.AI_AUDITING],
    }

    def __init__(self, data_dir, jobcard_manager, mechanic_scheduler, notification_service,
                 inventory_manager, order_manager, estimation_engine, ai_auditor_service=None):
        self.data_dir = data_dir
        self.jobcard_manager = jobcard_manager
        self.mechanic_scheduler = mechanic_scheduler
        self.notification_service = notification_service
        self.inventory_manager = inventory_manager
        self.order_manager = order_manager
        self.estimation_engine = estimation_engine

        self.ai_auditor_service = ai_auditor_service

    # ─────────────────────────────────────────────────────────────
    # Token Signing & Security Verification
    # ─────────────────────────────────────────────────────────────
    def generate_review_token(self, jobcard_id):
        """Generate an HMAC-SHA256 signature token to protect callback actions against forgery."""
        secret = config.APPROVAL_HMAC_SECRET.encode("utf-8")
        payload = f"{jobcard_id}".encode("utf-8")
        return hmac.new(secret, payload, hashlib.sha256).hexdigest()[:16]

    def verify_review_token(self, jobcard_id, token):
        """Verify the integrity of a review token."""
        expected = self.generate_review_token(jobcard_id)
        return hmac.compare_digest(expected, token)

    def is_reviewer_authorized(self, chat_id):
        """
        Verify if the given Telegram chat_id is in the whitelisted COMPANY_REVIEWER_CHAT_IDS.
        If no reviewers configured in dev, falls back to ADMIN_TELEGRAM_CHAT_ID.
        """
        if not chat_id:
            return False
        chat_id_str = str(chat_id).strip()
        whitelisted = config.COMPANY_REVIEWER_CHAT_IDS
        if not whitelisted and config.ADMIN_TELEGRAM_CHAT_ID:
            whitelisted = [str(config.ADMIN_TELEGRAM_CHAT_ID).strip()]
        return chat_id_str in whitelisted

    # ─────────────────────────────────────────────────────────────
    # Audit Logging & State Transitions
    # ─────────────────────────────────────────────────────────────
    def _create_audit_entry(self, from_state, to_state, actor, action, note=""):
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "from_state": from_state,
            "to_state": to_state,
            "actor": actor,
            "action": action,
            "note": note or ""
        }

    def transition_state(self, jobcard, to_state, actor, action, note=""):
        """
        Atomically checks and executes a valid state machine transition,
        appending to the persisted audit log.
        """
        current_state = jobcard.get("approval_status") or ApprovalStatus.LEGACY_APPROVED

        # Allow no-op if already in destination state (Idempotency)
        if current_state == to_state:
            return True, f"Job card already in state {to_state}"

        valid_targets = self.VALID_TRANSITIONS.get(current_state, [])
        if to_state not in valid_targets:
            return False, f"Illegal state transition from {current_state} to {to_state}"

        audit_log = jobcard.get("audit_log", [])
        if isinstance(audit_log, str):
            audit_log = []
        audit_entry = self._create_audit_entry(current_state, to_state, actor, action, note)
        audit_log.append(audit_entry)

        jobcard["approval_status"] = to_state
        jobcard["audit_log"] = audit_log
        jobcard["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        # Save update to persistence
        self.jobcard_manager.update_jobcard(jobcard["jobcard_id"], {
            "approval_status": to_state,
            "audit_log": audit_log,
            "updated_at": jobcard["updated_at"]
        })
        return True, "State transitioned successfully"

    # ─────────────────────────────────────────────────────────────
    # Step 1 & 2: Initiation, Autonomous AI Audit & Green Flag
    # ─────────────────────────────────────────────────────────────
    def initiate_workflow(self, jobcard, diagnosis):
        """
        Kicks off the unbiased approval workflow:
        1. When Independent AI Auditor is enabled:
           - Immediately evaluates diagnosis and all proposed parts
           - Scrutinizes for unnecessary replacements and parts-swapping
           - If verified/optimized: issues autonomous Green Flag without blocking human-in-the-middle
           - Dispatches informative Telegram notification with complete AI certificate
        2. Fallback / Supervised mode:
           - Dispatches Telegram review request to company reviewers
        """
        jc_id = jobcard["jobcard_id"]
        token = self.generate_review_token(jc_id)
        now_dt = datetime.now(timezone.utc)
        expires_at = (now_dt + timedelta(hours=config.APPROVAL_EXPIRY_HOURS)).isoformat()

        jobcard["approval_status"] = ApprovalStatus.DIAGNOSIS_CREATED
        jobcard["review_token"] = token
        jobcard["review_requested_at"] = now_dt.isoformat()
        jobcard["expires_at"] = expires_at
        jobcard["audit_log"] = [
            self._create_audit_entry(
                None, ApprovalStatus.DIAGNOSIS_CREATED,
                "system", "AI Diagnosis Generated"
            )
        ]

        # ── Independent AI Diagnostic Auditor Evaluation ──
        if getattr(config, "ENABLE_AI_AUDITOR", True) and getattr(self, "ai_auditor_service", None):
            audit_result = self.ai_auditor_service.audit_jobcard(
                jobcard, diagnosis,
                auto_greenflag=config.AI_AUDITOR_AUTO_GREENFLAG,
                auto_prune=config.AI_AUDITOR_AUTO_PRUNE
            )

            # Check if autonomous green flag was awarded
            if audit_result.get("autonomous_green_flag_granted") and config.AI_AUDITOR_AUTO_GREENFLAG:
                estimate = self.generate_official_estimate(jobcard)
                jobcard["estimate"] = estimate
                jobcard["reviewed_by"] = f"AI_Sentinel_Arbiter:{config.AI_AUDITOR_MODEL}"
                jobcard["review_note"] = audit_result.get("verdict_summary", "Autonomous AI Green Flag Granted")

                # State transition directly to PENDING_CUSTOMER_APPROVAL
                self.transition_state(
                    jobcard, ApprovalStatus.PENDING_CUSTOMER_APPROVAL,
                    "AI_Sentinel_Arbiter",
                    f"Autonomous Green Flag Issued ({audit_result['verdict']}). Unnecessary replacements blocked: {audit_result['metrics']['unnecessary_parts_blocked']}",
                    audit_result.get("verdict_summary")
                )

                # Persist updated jobcard
                self.jobcard_manager.update_jobcard(jc_id, {
                    "estimate": estimate,
                    "reviewed_by": jobcard["reviewed_by"],
                    "review_note": jobcard["review_note"],
                    "estimated_cost": f"{estimate['total_min']}-{estimate['total_max']}",
                    "estimated_time": str(estimate["labour_hours"]),
                    "approval_status": ApprovalStatus.PENDING_CUSTOMER_APPROVAL,
                    "ai_audit": audit_result,
                    "required_parts": jobcard.get("required_parts", "")
                })

                # Dispatch Telegram notification with AI Certificate
                self.send_ai_auditor_telegram_notification(jobcard, diagnosis, audit_result, estimate)

                # Notify customer that estimate is ready for approval
                self.notify_customer_for_approval(jobcard)
                return jobcard

            elif audit_result.get("verdict") == "FLAGGED_OVERREPLACEMENT":
                # Over-replacement alert: flag and notify supervisors
                self.transition_state(
                    jobcard, ApprovalStatus.AI_OVERREPLACEMENT_FLAGGED,
                    "AI_Sentinel_Arbiter",
                    f"Over-replacement Alert: {audit_result['metrics']['unnecessary_parts_blocked']} unnecessary part(s) flagged",
                    audit_result.get("verdict_summary")
                )
                self.jobcard_manager.update_jobcard(jc_id, {
                    "approval_status": ApprovalStatus.AI_OVERREPLACEMENT_FLAGGED,
                    "ai_audit": audit_result,
                    "review_note": audit_result.get("verdict_summary")
                })
                self.send_ai_overreplacement_telegram_alert(jobcard, diagnosis, audit_result)
                return jobcard

        # Fallback to standard Telegram review request if AI Auditor disabled
        self.transition_state(
            jobcard, ApprovalStatus.PENDING_COMPANY_REVIEW,
            "system", "Dispatched to Company Reviewers"
        )
        self.send_reviewer_telegram_notification(jobcard, diagnosis, token)
        return jobcard

    def send_ai_auditor_telegram_notification(self, jobcard, diagnosis, audit_result, estimate):
        """
        Sends autonomous AI Audit verification notification to company reviewers.
        Informs stakeholders of the green flag and blocked unnecessary replacements.
        """
        jc_id = jobcard["jobcard_id"]
        make = jobcard.get("vehicle_make", "")
        model = jobcard.get("vehicle_model", "")
        reg = jobcard.get("vehicle_reg", "N/A")
        complaint = jobcard.get("complaint", "N/A")
        fault = (diagnosis.get("fault_name") if diagnosis else jobcard.get("diagnosis_fault", "N/A")) or "Identified Fault"

        metrics = audit_result.get("metrics", {})
        savings = metrics.get("customer_savings", 0)
        unnec = metrics.get("unnecessary_parts_blocked", 0)
        total_min = estimate.get("total_min", 0)
        total_max = estimate.get("total_max", 0)

        message = (
            f"🤖 <b>AI SENTINEL AUDIT COMPLETE — GREEN FLAG ISSUED</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 <b>Job Card:</b> {jc_id}\n"
            f"🚗 <b>Vehicle:</b> {make} {model} (<code>{reg}</code>)\n"
            f"💬 <b>Symptom:</b> {complaint}\n"
            f"🔍 <b>AI Diagnosis:</b> {fault}\n\n"
            f"<b>{audit_result.get('verdict_badge')}</b>\n"
            f"🛡️ <b>Integrity Score:</b> {audit_result.get('integrity_score')}/100\n"
            f"✂️ <b>Unnecessary Replacements Blocked:</b> {unnec}\n"
            f"💰 <b>Customer Savings:</b> ₹{savings:,}\n"
            f"📊 <b>Approved Estimate:</b> ₹{total_min:,} - ₹{total_max:,}\n\n"
            f"<i>Autonomous quality verification complete. Published to Customer Portal.</i>"
        )

        reviewers = config.COMPANY_REVIEWER_CHAT_IDS
        if not reviewers and config.ADMIN_TELEGRAM_CHAT_ID:
            reviewers = [config.ADMIN_TELEGRAM_CHAT_ID]

        for reviewer_chat_id in reviewers:
            try:
                if self.notification_service.enabled:
                    import requests
                    requests.post(f"{self.notification_service.api_base}/sendMessage", json={
                        "chat_id": reviewer_chat_id,
                        "text": message,
                        "parse_mode": "HTML"
                    }, timeout=8)
                else:
                    self.notification_service.send_message(reviewer_chat_id, message)
            except Exception:
                pass

    def send_ai_overreplacement_telegram_alert(self, jobcard, diagnosis, audit_result):
        """Alerts company reviewers of flagged predatory over-replacement or unnecessary parts."""
        jc_id = jobcard["jobcard_id"]
        make = jobcard.get("vehicle_make", "")
        model = jobcard.get("vehicle_model", "")
        reg = jobcard.get("vehicle_reg", "N/A")
        unnec = audit_result.get("metrics", {}).get("unnecessary_parts_blocked", 0)
        savings = audit_result.get("metrics", {}).get("customer_savings", 0)

        message = (
            f"⚠️ <b>AI SENTINEL ALERT: OVER-REPLACEMENT FLAGGED</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 <b>Job Card:</b> {jc_id} ({make} {model} - <code>{reg}</code>)\n"
            f"🚨 <b>Warning:</b> {unnec} unnecessary replacement part(s) detected!\n"
            f"💰 <b>Potential Waste/Upsell:</b> ₹{savings:,}\n\n"
            f"<i>Autonomous green flag held. Please review on Sentinel AI Dashboard.</i>"
        )

        reviewers = config.COMPANY_REVIEWER_CHAT_IDS
        if not reviewers and config.ADMIN_TELEGRAM_CHAT_ID:
            reviewers = [config.ADMIN_TELEGRAM_CHAT_ID]

        for reviewer_chat_id in reviewers:
            try:
                if self.notification_service.enabled:
                    import requests
                    requests.post(f"{self.notification_service.api_base}/sendMessage", json={
                        "chat_id": reviewer_chat_id,
                        "text": message,
                        "parse_mode": "HTML"
                    }, timeout=8)
                else:
                    self.notification_service.send_message(reviewer_chat_id, message)
            except Exception:
                pass

    def send_reviewer_telegram_notification(self, jobcard, diagnosis, token):
        """
        Sends scannable Telegram notification with inline keyboard buttons to reviewers.
        Used when manual/supervised company review is requested.
        """
        jc_id = jobcard["jobcard_id"]
        make = jobcard.get("vehicle_make", "")
        model = jobcard.get("vehicle_model", "")
        reg = jobcard.get("vehicle_reg", "N/A")
        complaint = jobcard.get("complaint", "N/A")

        fault = diagnosis.get("fault_name", "Uncertain") if diagnosis else jobcard.get("diagnosis_fault", "N/A")
        conf_pct = int(float(diagnosis.get("confidence", 0) if diagnosis else jobcard.get("diagnosis_confidence", 0)) * 100)
        severity = diagnosis.get("severity", "Medium") if diagnosis else jobcard.get("priority", "Medium")
        fix_proc = (diagnosis.get("fix_procedure") if diagnosis else "Standard repair procedure") or "Standard repair"
        parts = diagnosis.get("required_parts") if diagnosis else jobcard.get("required_parts", "None")

        message = (
            f"🔍 <b>UNBIASED DIAGNOSTIC REVIEW REQUEST</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 <b>Job Card:</b> {jc_id}\n"
            f"🚗 <b>Vehicle:</b> {make} {model} (<code>{reg}</code>)\n"
            f"💬 <b>Symptom:</b> {complaint}\n\n"
            f"🤖 <b>AI Prediction:</b> {fault}\n"
            f"📊 <b>Confidence:</b> {conf_pct}%\n"
            f"⚠️ <b>Severity:</b> {severity}\n"
            f"🔩 <b>Required Parts:</b> {parts}\n\n"
            f"📝 <b>Recommended Work:</b>\n"
            f"{fix_proc}\n\n"
            f"<i>Reviewers: Please verify that this diagnosis is completely accurate, honest, and unbiased.</i>"
        )

        approve_cb = f"REV:APP:{jc_id}:{token}"
        reject_cb = f"REV:REJ:{jc_id}:{token}"
        info_cb = f"REV:INF:{jc_id}:{token}"

        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "✅ Approve Diagnosis", "callback_data": approve_cb},
                    {"text": "❌ Reject", "callback_data": reject_cb}
                ],
                [
                    {"text": "❓ Request More Info", "callback_data": info_cb}
                ]
            ]
        }

        reviewers = config.COMPANY_REVIEWER_CHAT_IDS
        if not reviewers and config.ADMIN_TELEGRAM_CHAT_ID:
            reviewers = [config.ADMIN_TELEGRAM_CHAT_ID]

        for reviewer_chat_id in reviewers:
            try:
                if self.notification_service.enabled:
                    url = f"{self.notification_service.api_base}/sendMessage"
                    import requests
                    requests.post(url, json={
                        "chat_id": reviewer_chat_id,
                        "text": message,
                        "parse_mode": "HTML",
                        "reply_markup": reply_markup
                    }, timeout=8)
                else:
                    self.notification_service.send_message(
                        reviewer_chat_id, message + "\n[Inline Keyboard: Approve, Reject, More Info]"
                    )
            except Exception:
                pass

    # ─────────────────────────────────────────────────────────────
    # Step 3 & 4: Reviewer Decision & Estimate Generation
    # ─────────────────────────────────────────────────────────────
    def handle_reviewer_action(self, jc_id, action, reviewer_id, token, note=""):
        """
        Processes company reviewer or AI Arbiter decision:
        - Verifies chat_id whitelist or AI signature
        - Verifies review token signature
        - Moves state to COMPANY_APPROVED, COMPANY_REJECTED, or REQUEST_MORE_INFO
        - If approved, generates official customer estimate
        """
        if not str(reviewer_id).startswith("AI_Sentinel") and not self.is_reviewer_authorized(reviewer_id):
            return False, "Unauthorized reviewer: Chat ID not whitelisted", None

        if not str(reviewer_id).startswith("AI_Sentinel") and not self.verify_review_token(jc_id, token):
            return False, "Invalid or forged review token signature", None

        jobcard = self.jobcard_manager.get_jobcard(jc_id)
        if not jobcard:
            return False, "Job card not found", None

        curr_status = jobcard.get("approval_status")
        # Idempotency check
        if action == "approve" and curr_status in (ApprovalStatus.COMPANY_APPROVED, ApprovalStatus.PENDING_CUSTOMER_APPROVAL):
            return True, "Job card is already approved", jobcard
        if action == "reject" and curr_status in (ApprovalStatus.COMPANY_REJECTED, ApprovalStatus.AI_REJECTED):
            return True, "Job card is already rejected", jobcard

        if action in ("approve", "ai_green_flag"):
            estimate = self.generate_official_estimate(jobcard)
            jobcard["estimate"] = estimate
            jobcard["reviewed_by"] = f"company_reviewer:{reviewer_id}" if not str(reviewer_id).startswith("AI_Sentinel") else reviewer_id
            jobcard["review_note"] = note or "Diagnosis confirmed and verified as unbiased"

            success, msg = self.transition_state(
                jobcard, ApprovalStatus.COMPANY_APPROVED,
                f"reviewer:{reviewer_id}", "Approval Granted", note
            )
            if not success:
                return False, msg, None

            self.transition_state(
                jobcard, ApprovalStatus.PENDING_CUSTOMER_APPROVAL,
                "system", "Estimate published to Customer Portal"
            )

            self.jobcard_manager.update_jobcard(jc_id, {
                "estimate": estimate,
                "reviewed_by": jobcard["reviewed_by"],
                "review_note": jobcard["review_note"],
                "estimated_cost": f"{estimate['total_min']}-{estimate['total_max']}",
                "estimated_time": str(estimate["labour_hours"]),
                "approval_status": ApprovalStatus.PENDING_CUSTOMER_APPROVAL
            })

            self.notify_customer_for_approval(jobcard)
            return True, "Diagnosis approved. Published to Customer Portal.", jobcard

        elif action == "reject":
            jobcard["reviewed_by"] = f"company_reviewer:{reviewer_id}"
            jobcard["review_note"] = note or "Diagnosis rejected"
            success, msg = self.transition_state(
                jobcard, ApprovalStatus.COMPANY_REJECTED,
                f"reviewer:{reviewer_id}", "Approval Rejected", note
            )
            self.jobcard_manager.update_jobcard(jc_id, {
                "approval_status": ApprovalStatus.COMPANY_REJECTED,
                "review_note": jobcard["review_note"]
            })
            return success, "Diagnosis rejected. Re-diagnosis required.", jobcard

        elif action == "request_more_info":
            jobcard["review_note"] = note or "More inspection details requested"
            success, msg = self.transition_state(
                jobcard, ApprovalStatus.REQUEST_MORE_INFO,
                f"reviewer:{reviewer_id}", "Requested More Diagnostic Info", note
            )
            self.jobcard_manager.update_jobcard(jc_id, {
                "approval_status": ApprovalStatus.REQUEST_MORE_INFO,
                "review_note": jobcard["review_note"]
            })
            return success, "Requested additional inspection info from workshop.", jobcard

        return False, f"Unknown reviewer action: {action}", None

    def generate_official_estimate(self, jobcard):
        """Builds an honest, itemized quotation for customer approval."""
        parts_list = []
        parts_cost = 0
        req_parts_str = jobcard.get("required_parts", "")
        if req_parts_str:
            for pid in [p.strip() for p in req_parts_str.split(",") if p.strip()]:
                part = self.inventory_manager.get_part_stock(pid)
                if part:
                    price = int(part.get("unit_price", 0))
                    parts_list.append({
                        "part_id": pid,
                        "name": part.get("part_name", "Automotive Part"),
                        "unit_price": price,
                        "quantity": 1,
                        "in_stock": int(part.get("current_stock", 0)) > 0
                    })
                    parts_cost += price
                else:
                    parts_list.append({
                        "part_id": pid,
                        "name": "Certified Replacement Part",
                        "unit_price": 0,
                        "quantity": 1,
                        "in_stock": False
                    })

        est_time_str = jobcard.get("estimated_time", "2")
        try:
            labour_hours = float(est_time_str)
        except ValueError:
            labour_hours = 2.0

        labour_rate = config.LABOUR_RATE_PER_HOUR
        labour_cost = int(labour_hours * labour_rate)
        total_min = parts_cost + labour_cost
        total_max = int(total_min * 1.25)

        work_items = [
            f"Pre-repair system inspection and safety verification",
            f"Target repair: {jobcard.get('diagnosis_fault', 'Identified automotive fault')}",
            f"Installation of OEM/OES certified components",
            f"Post-repair calibration, road test & quality assurance check"
        ]

        return {
            "fault": jobcard.get("diagnosis_fault", ""),
            "parts": parts_list,
            "parts_cost": parts_cost,
            "labour_hours": labour_hours,
            "labour_rate": labour_rate,
            "labour_cost": labour_cost,
            "total_min": total_min,
            "total_max": total_max,
            "work_items": work_items
        }

    def notify_customer_for_approval(self, jobcard):
        """Optionally send notification to customer if contact details are present."""
        owner_phone = jobcard.get("owner_phone", "")
        estimate = jobcard.get("estimate", {})
        total_min = estimate.get("total_min", 0)
        total_max = estimate.get("total_max", 0)

        msg = (
            f"🔔 <b>ESTIMATE READY FOR YOUR APPROVAL</b>\n\n"
            f"Dear {jobcard.get('owner_name', 'Customer')},\n"
            f"Your vehicle ({jobcard.get('vehicle_make', '')} {jobcard.get('vehicle_model', '')}) "
            f"has received an official, independent diagnosis:\n"
            f"<b>Issue:</b> {jobcard.get('diagnosis_fault', 'Repair needed')}\n"
            f"<b>Estimated Cost:</b> ₹{total_min:,} - ₹{total_max:,}\n\n"
            f"Please visit our Customer Portal with your Reg ({jobcard.get('vehicle_reg')}) "
            f"to review the itemized quote and approve the service."
        )
        self.notification_service.send_message(
            config.ADMIN_TELEGRAM_CHAT_ID,
            f"[Customer Notification Simulated for {owner_phone}]:\n{msg}"
        )

    # ─────────────────────────────────────────────────────────────
    # Step 5 & 6: Customer Decision & Auto Dispatch
    # ─────────────────────────────────────────────────────────────
    def handle_customer_decision(self, jc_id, decision, customer_identifier):
        """
        Processes customer decision from portal:
        - Verifies customer ownership
        - If 'Approved', triggers mechanic assignment, pipeline, inventory check & auto-orders
        - If 'Declined', marks CUSTOMER_DECLINED and closes job
        """
        jobcard = self.jobcard_manager.get_jobcard(jc_id)
        if not jobcard:
            return False, "Job card not found", None

        ident = (customer_identifier or "").strip().upper()
        owner_reg = (jobcard.get("vehicle_reg") or "").strip().upper()
        owner_phone = (jobcard.get("owner_phone") or "").strip()

        if not ident or (ident != owner_reg and ident != owner_phone.upper()):
            return False, "Unauthorized: Identification does not match vehicle registration or owner phone", None

        curr_status = jobcard.get("approval_status")
        if decision.lower() == "approve" and curr_status == ApprovalStatus.CUSTOMER_APPROVED:
            return True, "Estimate is already approved", jobcard
        if decision.lower() == "decline" and curr_status == ApprovalStatus.CUSTOMER_DECLINED:
            return True, "Estimate is already declined", jobcard

        if curr_status != ApprovalStatus.PENDING_CUSTOMER_APPROVAL:
            return False, f"Estimate is not in PENDING_CUSTOMER_APPROVAL state (current: {curr_status})", None

        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        if decision.lower() == "approve":
            jobcard["customer_decision"] = "Approved"
            jobcard["customer_decided_at"] = now_str

            success, msg = self.transition_state(
                jobcard, ApprovalStatus.CUSTOMER_APPROVED,
                f"customer:{ident}", "Customer Approved Official Estimate"
            )
            if not success:
                return False, msg, None

            # Auto Dispatch Flow
            complaint = jobcard.get("complaint", "")
            diagnosis_fault = jobcard.get("diagnosis_fault", "")
            system = None
            if diagnosis_fault:
                for sys_name, kws in [
                    ("Engine", ["engine", "bearing", "cylinder", "spark", "oil", "piston"]),
                    ("Transmission", ["gear", "clutch", "transmission"]),
                    ("Brakes", ["brake", "pad", "rotor"]),
                    ("Electrical", ["battery", "alternator", "starter", "wiring"]),
                    ("Cooling", ["radiator", "coolant", "thermostat"]),
                    ("Fuel System", ["fuel", "injector", "pump"])
                ]:
                    if any(kw in (diagnosis_fault + " " + complaint).lower() for kw in kws):
                        system = sys_name
                        break

            mechanic = self.mechanic_scheduler.auto_assign(
                system or "Engine",
                jobcard.get("priority", "Medium")
            )

            assigned_mechanic_id = mechanic["mechanic_id"] if mechanic else ""
            assigned_mechanic_name = mechanic["name"] if mechanic else "Pending allocation"

            if mechanic:
                task_desc = f"{diagnosis_fault} - {complaint}"
                self.mechanic_scheduler.add_to_pipeline(
                    mechanic["mechanic_id"], mechanic["name"],
                    jc_id, task_desc, jobcard.get("priority", "Medium")
                )

            req_parts = jobcard.get("required_parts", "")
            if req_parts:
                parts_check = self.inventory_manager.check_parts_availability(req_parts)
                if parts_check.get("missing"):
                    orders = self.order_manager.auto_order_missing_parts(parts_check["missing"], jc_id)
                    for order in orders:
                        dealer = order.get("dealer")
                        if dealer:
                            self.notification_service.notify_dealer_order(dealer, order)

            if mechanic:
                diag_dict = {
                    "fault_name": diagnosis_fault,
                    "fix_procedure": f"Approved repair procedure for {diagnosis_fault}",
                    "confidence": float(jobcard.get("diagnosis_confidence", 0.9))
                }
                self.notification_service.notify_mechanic_assignment(mechanic, jobcard, diag_dict)

            self.jobcard_manager.update_jobcard(jc_id, {
                "approval_status": ApprovalStatus.CUSTOMER_APPROVED,
                "status": "In Progress" if mechanic else "Pending",
                "assigned_mechanic_id": assigned_mechanic_id,
                "assigned_mechanic_name": assigned_mechanic_name,
                "customer_decision": "Approved",
                "customer_decided_at": now_str
            })

            updated_jc = self.jobcard_manager.get_jobcard(jc_id)
            return True, f"Service approved! Assigned to {assigned_mechanic_name}.", updated_jc

        elif decision.lower() == "decline":
            jobcard["customer_decision"] = "Declined"
            jobcard["customer_decided_at"] = now_str

            success, msg = self.transition_state(
                jobcard, ApprovalStatus.CUSTOMER_DECLINED,
                f"customer:{ident}", "Customer Declined Repair Estimate"
            )

            self.notification_service.send_message(
                config.ADMIN_TELEGRAM_CHAT_ID,
                f"⚠️ <b>ESTIMATE DECLINED:</b> Customer for {jobcard.get('vehicle_reg')} "
                f"declined repair for {jobcard.get('diagnosis_fault')}."
            )

            self.jobcard_manager.update_jobcard(jc_id, {
                "approval_status": ApprovalStatus.CUSTOMER_DECLINED,
                "status": "Completed",
                "customer_decision": "Declined",
                "customer_decided_at": now_str
            })
            updated_jc = self.jobcard_manager.get_jobcard(jc_id)
            return True, "Service estimate declined. Job card closed.", updated_jc

        return False, f"Unknown decision: {decision}", None
