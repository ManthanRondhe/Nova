"""
Nova AI - Notification Service
Sends notifications to mechanics and dealers via Telegram Bot.
"""
import requests
import os
from config import config

class NotificationService:
    """Handles sending messages via Telegram Bot API."""
    
    def __init__(self):
        self.bot_token = config.TELEGRAM_BOT_TOKEN
        self.enabled = config.TELEGRAM_ENABLED
        self.api_base = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else ""
        self.notification_log = []  # Keep log for UI display
    
    def send_message(self, chat_id, message, parse_mode="HTML"):
        """Send a message via Telegram Bot."""
        result = {
            "chat_id": chat_id,
            "message": message,
            "status": "pending",
            "response": None
        }
        
        if self.enabled and chat_id:
            try:
                url = f"{self.api_base}/sendMessage"
                data = {
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": parse_mode
                }
                response = requests.post(url, data=data, timeout=10)
                if response.status_code == 200:
                    result["status"] = "sent"
                    result["response"] = response.json()
                else:
                    # Check for chat not found error and fallback to admin chat ID
                    resp_json = response.json()
                    if resp_json.get("description", "").startswith("Bad Request: chat not found"):
                        admin_chat = os.getenv("TELEGRAM_ADMIN_CHAT_ID")
                        if admin_chat:
                            data["chat_id"] = admin_chat
                            admin_resp = requests.post(url, data=data, timeout=10)
                            if admin_resp.status_code == 200:
                                result["status"] = "sent (admin fallback)"
                                result["response"] = admin_resp.json()
                            else:
                                result["status"] = "failed"
                                result["response"] = admin_resp.text
                        else:
                            result["status"] = "failed"
                            result["response"] = response.text
                    else:
                        result["status"] = "failed"
                        result["response"] = response.text
            except Exception as e:
                result["status"] = "error"
                result["response"] = str(e)
        else:
            result["status"] = "simulated"
            result["response"] = "Telegram not configured - message logged only"
        
        self.notification_log.append(result)
        # Keep only last 100 notifications
        if len(self.notification_log) > 100:
            self.notification_log = self.notification_log[-100:]
        
        return result
    
    def notify_mechanic_assignment(self, mechanic, jobcard, diagnosis=None):
        """Send job assignment notification to mechanic."""
        parts_text = jobcard.get("required_parts", "None specified")
        
        message = f"""🔧 <b>NEW JOB ASSIGNMENT — Nova AI</b>

📋 <b>Job Card:</b> {jobcard.get('jobcard_id', 'N/A')}
🚗 <b>Vehicle:</b> {jobcard.get('vehicle_make', '')} {jobcard.get('vehicle_model', '')} {jobcard.get('vehicle_year', '')}
🔖 <b>Reg No:</b> {jobcard.get('vehicle_reg', 'N/A')}
👤 <b>Owner:</b> {jobcard.get('owner_name', 'N/A')}

🔍 <b>Diagnosis:</b> {jobcard.get('diagnosis_fault', 'Pending inspection')}
📊 <b>Confidence:</b> {float(jobcard.get('diagnosis_confidence', 0)) * 100:.0f}%
⚠️ <b>Priority:</b> {jobcard.get('priority', 'Medium')}

💬 <b>Complaint:</b> {jobcard.get('complaint', 'N/A')}

📝 <b>Work Required:</b>
{diagnosis.get('fix_procedure', 'Inspect and diagnose') if diagnosis else 'Inspect and diagnose'}

🔩 <b>Parts:</b> {parts_text}
⏱️ <b>Est. Time:</b> {jobcard.get('estimated_time', 'N/A')} hours
💰 <b>Est. Cost:</b> ₹{jobcard.get('estimated_cost', 'N/A')}
🅿️ <b>Bay:</b> #{jobcard.get('bay_number', 'N/A')}

Reply /done {jobcard.get('jobcard_id', '')} when complete."""
        
        chat_id = mechanic.get("telegram_chat_id", "")
        return self.send_message(chat_id, message)
    
    def notify_dealer_order(self, dealer, order):
        """Send order notification to dealer."""
        message = f"""📦 <b>NEW PARTS ORDER — Nova AI</b>

🔖 <b>Order:</b> {order.get('order_id', 'N/A')}
🏭 <b>Part:</b> {order.get('part_name', 'N/A')} ({order.get('part_id', '')})
📊 <b>Quantity:</b> {order.get('quantity', 1)}
💰 <b>Total:</b> ₹{order.get('total_cost', '0')}

📋 <b>Job Card Ref:</b> {order.get('jobcard_id', 'Direct Order')}
📅 <b>Expected By:</b> {order.get('expected_delivery', 'ASAP')}

Please confirm availability and dispatch.
Reply /confirm {order.get('order_id', '')} to confirm."""
        
        chat_id = dealer.get("telegram_chat_id", "")
        return self.send_message(chat_id, message)
    
    def notify_job_completion(self, owner_phone, jobcard):
        """Notify vehicle owner about job completion."""
        message = f"""✅ <b>VEHICLE READY — Nova AI</b>

Your vehicle {jobcard.get('vehicle_make', '')} {jobcard.get('vehicle_model', '')} 
(Reg: {jobcard.get('vehicle_reg', '')}) has been serviced.

📋 Job Card: {jobcard.get('jobcard_id', '')}
🔧 Work Done: {jobcard.get('diagnosis_fault', 'Service completed')}
💰 Total Cost: ₹{jobcard.get('actual_cost', jobcard.get('estimated_cost', 'N/A'))}

Please collect your vehicle from the garage.
Thank you for choosing our service! 🙏"""
        
        # Owner notification - would need their Telegram chat_id
        return {"status": "simulated", "message": message, "phone": owner_phone}
    
    def get_notification_log(self, limit=50):
        """Get recent notification log."""
        return self.notification_log[-limit:]
    
    def get_telegram_bot_info(self):
        """Get bot info for verification."""
        if not self.enabled:
            return {"status": "not_configured", "message": "Set TELEGRAM_BOT_TOKEN environment variable"}
        
        try:
            response = requests.get(f"{self.api_base}/getMe", timeout=5)
            if response.status_code == 200:
                return {"status": "connected", "bot": response.json().get("result", {})}
            return {"status": "error", "message": response.text}
        except Exception as e:
            return {"status": "error", "message": str(e)}
