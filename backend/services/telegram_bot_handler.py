"""
Nova AI - Telegram Bot Webhook & Long Polling Reviewer Callback Handler
Processes Telegram callback queries and text messages from company reviewers for unbiased diagnostic approvals.
"""
import threading
import time
import requests
from config import config
from database import db


class TelegramBotHandler:
    def __init__(self, approval_workflow_service, notification_service):
        self.approval_service = approval_workflow_service
        self.notification_service = notification_service
        self._polling_thread = None
        self._stop_polling = False

    def start_polling(self):
        """Starts background long-polling thread to receive button clicks and messages."""
        if not self.notification_service.enabled:
            print("[Telegram] Bot disabled or no token, not starting poller.")
            return

        if self._polling_thread and self._polling_thread.is_alive():
            return

        self._stop_polling = False
        self._polling_thread = threading.Thread(target=self._poll_loop, daemon=True, name="TelegramBotPoller")
        self._polling_thread.start()
        print("[+] Telegram Bot Long Polling started in background thread.")

    def stop_polling(self):
        self._stop_polling = True

    def _poll_loop(self):
        """Continuously long-polls Telegram getUpdates for reviewer actions."""
        # Ensure webhook is cleared so getUpdates works
        try:
            requests.post(
                f"{self.notification_service.api_base}/deleteWebhook",
                json={"drop_pending_updates": False},
                timeout=5
            )
        except Exception:
            pass

        offset = 0
        while not self._stop_polling:
            try:
                url = f"{self.notification_service.api_base}/getUpdates"
                params = {
                    "offset": offset,
                    "timeout": 10,
                    "allowed_updates": '["message", "callback_query"]'
                }
                resp = requests.get(url, params=params, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("ok"):
                        for update in data.get("result", []):
                            offset = update["update_id"] + 1
                            try:
                                self.handle_update(update)
                            except Exception as e:
                                print(f"[Telegram] Error processing update: {e}")
                elif resp.status_code == 409:
                    time.sleep(3)
                else:
                    time.sleep(2)
            except requests.exceptions.Timeout:
                continue
            except Exception as e:
                time.sleep(2)

    def answer_callback_query(self, callback_query_id, text, show_alert=False):
        """Acknowledge Telegram callback query so client stops showing loading indicator."""
        if not self.notification_service.enabled or not callback_query_id:
            return
        try:
            url = f"{self.notification_service.api_base}/answerCallbackQuery"
            requests.post(url, json={
                "callback_query_id": callback_query_id,
                "text": text,
                "show_alert": show_alert
            }, timeout=5)
        except Exception:
            pass

    def edit_message_text(self, chat_id, message_id, new_text, reply_markup=None):
        """Update original message with confirmation of reviewer action."""
        if not self.notification_service.enabled:
            return
        try:
            url = f"{self.notification_service.api_base}/editMessageText"
            payload = {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": new_text,
                "parse_mode": "HTML"
            }
            if reply_markup is not None:
                payload["reply_markup"] = reply_markup
            resp = requests.post(url, json=payload, timeout=5)
            if resp.status_code != 200:
                # Retry without HTML formatting if parsing error occurred
                payload.pop("parse_mode", None)
                requests.post(url, json=payload, timeout=5)
        except Exception:
            pass

    def send_reply(self, chat_id, text):
        """Helper to send a text reply to a user."""
        if not self.notification_service.enabled:
            return
        try:
            url = f"{self.notification_service.api_base}/sendMessage"
            requests.post(url, json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML"
            }, timeout=5)
        except Exception:
            pass

    def handle_update(self, update: dict):
        """
        Process incoming Telegram update (from webhook or long polling).
        Handles both inline button callback queries and text commands.
        """
        # 1. Handle Inline Button Clicks
        if "callback_query" in update:
            return self._handle_callback_query(update["callback_query"])

        # 2. Handle Text Messages
        if "message" in update:
            return self._handle_text_message(update["message"])

        return {"status": "ignored", "reason": "Unsupported update type"}

    def _handle_callback_query(self, cb: dict):
        cb_id = cb.get("id")
        cb_data = cb.get("data", "")
        from_user = cb.get("from", {})
        chat_id = str(from_user.get("id", ""))
        message = cb.get("message", {})
        msg_id = message.get("message_id")

        if not cb_data.startswith("REV:"):
            self.answer_callback_query(cb_id, "Unknown action", show_alert=True)
            return {"status": "ignored", "reason": "Not a review callback"}

        parts = cb_data.split(":")
        if len(parts) != 4:
            self.answer_callback_query(cb_id, "Malformed callback data", show_alert=True)
            return {"status": "error", "reason": "Malformed callback payload"}

        _, action_code, jc_id, token = parts
        action_map = {
            "APP": "approve",
            "REJ": "reject",
            "INF": "request_more_info"
        }
        action = action_map.get(action_code)
        if not action:
            self.answer_callback_query(cb_id, "Invalid review action", show_alert=True)
            return {"status": "error", "reason": "Invalid action code"}

        # Authorize Reviewer
        if not self.approval_service.is_reviewer_authorized(chat_id):
            self.answer_callback_query(
                cb_id, "⛔ Access Denied: Your Telegram ID is not a whitelisted company reviewer.", show_alert=True
            )
            return {"status": "denied", "reason": "Chat ID not in reviewer whitelist"}

        # Execute Reviewer Decision
        success, msg, jobcard = self.approval_service.handle_reviewer_action(
            jc_id=jc_id,
            action=action,
            reviewer_id=chat_id,
            token=token,
            note=f"Reviewed via Telegram by {from_user.get('username') or from_user.get('first_name', chat_id)}"
        )

        if not success:
            self.answer_callback_query(cb_id, f"❌ {msg}", show_alert=True)
            return {"status": "error", "message": msg}

        # Acknowledge Telegram spinner
        self.answer_callback_query(cb_id, f"✅ Done: {msg}", show_alert=False)

        action_icons = {
            "approve": "✅ APPROVED BY COMPANY",
            "reject": "❌ REJECTED BY COMPANY",
            "request_more_info": "❓ MORE INFO REQUESTED"
        }
        orig_text = message.get("text", "")
        updated_text = (
            f"<b>[{action_icons.get(action, 'UPDATED')}]</b>\n\n"
            f"{orig_text}\n\n"
            f"<b>Reviewer:</b> {from_user.get('first_name', 'Reviewer')} (@{from_user.get('username', 'company')})\n"
            f"<b>Status:</b> {msg}"
        )
        self.edit_message_text(chat_id, msg_id, updated_text, reply_markup={"inline_keyboard": []})

        return {"status": "success", "action": action, "jobcard_id": jc_id, "message": msg}

    def _handle_text_message(self, message: dict):
        chat_id = str(message.get("chat", {}).get("id", ""))
        text = (message.get("text") or "").strip()
        from_user = message.get("from", {})

        if not text:
            return {"status": "ignored", "reason": "No text"}

        # /start command
        if text.lower().startswith("/start"):
            is_reviewer = self.approval_service.is_reviewer_authorized(chat_id)
            role_text = "<b>Authorized Company Executive Reviewer</b>" if is_reviewer else "Registered Mechanic / Garage Staff"
            welcome = (
                f"👋 <b>Welcome to AutoMech-AI (Nova AI)</b>\n\n"
                f"Your Chat ID: <code>{chat_id}</code>\n"
                f"Role: {role_text}\n\n"
                f"You will receive unbiased review notifications directly here with interactive Approve/Reject buttons."
            )
            self.send_reply(chat_id, welcome)
            return {"status": "handled", "command": "/start"}

        # Text-based approval: 'approve', 'approve JC-0011', 'reject', etc.
        text_lower = text.lower()
        if text_lower.startswith(("approve", "/approve", "reject", "/reject")):
            if not self.approval_service.is_reviewer_authorized(chat_id):
                self.send_reply(chat_id, "⛔ Access Denied: Your Telegram ID is not a whitelisted company reviewer.")
                return {"status": "denied"}

            action = "approve" if "approve" in text_lower else "reject"

            # Check if specific job card specified, else pick the latest pending one
            parts = text.split()
            target_jc_id = None
            for p in parts:
                if p.upper().startswith("JC-"):
                    target_jc_id = p.upper()
                    break

            if not target_jc_id:
                # Find most recent jobcard in PENDING_COMPANY_REVIEW
                pending_cards = list(db.jobcards.find({"approval_status": "PENDING_COMPANY_REVIEW"}, {"_id": 0}))
                if not pending_cards:
                    # Also check Pending status without approval_status
                    pending_cards = list(db.jobcards.find({"status": "Pending"}, {"_id": 0}))

                if pending_cards:
                    target_jc_id = pending_cards[-1]["jobcard_id"]

            if not target_jc_id:
                self.send_reply(chat_id, "ℹ️ No pending job cards awaiting review at this time.")
                return {"status": "not_found"}

            target_jc = self.approval_service.jobcard_manager.get_jobcard(target_jc_id)
            if not target_jc:
                self.send_reply(chat_id, f"❌ Job card {target_jc_id} not found.")
                return {"status": "not_found"}

            token = target_jc.get("review_token") or self.approval_service.generate_review_token(target_jc_id)

            success, msg, _ = self.approval_service.handle_reviewer_action(
                jc_id=target_jc_id,
                action=action,
                reviewer_id=chat_id,
                token=token,
                note=f"Text command '{text}' by {from_user.get('first_name', chat_id)}"
            )

            status_icon = "✅" if success else "❌"
            reply_msg = f"{status_icon} <b>Job Card {target_jc_id}:</b> {msg}"
            self.send_reply(chat_id, reply_msg)
            return {"status": "success" if success else "failed", "jobcard_id": target_jc_id}

        return {"status": "ignored", "reason": "Unrecognized message"}
