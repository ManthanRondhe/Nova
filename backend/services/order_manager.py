"""
AutoMech AI - Order Manager
Auto-generates spare part orders linked to dealers.
"""
import csv, os
from datetime import datetime, timedelta

from database import db

class OrderManager:
    def __init__(self, data_dir):
        self.orders_file = "orders"
        self.dealers_file = "dealers"
        self.order_headers = ["order_id","part_id","part_name","quantity","dealer_id","dealer_name","jobcard_id","status","order_date","expected_delivery","actual_delivery","total_cost"]
        self.dealer_headers = ["dealer_id","name","phone","email","parts_category","location","delivery_time_days","rating","telegram_chat_id"]
    
    def _read_csv(self, file_key):
        if file_key == self.orders_file:
            return list(db.orders.find({}, {"_id": 0}))
        elif file_key == self.dealers_file:
            return list(db.dealers.find({}, {"_id": 0}))
        return []
    
    def _write_csv(self, file_key, headers, rows):
        if file_key == self.orders_file:
            db.orders.delete_many({})
            if rows:
                db.orders.insert_many([{**r} for r in rows])
        elif file_key == self.dealers_file:
            db.dealers.delete_many({})
            if rows:
                db.dealers.insert_many([{**r} for r in rows])
    
    # ─── Dealer CRUD ───
    
    def add_dealer(self, name, phone, email="", parts_category="General", location="", delivery_time_days=2, rating=4, telegram_chat_id=""):
        """Add a new spare part dealer."""
        rows = self._read_csv(self.dealers_file)
        next_id = f"D-{len(rows) + 1:03d}"
        
        dealer = {
            "dealer_id": next_id,
            "name": name,
            "phone": phone,
            "email": email,
            "parts_category": parts_category,
            "location": location,
            "delivery_time_days": str(delivery_time_days),
            "rating": str(rating),
            "telegram_chat_id": telegram_chat_id
        }
        rows.append(dealer)
        self._write_csv(self.dealers_file, self.dealer_headers, rows)
        return dealer
    
    def get_all_dealers(self):
        return self._read_csv(self.dealers_file)
    
    def get_dealer(self, dealer_id):
        rows = self._read_csv(self.dealers_file)
        for r in rows:
            if r["dealer_id"] == dealer_id:
                return r
        return None
    
    def update_dealer(self, dealer_id, updates):
        rows = self._read_csv(self.dealers_file)
        for r in rows:
            if r["dealer_id"] == dealer_id:
                for k, v in updates.items():
                    if k in self.dealer_headers:
                        r[k] = v
                self._write_csv(self.dealers_file, self.dealer_headers, rows)
                return r
        return None
    
    def delete_dealer(self, dealer_id):
        rows = self._read_csv(self.dealers_file)
        rows = [r for r in rows if r["dealer_id"] != dealer_id]
        self._write_csv(self.dealers_file, self.dealer_headers, rows)
        return True
    
    def find_best_dealer(self, part_category):
        """Find the best dealer for a part category (highest rating, fastest delivery)."""
        dealers = self._read_csv(self.dealers_file)
        matching = []
        
        for d in dealers:
            categories = d.get("parts_category", "").lower()
            if part_category.lower() in categories or "general" in categories:
                matching.append(d)
        
        if not matching:
            # Fallback to any dealer
            matching = dealers
        
        if not matching:
            return None
        
        # Sort by rating (desc), then delivery time (asc)
        matching.sort(key=lambda x: (-int(x.get("rating", 3)), int(x.get("delivery_time_days", 5))))
        return matching[0]
    
    # ─── Order Management ───
    
    def create_order(self, part_id, part_name, quantity, dealer_id, dealer_name, jobcard_id="", unit_price=0):
        """Create a new spare part order."""
        rows = self._read_csv(self.orders_file)
        next_id = f"ORD-{len(rows) + 1:04d}"
        now = datetime.now()
        
        # Estimate delivery based on dealer
        dealer = self.get_dealer(dealer_id)
        delivery_days = int(dealer.get("delivery_time_days", 3)) if dealer else 3
        expected = (now + timedelta(days=delivery_days)).strftime("%Y-%m-%d")
        
        order = {
            "order_id": next_id,
            "part_id": part_id,
            "part_name": part_name,
            "quantity": str(quantity),
            "dealer_id": dealer_id,
            "dealer_name": dealer_name,
            "jobcard_id": jobcard_id,
            "status": "Ordered",
            "order_date": now.strftime("%Y-%m-%d %H:%M:%S"),
            "expected_delivery": expected,
            "actual_delivery": "",
            "total_cost": str(unit_price * quantity)
        }
        rows.append(order)
        self._write_csv(self.orders_file, self.order_headers, rows)
        return order
    
    def auto_order_missing_parts(self, missing_parts, jobcard_id=""):
        """Auto-order all missing parts from best dealers."""
        orders = []
        for part in missing_parts:
            part_id = part.get("part_id", "")
            part_name = part.get("part_name", "Unknown")
            category = part.get("category", "General")
            unit_price = int(part.get("unit_price", 0))
            deficit = int(part.get("deficit", 2))
            
            dealer = self.find_best_dealer(category)
            if dealer:
                order = self.create_order(
                    part_id=part_id,
                    part_name=part_name,
                    quantity=max(deficit, 1),
                    dealer_id=dealer["dealer_id"],
                    dealer_name=dealer["name"],
                    jobcard_id=jobcard_id,
                    unit_price=unit_price
                )
                order["dealer"] = dealer
                orders.append(order)
        
        return orders
    
    def get_all_orders(self, status=None):
        rows = self._read_csv(self.orders_file)
        if status:
            rows = [r for r in rows if r.get("status","").lower() == status.lower()]
        return rows
    
    def update_order_status(self, order_id, status):
        rows = self._read_csv(self.orders_file)
        for r in rows:
            if r["order_id"] == order_id:
                r["status"] = status
                if status == "Delivered":
                    r["actual_delivery"] = datetime.now().strftime("%Y-%m-%d")
                self._write_csv(self.orders_file, self.order_headers, rows)
                return r
        return None
    
    def get_order_stats(self):
        rows = self._read_csv(self.orders_file)
        return {
            "total_orders": len(rows),
            "pending": len([r for r in rows if r.get("status") == "Ordered"]),
            "in_transit": len([r for r in rows if r.get("status") == "In Transit"]),
            "delivered": len([r for r in rows if r.get("status") == "Delivered"]),
            "total_value": sum(int(r.get("total_cost", 0)) for r in rows)
        }
